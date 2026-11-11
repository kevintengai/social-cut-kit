#!/usr/bin/env python3
"""Transfer Measured Reference Camera Motion To A Second Clip."""

import argparse
import bisect
import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from fractions import Fraction
from itertools import zip_longest

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = np = None


def finite(value, label, low=None, high=None):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(f"{label} Requires A Number.")
    if not math.isfinite(value) or low is not None and value < low or high is not None and value > high:
        raise ValueError(f"{label} Is Outside Its Supported Range.")
    return value


def require_vision():
    if cv2 is None:
        raise ValueError("Install The Camera Dependencies With: python -m pip install numpy opencv-python-headless")


def probe(path):
    data = json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path),
    ]))
    streams = data["streams"]
    video = next((s for s in streams if s["codec_type"] == "video" and
                  not s.get("disposition", {}).get("attached_pic")), None)
    if not video:
        raise ValueError(f"No Video Stream In {path}")
    width, height = video["width"], video["height"]
    aspect = video.get("sample_aspect_ratio", "1:1")
    if aspect not in ("N/A", "0:1"):
        width = round(width * float(Fraction(aspect.replace(":", "/"))))
    rotation = next((s["rotation"] for s in video.get("side_data_list", []) if "rotation" in s), 0)
    if round(rotation) % 90:
        raise ValueError("Only Right-Angle Display Orientation Metadata Is Supported.")
    if round(rotation / 90) % 2:
        width, height = height, width
    duration = float(data["format"].get("duration") or video.get("duration") or 0)
    rate = next((r for r in [video.get("avg_frame_rate"), video.get("r_frame_rate")]
                 if r and r != "0/0" and Fraction(r) > 0), "30")
    finite(duration, "Duration", .000001)
    if min(width, height) < 2:
        raise ValueError("Video Dimensions Must Exceed One Pixel.")
    return {"path": str(path.resolve()), "name": path.name, "bytes": path.stat().st_size,
            "width": width, "height": height, "duration": duration, "fps": float(Fraction(rate)),
            "stream": video["index"], "audio_codecs": [s["codec_name"] for s in streams if s["codec_type"] == "audio"]}


def timestamps(info):
    raw = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", str(info["stream"]), "-show_frames",
        "-show_entries", "frame=best_effort_timestamp_time", "-of", "json", info["path"],
    ])
    frames = json.loads(raw)["frames"]
    if not frames:
        raise ValueError("The Reference Contains No Decodable Frames.")
    result = []
    for item in frames:
        value = item.get("best_effort_timestamp_time")
        if value is None:
            value = result[-1] + 1 / info["fps"] if result else 0
        value = float(value)
        if result and value <= result[-1]:
            raise ValueError("Reference Frame Timestamps Must Advance In Display Order.")
        result.append(value)
    return [value - result[0] for value in result]


def digest(path):
    checksum = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def decode(info, width, height, *, gray=False, fps=None):
    filters = [f"scale={width}:{height}:flags=lanczos", "setsar=1"]
    limits = []
    if fps is not None:
        filters += ["tpad=stop_mode=clone:stop_duration=1", f"fps={fps}:start_time=0:round=up:eof_action=pass"]
        limits = ["-frames:v", str(frame_count(info["duration"], fps))]
    command = ["ffmpeg", "-v", "error", "-xerror", "-nostdin", "-i", info["path"], "-map", f"0:{info['stream']}",
               "-an", "-sn", "-dn", "-vf", ",".join(filters), "-fps_mode", "passthrough",
               *limits, "-pix_fmt", "gray" if gray else "bgr24", "-c:v", "rawvideo", "-f", "rawvideo", "pipe:1"]
    channels = 1 if gray else 3
    frame_bytes = width * height * channels
    shape = (height, width) if gray else (height, width, 3)
    with tempfile.TemporaryFile() as errors, subprocess.Popen(command, stdout=subprocess.PIPE, stderr=errors) as proc:
        try:
            while True:
                raw = proc.stdout.read(frame_bytes)
                if not raw:
                    break
                if len(raw) != frame_bytes:
                    raise ValueError("FFmpeg Returned A Partial Raw Frame.")
                yield np.frombuffer(raw, np.uint8).reshape(shape)
            if proc.wait():
                errors.seek(0)
                raise ValueError(errors.read().decode(errors="replace") or "Video Decoding Failed.")
        finally:
            proc.stdout.close()
            if proc.poll() is None:
                proc.kill()


