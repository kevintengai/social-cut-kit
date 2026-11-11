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


def probe(path):
    args = [binary("ffprobe"), "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)]
    data = json.loads(run(args).stdout)
    streams = data.get("streams", [])
    video = next((s for s in streams if s["codec_type"] == "video" and not s.get("disposition", {}).get("attached_pic")), None)
    audio = next((s for s in streams if s["codec_type"] == "audio"), None)
    duration = data["format"].get("duration")
    return {"duration": float(duration) if duration and duration != "N/A" else None,
            "video": video, "audio": audio, "format": data["format"].get("format_name", "")}


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
    rotation = next((s["rotation"] for s in video.get("side_data_list", []) if "rotation" in s), 0)
    if abs(round(rotation/90)) % 2:
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


def caption_style(doc, w, h):
    style = doc.get("caption_style", {})
    fields(style, "font size color outline stroke margin", "Caption Style")
    font = choice(style.get("font", "Arial"), ("Arial","Georgia","Verdana","Tahoma","Trebuchet MS"), "Caption Font")
    def color(key, default):
        value = style.get(key, default)
        if not isinstance(value,str) or not re.fullmatch(r"#[0-9a-fA-F]{6}",value):
            raise EditError(f"{key} Requires A Six-Digit Hex Color.")
        return value
    size = integer(style.get("size",max(12,round(min(h*.078,w*.085)))), "Caption Size", 4, 1024)
    return {"font":font, "size":size, "color":color("color","#FFFFFF"), "outline":color("outline","#101010"),
            "stroke":number(style.get("stroke",max(1,round(size*.07))),"Caption Stroke",0,96),
            "margin":number(style.get("margin",7),"Caption Margin",0,45)}


def prepare(doc, root):
    fields(doc, "version title canvas assets shots overlays captions audio caption_style", "Project")
    if type(doc.get("version")) is not int or doc["version"] != 1:
        raise EditError("Set Project Version To 1.")
    title = word(doc.get("title"), "Title")
    canvas = doc.get("canvas", {})
    fields(canvas, "width height fps fit", "Canvas")
    w = integer(canvas.get("width", 1080), "Width", 16, 8192)
    h = integer(canvas.get("height", 1920), "Height", 16, 8192)
    if w % 2 or h % 2:
        raise EditError("Canvas Dimensions Must Be Even.")
    fps = integer(canvas.get("fps", 30), "FPS", 1, 120)
    fit = choice(canvas.get("fit", "contain"), ("contain", "cover"), "Fit")
    assets = {}
    if not isinstance(doc.get("assets"), dict):
        raise EditError("Assets Requires A Named Object.")
    for key, obj in doc["assets"].items():
        word(key, "Asset Name")
        fields(obj, "path kind", "Asset")
        path = (root / word(obj.get("path"), "Asset Path")).resolve()
        if not path.is_file():
            raise EditError(f"Missing Asset {path}.")
        kind = choice(obj.get("kind"), ("video", "image", "audio"), "Asset Kind")
        meta = probe(path)
        stream = meta["audio" if kind == "audio" else "video"]
        if not stream:
            raise EditError(f"Missing {kind} Stream In {path}.")
        assets[key] = dict(meta, path=str(path), kind=kind)

    def asset(item, kinds):
        key = word(item.get("asset"), "Asset")
        if key not in assets or assets[key]["kind"] not in kinds:
            raise EditError(f"Invalid Asset For This Track {key}.")
        return assets[key]

    def within(end, item):
        if item["kind"] != "image" and item["duration"] is not None and end > item["duration"] + 0.001:
            raise EditError(f"Selection Extends Past The End Of {item['path']}.")

    def quantize(seconds):
        return math.floor(seconds * fps + 0.5) / fps

    shots, total = [], 0
    for obj in collection(doc, "shots"):
        fields(obj, "asset in out lead tail speed gain fit zoom pan_x pan_y brightness contrast saturation", "Shot")
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
        shots.append(dict(asset=obj["asset"], start=start, end=end, at=total, duration=duration, speed=speed,
                          gain=number(obj.get("gain", 1), "Gain", 0, 4), fit=shot_fit,
                          zoom=zoom, pan_x=pan_x, pan_y=pan_y, geometry=framing(a["video"],w,h,shot_fit,zoom,pan_x,pan_y),
                          brightness=number(obj.get("brightness",1),"Brightness",0,3),
                          contrast=number(obj.get("contrast",1),"Contrast",0,3),
                          saturation=number(obj.get("saturation",1),"Saturation",0,2)))
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
        fields(obj, "asset at end in x y width", "Overlay")
        a = asset(obj, ("video", "image"))
        at, end = span(obj, "Overlay")
        start = number(obj.get("in", 0), "Overlay Source In")
        within(start + end - at, a)
        overlays.append(dict(asset=obj["asset"], at=at, end=end, start=start,
                             x=integer(obj.get("x", 0), "Overlay X", -w, w),
                             y=integer(obj.get("y", 0), "Overlay Y", -h, h),
                             width=integer(obj.get("width", w), "Overlay Width", 2, w * 4)))
    for obj in collection(doc, "audio"):
        fields(obj, "asset at end in gain", "Audio")
        a = asset(obj, ("audio", "video"))
        if not a["audio"]:
            raise EditError("Audio Cue Requires An Audio Stream.")
        at, end = span(obj, "Audio Cue")
        start = number(obj.get("in", 0), "Audio Source In")
        within(start + end - at, a)
        audio.append(dict(asset=obj["asset"], at=at, end=end, start=start, gain=number(obj.get("gain", 1), "Gain", 0, 4)))
    for obj in collection(doc, "captions"):
        fields(obj, "at end text position", "Caption")
        at, end = span(obj, "Caption")
        captions.append(dict(at=at, end=end, text=word(obj.get("text"), "Caption Text"),
                             position=choice(obj.get("position", "bottom"), ("top", "center", "bottom"), "Caption Position")))
    return dict(title=title, width=w, height=h, fps=fps, duration=total, assets=assets, shots=shots,
                overlays=overlays, captions=captions, audio=audio, caption_style=caption_style(doc,w,h))


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
