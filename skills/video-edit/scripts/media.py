"""Sound, Picture, Subtitles, And Media Diagnostics."""

import math
import re
import subprocess
import tempfile
from pathlib import Path

from timeline import EditError, binary, framing, picture_info, probe, publish_file, run, timecode


# HDR Reference White In Nits. It Lands At Standard Peak White Before The Highlight Roll-Off.
REFERENCE_WHITE = 203
TONE_FILTERS = ("zscale", "tonemap")
ZSCALE_PRIMARIES = {"bt709", "bt470m", "bt470bg", "smpte170m", "smpte240m", "film", "bt2020",
                    "smpte428", "smpte431", "smpte432", "jedec-p22", "ebu3213"}
ZSCALE_MATRICES = {"bt709", "fcc", "bt470bg", "smpte170m", "smpte240m", "ycgco", "bt2020nc", "bt2020c",
                   "chroma-derived-nc", "chroma-derived-c", "ictcp"}
LAYERS = ("mix", "voice", "cues")
_filters = None


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


def tone_filters(video):
    """One Conversion From PQ Or HLG To BT.709 Standard Dynamic Range. The Result Ends In A Comma."""
    info = picture_info(video)
    if not info or not info["hdr"]:
        return ""
    primaries = info["color_primaries"] if info["color_primaries"] in ZSCALE_PRIMARIES else "bt2020"
    source = ["transferin=" + info["color_transfer"], "primariesin=" + primaries]
    layout = str(video.get("pix_fmt") or "").lower()
    if re.match(r"(gbr|rgb|bgr|argb|abgr|x2)", layout):
        source.append("rangein=full")
    else:
        matrix = info["color_space"] if info["color_space"] in ZSCALE_MATRICES else "bt2020nc"
        full = info["color_range"] == "pc" or layout.startswith("yuvj")
        source += ["matrixin=" + matrix, "rangein=" + ("full" if full else "limited")]
    # HLG Is Nominally A 1000 Nit Signal. PQ Uses Its Own Light Level Metadata When Present.
    nits = 1000 if info["hdr"] == "hlg" else min(10000, max(400, info["peak_nits"] or 1000))
    return (f"zscale={':'.join(source)}:transfer=linear:primaries=bt709:npl={REFERENCE_WHITE},format=gbrpf32le,"
            f"tonemap=tonemap=mobius:param=0.3:desat=0:peak={decimal(nits / REFERENCE_WHITE)},"
            "zscale=transferin=linear:primariesin=bt709:transfer=bt709:primaries=bt709:matrix=bt709:range=limited:"
            "dither=error_diffusion,format=yuv420p,")


def fade_filters(row, length):
    """Opt-In Sound Fades For One Shot Or Cue, As A Suffix That Begins With A Comma."""
    parts = []
    if row.get("fade_in"):
        parts.append(f"afade=t=in:st=0:d={decimal(row['fade_in'])}")
    if row.get("fade_out"):
        parts.append(f"afade=t=out:st={decimal(max(0, length - row['fade_out']))}:d={decimal(row['fade_out'])}")
    return "".join("," + part for part in parts)


def available_filters():
    global _filters
    if _filters is None:
        listing = run([binary("ffmpeg"), "-hide_banner", "-filters"]).stdout
        rows = (line.split() for line in listing.splitlines())
        _filters = {row[1] for row in rows if len(row) > 2 and "->" in row[2]}
    return _filters


def missing_tone_filters(model):
    if not any(row.get("tone_map") for row in model["shots"] + model["overlays"]):
        return []
    return [name for name in TONE_FILTERS if name not in available_filters()]


def require_tone_filters(model):
    missing = missing_tone_filters(model)
    if missing:
        names = " And ".join(missing)
        raise EditError(f"This FFmpeg Build Lacks The {names} Filter{'s' if len(missing) > 1 else ''} Needed To "
                        "Convert HDR Shots To Standard Dynamic Range. Install A Build That Includes zscale "
                        "(libzimg) And tonemap, Or Set tone_map To false To Pass The Picture Through Unconverted.")


