"""Create, Read, And Check A Timed Two-Column Script."""

import json
import math
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from desk_support import (  # noqa: E402
    STANDARD_PACE,
    DeskParser,
    clock,
    guard_streams,
    number_text,
    pace_from,
    read_defaults,
    read_json,
    read_text,
    tidy_json,
)


OPENING_SECONDS = 3.0
SHORT_FORM = re.compile(
    r"(?:^|\s)(?:Dr|Mr|Mrs|Ms|St|Jr|Sr|Prof|Inc|Ltd|Co|No|Vs|Etc|[A-Za-z])\.$", re.IGNORECASE
)
LONG_SENTENCE = 25
LONG_ASK = 12
ASK_PURPOSES = {"invitation", "cta", "call to action"}
WORD = re.compile(r"[^\W_]+(?:['\u2019-][^\W_]+)*")
GREETING = re.compile(
    r"^\W*(hi|hey|hello|welcome|what'?s up|good (morning|afternoon|evening)|"
    r"my name is|i am|i'm|this is|in this video|today (i|we))\b",
    re.IGNORECASE,
)
ASK = re.compile(
    r"^\W*(follow (me|us|for|along|this)|subscribe|comment|leave a comment|"
    r"drop a comment|like (this|and|the)|save (this|it|the)|share (this|it|the)|"
    r"send (this|it)|dm (me|us)|message (me|us)|click|tap (the|that|below|here|follow)|"
    r"sign up|book (a|your|now)|download|join (me|us|the)|visit|check out|"
    r"grab (your|the|a)|get your|link in|hit (the|that|follow|subscribe))\b",
    re.IGNORECASE,
)
CLAIM = re.compile(
    r"\d+(\.\d+)?\s*(%|percent\b|x\b|times\b)|[$\u20ac\u00a3]\s?\d|\b\d+ out of \d+\b|"
    r"\b(study|studies|research|survey|data shows?|according to|proven|guaranteed?|"
    r"fastest|cheapest|best|most|number one|doubles?|doubled|triples?|tripled|"
    r"twice as|half as)\b",
    re.IGNORECASE,
)
LINK = re.compile(r"https?://|www\.|\b[\w-]+\.(com|net|org|io|co|ai|app)\b|(?<!\w)[@#]\w+", re.IGNORECASE)


def outline(brief, seconds):
    if brief["format"] != "school.campaign/1":
        raise ValueError("Expected A Campaign Brief.")
    proofs = brief["evidence"]
    if not proofs:
        raise ValueError(
            "Add At Least One Verified Proof To The Campaign Before Building A Proof-Led Script."
        )
    first = proofs[0]
    cards = [
        ("Opening", first["claim"], first["visual"], first["id"], 2),
        (
            "Context",
            f"Here Is The Starting Point For {brief['viewer']}.",
            "Show The Starting State In The Same Recording",
            "",
            2,
        ),
    ]
    cards.extend(("Demonstration", p["claim"], p["visual"], p["id"], 4) for p in proofs)
    cards.append(
        (
            "Invitation",
            brief["action"],
            brief["destination"] or "Show The Confirmed Next Step",
            "",
            2,
        )
    )
    weight = sum(c[-1] for c in cards)
    beats = []
    used = 0
    for index, (purpose, line, picture, proof, portion) in enumerate(cards, 1):
        end = round(seconds * (used + portion) / weight, 3)
        start = round(seconds * used / weight, 3)
        beats.append(
            {
                "id": f"B{index:02}",
                "purpose": purpose,
                "seconds": round(end - start, 3),
                "voice": line,
                "picture": picture,
                "proof": proof,
                "media": "",
                "source_in": 0,
            }
        )
        used += portion
    return {
        "format": "school.script/1",
        "title": brief["title"],
        "reviewer": brief["reviewer"],
        "openings": [
            {"angle": "Outcome First", "first_frame": first["visual"]},
            {
                "angle": "Question First",
                "first_frame": "Show The Decision Before Its Result",
            },
        ],
        "evidence": proofs,
        "beats": beats,
    }


# Reading A Script For Checks


