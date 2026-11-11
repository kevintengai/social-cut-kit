"""Project Validation, Source Inspection, And Editable Interchange."""

import json
import math
import os
import re
import shutil
import subprocess
from pathlib import Path


class EditError(Exception):
    pass


def binary(name):
    path = shutil.which(name)
    if not path:
        raise EditError(f"Install {name} And Add It To PATH.")
    return path


def run(args):
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise EditError(result.stderr.strip()[-4000:] or "Media Command Failed.")
    return result


HDR_TRANSFERS = {"smpte2084": "pq", "arib-std-b67": "hlg"}
HDR_NAMES = {"pq": "PQ", "hlg": "HLG"}


def rotation(video):
    # Clockwise Degrees Applied For Display. FFprobe Reports The Display Matrix Counterclockwise.
    for side in video.get("side_data_list") or []:
        if isinstance(side, dict) and "rotation" in side:
            try:
                return round(-float(side["rotation"])) % 360
            except (TypeError, ValueError):
                break
    try:
        return round(float((video.get("tags") or {}).get("rotate", 0))) % 360
    except (TypeError, ValueError):
        return 0


def fraction(value):
    try:
        if isinstance(value, str) and re.search(r"[:/]", value):
            top, bottom = re.split(r"[:/]", value, maxsplit=1)
            return float(top) / float(bottom)
        return float(value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def bit_depth(video):
    raw = str(video.get("bits_per_raw_sample") or "")
    if raw.isdigit() and int(raw):
        return int(raw)
    name = str(video.get("pix_fmt") or "").lower()
    if "f32" in name:
        return 32
    if "f16" in name or re.search(r"(48|64)(le|be)?$", name):
        return 16
    # Semi-Planar Names Such As nv12 End In A Layout Number, Not A Depth.
    match = None if name.startswith("nv") else re.search(r"(9|1[0246])(le|be)?$", name)
    return int(match[1]) if match else 8


def picture_info(video):
    """Displayed Geometry, Bit Depth, And Color Signalling For One Picture Stream."""
    if not video:
        return None
    turn = rotation(video)
    width, height = video.get("width"), video.get("height")
    shown = None
    if isinstance(width, int) and isinstance(height, int):
        sar = fraction(video.get("sample_aspect_ratio")) or 1
        shown = [max(1, round(width * sar)), height]
        if round(turn / 90) % 2:
            shown.reverse()

    def named(key):
        value = video.get(key)
        return value if isinstance(value, str) and value not in ("", "unknown") else "unspecified"

    transfer = named("color_transfer")
    light = mastering = dolby = None
    for side in video.get("side_data_list") or []:
        if not isinstance(side, dict):
            continue
        kind = str(side.get("side_data_type", "")).lower()
        if "content light" in kind:
            light = fraction(side.get("max_content")) or light
        elif "mastering display" in kind:
            mastering = fraction(side.get("max_luminance")) or mastering
        elif "dovi" in kind or "dolby vision" in kind:
            dolby = {"profile": side.get("dv_profile"), "level": side.get("dv_level"),
                     "compatibility": side.get("dv_bl_signal_compatibility_id")}
    # The Content Light Level Describes The Programme. The Mastering Display Is The Fallback.
    peak = light or mastering
    rate = fraction(video.get("avg_frame_rate")) or fraction(video.get("r_frame_rate"))
    return {"codec": video.get("codec_name"), "pixel_format": video.get("pix_fmt"), "bit_depth": bit_depth(video),
            "coded_size": [width, height], "displayed_size": shown, "rotation": turn,
            "frame_rate": round(rate, 4) if rate else None,
            "color_transfer": transfer, "color_primaries": named("color_primaries"),
            "color_space": named("color_space"), "color_range": named("color_range"),
            "hdr": HDR_TRANSFERS.get(transfer), "peak_nits": peak, "dolby_vision": dolby}


STANDARD_RATES = (24, 25, 30, 48, 50, 60, 100, 120)
CANVAS_RATE_RULE = ("Take The Standard Rate Nearest The Main Source, From 24, 25, 30, 48, 50, 60, 100, And 120, And "
                    "Halve It While It Is Above 30. Keep A Higher Rate Only When The Owner Asks For 50 Or 60 FPS "
                    "Delivery.")


def nearest_standard_rate(rate):
    # A Source Exactly Between Two Standard Rates Takes The Higher One.
    return min(STANDARD_RATES, key=lambda standard: (abs(standard - rate), -standard))


def canvas_rate(rate):
    """The Canvas Rate For A Source Rate: The Nearest Standard Rate, Halved While It Is Above 30."""
    if type(rate) not in (int, float) or not math.isfinite(rate) or rate <= 0:
        return 30
    chosen = nearest_standard_rate(rate)
    while chosen > 30:
        chosen //= 2
    return chosen


def still_image(meta):
    return bool(re.search(r"image2|_pipe", meta.get("format") or ""))


def rate_text(rate):
    return f"{rate:.3f}".rstrip("0").rstrip(".")


def canvas_rate_hint(meta):
    """A Suggested Canvas Rate For One Source, Or None When It Has No Moving Picture."""
    rate = (meta.get("picture") or {}).get("frame_rate")
    if not rate or still_image(meta):
        return None
    suggested, nearest = canvas_rate(rate), nearest_standard_rate(rate)
    if suggested == nearest:
        reason = f"{suggested} Is The Standard Rate Nearest The Source Rate Of {rate_text(rate)} FPS."
    else:
        reason = (f"The Standard Rate Nearest The Source Rate Of {rate_text(rate)} FPS Is {nearest}, Which Is Above 30, So "
                  f"It Is Halved To {suggested}.")
    return {"suggested": suggested, "source_fps": rate, "reason": reason, "rule": CANVAS_RATE_RULE}


BROWSER_VIDEO = {"h264", "vp8", "vp9", "av1"}
BROWSER_AUDIO = {"aac", "mp3", "opus", "vorbis", "flac"}
BROWSER_IMAGE = {"png", "mjpeg", "webp", "gif", "bmp", "apng"}
WORKING_COPY_ADVICE = ("Ask The Owner Once, Then Make A Working Copy With The Working Copy Command And Name It In "
                       "The Asset's working_copy Field. The Browser Editor And Remotion Then Play The Working Copy. "
                       "The Checks And The FFmpeg Render Keep Reading The Original.")


def browser_playback(meta):
    """Whether A Common Desktop Browser Is Likely To Play This Source, With Plain Reasons When It Is Not."""
    video, audio, info = meta.get("video"), meta.get("audio"), meta.get("picture") or {}
    reasons = []
    if video and still_image(meta):
        if video.get("codec_name") not in BROWSER_IMAGE:
            reasons.append(f"Browsers Do Not Draw {video.get('codec_name')} Images. Convert It To PNG Or JPEG.")
        return {"likely": not reasons, "reasons": reasons}
    if video:
        codec = video.get("codec_name")
        if codec == "hevc":
            reasons.append("HEVC Video Plays In A Browser Only Where The Computer Has Hardware Support For It.")
        elif codec and codec not in BROWSER_VIDEO:
            reasons.append(f"Browsers Do Not Play {codec} Video.")
        elif (info.get("bit_depth") or 8) > 8 and codec == "h264":
            reasons.append(f"Browsers Rarely Play {info['bit_depth']}-Bit H.264 Video.")
        if info.get("hdr"):
            reasons.append(f"The Picture Is {HDR_NAMES[info['hdr']]} HDR. A Browser Shows Its Own Conversion, Or A "
                           "Flat Picture, And Not The Kit's Conversion.")
        size, rate = info.get("coded_size") or [0, 0], info.get("frame_rate") or 0
        if all(isinstance(n, int) for n in size) and size[0] * size[1] > 2560 * 1440 and rate > 31:
            reasons.append(f"{size[0]} By {size[1]} At {rate_text(rate)} FPS Is Heavy For Live Browser Playback And May Stutter.")
    if audio:
        codec = str(audio.get("codec_name") or "")
        if codec and codec not in BROWSER_AUDIO and not codec.startswith("pcm_"):
            reasons.append(f"Browsers Do Not Play {codec} Sound.")
    if not re.search(r"mp4|mov|m4a|webm|matroska|ogg|wav|mp3|flac", meta.get("format") or ""):
        reasons.append(f"Browsers Do Not Open A {meta.get('format') or 'Unknown'} File.")
    report = {"likely": not reasons, "reasons": reasons}
    if reasons and video:
        report["advice"] = WORKING_COPY_ADVICE
    return report


def playback_warnings(assets, uses):
    """One Note For Each Video In Use That A Browser Is Unlikely To Play And That Has No Working Copy Yet."""
    notes = []
    for key in uses:
        item = assets[key]
        if item["kind"] != "video" or item.get("working_copy"):
            continue
        playback = browser_playback(item)
        if not playback["likely"]:
            notes.append(f"Asset {key} Is Unlikely To Play In The Browser Editor Or In Remotion Studio. "
                         f"{' '.join(playback['reasons'])} {WORKING_COPY_ADVICE}")
    return notes


def frame_total(video):
    frames = str((video or {}).get("nb_frames") or "")
    return int(frames) if frames.isdigit() else None


def working_copy_notes(key, original, copy):
    """Plain Notes About One Working Copy: Where It Is Used, And Any Disagreement With Its Original."""
    notes = [f"Asset {key} Plays From Its Working Copy In The Browser Editor And In Remotion. Check, Still, "
             "Loudness, Mix, And Render Read The Original."]
    first, second = original.get("picture") or {}, copy.get("picture") or {}
    rate = first.get("frame_rate") or 30
    a, b = original.get("duration"), copy.get("duration")
    if a is not None and b is not None and abs(a - b) > max(0.05, 1 / rate):
        notes.append(f"Asset {key} Working Copy Lasts {b:.3f} Seconds And Its Original Lasts {a:.3f} Seconds. "
                     "Review Timing May Not Match The Render. Make A Fresh Working Copy.")
    a, b = frame_total(original.get("video")), frame_total(copy.get("video"))
    if a is not None and b is not None and abs(a - b) > 1:
        notes.append(f"Asset {key} Working Copy Has {b} Frames And Its Original Has {a}. Frames Seen In Review "
                     "May Not Be The Frames Rendered. Make A Fresh Working Copy.")
    a, b = first.get("displayed_size"), second.get("displayed_size")
    if a and b and abs(a[0] / a[1] - b[0] / b[1]) > 0.01 * a[0] / a[1]:
        notes.append(f"Asset {key} Working Copy Is {b[0]} By {b[1]} And Its Original Displays At {a[0]} By {a[1]}. "
                     "The Shapes Differ, So Framing In Review Will Not Match The Render.")
    if second.get("hdr"):
        notes.append(f"Asset {key} Working Copy Is Itself {HDR_NAMES[second['hdr']]} HDR. Make It With The "
                     "Working Copy Command So It Carries The Kit's Conversion.")
    if second.get("rotation"):
        notes.append(f"Asset {key} Working Copy Carries A {second['rotation']} Degree Display Rotation. A Working "
                     "Copy Must Be Stored Upright.")
    playback = browser_playback(copy)
    if not playback["likely"]:
        notes.append(f"Asset {key} Working Copy May Not Play In A Browser. {' '.join(playback['reasons'])}")
    return notes


def probe(path):
    args = [binary("ffprobe"), "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)]
    data = json.loads(run(args).stdout)
    streams = data.get("streams", [])
    video = next((s for s in streams if s["codec_type"] == "video" and not s.get("disposition", {}).get("attached_pic")), None)
    audio = next((s for s in streams if s["codec_type"] == "audio"), None)
    duration = data["format"].get("duration")
    return {"duration": float(duration) if duration and duration != "N/A" else None,
            "video": video, "audio": audio, "format": data["format"].get("format_name", ""),
            "picture": picture_info(video)}


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (ValueError, OSError) as exc:
        raise EditError(f"Cannot Read Project {path}. {exc}") from exc


def write_new(path, content):
    with path.open("x", encoding="utf-8", newline="\n") as output:
        output.write(content)


def number(value, name, minimum=0, maximum=86400):
    if type(value) not in (int, float) or not math.isfinite(value) or not minimum <= value <= maximum:
        raise EditError(f"{name} Must Be A Number Between {minimum} And {maximum}.")
    return value


def integer(value, name, minimum, maximum):
    if type(value) is not int:
        raise EditError(f"{name} Requires A Whole Number.")
    return number(value, name, minimum, maximum)


def fields(item, allowed, name):
    if not isinstance(item, dict):
        raise EditError(f"{name} Requires An Object.")
    unknown = set(item) - set(allowed.split())
    if unknown:
        raise EditError(f"Unknown {name} Field {sorted(unknown)[0]}.")


def word(value, name):
    if not isinstance(value, str) or not value.strip():
        raise EditError(f"{name} Requires Text.")
    return value


def choice(value, options, name):
    if value not in options:
        raise EditError(f"Unsupported {name} Value {value}.")
    return value


def flag(value, name):
    if type(value) is not bool:
        raise EditError(f"{name} Requires true Or false.")
    return value


def collection(obj, key):
    items = obj.get(key, [])
    if not isinstance(items, list) or not all(isinstance(x, dict) for x in items):
        raise EditError(f"{key} Requires A List Of Objects.")
    return items


def framing(video, w, h, fit, zoom, pan_x, pan_y):
    sw, sh = video.get("width", w), video.get("height", h)
    aspect = video.get("sample_aspect_ratio") or "1:1"
    ratio = re.fullmatch(r"(\d+):(\d+)", aspect)
    sar = int(ratio[1]) / int(ratio[2]) if ratio and int(ratio[1]) and int(ratio[2]) else 1
    # FFmpeg Rotates Decoded Frames To Their Displayed Orientation Before Any Filter Runs.
    if round(rotation(video)/90) % 2:
        sw, sh, sar = sh, sw, 1/sar
    size = max if fit == "cover" else min
    scale = size(w/(sw*sar), h/sh) * zoom
    draw_w, draw_h = sw*sar*scale, sh*scale
    anchor_x, anchor_y = (pan_x+1)/2, (pan_y+1)/2
    crop_w, crop_h = min(sw, max(1,round(sw*w/draw_w))), min(sh,max(1,round(sh*h/draw_h)))
    visible_w = min(w, max(2,2*round(draw_w/2)))
    visible_h = min(h, max(2,2*round(draw_h/2)))
    return {"crop": [crop_w,crop_h,round((sw-crop_w)*anchor_x),round((sh-crop_h)*anchor_y)],
            "scale": [visible_w,visible_h],
            "pad": [round((w-visible_w)*anchor_x),round((h-visible_h)*anchor_y)],
            "browser": [(w-draw_w)*anchor_x/w,(h-draw_h)*anchor_y/h,draw_w/w,draw_h/h]}


# Caption Defaults For A Vertical Canvas, Where The Platform Draws Its Own Controls Over The Video.
# The Size Is A Share Of The Canvas Width. Each Margin Is A Percentage Of The Canvas Height.
VERTICAL_CAPTIONS = {"size": 0.06, "margin": 25, "top_margin": 12}
HORIZONTAL_MARGIN = 7


def vertical(w, h):
    return h > w


def caption_style(doc, w, h):
    style = doc.get("caption_style", {})
    fields(style, "font size color outline stroke margin top_margin", "Caption Style")
    font = choice(style.get("font", "Arial"), ("Arial","Georgia","Verdana","Tahoma","Trebuchet MS"), "Caption Font")
    def color(key, default):
        value = style.get(key, default)
        if not isinstance(value,str) or not re.fullmatch(r"#[0-9a-fA-F]{6}",value):
            raise EditError(f"{key} Requires A Six-Digit Hex Color.")
        return value
    tall = vertical(w, h)
    usual = round(w * VERTICAL_CAPTIONS["size"]) if tall else round(min(h*.078,w*.085))
    size = integer(style.get("size",max(12,usual)), "Caption Size", 4, 1024)
    margin = number(style.get("margin",VERTICAL_CAPTIONS["margin"] if tall else HORIZONTAL_MARGIN),"Caption Margin",0,45)
    # A Timeline That Sets Its Own Margin Keeps One Margin For Both Edges, As Before.
    above = margin if "margin" in style else (VERTICAL_CAPTIONS["top_margin"] if tall else HORIZONTAL_MARGIN)
    return {"font":font, "size":size, "color":color("color","#FFFFFF"), "outline":color("outline","#101010"),
            "stroke":number(style.get("stroke",max(1,round(size*.07))),"Caption Stroke",0,96),
            "margin":margin, "top_margin":number(style.get("top_margin",above),"Caption Top Margin",0,45)}


def source_warnings(assets, uses):
    """Plain Notes About HDR And Rotated Sources For Validation Output."""
    notes = []
    for key, places in uses.items():
        info = assets[key].get("picture") or {}
        hdr, dolby = info.get("hdr"), info.get("dolby_vision") or {}
        if hdr:
            extra = f" With Dolby Vision Profile {dolby['profile']}" if dolby.get("profile") is not None else ""
            label = (f"Asset {key} Is {HDR_NAMES[hdr]} HDR{extra} "
                     f"({info['color_primaries']} Primaries, {info['bit_depth']}-Bit).")
            on = ", ".join(name for name, tone in places if tone)
            off = ", ".join(name for name, tone in places if not tone)
            if on:
                converted = assets[key].get("working_copy") and not assets[key].get("working_copy_hdr")
                shown = ("The Browser Editor And Remotion Play The Working Copy, Which Already Carries That "
                         "Conversion." if converted else "The Browser Player Shows Its Own Conversion.")
                notes.append(f"{label} Tone Mapping Converts {on} To Standard Dynamic Range Once In Check, Still, "
                             f"And Render. {shown}")
            if off:
                notes.append(f"{label} Tone Mapping Is Off For {off}. That Picture Passes Through Unconverted "
                             "And Can Look Flat.")
        elif dolby.get("profile") == 5:
            notes.append(f"Asset {key} Is Dolby Vision Profile 5 Without A Standard Base Layer. The Kit Cannot "
                         "Convert Its Colors. Use A Version Recorded Or Converted As HLG, HDR10, Or SDR.")
        elif info.get("color_primaries") == "bt2020":
            notes.append(f"Asset {key} Has bt2020 Primaries Without A PQ Or HLG Transfer "
                         f"({info['color_transfer']}). The Kit Leaves Its Colors Unconverted. Confirm How It "
                         "Was Recorded If It Looks Flat.")
        turn = info.get("rotation") or 0
        if turn % 90:
            notes.append(f"Asset {key} Has A {turn} Degree Display Rotation. Only Right-Angle Rotations Are "
                         "Framed Correctly.")
        elif turn and info.get("displayed_size"):
            stored, shown = info["coded_size"], info["displayed_size"]
            notes.append(f"Asset {key} Is Stored {stored[0]} By {stored[1]} With A {turn} Degree Display Rotation. "
                         f"Framing, Crop, And Pan Use The Displayed {shown[0]} By {shown[1]} Picture.")
    return notes


def prepare(doc, root):
    fields(doc, "version title canvas assets shots overlays captions audio caption_style", "Project")
    if type(doc.get("version")) is not int or doc["version"] != 1:
        raise EditError("Set Project Version To 1.")
    title = word(doc.get("title"), "Title")
    canvas = doc.get("canvas", {})
    fields(canvas, "width height fps fit tone_map", "Canvas")
    w = integer(canvas.get("width", 1080), "Width", 16, 8192)
    h = integer(canvas.get("height", 1920), "Height", 16, 8192)
    if w % 2 or h % 2:
        raise EditError("Canvas Dimensions Must Be Even.")
    fps = integer(canvas.get("fps", 30), "FPS", 1, 120)
    fit = choice(canvas.get("fit", "contain"), ("contain", "cover"), "Fit")
    tone_default = flag(canvas.get("tone_map", True), "Canvas Tone Map")
    assets, uses, copies = {}, {}, []
    if not isinstance(doc.get("assets"), dict):
        raise EditError("Assets Requires A Named Object.")
    for key, obj in doc["assets"].items():
        word(key, "Asset Name")
        fields(obj, "path kind working_copy", "Asset")
        path = (root / word(obj.get("path"), "Asset Path")).resolve()
        if not path.is_file():
            raise EditError(f"Missing Asset {path}.")
        kind = choice(obj.get("kind"), ("video", "image", "audio"), "Asset Kind")
        meta = probe(path)
        stream = meta["audio" if kind == "audio" else "video"]
        if not stream:
            raise EditError(f"Missing {kind} Stream In {path}.")
        assets[key] = dict(meta, path=str(path), kind=kind)
        if "working_copy" in obj:
            # The Original Stays The Source For Every Check And For The Render. Only Review Players Use The Copy.
            if kind != "video":
                raise EditError("Only A Video Asset Can Name A Working Copy.")
            copy = (root / word(obj["working_copy"], "Working Copy Path")).resolve()
            if copy == path:
                raise EditError(f"The Working Copy Of {key} Must Be A Different File From Its Original.")
            if not copy.is_file():
                raise EditError(f"Missing Working Copy {copy}.")
            twin = probe(copy)
            if not twin["video"]:
                raise EditError(f"Missing Video Stream In {copy}.")
            assets[key]["working_copy"] = str(copy)
            if (twin.get("picture") or {}).get("hdr"):
                assets[key]["working_copy_hdr"] = True
            copies += working_copy_notes(key, meta, twin)

    def asset(item, kinds):
        key = word(item.get("asset"), "Asset")
        if key not in assets or assets[key]["kind"] not in kinds:
            raise EditError(f"Invalid Asset For This Track {key}.")
        return assets[key]

    def placed(row, item, key, label, tone):
        # Only HDR Rows Carry These Keys, So Standard Projects Keep Their Existing Model.
        hdr = (item.get("picture") or {}).get("hdr")
        if hdr:
            row.update(hdr=hdr, tone_map=tone)
        uses.setdefault(key, []).append((label, tone))
        return row

    def within(end, item):
        if item["kind"] != "image" and item["duration"] is not None and end > item["duration"] + 0.001:
            raise EditError(f"Selection Extends Past The End Of {item['path']}.")

    def quantize(seconds):
        return math.floor(seconds * fps + 0.5) / fps

    def faded(row, obj, length, label):
        # Sound Fades Are Opt-In. Rows Without Them Keep Their Existing Shape And Their Sound As Recorded.
        rise = number(obj.get("fade_in", 0), f"{label} Fade In", 0, 60)
        fall = number(obj.get("fade_out", 0), f"{label} Fade Out", 0, 60)
        if rise + fall > length + 1e-9:
            raise EditError(f"{label} Fades Must Fit Inside Its {length:g} Second Length.")
        if rise or fall:
            row.update(fade_in=rise, fade_out=fall)
        return row

    shots, total = [], 0
    for obj in collection(doc, "shots"):
        fields(obj, "asset in out lead tail speed gain fit zoom pan_x pan_y brightness contrast saturation tone_map "
                    "fade_in fade_out", "Shot")
        a = asset(obj, ("video", "image"))
        start = number(obj.get("in", 0), "Shot In") - number(obj.get("lead", 0), "Lead")
        end = number(obj.get("out"), "Shot Out") + number(obj.get("tail", 0), "Tail")
        if start < 0 or end <= start or obj["out"] <= obj.get("in", 0):
            raise EditError("Shot Bounds And Handles Must Form A Positive Source Range.")
        within(end, a)
        speed = number(obj.get("speed", 1), "Speed", 0.25, 4)
        duration = quantize((end - start) / speed)
        if duration <= 0:
            raise EditError("Shot Requires At Least One Output Frame.")
        shot_fit = choice(obj.get("fit", fit), ("contain", "cover"), "Fit")
        zoom = number(obj.get("zoom",1), "Zoom", 1, 4)
        pan_x = number(obj.get("pan_x",0), "Pan X", -1, 1)
        pan_y = number(obj.get("pan_y",0), "Pan Y", -1, 1)
        tone = flag(obj.get("tone_map", tone_default), "Shot Tone Map")
        shot = dict(asset=obj["asset"], start=start, end=end, at=total, duration=duration, speed=speed,
                    gain=number(obj.get("gain", 1), "Gain", 0, 4), fit=shot_fit,
                    zoom=zoom, pan_x=pan_x, pan_y=pan_y, geometry=framing(a["video"],w,h,shot_fit,zoom,pan_x,pan_y),
                    brightness=number(obj.get("brightness",1),"Brightness",0,3),
                    contrast=number(obj.get("contrast",1),"Contrast",0,3),
                    saturation=number(obj.get("saturation",1),"Saturation",0,2))
        shots.append(placed(faded(shot, obj, duration, "Shot"), a, obj["asset"], f"Shot {len(shots)+1}", tone))
        total = quantize(total + duration)
    if not shots:
        raise EditError("Add At Least One Shot.")

    def span(obj, label):
        at = quantize(number(obj.get("at", 0), f"{label} Start"))
        end = quantize(number(obj.get("end"), f"{label} End"))
        if end <= at or end > total:
            raise EditError(f"{label} Must Fit Inside The Timeline And Last At Least One Frame.")
        return at, end

    overlays, audio, captions = [], [], []
    for obj in collection(doc, "overlays"):
        fields(obj, "asset at end in x y width tone_map", "Overlay")
        a = asset(obj, ("video", "image"))
        at, end = span(obj, "Overlay")
        start = number(obj.get("in", 0), "Overlay Source In")
        within(start + end - at, a)
        tone = flag(obj.get("tone_map", tone_default), "Overlay Tone Map")
        overlay = dict(asset=obj["asset"], at=at, end=end, start=start,
                       x=integer(obj.get("x", 0), "Overlay X", -w, w),
                       y=integer(obj.get("y", 0), "Overlay Y", -h, h),
                       width=integer(obj.get("width", w), "Overlay Width", 2, w * 4))
        overlays.append(placed(overlay, a, obj["asset"], f"Overlay {len(overlays)+1}", tone))
    for obj in collection(doc, "audio"):
        fields(obj, "asset at end in gain fade_in fade_out", "Audio")
        a = asset(obj, ("audio", "video"))
        if not a["audio"]:
            raise EditError("Audio Cue Requires An Audio Stream.")
        at, end = span(obj, "Audio Cue")
        start = number(obj.get("in", 0), "Audio Source In")
        within(start + end - at, a)
        cue = dict(asset=obj["asset"], at=at, end=end, start=start, gain=number(obj.get("gain", 1), "Gain", 0, 4))
        audio.append(faded(cue, obj, end - at, "Audio Cue"))
    for obj in collection(doc, "captions"):
        fields(obj, "at end text position", "Caption")
        at, end = span(obj, "Caption")
        captions.append(dict(at=at, end=end, text=word(obj.get("text"), "Caption Text"),
                             position=choice(obj.get("position", "bottom"), ("top", "center", "bottom"), "Caption Position")))
    return dict(title=title, width=w, height=h, fps=fps, duration=total, assets=assets, shots=shots,
                overlays=overlays, captions=captions, audio=audio, caption_style=caption_style(doc,w,h),
                warnings=source_warnings(assets, uses) + copies + playback_warnings(assets, uses))


def timecode(t, scale, separator):
    units = int(t * scale + 0.5)
    seconds, sub = divmod(units, scale)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    digits = len(str(scale)) - 1
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}{separator}{sub:0{digits}d}"


def srt(model):
    lines = []
    for i, cue in enumerate(sorted(model["captions"], key=lambda c: c["at"]), 1):
        lines.append(f"{i}\n{timecode(cue['at'], 1000, ',')} --> {timecode(cue['end'], 1000, ',')}\n{cue['text']}\n")
    return "\n".join(lines)


def publish_file(source, target):
    try:
        os.link(source, target)
    except FileExistsError:
        raise
    except OSError:
        with target.open("xb") as output:
            try:
                with source.open("rb") as inp:
                    shutil.copyfileobj(inp, output)
            except BaseException:
                output.close()
                target.unlink()
                raise
