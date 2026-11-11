"""Prepare Timed Speech, Map Captions To A Cut, And Align Two Recordings."""

import argparse
from array import array
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
from tempfile import TemporaryDirectory


def stamp(raw):
    parts = raw.replace(",", ".").split(":")
    return sum(float(part) * (60**i) for i, part in enumerate(reversed(parts)))


def load_words(file):
    if file.suffix.lower() in (".srt", ".vtt"):
        words = []
        timing = re.compile(r"([\d:]+[.,]\d+)\s+-->\s+([\d:]+[.,]\d+)")
        for block in re.split(r"\n\s*\n", file.read_text(encoding="utf-8-sig").strip()):
            match = timing.search(block)
            if match:
                body = block[match.end() :].split("\n", 1)
                if len(body) > 1:
                    words.append(
                        (stamp(match[1]), stamp(match[2]), " ".join(body[1].split()))
                    )
    else:
        raw = json.loads(file.read_text(encoding="utf-8-sig"))
        if isinstance(raw, list):
            entries = raw
        elif "segments" in raw:
            entries = [
                w
                for segment in raw["segments"]
                for w in (segment.get("words") or [segment])
            ]
        else:
            entries = raw["words"]
        words = [
            (
                float(w["start"]),
                float(w["end"]),
                (w.get("word") or w.get("text") or "").strip(),
            )
            for w in entries
        ]
    if not words or any(
        not math.isfinite(s) or not math.isfinite(e) or s < 0 or e <= s or not t
        for s, e, t in words
    ):
        raise ValueError("Expected Nonempty Timed Words Or Subtitle Cues.")
    return sorted(words)


def project(words, timeline, source):
    if source not in timeline["assets"]:
        raise ValueError(f"Unknown Timeline Asset: {source}")
    fps = float(timeline["canvas"]["fps"])
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("Expected A Positive Frame Rate.")
    at = 0.0
    pieces = []
    clipped = 0
    for cut, shot in enumerate(timeline["shots"]):
        lo = float(shot["in"]) - float(shot.get("lead", 0))
        hi = float(shot["out"]) + float(shot.get("tail", 0))
        speed = float(shot.get("speed", 1))
        if not all(math.isfinite(x) for x in (lo, hi, speed)) or hi <= lo or speed <= 0:
            raise ValueError("Invalid Shot Trim Or Speed.")
        length = math.floor(((hi - lo) / speed) * fps + 0.5) / fps
        if shot["asset"] == source:
            for start, end, text in words:
                if start < hi and end > lo:
                    if start < lo - 0.0001 or end > hi + 0.0001:
                        clipped += 1
                        continue
                    s = at + max(0.0, (start - lo) / speed)
                    e = at + min(length, (end - lo) / speed)
                    if e > s:
                        pieces.append((s, e, text, cut))
        at += length
    return pieces, clipped


def captions(words):
    cues, active = [], []

    def flush():
        if active:
            cues.append(
                {
                    "at": round(active[0][0], 3),
                    "end": round(max(w[1] for w in active), 3),
                    "text": " ".join(w[2] for w in active),
                    "position": "bottom",
                }
            )
            active.clear()

    for word in words:
        if active and (
            word[3] != active[-1][3]
            or word[0] - active[-1][1] > 0.4
            or word[1] - active[0][0] > 3
            or sum(len(w[2]) + 1 for w in active) + len(word[2]) > 44
        ):
            flush()
        active.append(word)
        if word[2].endswith((".", "?", "!")):
            flush()
    flush()
    return cues


PHRASE_DEFAULTS = {"max_words": 4, "max_chars": 28, "pause": 0.4, "min_seconds": 0.3}
ABBREVIATIONS = {"mr", "mrs", "ms", "dr", "st", "vs", "jr", "sr", "prof", "e.g", "i.e", "u.s", "u.k"}


def edges(text):
    """Split A Token Into Leading Punctuation, Its Core, And Trailing Punctuation."""
    lead = re.match(r"[^\w]*", text)[0]
    rest = text[len(lead):]
    trail = re.search(r"[^\w]*$", rest)[0]
    return lead, rest[: len(rest) - len(trail)], trail