def graph(model, with_captions=True, picture=True, sound="mix", master_gain=None):
    """Build FFmpeg Inputs And The Composition Graph.

    The Defaults Describe The Complete Edit. The Keyword Options Select A Sound-Only Graph,
    One Sound Layer (The Whole Mix, The Shot Audio Alone, Or The Added Cues Alone), And One
    Constant Gain On The Finished Mix.
    """
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
        # A Blank Shot Holds Its Place In Time Without Opening A Source File.
        a = None if shot.get("blank") else model["assets"][shot["asset"]]
        voiced = bool(a and a["audio"] and a["kind"] != "image" and shot["gain"] and sound != "cues")
        if a and (picture or voiced):
            index, a = input_ref(shot["asset"], shot["start"], shot["end"] - shot["start"])
        if picture and a:
            geometry = shot.get("geometry") or framing(a["video"],w,h,shot["fit"],1,0,0)
            crop = ":".join(str(n) for n in geometry["crop"])
            sw,sh = geometry["scale"]
            px,py = geometry["pad"]
            tone = tone_filters(a["video"]) if shot.get("tone_map") else ""
            size = f"crop={crop}:exact=1,scale={sw}:{sh},setsar=1,{tone}{colour_filters(shot)}pad={w}:{h}:{px}:{py}"
            video = stream(index, a, "video")
            filters.append(f"{video}settb=AVTB,setpts=PTS/{decimal(shot['speed'])},fps=fps={fps}:start_time=0,{size},setsar=1,format=yuv420p,"
                           f"tpad=stop_mode=clone:stop_duration={duration},trim=duration={duration},setpts=PTS-STARTPTS[v{i}]")
        elif picture:
            filters.append(f"color=c=black:s={w}x{h}:r={fps},format=yuv420p,setsar=1,"
                           f"trim=duration={duration},setpts=PTS-STARTPTS[v{i}]")
        if voiced:
            audio = stream(index, a, "audio")
            filters.append(f"{audio}{audio_format},{tempo(shot['speed'])},volume={decimal(shot['gain'])},"
                           f"apad,atrim=duration={duration},asetpts=PTS-STARTPTS{fade_filters(shot, shot['duration'])}[a{i}]")
        else:
            filters.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={duration},asetpts=PTS-STARTPTS[a{i}]")
        shot_pads.append((f"[v{i}]" if picture else "") + f"[a{i}]")
    filters.append("".join(shot_pads) + f"concat=n={len(shot_pads)}:v={int(picture)}:a=1"
                   + ("[base][voice]" if picture else "[voice]"))
    if picture:
        current = "[base]"
        for i, obj in enumerate(model["overlays"]):
            index, a = input_ref(obj["asset"], obj["start"], obj["end"] - obj["at"])
            video = stream(index, a, "video")
            at, end = decimal(obj["at"]), decimal(obj["end"])
            tone = tone_filters(a["video"]) if obj.get("tone_map") else ""
            filters.append(f"{video}fps={fps},scale={obj['width']}:-2,setsar=1,{tone}format=rgba,setpts=PTS-STARTPTS+{at}/TB[o{i}]")
            filters.append(f"{current}[o{i}]overlay=x={obj['x']}:y={obj['y']}:eof_action=pass:repeatlast=0:"
                           f"enable='gte(t,{at})*lt(t,{end})'[ov{i}]")
            current = f"[ov{i}]"
        if with_captions and model["captions"]:
            current += "subtitles=filename=captions.ass,"
        filters.append(current + "format=yuv420p[picture]")
    music = ["[voice]"]
    for i, obj in enumerate(model["audio"] if sound != "voice" else []):
        duration = obj["end"] - obj["at"]
        index, a = input_ref(obj["asset"], obj["start"], duration)
        audio = stream(index, a, "audio")
        delay = round(obj["at"] * 48000)
        filters.append(f"{audio}{audio_format},atrim=duration={decimal(duration)},asetpts=PTS-STARTPTS,"
                       f"volume={decimal(obj['gain'])}{fade_filters(obj, duration)},adelay={delay}S:all=1[m{i}]")
        music.append(f"[m{i}]")
    # One Constant Gain On The Finished Mix Changes Level Only. Balance And Dynamics Stay As Mixed.
    mixed = "[sound]" if master_gain is None else "[blend]"
    if len(music) > 1:
        filters.append("".join(music) + f"amix=inputs={len(music)}:duration=first:normalize=0,aformat=channel_layouts=stereo{mixed}")
    else:
        filters.append(f"[voice]anull{mixed}")
    if master_gain is not None:
        filters.append(f"[blend]volume={decimal(master_gain)}[sound]")
    return args, ";\n".join(filters)


def focus(model, start, end):
    """Keep What Plays Between Two Edit Times. Other Shots Become Blank Segments Of Equal Length."""
    def live(at, finish):
        return at < end - 1e-9 and finish > start + 1e-9
    shots = [shot if live(shot["at"], shot["at"] + shot["duration"]) else
             {"blank": True, "at": shot["at"], "duration": shot["duration"], "gain": 0}
             for shot in model["shots"]]
    return dict(model, shots=shots,
                overlays=[row for row in model["overlays"] if live(row["at"], row["end"])],
                audio=[row for row in model["audio"] if live(row["at"], row["end"])])


