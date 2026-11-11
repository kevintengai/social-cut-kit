"""Sound, Picture, Subtitles, And Media Diagnostics."""

import re
import subprocess
import tempfile
from pathlib import Path

from timeline import EditError, binary, framing, probe, publish_file, run, timecode


def decimal(value):
    return f"{value:.9f}".rstrip("0").rstrip(".") or "0"


def ass(model):
    h, w = model["height"], model["width"]
    style = model["caption_style"]
    size, outline = style["size"],style["stroke"]
    margin = round(h*style["margin"]/100)
    def colour(value):
        return "&H00" + value[5:7] + value[3:5] + value[1:3]
    ink, edge = colour(style["color"]),colour(style["outline"])
    result = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {w}", f"PlayResY: {h}", "ScaledBorderAndShadow: yes",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Default,{style['font']},{size},{ink},{ink},{edge},&H00000000,-1,0,0,0,100,100,0,0,1,{outline},0,2,{round(w*.055)},{round(w*.055)},{margin},1",
        "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for cue in model["captions"]:
        alignment = {"top": 8, "center": 5, "bottom": 2}[cue["position"]]
        raw = cue["text"].replace("\\", "＼").replace("{", "｛").replace("}", "｝")
        content = r"\N".join(raw.splitlines())
        style = "{\\an" + str(alignment) + "}"
        result.append(f"Dialogue: 0,{timecode(cue['at'],100,'.')},{timecode(cue['end'],100,'.')},Default,,0,0,0,,{style}{content}")
    return "\n".join(result) + "\n"


def tempo(speed):
    factors = []
    while speed > 2:
        factors.append(2)
        speed /= 2
    while speed < .5:
        factors.append(.5)
        speed *= 2
    factors.append(speed)
    return ",".join("atempo=" + decimal(factor) for factor in factors)


def colour_filters(shot):
    b, c, s = (shot.get(k,1) for k in ("brightness","contrast","saturation"))
    if (b,c,s) == (1,1,1):
        return ""
    # The Browser Uses The Same RGB Brightness, Contrast, Then Saturation Order.
    expression = f"'clip((clip(val*{decimal(b)},0,255)-127.5)*{decimal(c)}+127.5,0,255)'"
    filters = ["format=gbrp", "lutrgb=" + ":".join(ch+"="+expression for ch in "rgb")]
    if s != 1:
        channels = []
        for out_ch in "rgb":
            for in_ch, weight in zip("rgb", (.213,.715,.072)):
                coefficient = weight * (1-s) + (s if out_ch == in_ch else 0)
                channels.append(out_ch+in_ch+"="+decimal(coefficient))
        filters.append("colorchannelmixer=" + ":".join(channels))
    return ",".join(filters) + ","


def graph(model, with_captions=True):
    w, h, fps = model["width"], model["height"], model["fps"]
    args, filters = [], []
    count = 0

    def input_ref(key, start, duration):
        nonlocal count
        info = model["assets"][key]
        if info["kind"] == "image":
            args.extend(["-loop", "1", "-framerate", str(fps)])
        elif start:
            args.extend(["-ss", decimal(start)])
        args.extend(["-t", decimal(duration), "-i", info["path"]])
        index = count
        count += 1
        return index, info

    def stream(index, info, kind):
        return f"[{index}:{info[kind]['index']}]"

    audio_format = "aresample=48000:async=1:first_pts=0,aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
    shot_pads = []
    for i, shot in enumerate(model["shots"]):
        duration = decimal(shot["duration"])
        index, a = input_ref(shot["asset"], shot["start"], shot["end"] - shot["start"])
        geometry = shot.get("geometry") or framing(a["video"],w,h,shot["fit"],1,0,0)
        crop = ":".join(str(n) for n in geometry["crop"])
        sw,sh = geometry["scale"]
        px,py = geometry["pad"]
        size = f"crop={crop}:exact=1,scale={sw}:{sh},setsar=1,{colour_filters(shot)}pad={w}:{h}:{px}:{py}"
        video = stream(index, a, "video")
        filters.append(f"{video}settb=AVTB,setpts=PTS/{decimal(shot['speed'])},fps=fps={fps}:start_time=0,{size},setsar=1,format=yuv420p,"
                       f"tpad=stop_mode=clone:stop_duration={duration},trim=duration={duration},setpts=PTS-STARTPTS[v{i}]")
        if a["audio"] and a["kind"] != "image" and shot["gain"]:
            audio = stream(index, a, "audio")
            filters.append(f"{audio}{audio_format},{tempo(shot['speed'])},volume={decimal(shot['gain'])},"
                           f"apad,atrim=duration={duration},asetpts=PTS-STARTPTS[a{i}]")
        else:
            filters.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={duration},asetpts=PTS-STARTPTS[a{i}]")
        shot_pads.append(f"[v{i}][a{i}]")
    filters.append("".join(shot_pads) + f"concat=n={len(shot_pads)}:v=1:a=1[base][voice]")
    current = "[base]"
    for i, obj in enumerate(model["overlays"]):
        index, a = input_ref(obj["asset"], obj["start"], obj["end"] - obj["at"])
        video = stream(index, a, "video")
        at, end = decimal(obj["at"]), decimal(obj["end"])
        filters.append(f"{video}fps={fps},scale={obj['width']}:-2,setsar=1,format=rgba,setpts=PTS-STARTPTS+{at}/TB[o{i}]")
        filters.append(f"{current}[o{i}]overlay=x={obj['x']}:y={obj['y']}:eof_action=pass:repeatlast=0:"
                       f"enable='gte(t,{at})*lt(t,{end})'[ov{i}]")
        current = f"[ov{i}]"
    if with_captions and model["captions"]:
        current += "subtitles=filename=captions.ass,"
    filters.append(current + "format=yuv420p[picture]")
    music = ["[voice]"]
    for i, obj in enumerate(model["audio"]):
        duration = obj["end"] - obj["at"]
        index, a = input_ref(obj["asset"], obj["start"], duration)
        audio = stream(index, a, "audio")
        delay = round(obj["at"] * 48000)
        filters.append(f"{audio}{audio_format},atrim=duration={decimal(duration)},asetpts=PTS-STARTPTS,"
                       f"volume={decimal(obj['gain'])},adelay={delay}S:all=1[m{i}]")
        music.append(f"[m{i}]")
    if len(music) > 1:
        filters.append("".join(music) + f"amix=inputs={len(music)}:duration=first:normalize=0,aformat=channel_layouts=stereo[sound]")
    else:
        filters.append("[voice]anull[sound]")
    return args, ";\n".join(filters)


