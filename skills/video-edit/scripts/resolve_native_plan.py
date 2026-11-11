"""Plan Native Resolve Tracks And Source Selections Without Opening Resolve."""

import math

from timeline import framing


def frames(seconds, fps):
    return math.floor(seconds * fps + 0.5)


def plan_timeline(model):
    fps, w, h = model["fps"], model["width"], model["height"]
    tracks = {"video": ["Picture"], "audio": ["Source Audio"]}
    clips = []

    def place(role, kind, index, row, duration, **options):
        clips.append(dict(role=role, kind=kind, track=index, at=frames(row["at"], fps),
                          frames=frames(duration, fps), **options))

    def lanes(rows, track_type, label):
        # Later Composited Elements Must Be Above Every Earlier Intersecting Element.
        start = len(tracks[track_type]) + 1
        used = []
        for row in rows:
            overlap = [lane for at, end, lane in used if at < row["end"] and end > row["at"]]
            lane = max(overlap, default=start - 1) + 1
            if lane > len(tracks[track_type]):
                tracks[track_type].append(label + " " + str(lane - start + 1))
            used.append((row["at"], row["end"], lane))
            yield row, lane

    def transform(left, top, width, height, zoom):
        return {"ZoomX": zoom, "ZoomY": zoom, "Pan": left + (width - w) / 2,
                "Tilt": (h - height) / 2 - top}

    for idx, shot in enumerate(model["shots"]):
        asset = model["assets"][shot["asset"]]
        original = framing(asset["video"], w, h, "contain", 1, 0, 0)["browser"]
        left, top, width, height = shot["geometry"]["browser"]
        common = dict(asset=shot["asset"], source_in=shot["start"], source_out=shot["end"],
                      speed=shot["speed"], shot=idx + 1)
        place("picture", "video", 1, shot, shot["duration"], **common,
              transform=transform(left*w, top*h, width*w, height*h, width/original[2]),
              color={key: shot[key] for key in ("brightness", "contrast", "saturation")})
        if asset["kind"] == "video" and asset["audio"]:
            place("source_audio", "audio", 1, shot, shot["duration"], gain=shot["gain"], **common)

    for row, lane in lanes(model["overlays"], "video", "Overlay"):
        asset = model["assets"][row["asset"]]
        _, _, bw, bh = framing(asset["video"], w, h, "contain", 1, 0, 0)["browser"]
        zoom = row["width"] / (bw*w)
        duration = row["end"] - row["at"]
        place("overlay", "video", lane, row, duration, asset=row["asset"],
              source_in=row["start"], source_out=row["start"] + duration, speed=1,
              transform=transform(row["x"], row["y"], row["width"], bh*h*zoom, zoom))
    for row, lane in lanes(model["audio"], "audio", "Sound"):
        duration = row["end"] - row["at"]
        place("sound", "audio", lane, row, duration, asset=row["asset"],
              source_in=row["start"], source_out=row["start"] + duration, speed=1, gain=row["gain"])
    for row, lane in lanes(model["captions"], "video", "Captions"):
        place("caption", "video", lane, row, row["end"]-row["at"],
              text=row["text"], position=row["position"])
    keys = {c["asset"] for c in clips if "asset" in c}
    return dict(title=model["title"], width=w, height=h, fps=fps, frames=frames(model["duration"], fps),
                caption_style=model["caption_style"], tracks=tracks, clips=clips,
                assets={key: {"path": a["path"], "kind": a["kind"]} for key, a in model["assets"].items()
                        if key in keys})
