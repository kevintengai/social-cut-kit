"""Keep A Video Library: One Record Per Video, Snapshots, Retention, An Index, And Findings."""

import argparse
import bisect
from datetime import date, datetime
import math
from pathlib import Path
import re
import sys
import unicodedata

sys.path.insert(0, str(Path(__file__).resolve().parent))
from desk_support import (  # noqa: E402
    STANDARD_PACE,
    DeskParser,
    clock,
    defaults_file,
    guard_streams,
    number_text,
    read_defaults,
    read_object,
    read_text,
    tidy_json,
    write_new,
    write_text,
)


LIBRARY_FORMAT = "school.video-library/1"
VIDEO_FORMAT = "school.video/1"
FINDINGS_FORMAT = "school.findings/1"
MISSING = "Not Captured"
PAST = "Past The End"
COUNTS = ("views", "viewers", "follows", "likes", "comments", "shares", "saves", "reposts")
COMPARE_SECONDS = (1, 2, 3, 5, 10, 15, 20, 30, 45, 60, 90, 120, 180)
STATUSES = ("open", "supported", "weakened")
SIDES = {"supported": "supports", "weakened": "weakens"}
ID_RULE = re.compile(r"[a-z0-9][a-z0-9-]{0,79}")
BACKLOG_LINE = re.compile(r"^- \[( |x|X)\] (.*)$")
CUE_TIME = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{1,3})")
BACKLOG_HEAD = (
    "# Idea Backlog\n\n"
    "One Line Per Idea, Oldest First. An Open Line Starts With `- [ ]`. "
    "A Used Line Starts With `- [x]`.\n\n"
)


# Values


def one_line(value, what):
    text = str(value)
    if "\n" in text or "\r" in text:
        raise ValueError(f"Write {what} On One Line.")
    return " ".join(text.split())


def moment(text, what):
    """Accept 2026-11-05, 2026-11-05 09:30, Or An ISO Time With An Offset."""
    raw = str(text).strip()
    if raw.endswith(("Z", "z")):
        raw = raw[:-1] + "+00:00"
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
            return date.fromisoformat(raw).isoformat()
        return datetime.fromisoformat(raw.replace(" ", "T", 1)).isoformat(timespec="minutes")
    except ValueError as exc:
        raise ValueError(f"Write {what} As 2026-11-05 Or 2026-11-05 09:30.") from exc


def now():
    return datetime.now().isoformat(timespec="minutes")


def today():
    return date.today().isoformat()


def spoken(stamp):
    """Show A Stored Time With A Space Between The Date And The Clock."""
    return MISSING if not stamp else str(stamp).replace("T", " ", 1)


def whole(text, what):
    """Read A Count Such As 12840, 12,840, Or 12.8K. Return It With Any Rounded Form."""
    raw = str(text).strip()
    match = re.fullmatch(r"(\d+(?:[.,]\d+)?)\s*([kKmMbB])", raw)
    if match:
        scale = {"k": 1e3, "m": 1e6, "b": 1e9}[match.group(2).lower()]
        figure = match.group(1)
        # A comma before exactly three digits groups thousands; otherwise it is a decimal mark.
        figure = figure.replace(",", "" if re.search(r",\d{3}$", figure) else ".")
        return int(round(float(figure) * scale)), raw
    if re.fullmatch(r"\d+|\d{1,3}(,\d{3})+", raw):
        return int(raw.replace(",", "")), None
    raise ValueError(f"Write {what} As A Whole Count Such As 12840, 12,840, Or 12.8K.")


def percent(text, what):
    raw = str(text).strip().rstrip("%").strip().replace(",", ".")
    try:
        value = float(raw)
    except ValueError:
        value = math.nan
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"Write {what} As A Percent Such As 87.5 Or 87.5%.")
    return value


def duration(text, what):
    try:
        return clock(text)
    except argparse.ArgumentTypeError as exc:
        raise ValueError(f"{what}: {exc}") from exc


def slug(title):
    plain = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    return "-".join(re.findall(r"[a-z0-9]+", plain.lower()))[:48].strip("-") or "video"


def count_text(value):
    return MISSING if value is None else f"{value:,}"


def percent_text(value):
    return MISSING if value is None else f"{value:.1f}%"


def seconds_text(value):
    if value is None:
        return MISSING
    return f"{number_text(value, 2)} Second{'' if value == 1 else 's'}"


def cell(value):
    """Make User Text Safe Inside One Markdown Table Cell."""
    return str(value).replace("|", "\\|").replace("\n", " ")


def plural(count, word):
    return f"{count} {word}{'' if count == 1 else 's'}"


# Storage


class Library:
    def __init__(self, root):
        self.root = Path(root).expanduser()
        self.marker = self.root / "library.json"
        self.videos = self.root / "videos"
        self.findings_file = self.root / "findings.json"
        self.captures = self.root / "captures"
        self.backlog_file = self.root / "backlog.md"

    def require(self):
        if not self.marker.is_file():
            raise ValueError(
                f"No Video Library At {self.root}. Start One With The init Command."
            )
        return self

    def video_file(self, key):
        if not ID_RULE.fullmatch(str(key)):
            raise ValueError(
                "A Video ID Uses Lower-Case Letters, Digits, And Hyphens, "
                "Such As 2026-11-03-find-the-ready-repair."
            )
        return self.videos / f"{key}.json"

    def read_video(self, path):
        record = read_object(path, "A Video Record")
        if record.get("format") != VIDEO_FORMAT:
            raise ValueError(f"{path} Is Not A Video Record.")
        if record.get("id") != path.stem or not record.get("title"):
            raise ValueError(
                f"{path} Needs A title And An id That Matches Its File Name, {path.stem}."
            )
        for key in ("snapshots", "retention"):
            if not isinstance(record.setdefault(key, []), list):
                raise ValueError(f"{path} Needs A List Under {key}.")
        return record

    def video(self, key):
        path = self.video_file(key)
        if not path.is_file():
            raise ValueError(f"No Video Record Named {key}. Run index To List The IDs.")
        return self.read_video(path)

    def all_videos(self):
        records = [self.read_video(path) for path in sorted(self.videos.glob("*.json"))]
        return sorted(
            records,
            key=lambda r: (str(r.get("posted") or r.get("created") or ""), r["id"]),
            reverse=True,
        )

    def save_video(self, record):
        record["updated"] = now()
        write_text(self.video_file(record["id"]), tidy_json(record) + "\n")

    def findings(self):
        if not self.findings_file.exists():
            return {"format": FINDINGS_FORMAT, "findings": []}
        data = read_object(self.findings_file, "A Findings File")
        if data.get("format") != FINDINGS_FORMAT or not isinstance(data.get("findings"), list):
            raise ValueError(f"{self.findings_file} Is Not A Findings File.")
        for entry in data["findings"]:
            if not isinstance(entry, dict) or not entry.get("id") or not entry.get("hypothesis"):
                raise ValueError(f"Each Finding In {self.findings_file} Needs An id And A hypothesis.")
            if entry.setdefault("status", "open") not in STATUSES:
                raise ValueError(f"{entry['id']} Has A Status Other Than open, supported, Or weakened.")
            for key in ("evidence", "history"):
                if not isinstance(entry.setdefault(key, []), list):
                    raise ValueError(f"{entry['id']} Needs A List Under {key}.")
        return data

    def save_findings(self, data):
        write_text(self.findings_file, tidy_json(data) + "\n")

    def rebuild(self):
        """Regenerate Every Readable File From The JSON Records."""
        records, findings = self.all_videos(), self.findings()
        for record in records:
            refresh(self.videos / f"{record['id']}.md", video_page(record, findings))
        refresh(self.root / "index.md", index_page(records, read_object(self.marker)))
        refresh(self.root / "findings.md", findings_page(findings, records))
        return records, findings