def process(model, output=None, burn=True):
    if output:
        output = output.resolve()
        if output.suffix.lower() != ".mp4":
            raise EditError("Choose An MP4 Output Filename.")
        if output.exists():
            raise EditError(f"Output Already Exists {output}.")
    inputs, expression = graph(model, burn)
    with tempfile.TemporaryDirectory(prefix="social-cut-", dir=output.parent if output else None) as tmp:
        work = Path(tmp)
        # Relative Filter Resource Paths Also Work On Windows Drive Letters.
        (work / "timeline.ffgraph").write_text(expression, encoding="utf-8")
        if burn and model["captions"]:
            (work / "captions.ass").write_text(ass(model), encoding="utf-8")
        args = [binary("ffmpeg"), "-hide_banner", "-loglevel", "error", "-nostdin", "-n", "-progress", "pipe:1", *inputs,
                "-filter_complex_threads", "1", "-filter_complex_script", "timeline.ffgraph",
                "-map", "[picture]", "-map", "[sound]", "-t", decimal(model["duration"])]
        if output:
            args += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "19", "-preset", "medium",
                     "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "render.mp4"]
        else:
            args += ["-f", "null", "-"]
        result = subprocess.run(args, cwd=work, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode:
            raise EditError(result.stderr[-4000:] or "Media Processing Failed.")
        frames = re.findall(r"^frame=(\d+)\s*$", result.stdout, re.MULTILINE)
        expected = round(model["duration"] * model["fps"])
        if not frames or abs(int(frames[-1]) - expected) > 1:
            raise EditError(f"Composition Frame Count Mismatch. Expected {expected}.")
        if output:
            target = work / "render.mp4"
            verify_encoded(probe(target), model)
            publish_file(target, output)


def verify_encoded(meta, model):
    video, audio = meta["video"], meta["audio"]
    if not video or not audio or (video["width"], video["height"]) != (model["width"], model["height"]):
        raise EditError("Export Stream Or Dimensions Failed Verification.")
    if audio.get("channels") != 2 or int(audio.get("sample_rate", 0)) != 48000:
        raise EditError("Export Stereo Audio Failed Verification.")
    if meta["duration"] is None or abs(meta["duration"] - model["duration"]) > max(.08, 1 / model["fps"]):
        raise EditError("Export Duration Failed Verification.")
    frames = video.get("nb_frames")
    if frames and frames.isdigit() and abs(int(frames) - round(model["duration"] * model["fps"])) > 1:
        raise EditError("Export Frame Count Failed Verification.")


def analyze(path, silence_db, silence_length, scene_threshold):
    info = probe(path)
    result = {"source": str(path), "duration": info["duration"], "silence": [], "scene_changes": []}
    base = [binary("ffmpeg"), "-hide_banner", "-nostdin", "-i", str(path)]
    if info["audio"]:
        audio = base + ["-map", f"0:{info['audio']['index']}", "-af",
                        f"silencedetect=noise={silence_db}dB:d={silence_length}", "-f", "null", "-"]
        report = run(audio).stderr
        start = None
        for kind, value in re.findall(r"silence_(start|end):\s*(-?[0-9.]+)", report):
            if kind == "start":
                start = float(value)
            elif start is not None:
                result["silence"].append({"start": start, "end": float(value)})
                start = None
    if info["video"]:
        scene = base + ["-map", f"0:{info['video']['index']}", "-vf",
                        f"select='gt(scene,{scene_threshold})',metadata=print", "-an", "-f", "null", "-"]
        report = run(scene).stderr
        result["scene_changes"] = [float(t) for t in re.findall(r"pts_time:\s*([\d.eE+-]+)", report)]
    return result