def element_lines(text, key):
    """Return The Line Number Where Each Item Of A Top-Level List Starts."""
    decoder = json.JSONDecoder()

    def skip(at):
        while at < len(text) and text[at] in " \t\r\n":
            at += 1
        return at

    try:
        at = skip(0)
        if text[at] != "{":
            return []
        at = skip(at + 1)
        while text[at] != "}":
            name, at = decoder.raw_decode(text, at)
            at = skip(at)
            at = skip(at + 1)
            if name == key and text[at] == "[":
                lines = []
                at = skip(at + 1)
                while text[at] != "]":
                    lines.append(text.count("\n", 0, at) + 1)
                    _, at = decoder.raw_decode(text, at)
                    at = skip(at)
                    if text[at] == ",":
                        at = skip(at + 1)
                return lines
            _, at = decoder.raw_decode(text, at)
            at = skip(at)
            if text[at] == ",":
                at = skip(at + 1)
    except (IndexError, ValueError):
        pass
    return []


def load_script(path):
    script = read_json(path)
    if not isinstance(script, dict) or script.get("format") != "school.script/1":
        raise ValueError("Expected A Script File.")
    if not isinstance(script.get("beats"), list) or not script["beats"]:
        raise ValueError("Expected A Script File With At Least One Beat.")
    for key in ("beats", "evidence", "openings"):
        rows = script.get(key)
        if rows is not None and not (
            isinstance(rows, list) and all(isinstance(row, dict) for row in rows)
        ):
            raise ValueError(f"Expected {key} To Be A List Of Objects.")
    text = read_text(path)
    lines = {key: element_lines(text, key) for key in ("beats", "evidence", "openings")}
    return script, lines


def words(text):
    return WORD.findall(str(text or ""))


def sentences(text):
    """Split Speech Into Sentences Without Breaking After A Title Or An Initial."""
    parts = []
    for part in re.split(r"(?<=[.!?])\s+", str(text or "").strip()):
        if parts and SHORT_FORM.search(parts[-1]):
            parts[-1] += " " + part
        elif part:
            parts.append(part)
    return parts


def choose_pace(given, script):
    if given is not None:
        pace, source = given, "Given"
    elif isinstance(script.get("pace"), (int, float)) and not isinstance(script["pace"], bool):
        pace, source = float(script["pace"]), "From The Script File"
    else:
        pace = pace_from(read_defaults())
        source = "From The Defaults File"
        if pace is None:
            pace, source = STANDARD_PACE, "Standard"
    if not math.isfinite(pace) or not 0.5 <= pace <= 8:
        raise ValueError("Use A Pace Between 0.5 And 8 Spoken Words Per Second.")
    return pace, source


def is_ask(beat):
    return beat.get("cta") is True or str(beat.get("purpose", "")).strip().lower() in ASK_PURPOSES


def timeline(script):
    """Return Each Beat With Its Start Time. A Bad Duration Counts As Zero Here."""
    rows, start = [], 0.0
    for beat in script["beats"]:
        try:
            length = float(beat.get("seconds"))
        except (TypeError, ValueError):
            length = math.nan
        good = math.isfinite(length) and length > 0
        rows.append((beat, start, length if good else 0.0, good))
        start += length if good else 0.0
    return rows, start