def run_graph(work, inputs, expression, tail, level="error"):
    # Relative Filter Resource Paths Also Work On Windows Drive Letters.
    (work / "timeline.ffgraph").write_text(expression, encoding="utf-8")
    args = [binary("ffmpeg"), "-hide_banner", "-loglevel", level, "-nostdin", "-nostats", "-n", *inputs,
            "-filter_complex_threads", "1", "-filter_complex_script", "timeline.ffgraph", *tail]
    result = subprocess.run(args, cwd=work, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise EditError(result.stderr[-4000:] or "Media Processing Failed.")
    return result


def new_file(output, suffix, kind):
    output = output.resolve()
    if output.suffix.lower() != suffix:
        raise EditError(f"Choose A {kind} Output Filename.")
    if output.exists():
        raise EditError(f"Output Already Exists {output}.")
    if not output.parent.is_dir():
        raise EditError(f"Output Folder Does Not Exist {output.parent}.")
    return output


def process(model, output=None, burn=True, master_gain=None):
    if output:
        output = output.resolve()
        if output.suffix.lower() != ".mp4":
            raise EditError("Choose An MP4 Output Filename.")
        if output.exists():
            raise EditError(f"Output Already Exists {output}.")
    require_tone_filters(model)
    inputs, expression = graph(model, burn, master_gain=master_gain)
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


def still(model, at, output, burn=True):
    """Write One Composed Frame As A PNG For Inspection. A Single Still Is Not A Video Export."""
    output = new_file(output, ".png", "PNG")
    fps = model["fps"]
    total = round(model["duration"] * fps)
    frame = math.floor(at * fps + 0.5)
    if not 0 <= frame < total:
        raise EditError(f"Choose A Time From 0 To {decimal((total - 1) / fps)} Seconds.")
    # Only The Picture Of The Shot Under The Playhead Is Decoded. Other Shots Hold Their Length As
    # Blank Frames, And No Sound Is Read.
    scene = dict(focus(model, frame / fps, (frame + 1) / fps), audio=[])
    scene["shots"] = [dict(shot, gain=0) for shot in scene["shots"]]
    require_tone_filters(scene)
    inputs, expression = graph(scene, burn, sound="voice")
    expression += f";\n[picture]select='eq(n,{frame})'[frame];\n[sound]anullsink"
    with tempfile.TemporaryDirectory(prefix="social-cut-", dir=output.parent) as tmp:
        work = Path(tmp)
        if burn and model["captions"]:
            (work / "captions.ass").write_text(ass(model), encoding="utf-8")
        run_graph(work, inputs, expression, ["-map", "[frame]", "-frames:v", "1", "-update", "1", "-c:v", "png", "still.png"])
        if not (work / "still.png").is_file():
            raise EditError("No Frame Was Produced At That Time.")
        publish_file(work / "still.png", output)
    shot = next(i for i, row in enumerate(scene["shots"], 1) if not row.get("blank"))
    return {"output": str(output), "frame": frame, "seconds": frame / fps, "shot": shot}


def window_filters(start, seconds):
    if start is None:
        return ""
    return f"atrim=start={decimal(start)}:duration={decimal(seconds)},asetpts=PTS-STARTPTS,"


def sound_graph(model, layer="mix", start=None, seconds=None, master_gain=None):
    """Inputs And A Sound-Only Graph Whose Final Chain Still Needs A Destination Filter."""
    if layer not in LAYERS:
        raise EditError(f"Unsupported Layer Value {layer}.")
    if (start is None) != (seconds is None):
        raise EditError("Supply Both A Window Start And A Window Length.")
    if start is not None and (start < 0 or seconds <= 0 or start + seconds > model["duration"] + 1e-6):
        raise EditError(f"The Window Must Fit Inside The {decimal(model['duration'])} Second Edit.")
    scene = model if start is None else focus(model, start, start + seconds)
    inputs, expression = graph(scene, False, picture=False, sound=layer, master_gain=master_gain)
    return inputs, expression + ";\n[sound]" + window_filters(start, seconds)


def mix(model, output, layer="mix", start=None, seconds=None):
    """Write The Composed Sound As A 48 kHz Stereo WAV For Listening Checks And Transcription."""
    output = new_file(output, ".wav", "WAV")
    inputs, expression = sound_graph(model, layer, start, seconds)
    with tempfile.TemporaryDirectory(prefix="social-cut-", dir=output.parent) as tmp:
        work = Path(tmp)
        run_graph(work, inputs, expression + "anull[mixdown]",
                  ["-map", "[mixdown]", "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2", "mix.wav"])
        publish_file(work / "mix.wav", output)
    length = model["duration"] if seconds is None else seconds
    return {"output": str(output), "layer": layer, "seconds": length, "sample_rate": 48000, "channels": 2}


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