def corners(image):
    height, width = image.shape
    groups = []
    # A Moving Foreground Subject Should Not Consume All Available Features.
    for row in range(4):
        y0, y1 = row * height // 4, (row + 1) * height // 4
        for col in range(5):
            x0, x1 = col * width // 5, (col + 1) * width // 5
            tile = image[y0:y1, x0:x1]
            if min(tile.shape) < 6:
                continue
            found = cv2.goodFeaturesToTrack(tile, 24, .015, 5)
            if found is not None:
                groups.append(found + np.float32([x0, y0]))
    return np.concatenate(groups) if groups else None


def feature_motion(previous, current):
    height, width = previous.shape
    pts = corners(previous)
    if pts is None or len(pts) < 8:
        return None
    opts = dict(winSize=(21, 21), maxLevel=3,
                criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, .01))
    nxt, good_forward, _ = cv2.calcOpticalFlowPyrLK(previous, current, pts, None, **opts)
    if nxt is None:
        return None
    back, good_reverse, _ = cv2.calcOpticalFlowPyrLK(current, previous, nxt, None, **opts)
    if back is None:
        return None
    ok = (good_forward.ravel() > 0) & (good_reverse.ravel() > 0)
    ok &= np.linalg.norm((pts - back).reshape(-1, 2), axis=1) <= 1.3
    a, b = pts.reshape(-1, 2)[ok], nxt.reshape(-1, 2)[ok]
    if len(a) < 8:
        return None
    affine, mask = cv2.estimateAffinePartial2D(a, b, method=cv2.RANSAC, ransacReprojThreshold=2,
                                               maxIters=1200, confidence=.995, refineIters=10)
    if affine is None:
        return None
    keep = mask.ravel().astype(bool)
    subset = a[keep]
    fraction = len(subset) / len(a)
    if len(subset) < 8 or fraction < .5:
        return None
    coverage = cv2.contourArea(cv2.convexHull(subset)) / (width * height)
    if coverage < .08:
        return None
    scale = math.hypot(affine[0, 0], affine[1, 0])
    angle = math.degrees(math.atan2(affine[1, 0], affine[0, 0]))
    center = np.float64([(width - 1) / 2, (height - 1) / 2])
    jump = np.abs(affine[:, :2] @ center + affine[:, 2] - center)
    if not .7 <= scale <= 1.4 or abs(angle) > 32 or np.any(jump > np.float64([width, height]) * .33):
        return None
    predicted = subset @ affine[:, :2].T + affine[:, 2]
    residual = np.median(np.linalg.norm(predicted - b[keep], axis=1))
    confidence = fraction * min(1, coverage / .35) * math.exp(-residual / 2.5)
    return affine, round(confidence, 5), "tracked"


def phase_motion(previous, current):
    height, width = previous.shape
    if min(height, width) < 8 or min(previous.std(), current.std()) < 3:
        return None
    window = cv2.createHanningWindow((width, height), cv2.CV_32F)
    (dx, dy), score = cv2.phaseCorrelate(previous.astype(np.float32), current.astype(np.float32), window)
    if not score >= .35 or abs(dx) > width * .25 or abs(dy) > height * .25:
        return None
    affine = np.float64([[1, 0, dx], [0, 1, dy]])
    registered = cv2.warpAffine(previous, affine, (width, height))
    left = max(0, math.ceil(dx)) + 2
    top = max(0, math.ceil(dy)) + 2
    right = min(width, width + math.floor(dx)) - 2
    bottom = min(height, height + math.floor(dy)) - 2
    a = registered[top:bottom:2, left:right:2].astype(np.float32)
    b = current[top:bottom:2, left:right:2].astype(np.float32)
    a -= a.mean()
    b -= b.mean()
    denom = math.sqrt(float(np.sum(a * a)) * float(np.sum(b * b)))
    corr = float(np.sum(a * b)) / denom if denom > 0 else 0
    if corr < .65:
        return None
    return affine, round(min(.75, score * corr), 5), "translation"


