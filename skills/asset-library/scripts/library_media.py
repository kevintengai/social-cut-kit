"""Asset Kinds, Media Facts From FFprobe, And JPEG Preview Stills From FFmpeg."""

import json
from pathlib import Path
import re
import shutil
import subprocess


KINDS = ("footage", "image", "music", "sfx", "voice", "character", "code", "model", "other")
VIDEO = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi", ".mxf", ".mts", ".m2ts", ".wmv", ".mpg",
         ".mpeg", ".3gp"}
IMAGE = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".tga"}
DRAWING = {".svg", ".psd", ".ai", ".exr", ".heic"}
AUDIO = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".aif", ".aiff", ".wma"}
CODE = {".py", ".js", ".cjs", ".mjs", ".ts", ".tsx", ".jsx", ".html", ".css", ".json", ".glsl",
        ".lua", ".sh", ".ps1"}
MODEL = {".blend", ".glb", ".gltf", ".fbx", ".obj", ".usd", ".usda", ".usdc", ".usdz", ".stl",
         ".dae", ".abc"}
SHORT_SOUND_SECONDS = 15.0
PREVIEW_SIDE = 560
TOOL_TIMEOUT = 180
FACT_FIELDS = ("duration", "width", "height", "frame_rate", "audio_channels", "sample_rate", "peak_db")


def media_class(path):
    suffix = Path(path).suffix.lower()
    if suffix in VIDEO:
        return "video"
    if suffix in IMAGE:
        return "image"
    if suffix in AUDIO:
        return "audio"
    return None


def infer_kind(path, storage, facts):
    """Choose A Kind From The File Type. Audio Under Fifteen Seconds Reads As A Sound Effect."""
    path = Path(path)
    if storage == "bundle":
        suffixes = {p.suffix.lower() for p in path.rglob("*") if p.is_file()}
        if suffixes & MODEL:
            return "model"
        if suffixes & CODE:
            return "code"
        return "other"
    suffix = path.suffix.lower()
    group = media_class(path)
    if group == "video":
        return "footage"
    if group == "image" or suffix in DRAWING:
        return "image"
    if group == "audio":
        duration = (facts or {}).get("duration")
        return "sfx" if duration is not None and duration < SHORT_SOUND_SECONDS else "music"
    if suffix in MODEL:
        return "model"
    if suffix in CODE:
        return "code"
    return "other"


def run_tool(command):
    return subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=TOOL_TIMEOUT, check=False)


def number(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result and result not in (float("inf"), float("-inf")) else None


def rate(value):
    try:
        top, _, bottom = str(value).partition("/")
        result = float(top) / float(bottom or 1)
    except (ValueError, ZeroDivisionError):
        return None
    return round(result, 3) if result > 0 else None


def peak_level(ffmpeg, path):
    done = run_tool([ffmpeg, "-hide_banner", "-nostdin", "-nostats", "-i", str(path), "-map", "0:a:0",
                     "-af", "volumedetect", "-f", "null", "-"])
    found = re.search(r"max_volume:\s*(-?\d+(?:\.\d+)?|-?inf) dB", done.stderr.decode("utf-8", "replace"))
    if done.returncode or not found:
        return None
    return number(found.group(1))


def probe(path, storage="file"):
    """Return Media Facts And A Status Sentence. Facts Are None When Nothing Was Measured."""
    if storage != "file":
        return None, "Media Facts Are Recorded For Single Media Files, Not For Folders."
    group = media_class(path)
    if group is None:
        return None, "The File Type Is Not A Recognised Media Type, So No Media Facts Were Recorded."
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        return None, "FFprobe Was Not Found On PATH, So No Media Facts Were Recorded."
    try:
        done = run_tool([ffprobe, "-v", "error", "-print_format", "json", "-show_format",
                         "-show_streams", str(path)])
        report = json.loads(done.stdout.decode("utf-8", "replace")) if done.returncode == 0 else None
    except (OSError, subprocess.SubprocessError, ValueError):
        report = None
    if not isinstance(report, dict) or not report.get("streams"):
        return None, "FFprobe Could Not Read The File, So No Media Facts Were Recorded."
    facts = dict.fromkeys(FACT_FIELDS)
    streams = report["streams"]
    picture = next((s for s in streams if s.get("codec_type") == "video"
                    and not (s.get("disposition") or {}).get("attached_pic")), None)
    sound = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if picture and group != "audio":
        facts["width"] = picture.get("width")
        facts["height"] = picture.get("height")
        if group == "video":
            facts["frame_rate"] = rate(picture.get("avg_frame_rate")) or rate(picture.get("r_frame_rate"))
    if sound:
        facts["audio_channels"] = sound.get("channels")
        sample_rate = number(sound.get("sample_rate"))
        facts["sample_rate"] = int(sample_rate) if sample_rate else None
    if group != "image":
        duration = number((report.get("format") or {}).get("duration"))
        if duration is None:
            duration = number((picture or sound or {}).get("duration"))
        facts["duration"] = round(duration, 3) if duration is not None else None
    status = "Measured With FFprobe."
    if group == "audio" and sound:
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            status = "Measured With FFprobe. FFmpeg Was Not Found On PATH, So The Peak Level Is Empty."
        else:
            try:
                facts["peak_db"] = peak_level(ffmpeg, path)
            except (OSError, subprocess.SubprocessError):
                facts["peak_db"] = None
            if facts["peak_db"] is None:
                status = "Measured With FFprobe. FFmpeg Could Not Measure The Peak Level."
    return facts, status


def preview(path, storage, facts):
    """Return JPEG Bytes For A Video Or Image Asset And A Status Sentence. Never Writes Video."""
    group = media_class(path) if storage == "file" else None
    if group not in ("video", "image"):
        return None, "Preview Stills Are Kept For Video And Image Files Only."
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return None, "FFmpeg Was Not Found On PATH, So No Preview Still Was Kept."
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin"]
    duration = (facts or {}).get("duration")
    if group == "video" and duration:
        command += ["-ss", f"{duration / 3:.3f}"]
    scale = (f"scale=w=min({PREVIEW_SIDE}\\,iw):h=min({PREVIEW_SIDE}\\,ih)"
             ":force_original_aspect_ratio=decrease")
    command += ["-i", str(path), "-map", "0:v:0", "-frames:v", "1", "-an", "-vf", scale,
                "-c:v", "mjpeg", "-q:v", "5", "-f", "image2pipe", "pipe:1"]
    try:
        done = run_tool(command)
    except (OSError, subprocess.SubprocessError):
        return None, "FFmpeg Could Not Make A Preview Still."
    if done.returncode or not done.stdout.startswith(b"\xff\xd8"):
        return None, "FFmpeg Could Not Make A Preview Still."
    return done.stdout, "Kept A JPEG Preview Still."
