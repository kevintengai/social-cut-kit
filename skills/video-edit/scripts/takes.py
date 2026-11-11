"""Locate Repeated Phrase Attempts And Suggest Speech-Safe Take Handles.

Without --retakes Or --script, The Output Is The List Of Nearby Repeats Inside The Window. With Either
Option, The Tool Also Groups Whole Passages Performed Several Times Anywhere In The Recording, Says How
Complete Each Attempt Looks From Its Words, And Can Align The Attempts Against The Lines Of A Script.
It Reads Words And Times Only. It Cannot Hear Performance.
"""

import argparse
from difflib import SequenceMatcher
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from speech import ends_sentence, load_words, single_words

TOKEN = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", flags=re.UNICODE)
# A Dash Or An Ellipsis At The End Of A Word Marks Speech That Trails Off Or Is Cut Short.
TRAILS = re.compile(r"(\.\.\.|…|-|–|—)[\"'”’)\]]*$")
LISTENING_NOTE = ("These Hints Come From Words And Times Only. The Tool Cannot Hear Performance. Audition Each "
                  "Range, And When Attempts Are Equally Complete, Offer The Owner The Choice.")
REPEAT_NOTE = "A Repeat Inside One Sentence Can Be Deliberate. Listen Before Treating It As A Restart."


def normalize(text):
    return TOKEN.findall(text.casefold())


def candidates(words, phrase, window, handle):
    tokens = []
    for s, e, w in words:
        # Subtitle cues can contain multiple words but supply only cue-level boundaries.
        tokens.extend((t, s, e) for t in normalize(w))
    occurrences = {}
    for i in range(len(tokens) - phrase + 1):
        span = tokens[i : i + phrase]
        if span[-1][2] - span[0][1] > phrase * 2:
            continue
        key = tuple(t[0] for t in span)
        occurrences.setdefault(key, []).append((i, span[0][1], span[-1][2]))
    choices = []
    for key, runs in occurrences.items():
        for first, second in zip(runs, runs[1:]):
            i, s, e = first
            j, t, u = second
            if not (i + phrase <= j and e <= t <= e + window):
                continue
            if i > 0 and j > 0 and tokens[i - 1][0] == tokens[j - 1][0]:
                continue
            choices.append(
                {
                    "phrase": " ".join(key),
                    "first_attempt": [s, e],
                    "next_attempt": [t, u],
                    "audition_ranges": [
                        [round(max(0, s - handle), 3), round(e + handle, 3)],
                        [round(max(0, t - handle), 3), round(u + handle, 3)],
                    ],
                }
            )
    return sorted(choices, key=lambda c: c["first_attempt"][0])


def spoken_units(words):
    """One Entry Per Spoken Word That Carries At Least One Letter Or Digit."""
    units = []
    for start, end, text in words:
        tokens = normalize(text)
        if tokens:
            units.append({"start": start, "end": end, "text": text, "tokens": tokens})
    return units


def restart_at(tokens, phrase):
    """The Index Where An Opening Phrase Is Said Again Inside One Utterance, Or None."""
    seen = {}
    for i in range(len(tokens) - phrase + 1):
        key = tuple(tokens[i : i + phrase])
        first = seen.setdefault(key, i)
        if i >= first + phrase:
            return i
    return None


def utterances(units, gap, phrase):
    """Split Speech At Sentence Ends, Trailing-Off Marks, Pauses, And Restarts Inside A Sentence."""
    runs, active = [], []
    for i, unit in enumerate(units):
        active.append(i)
        following = units[i + 1] if i + 1 < len(units) else None
        trails = bool(TRAILS.search(unit["text"]))
        if following is None or trails or ends_sentence(unit["text"]) or following["start"] - unit["end"] >= gap:
            runs.append(active)
            active = []
    pieces = []
    for run in runs:
        split = False
        while True:
            # One Token List Per Word, So A Restart Is Cut At A Word Boundary.
            flat = [(token, n) for n, i in enumerate(run) for token in units[i]["tokens"]]
            at = restart_at([token for token, _ in flat], phrase)
            cut = flat[at][1] if at is not None else 0
            if not cut:
                break
            pieces.append((run[:cut], True, split))
            run, split = run[cut:], True
        pieces.append((run, False, split))
    result = []
    for n, (run, restarted, after_repeat) in enumerate(pieces):
        first, last = units[run[0]], units[run[-1]]
        before = units[run[0] - 1]["end"] if run[0] else None
        after = units[run[-1] + 1]["start"] if run[-1] + 1 < len(units) else None
        result.append({
            "index": n, "start": first["start"], "end": last["end"],
            "text": " ".join(units[i]["text"] for i in run),
            "tokens": [token for i in run for token in units[i]["tokens"]],
            "restarted": restarted, "after_repeat": after_repeat,
            "trails": bool(TRAILS.search(last["text"])) and not restarted,
            "sentence_end": ends_sentence(last["text"]) and not TRAILS.search(last["text"]),
            "gap_before": None if before is None else max(0.0, first["start"] - before),
            "gap_after": None if after is None else max(0.0, after - last["end"]),
        })
    return result