def track(frames, times):
    previous = None
    pose = np.eye(3)
    angle = 0.0
    samples = []
    for frame, time in zip_longest(frames, times):
        if frame is None or time is None:
            raise ValueError("The Decoded Frame Count Differs From The Reference Timestamps.")
        height, width = frame.shape
        confidence, status = (1.0, "origin") if previous is None else (0.0, "held")
        if previous is not None:
            estimate = feature_motion(previous, frame) or phase_motion(previous, frame)
            if estimate:
                delta, confidence, status = estimate
                pose = np.vstack((delta, [0, 0, 1])) @ pose
                angle += math.degrees(math.atan2(delta[1, 0], delta[0, 0]))
        center = np.float64([(width - 1) / 2, (height - 1) / 2])
        shift = pose[:2, :2] @ center + pose[:2, 2] - center
        samples.append({"t": time, "x": float(shift[0] / (width - 1)), "y": float(shift[1] / (height - 1)),
                        "zoom": math.hypot(pose[0, 0], pose[1, 0]), "angle": angle,
                        "confidence": confidence, "status": status})
        previous = frame
    if not samples:
        raise ValueError("The Reference Contains No Decodable Frames.")
    return samples


class MotionPath:
    def __init__(self, plan):
        if plan["schema"] != "camera-transfer/v1":
            raise ValueError("Unknown Camera Plan Format.")
        self.settings = plan["settings"]
        self.target = plan["source"]
        self.duration = finite(self.target["duration"], "Source Duration", .000001)
        self.reference_duration = finite(plan["reference"]["duration"], "Reference Duration", .000001)
        self.width = self.target["width"]
        self.height = self.target["height"]
        for size in (self.width, self.height):
            if type(size) is not int or size < 2:
                raise ValueError("Invalid Source Dimensions.")
        self.strength = finite(self.settings["strength"], "Strength", 0, 3)
        self.anchor_x = finite(self.settings["anchor_x"], "Horizontal Anchor", 0, 1)
        self.anchor_y = finite(self.settings["anchor_y"], "Vertical Anchor", 0, 1)
        self.fps = finite(self.settings["fps"], "FPS", 1, 240)
        if self.settings["timing"] not in ("stretch", "hold") or self.settings["edge_mode"] not in ("cover", "reflect"):
            raise ValueError("Invalid Camera Timing Or Edge Mode.")
        self.samples = plan["samples"]
        self.times = []
        for p in self.samples:
            time = finite(p["t"], "Sample Time", 0)
            if self.times and time <= self.times[-1]:
                raise ValueError("Sample Times Must Increase.")
            self.times.append(time)
            for key in ("x", "y", "angle"):
                finite(p[key], key.title())
            finite(p["zoom"], "Zoom", 1e-8, 1e8)
            finite(p["confidence"], "Confidence", 0, 1)
        if not self.times or self.times[0] != 0:
            raise ValueError("The Motion Path Must Begin At Zero.")

    def matrix(self, time):
        if self.settings["timing"] == "stretch":
            time = time * self.reference_duration / self.duration
        time = max(0.0, min(time, self.times[-1]))
        i = bisect.bisect_right(self.times, time) - 1
        a, b = self.samples[i], self.samples[min(i + 1, len(self.samples) - 1)]
        f = (time - a["t"]) / (b["t"] - a["t"]) if b["t"] > a["t"] else 0
        def lerp(key):
            return (1 - f) * a[key] + f * b[key]
        angle = math.radians(lerp("angle") * self.strength)
        scale = math.exp(((1 - f) * math.log(a["zoom"]) + f * math.log(b["zoom"])) * self.strength)
        cos, sin = math.cos(angle), math.sin(angle)
        rotation = np.float64([[cos, -sin], [sin, cos]])
        extents = np.float64([self.width - 1, self.height - 1])
        center = extents / 2
        anchor = extents * [self.anchor_x, self.anchor_y]
        displacement = extents * [lerp("x"), lerp("y")] * self.strength
        q = anchor + displacement + scale * rotation @ (center - anchor)
        if self.settings["edge_mode"] == "cover":
            corners = np.float64([[0, 0], [extents[0], 0], [0, extents[1]], extents])
            scale = max(scale, np.max(np.abs((corners - q) @ rotation) / center))
        linear = scale * rotation
        return np.column_stack((linear, q - linear @ center))

    def warp(self, frame, time):
        return cv2.warpAffine(frame, self.matrix(time), (self.width, self.height), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_REFLECT_101)