def single_words(words):
    """Estimate Per-Word Times Inside Units That Carry Several Words, Such As Subtitle Cues."""
    result, estimated = [], 0
    for start, end, text in words:
        parts = text.split()
        if len(parts) < 2:
            result.append((start, end, text))
            continue
        estimated += 1
        weights = [len(part) + 1 for part in parts]
        scale = (end - start) / sum(weights)
        at = start
        for part, weight in zip(parts, weights):
            result.append((at, at + weight * scale, part))
            at += weight * scale
    return result, estimated


def join_numbers(words, gap=0.3):
    """Rejoin One Spoken Number That A Recognizer Split, Such As $2 And ,000 Or 50 And %."""
    result, joined = [], 0
    for start, end, text in words:
        if result:
            first, last, before = result[-1]
            continues = (
                (re.search(r"\d$", before) and re.match(r"[.,:]\d|[%°]|(st|nd|rd|th)[.,!?]?$", text))
                or (re.fullmatch(r"[$€£¥#]", before) and re.match(r"\d", text))
                or (re.search(r"\d,$", before) and re.match(r"\d{3}(\D|$)", text))
            )
            if continues and start - last <= gap:
                result[-1] = (first, max(last, end), before + text)
                joined += 1
                continue
        result.append((start, end, text))
    return result, joined


def read_fixes(pairs, file):
    fixes = {}
    if file:
        loaded = json.loads(file.read_text(encoding="utf-8-sig"))
        if not isinstance(loaded, dict) or not all(isinstance(v, str) for v in loaded.values()):
            raise ValueError("The Fixes File Must Be A JSON Object Of Heard Text To Caption Text.")
        fixes.update(loaded)
    for pair in pairs or []:
        heard, mark, shown = pair.partition("=")
        if not mark:
            raise ValueError("Write Each Fix As Heard=Shown.")
        fixes[heard] = shown
    rules = []
    for heard, shown in fixes.items():
        parts = [edges(part)[1].casefold() or part.casefold() for part in heard.split()]
        if not parts:
            raise ValueError("A Fix Needs The Heard Text Before The Equals Sign.")
        rules.append((parts, " ".join(shown.split())))
    return sorted(rules, key=lambda rule: -len(rule[0]))


def apply_fixes(words, rules):
    """Change Caption Spelling Only. Matching Ignores Case And Surrounding Punctuation."""
    result, used, i = [], 0, 0
    while i < len(words):
        for parts, shown in rules:
            span = words[i : i + len(parts)]
            cores = [edges(w[2])[1].casefold() or w[2].casefold() for w in span]
            if len(span) < len(parts) or cores != parts:
                continue
            used += 1
            fresh = shown.split()
            if len(fresh) == len(span):
                for (start, end, text), new in zip(span, fresh):
                    lead, _, trail = edges(text)
                    result.append((start, end, lead + new + trail))
            elif fresh:
                lead, trail = edges(span[0][2])[0], edges(span[-1][2])[2]
                result.append((span[0][0], span[-1][1], lead + shown + trail))
            i += len(span)
            break
        else:
            result.append(words[i])
            i += 1
    return result, used


def project_phrases(words, timeline, source):
    """Map Words To Edit Time. A Word Cut By A Shot Edge Stays In The Shot That Holds Its Midpoint."""
    if source not in timeline["assets"]:
        raise ValueError(f"Unknown Timeline Asset: {source}")
    fps = float(timeline.get("canvas", {}).get("fps", 30))
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("Expected A Positive Frame Rate.")
    ranges, frame = [], 0
    for shot in timeline["shots"]:
        lo = float(shot.get("in", 0)) - float(shot.get("lead", 0))
        hi = float(shot["out"]) + float(shot.get("tail", 0))
        speed = float(shot.get("speed", 1))
        if not all(math.isfinite(x) for x in (lo, hi, speed)) or hi <= lo or speed <= 0:
            raise ValueError("Invalid Shot Trim Or Speed.")
        length = math.floor(((hi - lo) / speed) * fps + 0.5)
        ranges.append((lo, hi, speed, frame, length, shot["asset"]))
        frame += length
    pieces, clamped, dropped, crossing = [], [], [], 0
    for index, (lo, hi, speed, first, length, asset) in enumerate(ranges):
        if asset != source or length < 1:
            continue
        # A Split Of One Continuous Take Changes The Picture While The Sound Carries On.
        joined_before = index > 0 and ranges[index - 1][5] == source and abs(ranges[index - 1][1] - lo) < 0.001
        joined_after = index + 1 < len(ranges) and ranges[index + 1][5] == source and abs(ranges[index + 1][0] - hi) < 0.001
        for start, end, text in words:
            if not (start < hi and end > lo):
                continue
            early, late = start < lo - 0.0001, end > hi + 0.0001
            crossing += early or late
            middle = (start + end) / 2
            spoken = [round(start, 3), round(end, 3)]
            if not lo <= middle < hi:
                if not ((middle < lo and joined_before) or (middle >= hi and joined_after)):
                    dropped.append({"text": text, "shot": index + 1, "source_seconds": spoken,
                                    "seconds_inside_shot": round(min(end, hi) - max(start, lo), 3)})
                continue
            kept = (max(start, lo), min(end, hi))
            at = first / fps + (kept[0] - lo) / speed
            until = first / fps + (kept[1] - lo) / speed
            pieces.append({"at": at, "end": until, "text": text, "shot": index,
                           "first": first, "last": first + length})
            if early or late:
                clamped.append({"text": text, "shot": index + 1, "source_seconds": spoken,
                                "kept_source_seconds": [round(kept[0], 3), round(kept[1], 3)],
                                "timeline_seconds": [round(at, 3), round(until, 3)],
                                "trimmed": "both" if early and late else "start" if early else "end",
                                "sound_continues_across_cut": bool((not early or joined_before)
                                                                   and (not late or joined_after))})
    pieces.sort(key=lambda p: (p["shot"], p["at"], p["end"]))
    return pieces, clamped, dropped, crossing, fps, frame


