"""Build A New Editable Timeline In DaVinci Resolve Studio 21.1 Or Later."""

import argparse
import importlib
import json
import math
import os
import sys
import uuid
from pathlib import Path

# Resolve's Bundled Isolated Python Omits The Executed Script's Directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from resolve_native_plan import plan_timeline
from timeline import EditError, load, prepare


def require(condition, message):
    if not condition:
        raise EditError(message)
    return condition


def resolve_app():
    try:
        sdk = importlib.import_module("DaVinciResolveScript")
    except ImportError:
        root = os.getenv("RESOLVE_SCRIPT_API")
        if not root and os.name == "nt":
            root = Path(os.getenv("ProgramData", "C:/ProgramData")) / "Blackmagic Design/DaVinci Resolve/Support/Developer/Scripting"
        if not root:
            raise EditError("Use ResolvePython Or Set RESOLVE_SCRIPT_API To The Installed Scripting SDK.")
        sys.path.insert(0, str(Path(root) / "Modules"))
        sdk = importlib.import_module("DaVinciResolveScript")
    return require(sdk.scriptapp("Resolve"), "Open Resolve Studio And Enable Local External Scripting In Preferences.")


def frame_timecode(frame, fps):
    seconds, sub = divmod(frame, fps)
    hours, rem = divmod(seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{sub:02d}"


def near(actual, target, tolerance=.011):
    return actual is not None and math.isclose(float(actual), target, abs_tol=tolerance)


def checked_properties(item, properties):
    require(item.SetProperties(properties), f"Resolve Rejected Inspector Properties {list(properties)}.")
    actual = item.GetProperties()
    for key, value in properties.items():
        require(near(actual.get(key), value), f"Resolve Changed Inspector Property {key} From {value} To {actual.get(key)}.")


def fusion_input(tool, key, value):
    tool.SetInput(key, value)
    actual = tool.GetInput(key)
    if isinstance(value, (int, float)):
        good = near(actual, value, .0001)
    elif isinstance(value, dict):
        good = isinstance(actual, dict) and all(near(actual.get(k), v, .0001) for k, v in value.items())
    else:
        good = actual == value
    require(good, f"Resolve Could Not Apply Fusion Input {key}.")


def color_controls(item, values):
    if all(n == 1 for n in values.values()):
        return
    comp = require(item.AddFusionComp(), "Could Not Add The Editable Color Composition.")
    tool = require(comp.AddTool("Custom", -32768, -32768), "Could Not Create Fusion Color Controls.")
    require(tool.ConnectInput("Image1", comp.FindTool("MediaIn1")), "Could Not Connect The Source Picture.")
    # Match The Kit's Three Sequential RGB Operations, Including The Intermediate Clips.
    for idx, (name, channel) in enumerate(zip(("brightness", "contrast", "saturation"), "rgb"), 1):
        fusion_input(tool, f"NameforNumber{idx}", name.title())
        fusion_input(tool, f"NumberIn{idx}", values[name])
        fusion_input(tool, f"Intermediate{idx}", f"min(1,max(0,(min(1,max(0,{channel}1*n1))-0.5)*n2+0.5))")
    luma = "(0.213*i1+0.715*i2+0.072*i3)"
    for idx, channel in enumerate(("Red", "Green", "Blue"), 1):
        fusion_input(tool, channel+"Expression", f"min(1,max(0,i{idx}*n3+{luma}*(1-n3)))")
    fusion_input(tool, "AlphaExpression", "a1")
    require(comp.FindTool("MediaOut1").ConnectInput("Input", tool), "Could Not Connect The Color Output.")


def style_caption(item, cue, plan):
    comp = require(item.GetFusionCompByIndex(1), "The Text+ Clip Has No Fusion Composition.")
    text = next((v for v in comp.GetToolList().values() if v.GetAttrs().get("TOOLS_RegID") == "TextPlus"), None)
    require(text, "Could Not Find The Editable Text+ Node.")
    style = plan["caption_style"]
    margin, above = style["margin"]/100, style.get("top_margin", style["margin"])/100
    fusion_input(text, "StyledText", cue["text"])
    fusion_input(text, "Font", style["font"])
    fusion_input(text, "Style", "Bold")
    fusion_input(text, "Size", style["size"]/plan["width"])
    fusion_input(text, "LayoutType", 1)
    fusion_input(text, "LayoutWidth", .89)
    # The Layout Box Runs From The Bottom Margin To The Top Margin. Equal Margins Give The Centered Box Used Before.
    if cue["position"] == "center":
        above = margin
    fusion_input(text, "LayoutHeight", 1-margin-above)
    fusion_input(text, "Center", {1: .5, 2: .5+(margin-above)/2})
    text.SetInput("VerticalJustification"+cue["position"].title(), 1)
    alignment = {"top": -1, "center": 0, "bottom": 1}[cue["position"]]
    require(near(text.GetInput("VerticalTopCenterBottom"), alignment), "Resolve Could Not Align The Caption.")
    fusion_input(text, "Enabled2", int(style["stroke"] > 0))
    for idx, key in ((1, "color"), (2, "outline")):
        if idx == 2 and not style["stroke"]:
            continue
        if idx == 2:
            fusion_input(text, "ElementShape2", 1)
            fusion_input(text, "Thickness2", style["stroke"]/style["size"])
        for offset, channel in zip((1, 3, 5), ("Red", "Green", "Blue")):
            fusion_input(text, channel + str(idx), int(style[key][offset:offset+2], 16)/255)


def verify_placement(item, clip, at):
    expected = (at, clip["frames"], clip["kind"], clip["track"])
    actual = (item.GetStart(), item.GetDuration(), *item.GetTrackTypeAndIndex())
    require(actual == expected, f"Resolve Placement Mismatch For {clip['role']}. Expected {expected}. Received {actual}.")


class Assembly:
    def __init__(self, app, project, plan, bin_folder):
        self.app, self.project, self.plan = app, project, plan
        self.pool, self.folder = project.GetMediaPool(), bin_folder
        self.timeline = None
        self.sources = {}
        self.placed = []
        self.owned_media = set()

    def guard(self):
        live = self.app.GetProjectManager().GetCurrentProject()
        require(live and live.GetUniqueId() == self.project.GetUniqueId(), "The Active Resolve Project Changed.")
        if self.timeline:
            current = live.GetCurrentTimeline()
            require(current and current.GetUniqueId() == self.timeline.GetUniqueId(), "The Active Resolve Timeline Changed.")

    def setup(self, temp_name):
        self.guard()
        require(self.pool.SetCurrentFolder(self.folder), "Could Not Select The New Media Bin.")
        self.timeline = require(self.pool.CreateEmptyTimeline(temp_name), "Could Not Create A New Timeline.")
        tl, plan = self.timeline, self.plan
        require(self.project.SetCurrentTimeline(tl), "Could Not Activate The New Timeline.")
        self.owned_media.add(tl.GetMediaPoolItem().GetUniqueId())
        require(tl.SetSettings({"useCustomSettings": "1"}), "Could Not Enable Independent Timeline Settings.")
        require(tl.SetStartTimecode("00:00:00:00"), "Could Not Set The New Timeline Timecode.")
        settings = {"timelineFrameRate": plan["fps"], "timelineResolutionWidth": plan["width"],
                    "timelineResolutionHeight": plan["height"]}
        for key, value in settings.items():
            if not near(tl.GetSettings().get(key), value):
                require(tl.SetSettings({key: str(value)}), f"Resolve Rejected {key} At {value}.")
        if tl.GetSettings().get("timelinePixelAspectRatio") != "square":
            require(tl.SetSettings({"timelinePixelAspectRatio": "square"}), "Could Not Set Square Pixels.")
        actual = tl.GetSettings()
        require(all(near(actual.get(k), v) for k,v in settings.items()), "Resolve Changed The Requested Canvas Or Frame Rate.")
        self.base = tl.GetStartFrame()
        for kind, names in plan["tracks"].items():
            while tl.GetTrackCount(kind) > 1:
                require(tl.DeleteTrack(kind, tl.GetTrackCount(kind)), "Could Not Remove An Empty Default Track.")
            if kind == "audio":
                for _ in names[1:]:
                    require(tl.AddTrack("audio", "stereo"), "Could Not Create An Audio Track.")
                for idx, name in enumerate(names, 1):
                    require(tl.SetTrackName(kind, idx, name), f"Could Not Name Track {name}.")
        for key, asset in plan["assets"].items():
            self.guard()
            require(self.pool.GetCurrentFolder().GetUniqueId() == self.folder.GetUniqueId(), "The Selected Media Bin Changed.")
            path = str(Path(asset["path"]).resolve())
            imported = self.pool.ImportMedia([{"FilePath": path}]) or self.pool.ImportMedia([path])
            require(imported and len(imported) == 1, f"Could Not Import {path} As A Single Source.")
            media = imported[0]
            owned = {x.GetUniqueId() for x in self.folder.GetClipList()}
            require(media.GetUniqueId() in owned, "Resolve Returned A Source Outside The New Bin.")
            self.owned_media.add(media.GetUniqueId())
            require(Path(media.GetClipProperty("File Path")).resolve() == Path(path), f"Resolve Linked A Different File For {key}.")
            if asset["kind"] == "image" and not near(media.GetClipProperty("FPS"), plan["fps"]):
                require(media.SetClipProperty("FPS", str(plan["fps"])), "Could Not Set The Imported Still Frame Rate.")
            if asset["kind"] == "audio" and not near(media.GetClipProperty("FPS"), plan["fps"]):
                # Resolve Interprets Standalone Audio In The Project Frame Rate.
                # An Editable Full-Source Compound Gives It This Timeline's Clock.
                raw = self.append(media, {"kind": "audio", "track": 1, "at": 0, "role": "audio_source"})
                compound = require(tl.CreateCompoundClip([raw], {"name": key+" Audio Source", "startTimecode": "00:00:00:00"}),
                                   "Could Not Match The Sound Source Timebase.")
                media = require(compound.GetMediaPoolItem(), "Could Not Read The Native Audio Compound.")
                self.owned_media.add(media.GetUniqueId())
                require(near(media.GetClipProperty("FPS"), plan["fps"]), "The Native Audio Compound Has The Wrong Timebase.")
                require(tl.DeleteClips([compound], False), "Could Not Clear The Audio Staging Placement.")
            self.sources[key] = media

    def append(self, media, clip, **bounds):
        self.guard()
        result = self.pool.AppendToTimeline([dict(mediaPoolItem=media, trackIndex=clip["track"],
                    mediaType=1 if clip["kind"] == "video" else 2, recordFrame=self.base+clip["at"], **bounds)])
        require(result and len(result) == 1, f"Resolve Could Not Place {clip['role']} On Track {clip['track']}.")
        return result[0]

    def media_clip(self, clip):
        media = self.sources[clip["asset"]]
        if self.plan["assets"][clip["asset"]]["kind"] == "image":
            # Regular Source Bounds Are Ignored On Unmarked Stills. The Bin Owns This Copy.
            require(media.SetMarkInOut(0, clip["frames"] - 1, "video"), "Could Not Set Still Duration.")
            try:
                item = self.append(media, clip)
            finally:
                require(media.ClearMarkInOut("video"), "Could Not Clear Still Marks.")
        else:
            source_fps = float(media.GetClipProperty("FPS"))
            start = clip["source_in"] * source_fps
            end = clip["source_out"] * source_fps
            speed = clip["speed"]
            # Seed The Record Length, Then Retime In Place. A Ripple On An Audio
            # Item Can Otherwise Split A Picture Clip At The Same Timecode.
            raw_end = start + clip["frames"] * source_fps / self.plan["fps"]
            item = self.append(media, clip, startFrame=start, endFrame=raw_end)
            if speed != 1:
                ripple = item.GetDuration() != clip["frames"]
                if ripple:
                    # Slow Motion Close To EOF Can Need More Record Frames Than Available Source Frames.
                    require(self.timeline.DeleteClips([item], False), "Could Not Retry The Source Selection.")
                    item = self.append(media, clip, startFrame=start, endFrame=end)
                locked = []
                try:
                    if ripple:
                        for kind, names in self.plan["tracks"].items():
                            for lane in range(1, len(names)+1):
                                if (kind, lane) != (clip["kind"], clip["track"]) and not self.timeline.GetIsTrackLocked(kind, lane):
                                    require(self.timeline.SetTrackLock(kind, lane, True), "Could Not Protect Another Track During Retime.")
                                    locked.append((kind, lane))
                    require(item.SetSpeed({"Percentage": 100*speed, "PitchCorrection": True, "RippleTimeline": ripple}),
                            "Could Not Fit Native Retime To The Record Length.")
                finally:
                    for kind, lane in locked:
                        require(self.timeline.SetTrackLock(kind, lane, False), "Could Not Restore The Track Lock.")
                require(near(item.GetSpeed().get("Percentage"), 100*speed), "Resolve Returned A Different Clip Speed.")
            tol = max(1/source_fps, speed/self.plan["fps"]) + .001
            require(abs(item.GetSourceStartTime()-clip["source_in"]) <= tol and
                    abs(item.GetSourceEndTime()-clip["source_out"]) <= tol,
                    "Resolve Could Not Represent The Requested Source Range Within One Frame.")
        verify_placement(item, clip, self.base+clip["at"])
        if "transform" in clip:
            checked_properties(item, dict(Scaling=self.app.SCALE_FIT, **clip["transform"]))
        if "color" in clip:
            color_controls(item, clip["color"])
        if "gain" in clip:
            gain = clip["gain"]
            if gain == 0:
                require(item.SetClipEnabled(False) and not item.GetClipEnabled(), "Resolve Could Not Mute The Clip.")
            else:
                db = 20*math.log10(gain)
                require(db >= -100, "Resolve's Minimum Positive Clip Level Is -100 dB. Use Zero For True Mute.")
                checked_properties(item, {"AudioVolume": db})
        return item

    def caption(self, clip, idx, direct_lane):
        self.guard()
        tl, plan = self.timeline, self.plan
        # A Direct Text+ Insert Targets Resolve's Selected Track. For Overlap, Stage
        # A Native Text+ Beyond The Cut And Place Its Editable Compound On The Lower Lane.
        nested = clip["track"] != direct_lane
        at = plan["frames"] + plan["fps"] if nested else clip["at"]
        require(tl.SetMarkInOut(at, at+clip["frames"]-1, "video"), "Could Not Set The Title Range.")
        require(tl.SetCurrentTimecode(frame_timecode(self.base+at, plan["fps"])), "Could Not Position The Title.")
        title = require(tl.InsertFusionTitleIntoTimeline("Text+"), "Could Not Insert The Editable Text+ Title.")
        verify_placement(title, dict(clip, track=1), self.base+at)
        style_caption(title, clip, plan)
        name = f"Caption {idx:03d}"
        require(title.SetName(name), "Could Not Name The Title.")
        require(tl.ClearMarkInOut("video"), "Could Not Clear The Title Range.")
        if not nested:
            return title
        compound = require(tl.CreateCompoundClip([title], {"name": name+" Text", "startTimecode": "00:00:00:00"}),
                           "Could Not Create An Editable Nested Title.")
        source = require(compound.GetMediaPoolItem(), "Could Not Read The Nested Title.")
        self.owned_media.add(source.GetUniqueId())
        require(tl.DeleteClips([compound], False), "Could Not Remove The Temporary Title Placement.")
        return source

    def assemble(self):
        pairs = {}
        tl, tracks = self.timeline, self.plan["tracks"]["video"]
        captions = [c for c in self.plan["clips"] if c["role"] == "caption"]
        direct_lane = min((c["track"] for c in captions), default=1)
        nested = []
        # Resolve Inserts Text+ On V1 Of A Fresh Timeline. Populate It Before
        # Adding Lower Picture Tracks So The Main Caption Lane Stays Native.
        for idx, clip in enumerate(captions, 1):
            item = self.caption(clip, idx, direct_lane)
            if clip["track"] == direct_lane:
                self.placed.append((item, clip))
            else:
                nested.append((item, clip))
        for idx in range(2, len(tracks)+1):
            args = ("video", {"index": 1}) if idx <= direct_lane else ("video",)
            require(tl.AddTrack(*args), "Could Not Insert A Video Track.")
        for idx, name in enumerate(tracks, 1):
            require(tl.SetTrackName("video", idx, name), f"Could Not Name Track {name}.")
        for source, clip in nested:
            item = self.append(source, clip, startFrame=0, endFrame=clip["frames"])
            self.placed.append((item, clip))
        caption_lanes = sorted({c["track"] for c in captions})
        for lane in caption_lanes:
            require(tl.SetTrackLock("video", lane, True), "Could Not Protect The Caption Timing.")
        for clip in self.plan["clips"]:
            if clip["role"] == "caption":
                continue
            item = self.media_clip(clip)
            self.placed.append((item, clip))
            if clip["role"] == "picture":
                pairs[clip["shot"]] = item
            elif clip["role"] == "source_audio":
                require(self.timeline.SetClipsLinked([pairs[clip["shot"]], item], True), "Could Not Link Original Audio And Picture.")
        for lane in caption_lanes:
            require(tl.SetTrackLock("video", lane, False), "Could Not Unlock The Caption Track.")
        for item, clip in self.placed:
            verify_placement(item, clip, self.base+clip["at"])
        require(self.timeline.GetEndFrame()-self.base == self.plan["frames"], "The Final Timeline Duration Does Not Match.")
        require(self.timeline.SetCurrentTimecode(frame_timecode(self.base, self.plan["fps"])), "Could Not Cue The Timeline For Review.")


def build(app, plan, project_name, timeline_name):
    require(project_name.strip() and timeline_name.strip(), "Supply A Project Name And A New Timeline Name.")
    require(tuple(app.GetVersion()[:2]) >= (21, 1), "Native Assembly Requires DaVinci Resolve 21.1 Or Later.")
    manager = app.GetProjectManager()
    project = manager.GetCurrentProject()
    require(project and project.GetName() == project_name, "Open The Named Destination Project Before Building.")
    def check_name():
        names = [project.GetTimelineByIndex(i).GetName().casefold() for i in range(1, project.GetTimelineCount()+1)]
        require(timeline_name.casefold() not in names, "That Timeline Already Exists. Choose A New Revision Name.")
    check_name()
    pool = project.GetMediaPool()
    original, previous_folder = project.GetCurrentTimeline(), pool.GetCurrentFolder()
    token = uuid.uuid4().hex[:12]
    bin_name = f"{timeline_name} Sources {token}"
    folder = require(pool.AddSubFolder(pool.GetRootFolder(), bin_name), "Could Not Create A Private Source Bin.")
    assembly = Assembly(app, project, plan, folder)
    try:
        assembly.setup("Building Social Cut " + token)
        assembly.assemble()
        assembly.guard()
        check_name()
        require(assembly.timeline.SetName(timeline_name), "Could Not Publish The New Timeline Name.")
        require(manager.SaveProject(), "Resolve Could Not Save The Project.")
    except BaseException as error:
        live = manager.GetCurrentProject()
        if not live or live.GetUniqueId() != project.GetUniqueId():
            raise EditError(f"{error} The Destination Project Changed. Its Staging Bin Is {bin_name}.") from error
        selected = project.GetCurrentTimeline()
        restore_timeline = assembly.timeline and selected and selected.GetUniqueId() == assembly.timeline.GetUniqueId()
        failed = []
        if assembly.timeline and not pool.DeleteTimelines([assembly.timeline]):
            failed.append(assembly.timeline.GetName())
        if not failed:
            unknown_media = {m.GetUniqueId() for m in folder.GetClipList()} - assembly.owned_media
            if unknown_media or folder.GetSubFolderList() or not pool.DeleteFolders([folder]):
                failed.append(bin_name)
        if original and restore_timeline:
            project.SetCurrentTimeline(original)
        pool.SetCurrentFolder(previous_folder)
        if failed:
            raise EditError(f"{error} Resolve Could Not Remove This Run's Staging Items: {failed}.") from error
        raise
    pool.SetCurrentFolder(previous_folder)
    return {"project": project_name, "timeline": timeline_name, "timeline_id": assembly.timeline.GetUniqueId(),
            "edition": app.GetProductName(), "version": app.GetVersionString(), "clips": len(assembly.placed),
            "frames": plan["frames"], "source_bin": bin_name}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("timeline", type=Path)
    parser.add_argument("--project", help="Exact Open Resolve Project Name")
    parser.add_argument("--name", help="New Timeline Name")
    parser.add_argument("--dry-run", action="store_true", help="Print The Native Plan Without Connecting To Resolve")
    args = parser.parse_args()
    if not args.dry_run and not (args.project and args.name):
        parser.error("Supply --project And --name For A Live Build.")
    try:
        path = args.timeline.resolve(strict=True)
        plan = plan_timeline(prepare(load(path), path.parent))
        result = plan if args.dry_run else build(resolve_app(), plan, args.project, args.name)
        print(json.dumps(result, indent=2, ensure_ascii=True))
    except (EditError, OSError, ImportError, ValueError, TypeError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
