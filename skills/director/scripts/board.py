"""Convert Script Beats Into A Shot Board Or An Editable Timeline."""

import argparse
import html
import json
import math
import os
from pathlib import Path


def load(path):
    plan = json.loads(path.read_text(encoding="utf-8"))
    if plan["format"] != "school.script/1" or not plan["beats"]:
        raise ValueError("Supply A Script Desk File With Beats.")
    seen = set()
    evidence = {p["id"] for p in plan["evidence"]}
    for beat in plan["beats"]:
        if beat["id"] in seen or not beat["id"]:
            raise ValueError("Each Beat Needs A Unique ID.")
        seen.add(beat["id"])
        if beat.get("proof") and beat["proof"] not in evidence:
            raise ValueError(f"Unknown Proof In {beat['id']}.")
        for key in ("seconds", "source_in"):
            number = float(beat[key])
            if (
                not math.isfinite(number)
                or number < 0
                or (key == "seconds" and number == 0)
            ):
                raise ValueError(f"Invalid {key} In {beat['id']}.")
    return plan


def board(plan):
    e = lambda v: html.escape(str(v))
    rows = []
    elapsed = 0.0
    for b in plan["beats"]:
        dur = float(b["seconds"])
        rows.append(
            "<tr>"
            + "".join(
                "<td>" + e(value) + "</td>"
                for value in (
                    b["id"],
                    f"{elapsed:.2f} - {elapsed + dur:.2f}",
                    b["purpose"],
                    b["picture"],
                    b["voice"],
                    b.get("proof") or "",
                    b.get("media") or "Capture Needed",
                )
            )
            + "</tr>"
        )
        elapsed += dur
    head = "".join(
        "<th>" + s + "</th>"
        for s in ("Beat", "Seconds", "Purpose", "Picture", "Voice", "Proof", "Media")
    )
    return (
        "<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{e(plan['title'])}</title><style>body{{font:16px system-ui;color:#152944;max-width:1100px;margin:4vw auto;padding:1rem}}"
        "table{border-collapse:collapse}td,th{padding:.7rem;text-align:left;border:1px solid #bcc6d0;vertical-align:top}th{background:#f2f4f6}"
        "section{overflow:auto}</style><header>TENG AI SCHOOL | Social Cut Kit</header>"
        f"<h1>{e(plan['title'])}</h1><p>Shot Board · {elapsed:.2f} Seconds</p><section><table><thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></section><h2>Evidence</h2><ul>"
        + "".join(
            f"<li>{e(p['id'])} | {e(p['source'])} | {e(p['visual'])}</li>"
            for p in plan["evidence"]
        )
        + "</ul></html>"
    )


def timeline(plan, a):
    if (
        min(a.width, a.height) < 2
        or a.width % 2
        or a.height % 2
        or not 1 <= a.fps <= 120
    ):
        raise ValueError("Use Positive Even Dimensions And An FPS From 1 To 120.")
    assets, shots = {}, []
    for b in plan["beats"]:
        if not b.get("media"):
            raise ValueError(f"Assign Source Media To {b['id']} First.")
        src = (a.script.parent / b["media"]).resolve(strict=True)
        if not src.is_file():
            raise ValueError(f"Expected A Media File For {b['id']}.")
        try:
            path = os.path.relpath(src, a.output.resolve().parent)
        except ValueError:
            path = str(src)
        kind = (
            "image"
            if src.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".bmp")
            else "video"
        )
        assets[b["id"]] = {"path": path, "kind": kind}
        start = float(b["source_in"])
        shots.append(
            {
                "asset": b["id"],
                "in": start,
                "out": round(start + float(b["seconds"]), 6),
            }
        )
    return json.dumps(
        {
            "version": 1,
            "title": plan["title"],
            "canvas": {
                "width": a.width,
                "height": a.height,
                "fps": a.fps,
                "fit": "contain",
            },
            "assets": assets,
            "shots": shots,
            "captions": [],
            "overlays": [],
            "audio": [],
        },
        indent=2,
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=("board", "timeline"))
    p.add_argument("script", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--width", type=int, default=1080)
    p.add_argument("--height", type=int, default=1920)
    p.add_argument("--fps", type=int, default=30)
    a = p.parse_args()
    try:
        plan = load(a.script)
        result = board(plan) if a.command == "board" else timeline(plan, a)
        with a.output.open("x", encoding="utf-8") as handle:
            handle.write(result + "\n")
        print(f"Created {a.output}")
    except (OSError, KeyError, ValueError, TypeError) as exc:
        p.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