def ends_sentence(text):
    _, core, trail = edges(text)
    if not re.search(r"[.?!…]", trail):
        return False
    # A Title Or A Lone Initial Before A Period Is Not The End Of A Sentence.
    initial = len(core) == 1 and core.isalpha() and core != "I"
    return core.casefold() not in ABBREVIATIONS and not initial


def phrase_captions(pieces, fps, options, position="bottom"):
    """Group Words Into Short Cues On The Frame Grid. Cues Stay Inside One Shot And Never Overlap."""
    groups, active = [], []
    for word in pieces:
        if active:
            last = active[-1]
            length = sum(len(w["text"]) + 1 for w in active) + len(word["text"])
            if (
                word["shot"] != last["shot"]
                or word["at"] - last["end"] >= options["pause"]
                or len(active) >= options["max_words"]
                or length > options["max_chars"]
                or (options["sentence_breaks"] and ends_sentence(last["text"]))
            ):
                groups.append(active)
                active = []
        active.append(word)
    if active:
        groups.append(active)
    rows = []
    for group in groups:
        first, last = group[0]["first"], group[0]["last"]
        start = min(max(math.floor(group[0]["at"] * fps + 0.5), first), last - 1)
        stop = min(max(math.floor(group[-1]["end"] * fps + 0.5), start + 1), last)
        text = " ".join(w["text"] for w in group)
        if rows and rows[-1]["shot"] == group[0]["shot"]:
            start = max(start, rows[-1]["stop"])
            if start >= last:
                # No Frame Is Left In This Shot, So The Words Join The Previous Cue.
                rows[-1]["text"] += " " + text
                continue
            stop = max(stop, start + 1)
        rows.append({"shot": group[0]["shot"], "start": start, "stop": stop, "limit": last, "text": text})
    minimum = math.ceil(options["min_seconds"] * fps - 1e-9)
    short = []
    for i, row in enumerate(rows):
        following = rows[i + 1] if i + 1 < len(rows) and rows[i + 1]["shot"] == row["shot"] else None
        limit = following["start"] if following else row["limit"]
        # A Gap Shorter Than The Pause Is Closed So The Text Does Not Flicker Between Phrases.
        if following and (following["start"] - row["stop"]) / fps < options["pause"]:
            row["stop"] = following["start"]
        if row["stop"] - row["start"] < minimum:
            row["stop"] = min(limit, row["start"] + minimum)
        if row["stop"] - row["start"] < minimum:
            short.append({"text": row["text"], "at": round(row["start"] / fps, 6),
                          "seconds": round((row["stop"] - row["start"]) / fps, 6)})
    cues = [{"at": round(row["start"] / fps, 6), "end": round(row["stop"] / fps, 6),
             "text": row["text"], "position": position} for row in rows]
    return cues, short