def study(script, lines, pace, target):
    """Hold A Script Against The Mechanical Parts Of The Writing Checklist."""
    issues = []

    def where(kind, position, name):
        found = lines.get(kind) or []
        line = found[position] if position < len(found) else None
        return (f"{name} (Line {line})" if line else str(name)), line

    def flag(level, code, kind, position, name, message):
        label, line = where(kind, position, name) if kind else (name, None)
        issues.append({"level": level, "code": code, "where": label, "line": line, "message": message})

    rows, total = timeline(script)
    proofs = {}
    for position, proof in enumerate(script.get("evidence") or []):
        name = str(proof.get("id") or f"Evidence {position + 1}")
        proofs[name] = proof
        if not str(proof.get("source") or "").strip():
            flag("fix", "claim-without-source", "evidence", position, name,
                 "This Claim Has No Source. Add One Or Cut The Claim.")
        elif proof.get("opened") is False:
            flag("review", "source-not-opened", "evidence", position, name,
                 "The Source Could Not Be Opened. Tell The Creator It Is Unverified.")
    seen, used, asks, spoken = set(), set(), [], 0
    for position, (beat, start, length, good) in enumerate(rows):
        name = str(beat.get("id") or f"Beat {position + 1}")
        voice, said = str(beat.get("voice") or ""), words(beat.get("voice"))
        spoken += len(said)
        if not beat.get("id") or name in seen:
            flag("fix", "beat-id", "beats", position, name,
                 "Each Line Needs Its Own ID. The Director Rejects A Repeated Or Empty One.")
        seen.add(name)
        if not good:
            flag("fix", "beat-seconds", "beats", position, name,
                 "Give This Line A Duration Above Zero Seconds.")
        if not str(beat.get("picture") or "").strip():
            flag("fix", "missing-picture", "beats", position, name,
                 "No Picture. Write What The Viewer Sees While This Line Plays.")
        elif not str(beat.get("media") or "").strip() and not str(beat.get("capture") or "").strip():
            flag("review", "missing-capture", "beats", position, name,
                 "No Capture Note Or Media. Say What Must Be Recorded For This Picture.")
        proof = str(beat.get("proof") or "")
        if proof:
            used.add(proof)
            if proof not in proofs:
                flag("fix", "unknown-proof", "beats", position, name,
                     f"The Proof {proof} Is Not In The Evidence List.")
        elif CLAIM.search(voice):
            flag("review", "claim-without-proof", "beats", position, name,
                 "This Line Reads Like A Claim But Names No Proof. Tie It To A Sourced "
                 "Evidence Entry Or Reword It.")
        if is_ask(beat):
            asks.append(position)
            if len(said) > LONG_ASK:
                flag("review", "long-ask", "beats", position, name,
                     f"The Call To Action Runs {len(said)} Words. Keep It Short.")
        elif any(ASK.match(part) for part in sentences(voice)):
            flag("review", "unmarked-ask", "beats", position, name,
                 "This Line Reads Like A Call To Action. Keep One, Mark It, And Place It Last.")
        if LINK.search(voice):
            flag("review", "link-in-speech", "beats", position, name,
                 "A Link, Handle, Or Hashtag Is Hard To Say. Move It To The Caption.")
        for part in sentences(voice):
            if len(words(part)) > LONG_SENTENCE:
                flag("review", "long-sentence", "beats", position, name,
                     f"One Sentence Runs {len(words(part))} Words. Split It So Each Part Stands Alone.")
        if good and said and len(said) / pace > length + 0.25:
            flag("review", "line-over-time", "beats", position, name,
                 f"The Line Needs About {number_text(len(said) / pace)} Seconds At "
                 f"{number_text(pace, 2)} Words Per Second But Has {number_text(length, 2)}. "
                 "Trim The Line Or Lengthen The Beat.")
    for position, proof in enumerate(script.get("evidence") or []):
        name = str(proof.get("id") or f"Evidence {position + 1}")
        if name not in used:
            flag("review", "claim-not-shown", "evidence", position, name,
                 "No Line Shows This Claim. Tie It To A Line Or Keep It For The Caption.")
    for position in asks[1:]:
        flag("fix", "second-ask", "beats", position, str(rows[position][0].get("id")),
             "This Is A Second Call To Action. Keep One.")
    if asks and asks[0] != len(rows) - 1:
        flag("fix", "ask-not-last", "beats", asks[0], str(rows[asks[0]][0].get("id")),
             "The Call To Action Is Not The Last Line. Move It After The Payoff.")

    # The opening sentence, the sentence after it, and the ten-second mark.
    stream = []
    for position, (beat, start, length, good) in enumerate(rows):
        clock_at = start
        for part in sentences(beat.get("voice")):
            count = len(words(part))
            if count:
                stream.append((position, part, count, clock_at + count / pace))
                clock_at += count / pace
    opening = second = None
    if stream:
        position, part, count, end = stream[0]
        name = str(rows[position][0].get("id") or f"Beat {position + 1}")
        label, line = where("beats", position, name)
        opening = {"beat": name, "line": line, "words": count, "ends_at": round(end, 2), "sentence": part}
        if end > OPENING_SECONDS + 1e-9:
            flag("fix", "opening-too-long", "beats", position, name,
                 f"The Opening Sentence Runs {count} Words And Ends At About "
                 f"{number_text(end)} Seconds At {number_text(pace, 2)} Words Per Second. "
                 "Finish It Within 3 Seconds.")
        if GREETING.match(part):
            flag("review", "greeting-opening", "beats", position, name,
                 "The Opening Starts With A Greeting Or An Introduction. Open On The "
                 "Viewer's Stake Or What Is On Screen.")
        if len(stream) > 1:
            position, part, count, end = stream[1]
            name = str(rows[position][0].get("id") or f"Beat {position + 1}")
            second = {"beat": name, "line": where("beats", position, name)[1], "words": count,
                      "ends_at": round(end, 2), "sentence": part}
    else:
        flag("fix", "no-speech", "", 0, "Script", "No Line Has Spoken Words.")
    mark = {"state": "ended", "runtime": round(total, 2)}
    for position, (beat, start, length, good) in enumerate(rows):
        if start <= 10 < start + length:
            name = str(beat.get("id") or f"Beat {position + 1}")
            tokens = str(beat.get("voice") or "").split()
            said = [token for token in tokens if WORD.search(token)]
            reached = int((10 - start) * pace + 1e-9)
            mark = {"beat": name, "line": where("beats", position, name)[1], "words_in": min(reached, len(said))}
            if reached >= len(said):
                mark.update(state="hold", said_before=" ".join(tokens))
            else:
                cut = 0
                for index, token in enumerate(tokens):
                    if WORD.search(token):
                        if cut == reached:
                            break
                        cut += 1
                else:
                    index = len(tokens)
                mark.update(state="speaking", said_before=" ".join(tokens[:index]),
                            said_after=" ".join(tokens[index:]))
            break
    middle = [
        str(beat.get("id") or f"Beat {position + 1}")
        for position, (beat, start, length, good) in enumerate(rows)
        if start < 10 and start + length > OPENING_SECONDS
    ]
    if target is not None:
        if total > target + 0.5:
            flag("fix", "over-target", "", 0, "Runtime",
                 f"The Timed Script Runs {number_text(total, 2)} Seconds, "
                 f"{number_text(total - target, 2)} Over The {number_text(target, 2)}-Second "
                 "Target. Cut A Part Rather Than Rushing Every Line.")
        elif total < 0.9 * target:
            flag("review", "under-target", "", 0, "Runtime",
                 f"The Timed Script Runs {number_text(total, 2)} Seconds, "
                 f"{number_text(target - total, 2)} Under The {number_text(target, 2)}-Second "
                 "Target. Confirm The Shorter Runtime Is Intended.")
    if spoken / pace > total + 1:
        flag("review", "speech-over-runtime", "", 0, "Runtime",
             f"The Lines Need About {number_text(spoken / pace)} Seconds To Say But The "
             f"Beats Total {number_text(total, 2)}.")
    if not str(script.get("caption") or "").strip():
        flag("review", "no-caption", "", 0, "Caption",
             "No Draft Post Caption. Write One That Carries The Caveats And Links The "
             "Spoken Script Cannot.")
    options = script.get("openings") or []
    if not options:
        flag("review", "no-alternatives", "", 0, "Openings", "No Alternative Opening Is Written.")
    for position, option in enumerate(options):
        name = f"Opening {position + 1}"
        missing = [
            label
            for key, label in (("first_sentence", "First Sentence"), ("second_sentence", "Second Sentence"))
            if not str(option.get(key) or "").strip()
        ]
        if missing:
            flag("review", "opening-unwritten", "openings", position, name,
                 f"This Alternative Opening Has No {' Or '.join(missing)}.")
    return {
        "title": script.get("title", ""),
        "pace": pace,
        "runtime_seconds": round(total, 3),
        "spoken_seconds": round(spoken / pace, 2),
        "spoken_words": spoken,
        "target_seconds": target,
        "opening": opening,
        "second_sentence": second,
        "seconds_3_to_10": middle,
        "ten_second_mark": mark,
        "issues": issues,
        "fix": sum(1 for issue in issues if issue["level"] == "fix"),
        "review": sum(1 for issue in issues if issue["level"] == "review"),
    }


