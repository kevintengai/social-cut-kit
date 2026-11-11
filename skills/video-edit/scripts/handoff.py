"""Portable Cut List For OpenTimelineIO Readers."""

from pathlib import Path


def otio(model):
    fps = model["fps"]

    def tagged(schema, **props):
        return {"OTIO_SCHEMA": schema, **props}

    def time(seconds):
        return tagged("RationalTime.1", rate=float(fps), value=seconds * fps)

    def span(start, duration):
        return tagged("TimeRange.1", start_time=time(start), duration=time(duration))

    def item(name, **fields):
        return dict(name=name, metadata={}, source_range=None, effects=[], markers=[], **fields)

    def track(name, kind, children):
        return tagged("Track.1", **item(name, kind=kind, children=children))

    def clip(row, duration, name):
        asset = model["assets"][row["asset"]]
        available = asset["duration"]
        ref = tagged("ExternalReference.1", name=row["asset"], metadata={}, target_url=Path(asset["path"]).as_uri(),
                     available_range=span(0, available) if available is not None else None)
        props = item(name)
        props["source_range"] = span(row["start"], duration)
        props["metadata"] = {"social_cut_kit": dict(row)}
        if row.get("speed", 1) != 1:
            props["effects"].append(tagged("LinearTimeWarp.1", name="Source Speed", effect_name="LinearTimeWarp",
                                           time_scalar=float(row["speed"]), metadata={}))
        return tagged("Clip.1", **props, media_reference=ref)

    def gap(duration):
        props = item("")
        props["source_range"] = span(0, duration)
        return tagged("Gap.1", **props)

    tracks = [track("Picture Cuts", "Video", [clip(s, s["duration"], s["asset"]) for s in model["shots"]])]
    for i, cue in enumerate(model["overlays"], 1):
        children = [gap(cue["at"])] if cue["at"] else []
        children.append(clip(cue, cue["end"]-cue["at"], cue["asset"]))
        tracks.append(track("Overlay " + str(i), "Video", children))
    # Linked Picture And Sound Become Explicit Tracks For Portable Readers.
    voice = []
    for s in model["shots"]:
        a = model["assets"][s["asset"]]
        if a["kind"] == "video" and a["audio"] and s["gain"]:
            voice.append(clip(s, s["duration"], s["asset"]))
        else:
            voice.append(gap(s["duration"]))
    tracks.append(track("Source Sound", "Audio", voice))
    for i, cue in enumerate(model["audio"], 1):
        children = [gap(cue["at"])] if cue["at"] else []
        children.append(clip(cue, cue["end"]-cue["at"], cue["asset"]))
        tracks.append(track("Audio Cue " + str(i), "Audio", children))
    stack = tagged("Stack.1", **item("Tracks", children=tracks))
    for c in model["captions"]:
        stack["markers"].append(tagged("Marker.2", name=c["text"], color="CYAN",
                                       marked_range=span(c["at"], c["end"]-c["at"]),
                                       metadata={"social_cut_kit": {"position": c["position"]}}))
    return tagged("Timeline.1", name=model["title"], metadata={"social_cut_kit": {
        "width": model["width"], "height": model["height"], "fps": fps}},
        global_start_time=time(0), tracks=stack)