def make_plan(reference, source, settings, analysis_size):
    require_vision()
    ref, target = probe(reference), probe(source)
    target["sha256"] = digest(source)
    ratio = min(1, analysis_size / max(ref["width"], ref["height"]))
    width, height = [max(2, round(ref[key] * ratio)) for key in ("width", "height")]
    times = timestamps(ref)
    with contextlib.closing(decode(ref, width, height, gray=True)) as frames:
        samples = track(frames, times)
    settings = dict(settings)
    if settings["fps"] is None:
        settings["fps"] = target["fps"]
    plan = {"schema": "camera-transfer/v1", "reference": ref, "source": target, "settings": settings, "samples": samples}
    MotionPath(plan)
    return plan


def original(plan, override):
    info = dict(plan["source"])
    path = Path(override or info["path"]).resolve()
    if path.stat().st_size != info["bytes"] or digest(path) != info["sha256"]:
        raise ValueError("This File Does Not Match The Original Target Clip In The Reviewed Plan.")
    actual = probe(path)
    for key in ("stream", "width", "height", "duration"):
        if actual[key] != info[key]:
            raise ValueError("The Source Metadata In The Plan Does Not Match The Original Clip.")
    return actual


@contextlib.contextmanager
def new_destination(path):
    if path.exists():
        raise ValueError(f"Choose A New Output Path. This File Already Exists: {path}")
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=path.suffix, delete=False) as temporary:
        staged = Path(temporary.name)
    try:
        yield staged
        if os.name == "nt":
            os.rename(staged, path)
        else:
            os.link(staged, path)
    finally:
        staged.unlink(missing_ok=True)


def make_review(plan, output):
    if output.suffix.lower() != ".html":
        raise ValueError("Choose An HTML Review File.")
    template = Path(__file__).with_name("camera_review.html").read_text(encoding="utf-8")
    if "<!--CAMERA_PLAN-->" not in template:
        raise ValueError("The Review Template Is Missing Its Motion Plan Slot.")
    payload = json.dumps(plan, ensure_ascii=True, allow_nan=False).replace("<", "\\u003c")
    template = template.replace("<!--CAMERA_PLAN-->", f'<script type="application/json" id="embeddedPlan">{payload}</script>')
    with new_destination(output) as staged:
        staged.write_text(template, encoding="utf-8")


def frame_count(duration, fps):
    return max(1, math.ceil(duration * fps - 1e-7))


def output_frames(info, motion):
    fps = motion.fps
    count = frame_count(info["duration"], fps)
    with contextlib.closing(decode(info, motion.width, motion.height, fps=fps)) as frames:
        last = None
        for i in range(count):
            frame = next(frames, None)
            if frame is not None:
                last = frame
            if last is None:
                raise ValueError("The Source Contains No Decodable Frames.")
            yield motion.warp(last, i / fps)
        # Finish Reading FFmpeg's Status Even When The Last Frame Exactly Fills The Timeline.
        if next(frames, None) is not None:
            raise ValueError("The Decoder Exceeded The Target Frame Count.")


def encoder_args(info, fps, output):
    end = float(info["duration"])
    packet_length = f"setts=pts=PTS:dts=DTS:duration='min(DURATION,max(1,round({end}/TB)-PTS))'"
    command = ["ffmpeg", "-v", "error", "-xerror", "-nostdin", "-copyts", "-start_at_zero",
               "-f", "rawvideo", "-pixel_format", "bgr24", "-video_size", f"{info['width']}x{info['height']}",
               "-framerate", str(Fraction(fps).limit_denominator(1000000)), "-i", "pipe:0",
               "-i", str(info["path"]), "-map", "0:v:0", "-map", "1:a?", "-fps_mode:v", "passthrough",
               "-enc_time_base:v", "1:1000000", "-bsf:v", packet_length]
    if output is None:
        return command + ["-c:v", "rawvideo", "-c:a", "pcm_s32le", "-f", "streamhash", "-hash", "sha256", "pipe:1"]
    if output.suffix.lower() == ".mov":
        command += ["-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le"]
        audio_default = "pcm_s24le"
    else:
        pixel_format = "yuv420p" if info["width"] % 2 == 0 and info["height"] % 2 == 0 else "yuv444p"
        command += ["-c:v", "libx264", "-crf", "17", "-bf:v", "0", "-pix_fmt", pixel_format, "-movflags", "+faststart"]
        audio_default = "aac"
    for i, codec in enumerate(info["audio_codecs"]):
        can_copy = codec in {"aac", "alac", "mp3", "ac3", "eac3"} or (audio_default.startswith("pcm") and codec.startswith("pcm_"))
        command += [f"-c:a:{i}", "copy" if can_copy else audio_default]
        if not can_copy and audio_default == "aac":
            command += [f"-b:a:{i}", "256k"]
    return command + ["-video_track_timescale", "1000000", "-y", str(output)]