def check_report(result, pace_source):
    lines = [
        f"Script Check | {result['title']}",
        f"Pace: {number_text(result['pace'], 2)} Words Per Second ({pace_source}). "
        f"Timed Runtime: {number_text(result['runtime_seconds'], 2)} Seconds. "
        f"Spoken Estimate: {number_text(result['spoken_seconds'])} Seconds For "
        f"{result['spoken_words']} Words. Target: "
        + (
            "None Given."
            if result["target_seconds"] is None
            else f"{number_text(result['target_seconds'], 2)} Seconds."
        ),
    ]
    for level, heading in (("fix", "To Fix"), ("review", "To Review")):
        chosen = [issue for issue in result["issues"] if issue["level"] == level]
        if chosen:
            lines += ["", f"{heading} ({len(chosen)})"]
            lines += [f"- {issue['where']}: {issue['message']}" for issue in chosen]
    lines += ["", "Timing"]
    for key, label in (("opening", "Opening Sentence"), ("second_sentence", "Second Sentence")):
        part = result[key]
        if part:
            spot = part["beat"] + (f" (Line {part['line']})" if part["line"] else "")
            lines.append(
                f"- {label}, {spot}: {part['words']} Words, Finished At About "
                f"{number_text(part['ends_at'])} Seconds. \"{part['sentence']}\""
            )
    if result["seconds_3_to_10"]:
        lines.append("- Seconds 3 To 10 Run Through " + ", ".join(result["seconds_3_to_10"]) + ".")
    mark = result["ten_second_mark"]
    if mark["state"] == "ended":
        lines.append(
            f"- Ten-Second Mark: The Script Ends At {number_text(mark['runtime'], 2)} "
            "Seconds, Before The Mark."
        )
    else:
        spot = mark["beat"] + (f" (Line {mark['line']})" if mark["line"] else "")
        if mark["state"] == "hold":
            lines.append(f"- Ten-Second Mark: Falls In {spot}, During The Hold After Its Line.")
        else:
            lines.append(
                f"- Ten-Second Mark: Falls In {spot}, About {mark['words_in']} Words In. "
                f"Said Before It: \"{mark['said_before']}\" Still To Come: \"{mark['said_after']}\""
            )
    lines += ["", f"Result: {result['fix']} To Fix, {result['review']} To Review."]
    return "\n".join(lines)