def matched(a, b):
    return sum(block.size for block in SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks())


def prefix(a, b):
    count = 0
    for x, y in zip(a, b):
        if x != y:
            break
        count += 1
    return count


def same_line(a, b, phrase, minimum):
    """Whether Two Utterances Read As Attempts At One Line: A Shared Opening, Or Mostly Shared Words."""
    short, long = min(len(a), len(b)), max(len(a), len(b))
    opening = prefix(a, b)
    if opening >= phrase and opening >= 0.6 * short:
        return True
    shared = matched(a, b)
    return shared >= minimum and shared >= 0.7 * short and shared >= 0.4 * long


def safe_handles(piece, handle):
    """Handles That Stop Short Of The Neighboring Words, Ready For The Lead And Tail Fields Of A Shot."""
    lead = handle if piece["gap_before"] is None else min(handle, piece["gap_before"])
    tail = handle if piece["gap_after"] is None else min(handle, piece["gap_after"])
    lead = min(lead, piece["start"])
    return round(lead, 3), round(tail, 3)


def describe(piece, following, punctuated, gap, handle):
    """Times, Handles, And A Completeness Hint For One Attempt."""
    resumed = (following is not None and piece["gap_after"] is not None and piece["gap_after"] < max(gap, 1.5)
               and prefix(piece["tokens"], following["tokens"]) >= 2 and not piece["sentence_end"])
    interrupted = piece["restarted"] or piece["trails"] or resumed
    reaches = (piece["sentence_end"] and not interrupted) if punctuated else None
    if interrupted:
        hint = "interrupted"
    elif reaches:
        hint = "complete"
    elif punctuated:
        hint = "no_sentence_end"
    else:
        hint = "ends_at_a_pause" if piece["gap_after"] is None or piece["gap_after"] >= gap else "runs_on"
    lead, tail = safe_handles(piece, handle)
    row = {
        "source_seconds": [round(piece["start"], 3), round(piece["end"], 3)],
        "audition_range": [round(piece["start"] - lead, 3), round(piece["end"] + tail, 3)],
        "handles": {"lead": lead, "tail": tail},
        "text": piece["text"], "words": len(piece["tokens"]),
        "reaches_sentence_end": reaches, "interrupted": interrupted, "hint": hint,
    }
    if piece["restarted"] or piece["after_repeat"]:
        row["split_at_repeat"] = True
    return row


def looks_complete(row, longest, punctuated):
    if row["interrupted"]:
        return False
    if punctuated:
        return row["hint"] == "complete"
    return row["hint"] == "ends_at_a_pause" and row["words"] >= 0.9 * longest


def choice(rows):
    """Say Which Takes Look Complete And Who Decides Between Them."""
    complete = [row["take"] for row in rows if row["complete"]]
    if not complete:
        return {"complete_takes": [], "decision": "no_complete_take",
                "note": "No Attempt Looks Complete From Its Words. Audition Each Range, Then Tell The Owner Which Line Has No Clean Take."}
    if len(complete) == 1:
        return {"complete_takes": complete, "decision": "one_complete_take",
                "note": f"Take {complete[0]} Is The Only Attempt That Looks Complete. Audition It Before Committing The Cut."}
    return {"complete_takes": complete, "decision": "owner_choice", "latest_complete_take": complete[-1],
            "note": f"Takes {', '.join(str(n) for n in complete)} Look Equally Complete. The Tool Cannot Hear Performance. "
                    f"Offer The Owner The Choice, And Recommend Take {complete[-1]}, The Latest, Unless They Prefer Another."}