def subrip(cues):
    def clock(seconds):
        total = int(seconds * 1000 + 0.5)
        whole, milli = divmod(total, 1000)
        minutes, secs = divmod(whole, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milli:03d}"

    ordered = sorted(cues, key=lambda c: c["at"])
    return "\n".join(f"{i}\n{clock(c['at'])} --> {clock(c['end'])}\n{c['text']}\n" for i, c in enumerate(ordered, 1))


def save(path, result):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def decoded_samples(path):
    """Decode Any Source To 16 kHz Mono Float Samples For The Optional Recognizer. The Source Is Only Read."""
    import numpy

    raw = subprocess.check_output(
        ["ffmpeg", "-v", "error", "-nostdin", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "pipe:1"]
    )
    return numpy.frombuffer(raw, dtype="<f4")


def envelope(path, seconds, start=0):
    # A Later Start Reads The Same Stretch Of Both Recordings To Measure Drift.
    seek = ["-ss", str(start)] if start else []
    raw = subprocess.check_output(
        [
            "ffmpeg",
            "-v",
            "error",
            *seek,
            "-i",
            str(path),
            "-vn",
            "-t",
            str(seconds),
            "-ac",
            "1",
            "-ar",
            "4000",
            "-f",
            "s16le",
            "pipe:1",
        ]
    )
    pcm = array("h")
    pcm.frombytes(raw)
    if sys.byteorder != "little":
        pcm.byteswap()
    # A 10 ms peak envelope is used only for analysis. Original media is never changed.
    return [
        math.log1p(max(abs(v) for v in pcm[i : i + 40]))
        for i in range(0, len(pcm) - 39, 40)
    ]