def sheet(script, pace, pace_source):
    """Lay Out Everything The Creator Receives With A Script."""
    rows, total = timeline(script)
    spoken = sum(len(words(beat.get("voice"))) for beat, *_ in rows)
    unwritten = "Not Written"

    def cell(value):
        return str(value or "").replace("|", "\\|").replace("\n", " ")

    lines = [
        f"# {script.get('title', '')}",
        "",
        f"- Runtime: {number_text(total, 2)} Seconds Timed. About "
        f"{number_text(spoken / pace)} Seconds Spoken At {number_text(pace, 2)} Words "
        f"Per Second ({pace_source}).",
    ]
    for key, label in (("goal", "Goal"), ("idea", "Idea"), ("target_seconds", "Target Runtime")):
        if script.get(key) not in (None, ""):
            value = script[key]
            if key == "target_seconds":
                value = f"{number_text(value, 2)} Seconds"
            lines.append(f"- {label}: {value}")
    lines += [
        "",
        "## Timed Script",
        "",
        "| Time | Line | Say | Show | Capture | Proof |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for beat, start, length, _ in rows:
        lines.append(
            f"| {start:05.2f} - {start + length:05.2f} | "
            + " | ".join(
                cell(value)
                for value in (
                    f"{beat.get('id', '')} {beat.get('purpose', '')}".strip(),
                    beat.get("voice"),
                    beat.get("picture"),
                    beat.get("capture") or (f"Media: {beat['media']}" if beat.get("media") else ""),
                    beat.get("proof"),
                )
            )
            + " |"
        )
    lines += ["", "## Capture List", ""]
    for beat, *_ in rows:
        need = beat.get("capture") or beat.get("picture") or unwritten
        state = f"Have {beat['media']}" if beat.get("media") else "Capture Needed"
        lines.append(f"- {beat.get('id', '')}: {need} | {state}")
    lines += ["", "## Alternative Openings", ""]
    options = script.get("openings") or []
    for number, option in enumerate(options, 1):
        lines.append(
            f"{number}. {option.get('angle') or 'Alternative'} | "
            f"First Sentence: {option.get('first_sentence') or unwritten} | "
            f"Second Sentence: {option.get('second_sentence') or unwritten} | "
            f"First Frame: {option.get('first_frame') or unwritten}"
        )
    if not options:
        lines.append(unwritten + ".")
    lines += ["", "## Draft Caption", "", str(script.get("caption") or "").strip() or unwritten + "."]
    lines += ["", "## Claims To Verify", ""]
    proofs = script.get("evidence") or []
    for proof in proofs:
        opened = proof.get("opened")
        state = (
            "Source Opened"
            if opened is True
            else "Source Could Not Be Opened, Unverified"
            if opened is False
            else "Source Not Yet Opened"
        )
        checked = f" Checked: {proof['checked']}." if proof.get("checked") else ""
        lines.append(
            f"- {proof.get('id', '')}: {proof.get('claim', '')} | Source: "
            f"{proof.get('source') or 'None'} | {state}.{checked}"
        )
    if not proofs:
        lines.append("None Listed.")
    return "\n".join(lines)


def main(argv=None):
    guard_streams()
    cli = DeskParser(description=__doc__)
    sub = cli.add_subparsers(dest="command", title="Commands", metavar="COMMAND", required=True)
    about = "Draft A Timed Script With Two Opening Treatments From A Campaign Brief"
    new = sub.add_parser("outline", help=about, description=about)
    new.add_argument("brief", type=Path, help="The Campaign Brief")
    new.add_argument("output", type=Path, help="A New Script File")
    new.add_argument("--seconds", type=float, default=30, help="Total Runtime. Default 30")
    about = "Print A Table Read"
    read = sub.add_parser("read", help=about, description=about)
    read.add_argument("script", type=Path, help="The Script File")
    about = "Hold A Script Against The Timing, Picture, Claim, And Call To Action Rules"
    lint = sub.add_parser("check", help=about, description=about)
    lint.add_argument("script", type=Path, help="The Script File")
    lint.add_argument("--target", type=clock, metavar="SECONDS", help="Target Runtime As 30 Or 0:30")
    lint.add_argument("--json", action="store_true", help="Print The Result As JSON")
    lint.add_argument("--strict", action="store_true", help="Also Fail When Anything Is Left To Review")
    about = "Print The Delivery Sheet: Timed Script, Capture List, Openings, Caption, And Claims"
    hand = sub.add_parser("sheet", help=about, description=about)
    hand.add_argument("script", type=Path, help="The Script File")
    for part in (lint, hand):
        part.add_argument(
            "--pace",
            type=float,
            metavar="WORDS",
            help="Spoken Words Per Second. Defaults To The Script, Then The Defaults File, Then 3",
        )
    a = cli.parse_args(argv)
    guard_streams(utf8=a.command in ("check", "sheet"))
    try:
        if a.command == "outline":
            if not math.isfinite(a.seconds) or not 3 <= a.seconds <= 7200:
                raise ValueError("Choose A Duration From 3 To 7200 Seconds.")
            obj = outline(json.loads(a.brief.read_text(encoding="utf-8")), a.seconds)
            if any(b["seconds"] <= 0 for b in obj["beats"]):
                raise ValueError("Increase Duration Or Use Fewer Proof Beats.")
            with a.output.open("x", encoding="utf-8") as handle:
                json.dump(obj, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            print(f"Created {a.output}")
        elif a.command == "read":
            script = json.loads(a.script.read_text(encoding="utf-8"))
            if script["format"] != "school.script/1":
                raise ValueError("Expected A Script File.")
            print(f"# {script['title']}\n")
            start = 0.0
            for b in script["beats"]:
                end = start + float(b["seconds"])
                print(
                    f"{start:06.2f} - {end:06.2f} | {b['voice']} | {b['picture']} | {b['proof']}"
                )
                start = end
        else:
            script, lines = load_script(a.script)
            pace, source = choose_pace(a.pace, script)
            if a.command == "sheet":
                print(sheet(script, pace, source))
                return 0
            target = a.target
            if target is None and isinstance(script.get("target_seconds"), (int, float)):
                target = float(script["target_seconds"])
            result = study(script, lines, pace, target)
            if a.json:
                print(tidy_json(dict(result, file=str(a.script), pace_source=source), ascii_only=True))
            else:
                print(check_report(result, source))
            if result["fix"] or (a.strict and result["review"]):
                return 1
    except (OSError, KeyError, TypeError, ValueError, AttributeError) as exc:
        cli.exit(1, f"{exc}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