def retake_groups(pieces, punctuated, phrase, minimum, gap, handle):
    """Group Utterances That Read As Attempts At The Same Line, However Far Apart They Are."""
    parent = list(range(len(pieces)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    index = {}
    for i, piece in enumerate(pieces):
        tokens = piece["tokens"]
        size = min(phrase, len(tokens))
        for at in range(len(tokens) - size + 1):
            index.setdefault(tuple(tokens[at : at + size]), set()).add(i)
    for members in index.values():
        ordered = sorted(members)
        for n, i in enumerate(ordered):
            for j in ordered[n + 1 :]:
                if find(i) != find(j) and same_line(pieces[i]["tokens"], pieces[j]["tokens"], phrase, minimum):
                    parent[find(j)] = find(i)
    groups = {}
    for i in range(len(pieces)):
        groups.setdefault(find(i), []).append(i)
    result = []
    for members in groups.values():
        if len(members) < 2:
            continue
        rows = []
        for take, i in enumerate(members, 1):
            following = pieces[i + 1] if i + 1 < len(pieces) else None
            rows.append(dict(take=take, **describe(pieces[i], following, punctuated, gap, handle)))
        longest = max(row["words"] for row in rows)
        for row in rows:
            row["share_of_longest_attempt"] = round(row["words"] / longest, 2)
            row["complete"] = looks_complete(row, longest, punctuated)
        fullest = max(rows, key=lambda row: (row["complete"], row["words"], row["take"]))
        group = {"line": fullest["text"], "attempts": rows, **choice(rows)}
        if any(row.get("split_at_repeat") for row in rows):
            group["caution"] = REPEAT_NOTE
        result.append(group)
    return sorted(result, key=lambda group: group["attempts"][0]["source_seconds"][0])


def script_lines(text):
    """Spoken Lines From A Script: One Per Sentence, Without Stage Directions, Labels, Or List Marks."""
    lines = []
    for raw in text.splitlines():
        line = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", raw).strip()
        if not line or line.startswith("#"):
            continue
        line = re.sub(r"^(?:[-*•]+|\d+[.)])\s+", "", line)
        line = re.sub(r"^\d{1,2}:\d{2}(?::\d{2})?(?:\s*[-–—]\s*\d{1,2}:\d{2}(?::\d{2})?)?\s*[-–—:]?\s*", "", line)
        line = re.sub(r"^[A-Z][A-Z0-9 /&-]{1,24}:\s*", "", line)
        sentence = []
        for part in line.split():
            sentence.append(part)
            if ends_sentence(part):
                lines.append(" ".join(sentence))
                sentence = []
        if sentence:
            lines.append(" ".join(sentence))
    return [line for line in lines if normalize(line)]


def align_script(lines, pieces, punctuated, gap, handle):
    """Find Each Script Line's Attempts In The Speech And Say Which Lines Have No Complete Take."""
    report, used = [], set()
    for number, text in enumerate(lines, 1):
        wanted = normalize(text)
        vocabulary = set(wanted)
        found = []
        for i in range(len(pieces)):
            for count in (1, 2, 3):
                run = pieces[i : i + count]
                if len(run) < count or any(a["gap_after"] is not None and a["gap_after"] > 3 for a in run[:-1]):
                    break
                spoken = [token for piece in run for token in piece["tokens"]]
                opening = prefix(wanted, spoken)
                if len(vocabulary & set(spoken)) < 0.4 * len(vocabulary) and opening < 3:
                    continue
                matcher = SequenceMatcher(None, wanted, spoken, autojunk=False)
                blocks = [block for block in matcher.get_matching_blocks() if block.size]
                shared = sum(block.size for block in blocks)
                coverage, purity = shared / len(wanted), shared / len(spoken)
                enough = shared >= min(len(wanted), 2) and coverage >= 0.5 and purity >= 0.5
                if len(wanted) <= 3:
                    enough = shared == len(wanted) and purity >= 0.5
                elif not enough:
                    # A False Start Covers Little Of Its Line, But It Opens With The Line's Own Words.
                    enough = count == 1 and opening >= 3 and purity >= 0.5
                if not enough:
                    continue
                reached = max(block.a + block.size for block in blocks) >= len(wanted) - (1 if len(wanted) > 4 else 0)
                # Every Run Is A Candidate. The Best Ones Are Kept First, And A Run That Overlaps A Kept One Is Dropped.
                found.append((coverage * purity, i, count, coverage, purity, reached))
        attempts, taken = [], set()
        for score, i, count, coverage, purity, reached in sorted(found, key=lambda row: (-row[0], row[2], row[1])):
            span = set(range(i, i + count))
            if span & taken:
                continue
            taken |= span
            run = pieces[i : i + count]
            joined = dict(run[-1], start=run[0]["start"], gap_before=run[0]["gap_before"],
                          text=" ".join(piece["text"] for piece in run),
                          tokens=[token for piece in run for token in piece["tokens"]],
                          after_repeat=any(piece["restarted"] or piece["after_repeat"] for piece in run))
            following = pieces[i + count] if i + count < len(pieces) else None
            row = describe(joined, following, punctuated, gap, handle)
            ends_well = row["hint"] in ("complete", "ends_at_a_pause")
            row.update(script_coverage=round(coverage, 2), reaches_line_end=reached,
                       complete=bool(coverage >= 0.8 and reached and not row["interrupted"] and ends_well))
            if row["complete"] and (coverage < 0.999 or purity < 0.85):
                row["wording_differs_from_script"] = True
            attempts.append((run[0]["start"], span, row))
        attempts.sort(key=lambda item: item[0])
        rows = []
        for take, (_, span, row) in enumerate(attempts, 1):
            used |= span
            rows.append(dict(take=take, **row))
        entry = {"line": number, "script_text": text, "attempts": rows}
        entry.update(choice(rows) if rows else {"complete_takes": [], "decision": "not_spoken",
                                              "note": "No Passage In The Recording Matches This Line."})
        report.append(entry)
    missing = [{"line": entry["line"], "script_text": entry["script_text"], "decision": entry["decision"]}
               for entry in report if not entry["complete_takes"]]
    extra = [{"source_seconds": [round(piece["start"], 3), round(piece["end"], 3)], "text": piece["text"]}
             for i, piece in enumerate(pieces) if i not in used and len(piece["tokens"]) >= 4]
    return {"lines": report, "lines_without_a_complete_take": missing, "spoken_but_not_in_script": extra}


def retakes(words, phrase, window, handle, minimum=5, gap=0.7, script=None):
    """The Full Report: Retake Groups Anywhere In The Recording, Nearby Repeats, And Script Alignment."""
    single, estimated = single_words(words)
    units = spoken_units(single)
    if not units:
        raise ValueError("Expected Nonempty Timed Words Or Subtitle Cues.")
    punctuated = any(ends_sentence(unit["text"]) for unit in units)
    pieces = utterances(units, gap, phrase)
    report = {
        "mode": "retakes", "words": sum(len(unit["tokens"]) for unit in units), "utterances": len(pieces),
        "sentence_punctuation": punctuated, "estimated_word_timings": estimated,
        "retakes": retake_groups(pieces, punctuated, phrase, minimum, gap, handle),
        "nearby_repeats": candidates(words, phrase, window, handle),
    }
    if script is not None:
        lines = script_lines(script)
        if not lines:
            raise ValueError("The Script File Holds No Spoken Lines.")
        report["script"] = align_script(lines, pieces, punctuated, gap, handle)
    notes = [LISTENING_NOTE]
    if not punctuated:
        notes.append("The Transcript Has No Sentence Punctuation, So Completeness Is Judged From Pauses Alone. "
                     "Transcribe With Punctuation For A Firmer Hint.")
    if estimated:
        notes.append("Some Transcript Units Carried Several Words. Their Word Times Are Estimates, So Check Each "
                     "Range By Ear Before Cutting.")
    report["notes"] = notes
    return report


def build_parser():
    p = argparse.ArgumentParser(description="Locate Repeated Phrase Attempts And Suggest Speech-Safe Take Handles.")
    p.add_argument("transcript", type=Path)
    p.add_argument("--words", type=int, default=3,
                   help="Words In A Phrase That Counts As A Repeat Or A Restart. The Default Is 3")
    p.add_argument("--window", type=float, default=30,
                   help="Seconds Within Which A Nearby Repeat Is Reported. The Default Is 30")
    p.add_argument("--handle", type=float, default=0.15,
                   help="Seconds Of Audio Handle Around Each Range. The Default Is 0.15")
    p.add_argument("--retakes", action="store_true",
                   help="Also Group Whole Passages Performed Several Times Anywhere In The Recording")
    p.add_argument("--script", type=Path,
                   help="A Plain Text Script. Attempts Are Aligned Against Its Lines. This Also Turns On --retakes")
    p.add_argument("--min-words", type=int, default=5,
                   help="Fewest Shared Words For Two Passages To Count As The Same Line. The Default Is 5")
    p.add_argument("--gap", type=float, default=0.7, metavar="SECONDS",
                   help="A Silence This Long Ends A Passage. The Default Is 0.7")
    return p


def main(argv=None):
    p = build_parser()
    a = p.parse_args(argv)
    if not 2 <= a.words <= 12 or not 0 < a.window <= 3600 or not 0 <= a.handle <= 5:
        p.error("Check Phrase Length, Window, And Audio Handle.")
    if not 2 <= a.min_words <= 50 or not 0.05 <= a.gap <= 30:
        p.error("Use 2 To 50 Shared Words And A Gap From 0.05 To 30 Seconds.")
    try:
        words = load_words(a.transcript)
        if a.retakes or a.script:
            if a.script and a.script.suffix.lower() == ".json":
                raise ValueError("Supply The Script As A Plain Text File.")
            script = a.script.read_text(encoding="utf-8-sig") if a.script else None
            result = retakes(words, a.words, a.window, a.handle, a.min_words, a.gap, script)
        else:
            result = candidates(words, a.words, a.window, a.handle)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ValueError, KeyError, OSError, TypeError) as exc:
        p.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