def sync(a):
    if not 1 <= a.seconds <= 300 or not 0 <= a.lag <= min(30, a.seconds / 2):
        raise ValueError(
            "Use A 1 To 300 Second Sample And A Lag At Most Half Its Length, Up To 30 Seconds."
        )
    start = getattr(a, "start", 0)
    if not math.isfinite(start) or not 0 <= start <= 86400:
        raise ValueError("Use A Start From 0 To 86400 Seconds.")
    x, y = (envelope(p, a.seconds, start) for p in (a.primary, a.secondary))
    if min(len(x), len(y)) < 50:
        raise ValueError("At Least Half A Second Of Overlapping Audio Is Needed.")
    candidates = []
    for delta in range(-round(a.lag * 100), round(a.lag * 100) + 1):
        s, t = max(-delta, 0), max(delta, 0)
        size = min(len(x) - s, len(y) - t)
        if size < max(50, min(len(x), len(y)) // 2):
            continue
        a1, a2 = x[s : s + size], y[t : t + size]
        m1, m2 = statistics.fmean(a1), statistics.fmean(a2)
        den = math.sqrt(sum((v - m1) ** 2 for v in a1) * sum((v - m2) ** 2 for v in a2))
        if den > 0.001:
            candidates.append(
                (sum((v - m1) * (w - m2) for v, w in zip(a1, a2)) / den, delta)
            )
    if not candidates:
        raise ValueError("Neither Track Supplied A Distinct Alignment Signal.")
    score, lag = max(candidates)
    others = [c for c, d in candidates if abs(d - lag) >= 10]
    result = {
        "secondary_event_later_by_seconds": lag / 100,
        "correlation": round(score, 4),
        "next_distinct_correlation": round(max(others), 4) if others else None,
        "resolution_seconds": 0.01,
    }
    if start:
        result["sample_start_seconds"] = start
    print(json.dumps(result, indent=2))


def phrase_options(a):
    """Return Phrase Settings When Any Phrase Option Was Supplied, Otherwise None."""
    chosen = (a.max_words, a.max_chars, a.pause, a.min_seconds, a.sentence_breaks, a.join_numbers, a.fix, a.fixes)
    if not a.phrases and all(value is None for value in chosen):
        return None
    options = dict(PHRASE_DEFAULTS)
    for key in PHRASE_DEFAULTS:
        if getattr(a, key) is not None:
            options[key] = getattr(a, key)
    if not 1 <= options["max_words"] <= 50 or not 1 <= options["max_chars"] <= 400:
        raise ValueError("Use 1 To 50 Words And 1 To 400 Characters For A Phrase.")
    if not 0.01 <= options["pause"] <= 30 or not 0 <= options["min_seconds"] <= 30:
        raise ValueError("Use A Pause From 0.01 To 30 Seconds And A Minimum Time From 0 To 30 Seconds.")
    options["sentence_breaks"] = a.sentence_breaks != "off"
    options["join_numbers"] = a.join_numbers != "off"
    options["fixes"] = read_fixes(a.fix, a.fixes)
    return options


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    cmd = parser.add_subparsers(dest="cmd", required=True)
    trans = cmd.add_parser(
        "transcribe", help="Run A Separately Installed Local Whisper CLI"
    )
    trans.add_argument("source", type=Path)
    trans.add_argument("output", type=Path)
    trans.add_argument("--model", default="base")
    trans.add_argument("--language")
    trans.add_argument(
        "--backend", choices=("whisper-cli", "faster-whisper"), default="whisper-cli"
    )
    trans.add_argument("--engine", default="whisper")
    mapping = cmd.add_parser(
        "captions", help="Map A Word Transcript Or SRT/VTT To Timeline Shots"
    )
    mapping.add_argument("transcript", type=Path)
    mapping.add_argument("timeline", type=Path)
    mapping.add_argument("--asset", required=True)
    mapping.add_argument("--output", required=True, type=Path)
    mapping.add_argument(
        "--with-timeline",
        action="store_true",
        help="Append Cues To A New Editable Timeline",
    )
    mapping.add_argument(
        "--phrases",
        action="store_true",
        help="Group Word Timings Into Short On-Screen Phrases. Any Option Below Also Turns This On",
    )
    mapping.add_argument("--max-words", type=int, help="Most Words In One Phrase. The Phrase Default Is 4")
    mapping.add_argument("--max-chars", type=int, help="Most Characters In One Phrase. The Phrase Default Is 28")
    mapping.add_argument(
        "--pause", type=float, metavar="SECONDS", help="A Silence This Long Forces A New Phrase. The Phrase Default Is 0.4"
    )
    mapping.add_argument(
        "--min-seconds", type=float, help="Shortest Time A Phrase Stays On Screen. The Phrase Default Is 0.3"
    )
    mapping.add_argument(
        "--sentence-breaks", choices=("on", "off"), help="Start A New Phrase After Sentence Punctuation. On By Default"
    )
    mapping.add_argument(
        "--join-numbers", choices=("on", "off"), help="Rejoin Split Number Fragments Such As $2 And ,000. On By Default"
    )
    mapping.add_argument(
        "--fix", action="append", metavar="HEARD=SHOWN", help="Caption-Only Spelling Fix. Repeat For More. Empty SHOWN Removes The Word"
    )
    mapping.add_argument("--fixes", type=Path, help="JSON Object Of Heard Text To Caption Text")
    mapping.add_argument("--position", choices=("top", "center", "bottom"), help="Caption Position For The New Cues")
    mapping.add_argument("--srt", type=Path, help="Also Write The New Cues To A New SubRip File")
    mapping.add_argument(
        "--replace-existing",
        action="store_true",
        help="With --with-timeline, Remove Existing Captions At The Same Position First",
    )
    align = cmd.add_parser(
        "sync", help="Find The Offset Between Camera And External Audio"
    )
    align.add_argument("primary", type=Path)
    align.add_argument("secondary", type=Path)
    align.add_argument("--seconds", type=float, default=30)
    align.add_argument("--lag", type=float, default=5)
    align.add_argument(
        "--start",
        type=float,
        default=0,
        help="Begin Both Samples This Many Seconds In, To Measure Drift Later In A Take",
    )
    level = cmd.add_parser(
        "levels", help="Measure Source Audio Level And Available Gain Headroom"
    )
    level.add_argument("source", type=Path)
    return parser


def main(argv=None):
    parser = build_parser()
    a = parser.parse_args(argv)
    try:
        if a.cmd == "transcribe":
            if a.output.exists():
                raise FileExistsError(a.output)
            src = a.source.resolve(strict=True)
            if a.backend == "faster-whisper":
                try:
                    from faster_whisper import WhisperModel
                except ImportError as exc:
                    raise ValueError(
                        "Install faster-whisper In This Python Environment Or Select The Whisper CLI."
                    ) from exc
                model = WhisperModel(a.model, device="cpu", compute_type="int8")
                try:
                    segments, _ = model.transcribe(
                        str(src), language=a.language, word_timestamps=True
                    )
                except TypeError:
                    # Some Releases Of The Recognizer's File Reader Reject Its Own Options.
                    # FFmpeg Then Decodes The Same 16 kHz Mono Samples For It.
                    segments, _ = model.transcribe(
                        decoded_samples(src), language=a.language, word_timestamps=True
                    )
                result = [
                    (w.start, w.end, w.word.strip())
                    for segment in segments
                    for w in segment.words or []
                    if w.word.strip() and w.end > w.start
                ]
            else:
                with TemporaryDirectory() as td:
                    args = [
                        a.engine,
                        str(src),
                        "--model",
                        a.model,
                        "--output_format",
                        "json",
                        "--word_timestamps",
                        "True",
                        "--output_dir",
                        td,
                    ]
                    if a.language:
                        args.extend(["--language", a.language])
                    subprocess.run(args, check=True)
                    result = load_words(Path(td) / (a.source.stem + ".json"))
            if not result:
                raise ValueError("No Timed Speech Found.")
            save(
                a.output,
                {"words": [{"start": s, "end": e, "text": t} for s, e, t in result]},
            )
        elif a.cmd == "captions":
            timeline = json.loads(a.timeline.read_text(encoding="utf-8-sig"))
            options = phrase_options(a)
            if a.replace_existing and not a.with_timeline:
                raise ValueError("Use --replace-existing Together With --with-timeline.")
            if a.srt and a.srt.exists():
                raise FileExistsError(a.srt)
            report = {}
            if options is None:
                mapped, clipped = project(load_words(a.transcript), timeline, a.asset)
                cues = captions(mapped)
                for cue in cues if a.position else []:
                    cue["position"] = a.position
            else:
                words, estimated = single_words(load_words(a.transcript))
                joined = fixed = 0
                if options["join_numbers"]:
                    words, joined = join_numbers(words)
                if options["fixes"]:
                    words, fixed = apply_fixes(words, options["fixes"])
                pieces, clamped, dropped, clipped, fps, _ = project_phrases(
                    words, timeline, a.asset
                )
                cues, short = phrase_captions(pieces, fps, options, a.position or "bottom")
                report = {
                    "mode": "phrases",
                    "clamped_words": clamped,
                    "dropped_words": dropped,
                    "below_minimum_time": short,
                    "joined_numbers": joined,
                    "spelling_fixes": fixed,
                    "estimated_word_timings": estimated,
                }
            if not cues:
                raise ValueError(
                    "No Complete Speech Units Fall Inside This Asset's Cuts."
                )
            if a.with_timeline:
                for asset in timeline["assets"].values():
                    path = (a.timeline.resolve().parent / asset["path"]).resolve()
                    try:
                        asset["path"] = os.path.relpath(path, a.output.resolve().parent)
                    except ValueError:
                        asset["path"] = str(path)
                existing = timeline.get("captions", [])
                if a.replace_existing:
                    spot = a.position or "bottom"
                    existing = [c for c in existing if c.get("position", "bottom") != spot]
                timeline["captions"] = sorted(
                    existing + cues, key=lambda c: c["at"]
                )
            save(a.output, timeline if a.with_timeline else cues)
            if a.srt:
                with a.srt.open("x", encoding="utf-8", newline="\n") as handle:
                    handle.write(subrip(cues))
            if report:
                print(
                    json.dumps(
                        {"cues": len(cues), "speech_units_cut_at_boundaries": clipped, **report},
                        indent=2,
                        ensure_ascii=True,
                    )
                )
            else:
                print(
                    json.dumps(
                        {"cues": len(cues), "speech_units_cut_at_boundaries": clipped}
                    )
                )
        elif a.cmd == "sync":
            sync(a)
        else:
            proc = subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-nostats",
                    "-i",
                    str(a.source),
                    "-vn",
                    "-af",
                    "volumedetect",
                    "-f",
                    "null",
                    "-",
                ],
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            vals = dict(
                re.findall(r"(mean_volume|max_volume):\s+([-\d.]+) dB", proc.stderr)
            )
            if "max_volume" not in vals:
                raise ValueError("Could Not Read Audio Level Measurements.")
            print(
                json.dumps(
                    {
                        "mean_dbfs": float(vals["mean_volume"]),
                        "peak_dbfs": float(vals["max_volume"]),
                        "gain_available_to_minus_1_dbfs": round(
                            -1 - float(vals["max_volume"]), 2
                        ),
                    },
                    indent=2,
                )
            )
    except (
        OSError,
        KeyError,
        TypeError,
        ValueError,
        subprocess.CalledProcessError,
    ) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