def refresh(path, text):
    try:
        if read_text(path) == text:
            return
    except (OSError, UnicodeError):
        pass
    write_text(path, text)


# Derived Numbers


def newest(entries):
    return sorted(entries, key=lambda entry: str(entry.get("captured") or ""), reverse=True)


def level_at(entry, second):
    """Read One Retention Entry At A Second. Return A Percent, PAST, Or None."""
    length = entry.get("duration_seconds")
    if length is not None and second > length + 0.25:
        return PAST
    curve = entry.get("curve") or []
    if len(curve) >= 2:
        times = [point[0] for point in curve]
        slack = max(0.25, 0.005 * (times[-1] - times[0]))
        if times[0] - slack <= second <= times[-1] + slack:
            if second <= times[0]:
                return curve[0][1]
            if second >= times[-1]:
                return curve[-1][1]
            at = bisect.bisect_right(times, second)
            (t0, p0), (t1, p1) = curve[at - 1], curve[at]
            return p0 + (p1 - p0) * (second - t0) / (t1 - t0)
    for row in entry.get("readings") or []:
        if row.get("seconds") == second:
            return row.get("retention_pct")
    return None


def day_of(record, stamp):
    """Return Whole Days From Posting To A Capture, Or None."""
    try:
        posted = date.fromisoformat(str(record.get("posted"))[:10])
        return (date.fromisoformat(str(stamp)[:10]) - posted).days
    except ValueError:
        return None


def comparable(record):
    """Derive The Numbers That Can Be Compared Across Videos, Each With Its Source."""
    found = {}
    runtime = record.get("runtime_seconds")
    # Every number comes from the latest snapshot, so one row never mixes two ages.
    for snap in newest(record.get("snapshots") or [])[:1]:
        source = "Snapshot " + spoken(snap.get("captured"))
        if "views" not in found and snap.get("views") is not None:
            found["views"] = (snap["views"], source)
        watch = snap.get("average_watch_seconds")
        if "watch_share" not in found and watch is not None and runtime:
            found["watch_share"] = (100 * watch / runtime, source)
        outside = snap.get("non_follower_share_pct")
        if outside is None and snap.get("follower_share_pct") is not None:
            outside = 100 - snap["follower_share_pct"]
        if "outside" not in found and outside is not None:
            found["outside"] = (outside, source)
        if (
            "follows" not in found
            and snap.get("follows") is not None
            and snap.get("viewers")
        ):
            found["follows"] = (1000 * snap["follows"] / snap["viewers"], source)
    for entry in newest(record.get("retention") or [])[:1]:
        source = "Retention " + spoken(entry.get("captured"))
        found["at_10"] = (level_at(entry, 10), source)
        if entry.get("drop_3_to_10_points") is not None:
            found["drop"] = (entry["drop_3_to_10_points"], source)
        elif found["at_10"][0] == PAST:
            found["drop"] = (PAST, source)
    return found


def shown(found, key, kind="percent"):
    value = found.get(key, (None, ""))[0]
    if value is None:
        return MISSING
    if value == PAST:
        return PAST
    if kind == "percent":
        return f"{value:.1f}%"
    if kind == "count":
        return f"{value:,}"
    if kind == "points":
        return f"{number_text(value)} Points"
    return f"{value:.2f}"


def standing(record):
    if record.get("kind") == "review":
        return "Review, Not Evidence"
    snaps = newest(record.get("snapshots") or [])
    if snaps:
        day = day_of(record, snaps[0].get("captured"))
        return "Measured" if day is None else f"Measured Day {day}"
    if record.get("retention"):
        return "Retention Only"
    return "Posted, No Numbers"


def measured(record):
    return bool(record.get("snapshots") or record.get("retention"))


# Readable Pages