def feed_encoder(command, frames):
    with tempfile.TemporaryFile() as errors, subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=errors) as proc:
        try:
            try:
                for frame in frames:
                    proc.stdin.write(frame.tobytes())
                proc.stdin.close()
            except BrokenPipeError:
                pass
            summary = proc.stdout.read().decode(errors="replace").strip()
            if proc.wait():
                errors.seek(0)
                raise ValueError(errors.read().decode(errors="replace") or "FFmpeg Could Not Process The Motion Plan.")
            return summary
        finally:
            if proc.poll() is None:
                proc.kill()


def process(plan, info, output=None, owner_approved=False):
    if output is not None and not owner_approved:
        raise ValueError("Export Requires The Owner's Personal Review And Explicit Approval Of This Exact Edit.")
    require_vision()
    motion = MotionPath(plan)
    if output is not None and output.suffix.lower() not in (".mp4", ".mov"):
        raise ValueError("Choose An MP4 Or MOV Output Path.")
    with new_destination(output) if output is not None else contextlib.nullcontext(None) as staged:
        with contextlib.closing(output_frames(info, motion)) as frames:
            return feed_encoder(encoder_args(info, motion.fps, staged), frames)


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    subs = cli.add_subparsers(dest="command", required=True)
    analyze = subs.add_parser("analyze", help="Measure Motion And Write An Editable Plan.")
    analyze.add_argument("reference", type=Path)
    analyze.add_argument("source", type=Path)
    analyze.add_argument("plan", type=Path)
    analyze.add_argument("--strength", type=float, default=1)
    analyze.add_argument("--anchor-x", type=float, default=.5)
    analyze.add_argument("--anchor-y", type=float, default=.5)
    analyze.add_argument("--edge-mode", choices=["cover", "reflect"], default="cover")
    analyze.add_argument("--timing", choices=["stretch", "hold"], default="stretch")
    analyze.add_argument("--fps", type=float)
    analyze.add_argument("--analysis-size", type=int, default=720)
    for name in ("review", "check", "render"):
        parser = subs.add_parser(name)
        parser.add_argument("plan", type=Path)
        parser.add_argument("--source", type=Path, help="Locate A Moved Original Target File.")
        if name == "review":
            parser.add_argument("--output", type=Path, help="Choose A New Local HTML Review File.")
        if name == "render":
            parser.add_argument("output", type=Path)
            parser.add_argument("--owner-approved", action="store_true")
    args = cli.parse_args(argv)
    if args.command == "render" and not args.owner_approved:
        raise ValueError("Export Requires The Owner's Personal Review And Explicit Approval Of This Exact Edit.")
    if args.command == "analyze":
        if args.plan.suffix.lower() != ".json" or args.plan.exists():
            raise ValueError("Choose A New JSON Motion Plan Path.")
        finite(args.analysis_size, "Analysis Size", 64, 4096)
        keys = ("strength", "anchor_x", "anchor_y", "edge_mode", "timing", "fps")
        plan = make_plan(args.reference, args.source, {k: getattr(args, k) for k in keys}, args.analysis_size)
        with new_destination(args.plan) as staged:
            with staged.open("w", encoding="utf-8") as f:
                json.dump(plan, f, ensure_ascii=False, allow_nan=False, indent=2)
                f.write("\n")
        summary = {state: sum(s["status"] == state for s in plan["samples"]) for state in ("tracked", "translation", "held", "origin")}
        print(json.dumps({"plan": str(args.plan.resolve()), "samples": len(plan["samples"]), **summary}))
        return
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    MotionPath(plan)
    info = original(plan, args.source)
    if args.command == "review":
        plan["source"].update(info)
        out = args.output or args.plan.with_suffix(".review.html")
        make_review(plan, out)
        print(out.resolve())
    elif args.command == "check":
        print(process(plan, info))
    else:
        process(plan, info, args.output, args.owner_approved)
        print(args.output.resolve())


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as exc:
        sys.exit(str(exc))
