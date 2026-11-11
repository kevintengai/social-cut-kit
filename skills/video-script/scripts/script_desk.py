"""Create And Read A Timed Two-Column Script."""

import argparse
import json
import math
from pathlib import Path


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


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    sub = cli.add_subparsers(dest="command", required=True)
    new = sub.add_parser("outline")
    new.add_argument("brief", type=Path)
    new.add_argument("output", type=Path)
    new.add_argument("--seconds", type=float, default=30)
    read = sub.add_parser("read")
    read.add_argument("script", type=Path)
    a = cli.parse_args()
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
        else:
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
    except (OSError, KeyError, TypeError, ValueError) as exc:
        cli.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