def index_page(records, library):
    posted = sum(1 for record in records if record.get("kind") != "review")
    lines = ["# Video Library Index", ""]
    context = [
        f"{label}: {library[key]}."
        for key, label in (("platform", "Platform"), ("audience", "Audience"))
        if library.get(key)
    ]
    if context:
        lines += [" ".join(context), ""]
    lines += [
        f"{plural(len(records), 'Record')}: {posted} Posted, {len(records) - posted} "
        f"Under Review. Newest First. {MISSING} Means The Number Was Never Recorded. "
        f"{PAST} Means The Video Is Shorter Than Ten Seconds. A Review Is An Unposted "
        "Video And Is Not Evidence.",
        "",
        "| Posted | Title | Platform | Format | Runtime | Views | Average Watch Share | "
        "Watching At 10 Seconds | Non-Follower Share | Follows Per 1,000 Viewers | "
        "Status | ID |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for record in records:
        found = comparable(record)
        lines.append(
            "| "
            + " | ".join(
                (
                    spoken(record.get("posted")) if record.get("posted") else "Unposted",
                    f"[{cell(record['title'])}](videos/{record['id']}.md)",
                    cell(record.get("platform") or MISSING),
                    cell(record.get("video_format") or MISSING),
                    seconds_text(record.get("runtime_seconds")),
                    shown(found, "views", "count"),
                    shown(found, "watch_share"),
                    shown(found, "at_10"),
                    shown(found, "outside"),
                    shown(found, "follows", "ratio"),
                    standing(record),
                    f"`{record['id']}`",
                )
            )
            + " |"
        )
    if not records:
        lines.append("| | No Videos Yet | | | | | | | | | | |")
    return "\n".join(lines) + "\n"


def video_page(record, findings):
    links = record.get("links") or {}
    opening = record.get("opening") or {}
    if record.get("kind") == "review":
        state = "Review, Not Evidence. This Video Is Unposted."
    else:
        state = f"Posted {spoken(record.get('posted'))}"
    lines = [
        f"# {record['title']}",
        "",
        f"- ID: `{record['id']}`",
        f"- Status: {state}",
        f"- Platform: {record.get('platform') or MISSING}",
        f"- Format: {record.get('video_format') or MISSING}",
        f"- Runtime: {seconds_text(record.get('runtime_seconds'))}",
        f"- Stake: {record.get('stake') or MISSING}",
        f"- First Sentence: {opening.get('first') or MISSING}",
        f"- Second Sentence: {opening.get('second') or MISSING}",
        f"- Project: {links.get('project') or MISSING}",
        f"- Final File: {links.get('final') or MISSING}",
        f"- Captions: {links.get('captions') or MISSING}",
        "",
        "## Comparable Numbers",
        "",
    ]
    found = comparable(record)
    if record.get("kind") == "review":
        lines.append("None. A Review Holds No Audience Numbers.")
    else:
        lines += ["| Measure | Value | Source |", "| --- | ---: | --- |"]
        for key, label, kind in (
            ("watch_share", "Average Watch As A Share Of Runtime", "percent"),
            ("at_10", "Still Watching At 10 Seconds", "percent"),
            ("drop", "Drop From 3 To 10 Seconds", "points"),
            ("outside", "Non-Follower Share Of Views", "percent"),
            ("follows", "Follows Per 1,000 Viewers", "ratio"),
        ):
            source = found.get(key, (None, ""))[1] if key in found else ""
            lines.append(f"| {label} | {shown(found, key, kind)} | {source} |")
    snaps = sorted(record.get("snapshots") or [], key=lambda s: str(s.get("captured") or ""))
    if snaps:
        lines += [
            "",
            "## Snapshots",
            "",
            "| Captured | Age | Views | Viewers | Average Watch | Follows | Likes | "
            "Comments | Shares | Saves | Reposts | Non-Follower Share |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        details = []
        for snap in snaps:
            day = day_of(record, snap.get("captured"))
            outside = snap.get("non_follower_share_pct")
            if outside is None and snap.get("follower_share_pct") is not None:
                outside = 100 - snap["follower_share_pct"]
            when = spoken(snap.get("captured"))
            row = [when, MISSING if day is None else f"Day {day}"]
            row += [count_text(snap.get("views")), count_text(snap.get("viewers"))]
            row.append(seconds_text(snap.get("average_watch_seconds")))
            row += [count_text(snap.get(name)) for name in COUNTS[2:]]
            row.append(percent_text(outside))
            lines.append("| " + " | ".join(row) + " |")
            if snap.get("rates"):
                details.append(
                    f"- {when} Rates: "
                    + " ".join(f"{r['label']} {number_text(r['percent'], 2)}%." for r in snap["rates"])
                )
            if snap.get("sources"):
                parts = []
                for origin in snap["sources"]:
                    amount = (
                        f"{number_text(origin['share_pct'], 2)}%"
                        if origin.get("share_pct") is not None
                        else f"{origin['views']:,} Views"
                    )
                    parts.append(f"{origin['label']} {amount}.")
                details.append(f"- {when} Views By Source: " + " ".join(parts))
            if snap.get("shown"):
                details.append(
                    f"- {when} Entered In Rounded Form: "
                    + " ".join(
                        f"{name.replace('_', ' ').title()} {text}."
                        for name, text in snap["shown"].items()
                    )
                )
            if snap.get("note"):
                details.append(f"- {when} Note: {snap['note']}")
        if details:
            lines += [""] + details
    for entry in sorted(record.get("retention") or [], key=lambda e: str(e.get("captured") or "")):
        if "## Retention" not in lines:
            lines += ["", "## Retention"]
        readings = entry.get("readings") or []
        lines += ["", f"### {spoken(entry.get('captured'))}", ""]
        if readings:
            lines.append(
                "| Seconds | " + " | ".join(number_text(r["seconds"], 2) for r in readings) + " |"
            )
            lines.append("| --- |" + " ---: |" * len(readings))
            lines.append(
                "| Still Watching | "
                + " | ".join(percent_text(r.get("retention_pct")) for r in readings)
                + " |"
            )
            lines.append("")
        watch = entry.get("average_watch_seconds")
        if watch is not None:
            text = f"- Area-Based Average Watch: {seconds_text(watch)}"
            if entry.get("average_watch_share_pct") is not None:
                text += f", {entry['average_watch_share_pct']:.1f}% Of Runtime"
            text += "."
            if entry.get("reported_average_seconds") is not None:
                text += f" The App Reported {seconds_text(entry['reported_average_seconds'])}."
            lines.append(text)
        if entry.get("drop_3_to_10_points") is not None:
            lines.append(
                f"- Drop From 3 To 10 Seconds: {number_text(entry['drop_3_to_10_points'])} Points."
            )
        for key, label in (("steepest_drops", "Steepest Drops"), ("flattest_stretches", "Flattest Stretches")):
            spans = [
                f"{number_text(s['from'], 2)} To {number_text(s['to'], 2)} Seconds "
                f"({number_text(s['delta_points'])} Points)."
                for s in entry.get(key) or []
            ]
            lines.append(f"- {label}: " + (" ".join(spans) if spans else "None Stood Out."))
        for warning in entry.get("warnings") or []:
            lines.append(f"- Warning: {warning}")
        origin = f"- Source: {entry.get('report') or MISSING}."
        setup = entry.get("calibration") or {}
        if len(setup.get("plot") or ()) == 4 and len(setup.get("color") or ()) == 3:
            origin += (
                " Plot {} {} {} {}".format(*setup["plot"])
                + f" ({setup.get('plot_source', 'supplied').title()}),"
                + " Color {} {} {}".format(*setup["color"])
                + f" ({setup.get('color_source', 'supplied').title()})."
            )
        lines.append(origin)
    bearing = []
    for finding in findings.get("findings") or []:
        for proof in finding.get("evidence") or []:
            if proof.get("video") == record["id"]:
                bearing.append(
                    f"- {finding['id']} ({finding['status'].title()}): "
                    f"{proof['direction'].title()}. {proof.get('note', '')}"
                )
    if bearing:
        lines += ["", "## Findings", ""] + bearing
    if record.get("notes"):
        lines += ["", "## Notes", ""] + [
            f"- {note.get('date', '')}: {note.get('text', '')}" for note in record["notes"]
        ]
    return "\n".join(lines) + "\n"


def tally(finding, records):
    """Return The Distinct Videos On Each Side Of A Finding.

    Only A Record That Still Exists, Is Posted, And Holds Numbers Counts As Evidence.
    """
    sides = {"supports": [], "weakens": []}
    for proof in finding.get("evidence") or []:
        record = records.get(proof.get("video"))
        if (
            record is not None
            and record.get("kind") != "review"
            and measured(record)
            and proof.get("direction") in sides
            and proof["video"] not in sides[proof["direction"]]
        ):
            sides[proof["direction"]].append(proof["video"])
    return sides


def sides_text(sides):
    return (
        f"Supporting Videos: {len(sides['supports'])}. "
        f"Weakening Videos: {len(sides['weakens'])}."
    )


def findings_page(findings, records):
    titles = {record["id"]: record for record in records}
    lines = [
        "# Findings",
        "",
        "Measured Findings About This Audience Outrank The Kit's General Defaults. "
        "A Status Changes Only When At Least Two Posted Videos Agree And Outnumber "
        "The Videos Against It. A Review Of An Unposted Video Is Not Evidence.",
    ]
    for status, heading in (
        ("supported", "Supported"),
        ("open", "Open Hypotheses"),
        ("weakened", "Weakened"),
    ):
        lines += ["", f"## {heading}", ""]
        group = [f for f in findings.get("findings") or [] if f.get("status") == status]
        if not group:
            lines.append("None Yet.")
        for position, finding in enumerate(group):
            sides = tally(finding, titles)
            since = ""
            if status != "open" and finding.get("history"):
                since = f" Since {finding['history'][-1].get('date', '')}"
            if position:
                lines.append("")
            lines += [
                f"### {finding['id']}. {finding['hypothesis']}",
                "",
                f"- Status: {status.title()}{since}. {sides_text(sides)}",
            ]
            for proof in finding.get("evidence") or []:
                record = titles.get(proof.get("video"))
                name = (
                    f"[{record['title']}](videos/{record['id']}.md), Posted "
                    f"{spoken(record.get('posted'))}"
                    if record
                    else f"`{proof.get('video')}` (Record Missing)"
                )
                lines.append(f"- {proof['direction'].title()}: {name}. {proof.get('note', '')}")
            if not finding.get("evidence"):
                lines.append("- Evidence: None Yet.")
    return "\n".join(lines) + "\n"


# Commands


def start(a, lib):
    if lib.marker.exists():
        raise ValueError(f"A Video Library Already Exists At {lib.root}.")
    lib.videos.mkdir(parents=True, exist_ok=True)
    lib.captures.mkdir(exist_ok=True)
    library = {
        "format": LIBRARY_FORMAT,
        "created": today(),
        "platform": one_line(a.platform or "", "The Platform"),
        "audience": one_line(a.audience or "", "The Audience"),
    }
    if not lib.findings_file.exists():
        write_new(lib.findings_file, tidy_json({"format": FINDINGS_FORMAT, "findings": []}) + "\n")
    if not lib.backlog_file.exists():
        write_new(lib.backlog_file, BACKLOG_HEAD)
    write_new(lib.marker, tidy_json(library) + "\n")
    lib.rebuild()
    print(f"Started A Video Library At {lib.root}")
    print("Add A Video With The add Command, Then Record Its Numbers With snapshot.")


def describe(record, a, creating):
    """Copy Supplied Fields Onto A Record. An Empty String Clears A Field."""
    for name, key, what in (
        ("platform", "platform", "The Platform"),
        ("format", "video_format", "The Format"),
        ("stake", "stake", "The Stake"),
    ):
        value = getattr(a, name)
        if value is not None:
            record[key] = one_line(value, what) or None
        elif creating:
            record[key] = None
    if a.runtime is not None:
        record["runtime_seconds"] = duration(a.runtime, "Runtime") if a.runtime.strip() else None
        if record["runtime_seconds"] == 0:
            raise ValueError("Write A Runtime Above Zero Seconds.")
    elif creating:
        record["runtime_seconds"] = None
    opening = record.setdefault("opening", {"first": None, "second": None})
    for name in ("first", "second"):
        value = getattr(a, name)
        if value is not None:
            opening[name] = one_line(value, "Each Opening Sentence") or None
    links = record.setdefault("links", {"project": None, "final": None, "captions": None})
    for name in ("project", "final", "captions"):
        value = getattr(a, name)
        if value is not None:
            links[name] = one_line(value, "Each Link") or None
    record.setdefault("notes", [])
    if a.note:
        record["notes"].append({"date": today(), "text": one_line(a.note, "The Note")})


def add(a, lib):
    title = one_line(a.title, "The Title")
    if not title:
        raise ValueError("Supply A Title.")
    if bool(a.posted) == bool(a.review):
        raise ValueError(
            "Supply --posted With The Posting Date, Or Mark An Unposted Video With --review."
        )
    posted = moment(a.posted, "The Posting Date") if a.posted else None
    key = a.id or f"{(posted or today())[:10]}-{slug(title)}"
    path = lib.video_file(key)
    if path.exists():
        raise ValueError(f"A Record Named {key} Already Exists. Pass --id To Choose Another Name.")
    record = {
        "format": VIDEO_FORMAT,
        "id": key,
        "title": title,
        "kind": "review" if a.review else "posted",
        "posted": posted,
    }
    describe(record, a, True)
    record.update(snapshots=[], retention=[], created=now())
    lib.save_video(record)
    lib.rebuild()
    kind = "A Review Record, Not Evidence" if a.review else "A Posted Video"
    print(f"Added {key} As {kind}")
    print(f"Record: {path.with_suffix('.md')}")


def update(a, lib):
    record = lib.video(a.id)
    if a.title is not None:
        record["title"] = one_line(a.title, "The Title")
        if not record["title"]:
            raise ValueError("Supply A Title.")
    if a.posted:
        record["posted"] = moment(a.posted, "The Posting Date")
        record["kind"] = "posted"
    describe(record, a, False)
    lib.save_video(record)
    lib.rebuild()
    print(f"Updated {record['id']}. Status: {standing(record)}")


def snapshot(a, lib):
    record = lib.video(a.id)
    if record.get("kind") == "review":
        raise ValueError(
            f"{record['id']} Is A Review Of An Unposted Video. "
            "Set Its Posting Date With update --posted Before Recording Numbers."
        )
    stamp = moment(a.captured, "The Capture Time") if a.captured else now()
    day = day_of(record, stamp)
    if day is not None and day < 0:
        raise ValueError("The Snapshot Is Dated Before The Video Was Posted.")
    snap, rounded = {"captured": stamp}, {}
    for name in COUNTS:
        value = getattr(a, name)
        snap[name] = None
        if value is not None:
            snap[name], form = whole(value, name.title())
            if form:
                rounded[name] = form
    snap["average_watch_seconds"] = (
        None if a.average_watch is None else duration(a.average_watch, "Average Watch Time")
    )
    for name, what in (
        ("non_follower_share", "The Non-Follower Share"),
        ("follower_share", "The Follower Share"),
    ):
        value = getattr(a, name)
        snap[name + "_pct"] = None if value is None else percent(value, what)
        if snap[name + "_pct"] is not None and snap[name + "_pct"] > 100:
            raise ValueError(f"{what} Cannot Exceed 100 Percent.")
    snap["rates"] = [
        {"label": one_line(label, "A Rate Label"), "percent": percent(value, label)}
        for label, value in a.rate
    ]
    snap["sources"] = []
    for label, value in a.source:
        label = one_line(label, "A Source Label")
        if str(value).strip().endswith("%"):
            snap["sources"].append(
                {"label": label, "views": None, "share_pct": percent(value, f"The {label} Share")}
            )
        else:
            views, form = whole(value, f"{label} Views")
            snap["sources"].append({"label": label, "views": views, "share_pct": None})
            if form:
                rounded[f"{label} Views"] = form
    if any(not row["label"] for row in snap["rates"] + snap["sources"]):
        raise ValueError("Give Each Rate And Each Source The Label The Platform Shows.")
    snap["shown"] = rounded
    snap["note"] = one_line(a.note or "", "The Note")
    numbers = [snap[name] for name in COUNTS] + [
        snap["average_watch_seconds"],
        snap["non_follower_share_pct"],
        snap["follower_share_pct"],
    ]
    if all(v is None for v in numbers) and not snap["rates"] and not snap["sources"]:
        raise ValueError("Supply At Least One Number From The Analytics Screen.")
    snap["not_captured"] = [
        name for name in COUNTS + ("average_watch_seconds",) if snap[name] is None
    ]
    if snap["non_follower_share_pct"] is None and snap["follower_share_pct"] is None:
        snap["not_captured"].append("non_follower_share_pct")
    existing = [s for s in record["snapshots"] if s.get("captured") == stamp]
    if existing and not a.replace:
        raise ValueError(
            f"A Snapshot Captured {spoken(stamp)} Already Exists. Pass --replace To Overwrite It."
        )
    record["snapshots"] = [s for s in record["snapshots"] if s.get("captured") != stamp]
    record["snapshots"].append(snap)
    record["snapshots"].sort(key=lambda s: str(s.get("captured") or ""))
    lib.save_video(record)
    lib.rebuild()
    missing = [name.replace("_", " ").title() for name in COUNTS if snap[name] is None]
    if snap["average_watch_seconds"] is None:
        missing.append("Average Watch")
    print(f"Recorded A Snapshot Of {record['id']} Captured {spoken(stamp)}")
    if not a.captured:
        print("The Capture Time Was Set To Now. Pass --captured When The Numbers Were Read Earlier.")
    if missing:
        print(f"{MISSING}: " + ", ".join(missing))


def attach(a, lib):
    record = lib.video(a.id)
    if record.get("kind") == "review":
        raise ValueError(
            f"{record['id']} Is A Review Of An Unposted Video. It Has No Retention To Attach."
        )
    report = read_object(a.report, "A Retention Report")
    readings = report.get("readings")
    if not isinstance(readings, list) or not all(
        isinstance(row, dict) and "seconds" in row and "retention_pct" in row for row in readings
    ):
        raise ValueError(
            f"{a.report} Is Not A Retention Report. "
            "Create One With retention.py And Its --output Option."
        )
    number = (int, float)
    pairs = report.get("curve") or []
    spans = (report.get("steepest_drops") or []) + (report.get("flattest_stretches") or [])
    sound = (
        all(isinstance(row["seconds"], number) for row in readings)
        and all(row["retention_pct"] is None or isinstance(row["retention_pct"], number) for row in readings)
        and isinstance(report.get("duration_seconds"), number)
        and isinstance(pairs, list)
        and all(
            isinstance(pair, list) and len(pair) == 2 and all(isinstance(v, number) for v in pair)
            for pair in pairs
        )
        and all(
            isinstance(span, dict)
            and all(isinstance(span.get(key), number) for key in ("from", "to", "delta_points"))
            for span in spans
        )
        and all(
            report.get(key) is None or isinstance(report.get(key), number)
            for key in ("drop_3_to_10_points", "average_watch_seconds", "average_watch_share_pct",
                        "reported_average_seconds")
        )
        and all(isinstance(w, str) for w in report.get("warnings") or [])
    )
    if not sound or any(isinstance(v, bool) for row in readings for v in row.values()):
        raise ValueError(
            f"{a.report} Holds Values That Are Not Numbers. "
            "Create A Fresh Report With retention.py And Its --output Option."
        )
    stamp = moment(a.captured, "The Capture Time") if a.captured else now()
    entry = {"captured": stamp, "report": Path(a.report).name}
    for key in (
        "duration_seconds",
        "readings",
        "drop_3_to_10_points",
        "average_watch_seconds",
        "average_watch_share_pct",
        "reported_average_seconds",
        "average_gap_seconds",
        "steepest_drops",
        "flattest_stretches",
        "warnings",
        "calibration",
        "curve",
    ):
        entry[key] = report.get(key)
    existing = [e for e in record["retention"] if e.get("captured") == stamp]
    if existing and not a.replace:
        raise ValueError(
            f"Retention Captured {spoken(stamp)} Is Already Attached. Pass --replace To Overwrite It."
        )
    record["retention"] = [e for e in record["retention"] if e.get("captured") != stamp]
    record["retention"].append(entry)
    record["retention"].sort(key=lambda e: str(e.get("captured") or ""))
    lib.save_video(record)
    lib.rebuild()
    print(f"Attached Retention To {record['id']} Captured {spoken(stamp)}")
    runtime, length = record.get("runtime_seconds"), entry.get("duration_seconds")
    if runtime is None:
        print("The Record Has No Runtime. Set It With update --runtime.")
    elif length is not None and abs(length - runtime) > max(1.0, 0.05 * runtime):
        print(
            f"Warning: The Report Covers {seconds_text(length)} But The Record's Runtime "
            f"Is {seconds_text(runtime)}. Check Which Is Right."
        )
    if not entry.get("curve"):
        print(
            "The Report Has No Curve, So compare Can Only Use Its Listed Seconds. "
            "Use The --output File From retention.py To Keep The Curve."
        )
    for warning in entry.get("warnings") or []:
        print(f"Warning Carried From The Report: {warning}")


def index(a, lib):
    lib.rebuild()
    print(read_text(lib.root / "index.md"), end="")


def show(a, lib):
    record = lib.video(a.id)
    print(video_page(record, lib.findings()), end="")


def compare(a, lib):
    if len(a.ids) < 2:
        raise ValueError("Name At Least Two Videos To Compare.")
    records = [lib.video(key) for key in a.ids]
    entries = [newest(record.get("retention") or [])[:1] for record in records]
    longest = max(
        [e[0].get("duration_seconds") or 0 for e in entries if e]
        + [record.get("runtime_seconds") or 0 for record in records]
    )
    if a.at:
        if any(not math.isfinite(s) or s < 0 for s in a.at):
            raise ValueError("Compare At Finite Nonnegative Seconds.")
        seconds = sorted(set(a.at))
    else:
        seconds = [s for s in COMPARE_SECONDS if s <= longest + 0.25]

    def value(entry, second):
        if not entry:
            return MISSING
        found = level_at(entry[0], second)
        return MISSING if found is None else found if found == PAST else f"{found:.1f}%"

    heads = [
        f"{cell(r['title'])} ({str(r['posted'])[:10] if r.get('posted') else 'Unposted'})"
        for r in records
    ]
    lines = [
        "| Seconds | " + " | ".join(heads) + " |",
        "| ---: |" + " ---: |" * len(records),
    ]
    for second in seconds:
        lines.append(
            f"| {number_text(second, 2)} | "
            + " | ".join(value(entry, second) for entry in entries)
            + " |"
        )
    found = [comparable(record) for record in records]
    for label, key, kind in (
        ("Drop From 3 To 10 Seconds", "drop", "points"),
        ("Average Watch Share", "watch_share", "percent"),
    ):
        lines.append(f"| {label} | " + " | ".join(shown(f, key, kind) for f in found) + " |")
    lines.append(
        "| Runtime | " + " | ".join(seconds_text(r.get("runtime_seconds")) for r in records) + " |"
    )
    print("\n".join(lines))
    bare = [record["id"] for record, entry in zip(records, entries) if not entry]
    if bare:
        print("\nNo Retention Is Attached To: " + ", ".join(bare))
    formats = {record.get("video_format") for record in records}
    if len(formats) > 1:
        print("\nThese Videos Use Different Formats. Compare Like With Like Before Drawing A Finding.")


def caption_cues(path):
    """Read SRT Or WebVTT Cues As Start Seconds, End Seconds, And Text."""
    cues, lines, at = [], read_text(path).splitlines(), 0
    while at < len(lines):
        stamps = CUE_TIME.findall(lines[at]) if "-->" in lines[at] else []
        at += 1
        if len(stamps) < 2:
            continue
        start, end = (
            int(hours or 0) * 3600 + int(minutes) * 60 + int(seconds) + int(part.ljust(3, "0")) / 1000
            for hours, minutes, seconds, part in stamps[:2]
        )
        said = []
        while at < len(lines) and lines[at].strip():
            said.append(re.sub(r"<[^>]*>", "", lines[at]).strip())
            at += 1
        text = " ".join(part for part in said if part)
        if text:
            cues.append((start, end, text))
    return cues


def lineup(a, lib):
    """Set Each Steep Drop And Flat Stretch Beside The Captions Spoken Around It."""
    record = lib.video(a.id)
    entries = newest(record.get("retention") or [])
    if not entries:
        raise ValueError(
            f"No Retention Is Attached To {record['id']}. Attach A Report With attach First."
        )
    if not math.isfinite(a.before) or a.before < 0:
        raise ValueError("Write --before As Nonnegative Seconds.")
    link = str(a.captions) if a.captions else (record.get("links") or {}).get("captions")
    places = [Path(link).expanduser(), lib.root / link] if link else []
    source = next((place for place in places if place.is_file()), None)
    if source is None:
        raise ValueError(
            f"No Captions File Was Found For {record['id']}. Pass --captions With An SRT "
            "Or WebVTT File, Or Set The Link With update --captions. Do Not Quote From Memory."
        )
    cues = caption_cues(source)
    if not cues:
        raise ValueError(f"{source} Holds No Timed Captions In SRT Or WebVTT Form.")
    entry = entries[0]
    spans = [("Drop", s) for s in entry.get("steepest_drops") or []]
    spans += [("Flat", s) for s in entry.get("flattest_stretches") or []]
    if not spans:
        print("No Steep Drop Or Flat Stretch Stood Out In This Curve. Read It As A Steady Slope.")
        return
    lines = [
        "| Stretch | Change | Said Just Before And During | Shown | Reading |",
        "| --- | --- | --- | --- | --- |",
    ]
    for kind, span in sorted(spans, key=lambda item: item[1]["from"]):
        said = [
            f'{number_text(start, 2)}: "{cell(text)}"'
            for start, end, text in cues
            if end > span["from"] - a.before and start < span["to"]
        ]
        lines.append(
            f"| {kind}, {number_text(span['from'], 2)} To {number_text(span['to'], 2)} Seconds | "
            f"{number_text(span['delta_points'])} Points | "
            f"{' '.join(said) or 'No Captions In This Stretch'} | | |"
        )
    print("\n".join(lines))
    print(
        f"\nQuotes And Times Come From {source}. Retention Was Captured "
        f"{spoken(entry.get('captured'))}. Fill Shown From The Posted Video, Then Write Each "
        "Reading As A Hypothesis."
    )


def find_one(data, key):
    for finding in data["findings"]:
        if finding.get("id", "").lower() == str(key).lower():
            return finding
    raise ValueError(f"No Finding Named {key}. Run finding list To See The IDs.")


def finding(a, lib):
    data = lib.findings()
    if a.action == "list":
        lib.rebuild()
        print(read_text(lib.root / "findings.md"), end="")
        return
    if a.action == "add":
        text = one_line(a.hypothesis, "The Hypothesis")
        if not text:
            raise ValueError("Write The Hypothesis As One Sentence That A Video Could Support Or Weaken.")
        numbers = [int(m.group(1)) for f in data["findings"] for m in [re.fullmatch(r"F(\d+)", f.get("id", ""))] if m]
        entry = {
            "id": f"F{max(numbers, default=0) + 1:02}",
            "hypothesis": text,
            "status": "open",
            "created": today(),
            "evidence": [],
            "history": [],
        }
        data["findings"].append(entry)
        lib.save_findings(data)
        lib.rebuild()
        print(f"Added {entry['id']} As An Open Hypothesis")
        return
    entry = find_one(data, a.finding)
    records = {record["id"]: record for record in lib.all_videos()}
    sides = tally(entry, records)
    if a.action == "evidence":
        record = lib.video(a.video)
        if record.get("kind") == "review":
            raise ValueError(
                f"{record['id']} Is A Review Of An Unposted Video. A Review Is Not Evidence."
            )
        if not measured(record):
            raise ValueError(
                f"{record['id']} Has No Recorded Numbers. Record A Snapshot Or Attach "
                "Retention Before Citing It As Evidence."
            )
        note = one_line(a.note, "The Evidence Note")
        if not note:
            raise ValueError("State The Number That Makes This Video Evidence In --note.")
        earlier = [p for p in entry["evidence"] if p.get("video") == record["id"]]
        if earlier and not a.replace:
            raise ValueError(
                f"{entry['id']} Already Cites {record['id']}. Pass --replace To Correct That Entry."
            )
        entry["evidence"] = [p for p in entry["evidence"] if p.get("video") != record["id"]]
        entry["evidence"].append(
            {"video": record["id"], "direction": a.direction, "note": note, "added": today()}
        )
        sides = tally(entry, records)
        side = SIDES.get(entry["status"])
        returned = bool(side) and len(sides[side]) < 2
        if returned:
            entry["history"].append(
                {
                    "date": today(),
                    "from": entry["status"],
                    "to": "open",
                    "reason": "Fewer Than Two Videos Still Agree",
                }
            )
            entry["status"] = "open"
        print(
            f"Recorded Evidence For {entry['id']}. {sides_text(sides)} "
            f"Status: {entry['status'].title()}"
        )
        if returned:
            print(
                f"{entry['id']} Returned To Open Because Fewer Than Two Videos Still "
                "Agree With Its Earlier Status."
            )
        for status, side in SIDES.items():
            other = "weakens" if side == "supports" else "supports"
            if (
                entry["status"] != status
                and len(sides[side]) >= 2
                and len(sides[side]) > len(sides[other])
            ):
                print(
                    "Two Or More Videos Now Agree. If The Evidence Holds, Run: "
                    f"finding status {entry['id']} {status}"
                )
    else:
        target = a.status
        if target == entry["status"]:
            raise ValueError(f"{entry['id']} Is Already {target.title()}.")
        supports, weakens = len(sides["supports"]), len(sides["weakens"])
        counts = sides_text(sides)
        if target == "open":
            against = weakens if entry["status"] == "supported" else supports
            if against < 2:
                raise ValueError(
                    f"{entry['id']} Stays {entry['status'].title()}. A Status Changes Only "
                    f"When At Least Two Videos Agree. {counts}"
                )
        else:
            agree = supports if target == "supported" else weakens
            against = weakens if target == "supported" else supports
            if agree < 2:
                raise ValueError(
                    f"{entry['id']} Stays {entry['status'].title()}. A Status Changes Only "
                    f"When At Least Two Videos Agree. {counts}"
                )
            if agree <= against:
                raise ValueError(
                    f"{entry['id']} Stays {entry['status'].title()}. The Agreeing Videos "
                    f"Must Outnumber The Others. {counts}"
                )
        entry["history"].append(
            {
                "date": today(),
                "from": entry["status"],
                "to": target,
                "supports": sides["supports"],
                "weakens": sides["weakens"],
            }
        )
        entry["status"] = target
        print(f"{entry['id']} Is Now {target.title()}. {counts}")
    lib.save_findings(data)
    lib.rebuild()


def backlog(a, lib):
    try:
        text = read_text(lib.backlog_file)
    except OSError:
        text = BACKLOG_HEAD
    lines = text.splitlines()
    if a.action == "add":
        idea = one_line(a.idea, "The Idea")
        if not idea:
            raise ValueError("Write The Idea As One Line.")
        entry = f"- [ ] {today()} | {idea}"
        if a.tests:
            entry += f" | Tests {one_line(a.tests, 'The Finding ID')}"
        lines.append(entry)
        write_text(lib.backlog_file, "\n".join(lines) + "\n")
        print(f"Saved To The Backlog: {idea}")
        return
    entries = [
        (number, match)
        for number, match in ((n, BACKLOG_LINE.match(line)) for n, line in enumerate(lines))
        if match
    ]
    waiting = [(n, m) for n, m in entries if m.group(1) == " "]
    if a.action == "done":
        if not 1 <= a.number <= len(waiting):
            raise ValueError(
                f"The Backlog Has {plural(len(waiting), 'Open Line')}. Run backlog list To See Their Numbers."
            )
        position, match = waiting[a.number - 1]
        lines[position] = f"- [x] {match.group(2)} | Used {today()}"
        write_text(lib.backlog_file, "\n".join(lines) + "\n")
        print(f"Marked As Used: {match.group(2)}")
        return
    if not waiting:
        print("The Backlog Has No Open Lines.")
    for number, (_, match) in enumerate(waiting, 1):
        print(f"{number}. {match.group(2)}")
    if a.all:
        for _, match in entries:
            if match.group(1) != " ":
                print(f"Used. {match.group(2)}")


def defaults(a, root):
    path = defaults_file()
    if a.action != "write":
        found = read_defaults(path)
        if not found:
            print(f"No Defaults File At {path}")
            print("Create One With defaults write After The Creator Agrees.")
            return
        print(f"Defaults File: {path}")
        for key, value in found.items():
            print(f"{key.title()}: {value}")
        return
    if not root:
        raise ValueError("Name The Library Folder With --library.")
    if path.exists():
        raise ValueError(f"A Defaults File Already Exists At {path}. Edit It By Hand.")
    if not math.isfinite(a.pace) or not 0.5 <= a.pace <= 8:
        raise ValueError("Write The Pace As Spoken Words Per Second, Between 0.5 And 8.")
    Library(root).require()
    folder = Path(root).expanduser().resolve()
    findings = Path(a.findings).expanduser().resolve() if a.findings else folder / "findings.md"
    unknown = "Not Recorded Yet"
    body = [
        "# Video Script Defaults",
        "",
        "Read This File Before Any Idea, Script, Or Review. Edit It By Hand When A Preference Changes.",
        "",
        f"- Library: {folder.as_posix()}",
        f"- Findings: {findings.as_posix()}",
        f"- Platform: {one_line(a.platform or '', 'The Platform') or unknown}",
        f"- Audience: {one_line(a.audience or '', 'The Audience') or unknown}",
        f"- Pace: {number_text(a.pace, 2)} Words Per Second",
        f"- Voice: {one_line(a.voice or '', 'The Voice') or unknown}",
        "",
        "## Platform Notes",
        "",
    ]
    body += [f"- {one_line(note, 'Each Platform Note')}" for note in a.platform_note] or [
        "- None Yet. Add The Labels And Definitions This Platform's Analytics Use."
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    write_new(path, "\n".join(body) + "\n")
    print(f"Created {path}")


def build_parser():
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        "--library",
        type=Path,
        default=argparse.SUPPRESS,
        metavar="FOLDER",
        help="The Video Library Folder. Defaults To The One Named In The Defaults File",
    )
    parser = DeskParser(description=__doc__)
    parser.add_argument(
        "--library",
        type=Path,
        metavar="FOLDER",
        help="The Video Library Folder. Defaults To The One Named In The Defaults File",
    )
    commands = parser.add_subparsers(dest="command", title="Commands", metavar="COMMAND", required=True)

    def command(group, name, about):
        return group.add_parser(name, help=about, description=about, parents=[shared])

    new = command(commands, "init", "Start A Library In A New Or Empty Folder")
    new.add_argument("--platform", help="The Platform The Creator Posts To")
    new.add_argument("--audience", help="Who The Videos Are For")

    def details(sub, creating):
        sub.add_argument("--platform", help="Where The Video Is Posted")
        sub.add_argument("--format", help="The Kind Of Video, Such As Screen Demo With Voiceover")
        sub.add_argument("--runtime", metavar="SECONDS", help="Runtime As 28, 28.5, Or 0:28")
        sub.add_argument("--stake", help="Who The Video Is For And What They Stand To Gain Or Lose")
        sub.add_argument("--first", metavar="SENTENCE", help="The First Spoken Sentence")
        sub.add_argument("--second", metavar="SENTENCE", help="The Second Spoken Sentence")
        sub.add_argument("--project", metavar="LINK", help="Path Or Link To The Editable Project")
        sub.add_argument("--final", metavar="LINK", help="Path Or Link To The Final File Or Post")
        sub.add_argument("--captions", metavar="LINK", help="Path Or Link To The Captions File")
        sub.add_argument("--note", help="A Dated Note To Keep With The Record")
        if creating:
            sub.add_argument("--id", help="A Record Name To Use Instead Of The Date And Title")

    plus = command(commands, "add", "Add One Video Record")
    plus.add_argument("--title", required=True, help="The Video's Working Title")
    plus.add_argument("--posted", metavar="DATE", help="Posting Date As 2026-11-03")
    plus.add_argument("--review", action="store_true", help="Mark An Unposted Video As A Review, Not Evidence")
    details(plus, True)

    change = command(commands, "update", "Change Fields On One Record")
    change.add_argument("id", help="The Record ID")
    change.add_argument("--title", help="A Corrected Title")
    change.add_argument("--posted", metavar="DATE", help="Posting Date. Turns A Review Into A Posted Video")
    details(change, False)

    snap = command(commands, "snapshot", "Record One Dated Analytics Snapshot")
    snap.add_argument("id", help="The Record ID")
    snap.add_argument("--captured", metavar="WHEN", help="Date And Time The Numbers Were Read, As 2026-11-05 09:30")
    for name in COUNTS:
        snap.add_argument("--" + name, metavar="COUNT", help=f"{name.title()} As Shown By The Platform")
    snap.add_argument("--average-watch", metavar="SECONDS", help="Average Watch Time As 9.4 Or 0:09")
    snap.add_argument("--non-follower-share", metavar="PERCENT", help="Share Of Views From Non-Followers")
    snap.add_argument("--follower-share", metavar="PERCENT", help="Share Of Views From Followers, When Only That Is Shown")
    snap.add_argument("--rate", nargs=2, action="append", default=[], metavar=("LABEL", "PERCENT"), help="A Rate Under The Platform's Own Label. Repeat As Needed")
    snap.add_argument("--source", nargs=2, action="append", default=[], metavar=("LABEL", "VALUE"), help="Views From One Source As A Count Or A Percent Such As 71%%. Repeat As Needed")
    snap.add_argument("--note", help="What Was Unusual About This Capture")
    snap.add_argument("--replace", action="store_true", help="Overwrite The Snapshot With The Same Capture Time")

    pin = command(commands, "attach", "Attach Retention Readings From A retention.py Report")
    pin.add_argument("id", help="The Record ID")
    pin.add_argument("report", type=Path, help="The JSON File Saved By retention.py --output")
    pin.add_argument("--captured", metavar="WHEN", help="Date And Time The Chart Was Captured")
    pin.add_argument("--replace", action="store_true", help="Overwrite Retention With The Same Capture Time")

    command(commands, "index", "Rebuild Every Readable File And Print The Index")
    command(commands, "show", "Print One Record").add_argument("id", help="The Record ID")

    beside = command(commands, "lineup", "Set Each Steep Drop And Flat Stretch Beside The Captions Spoken Around It")
    beside.add_argument("id", help="The Record ID")
    beside.add_argument("--captions", type=Path, metavar="FILE", help="An SRT Or WebVTT File. Defaults To The Record's Captions Link")
    beside.add_argument("--before", type=float, default=3.0, metavar="SECONDS", help="How Far Before Each Stretch To Quote. Default 3")

    versus = command(commands, "compare", "Compare Retention Of Several Videos At The Same Seconds")
    versus.add_argument("ids", nargs="+", metavar="ID", help="Two Or More Record IDs")
    versus.add_argument("--at", type=float, nargs="+", metavar="SECONDS", help="Seconds To Compare Instead Of The Standard List")

    claim = command(commands, "finding", "Manage Hypotheses And Their Evidence")
    steps = claim.add_subparsers(dest="action", title="Actions", metavar="ACTION", required=True)
    command(steps, "list", "Print Every Finding With Its Evidence")
    command(steps, "add", "Add An Open Hypothesis").add_argument("hypothesis", help="One Sentence A Video Could Support Or Weaken")
    proof = command(steps, "evidence", "Cite One Posted Video For Or Against A Hypothesis")
    proof.add_argument("finding", help="The Finding ID, Such As F01")
    proof.add_argument("video", help="The Record ID Of A Posted Video With Numbers")
    proof.add_argument("direction", choices=("supports", "weakens"), help="Whether The Video Supports Or Weakens The Hypothesis")
    proof.add_argument("--note", required=True, help="The Number That Makes This Video Evidence")
    proof.add_argument("--replace", action="store_true", help="Correct The Existing Entry For This Video")
    state = command(steps, "status", "Change A Status When At Least Two Videos Agree")
    state.add_argument("finding", help="The Finding ID")
    state.add_argument("status", choices=STATUSES, help="The New Status")

    ideas = command(commands, "backlog", "Save And List One-Line Ideas")
    moves = ideas.add_subparsers(dest="action", title="Actions", metavar="ACTION", required=True)
    saved = command(moves, "add", "Save One Idea As One Line")
    saved.add_argument("idea", help="The Idea In One Line")
    saved.add_argument("--tests", metavar="FINDING", help="The Finding Or Hypothesis The Idea Would Test")
    listing = command(moves, "list", "List Open Backlog Lines With Their Numbers")
    listing.add_argument("--all", action="store_true", help="Also List Used Lines")
    command(moves, "done", "Mark One Open Line As Used").add_argument("number", type=int, help="The Line Number From backlog list")

    prefs = command(commands, "defaults", "Show Or Create The Creator Defaults File")
    modes = prefs.add_subparsers(dest="action", title="Actions", metavar="ACTION")
    command(modes, "show", "Print The Defaults File Location And Values")
    make = command(modes, "write", "Create The Defaults File Once The Creator Agrees")
    make.add_argument("--platform", help="The Platform The Creator Posts To")
    make.add_argument("--audience", help="Who The Videos Are For")
    make.add_argument("--pace", type=float, default=STANDARD_PACE, help=f"Spoken Words Per Second. Default {STANDARD_PACE}")
    make.add_argument("--voice", help="How The Creator Speaks, In A Sentence")
    make.add_argument("--findings", metavar="FILE", help="The Findings File. Defaults To findings.md In The Library")
    make.add_argument("--platform-note", action="append", default=[], metavar="NOTE", help="A Platform Label Or Definition Worth Keeping. Repeat As Needed")
    return parser


def main(argv=None):
    guard_streams(utf8=True)
    parser = build_parser()
    a = parser.parse_args(argv)
    try:
        if a.command == "defaults":
            defaults(a, a.library)
            return 0
        root = a.library or read_defaults().get("library")
        if not root:
            raise ValueError(
                "Name The Library Folder With --library, Or Create A Defaults File That Names It."
            )
        lib = Library(root)
        if a.command == "init":
            start(a, lib)
        else:
            lib.require()
            {
                "add": add,
                "update": update,
                "snapshot": snapshot,
                "attach": attach,
                "index": index,
                "show": show,
                "compare": compare,
                "lineup": lineup,
                "finding": finding,
                "backlog": backlog,
            }[a.command](a, lib)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        parser.exit(1, f"{exc}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
