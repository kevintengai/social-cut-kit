"""Build And Inspect An Editable Social Cut Kit Campaign."""

import argparse
import json
from pathlib import Path


def text(value):
    value = value.strip()
    if not value or "\n" in value or "\r" in value:
        raise argparse.ArgumentTypeError("Enter One Nonempty Line.")
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("new", help="Start A Campaign File")
    create.add_argument("file", type=Path)
    for field in ("title", "viewer", "offer", "action"):
        create.add_argument("--" + field, required=True, type=text)
    for field in ("channel", "destination", "metric", "reviewer"):
        create.add_argument("--" + field, type=text)
    create.add_argument(
        "--proof",
        nargs=3,
        action="append",
        default=[],
        type=text,
        metavar=("CLAIM", "SOURCE", "VISIBLE_DETAIL"),
    )
    display = commands.add_parser("show", help="Read The Brief As Markdown")
    display.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "new":
            campaign = {
                k: getattr(args, k) or ""
                for k in (
                    "title",
                    "viewer",
                    "offer",
                    "action",
                    "channel",
                    "destination",
                    "metric",
                    "reviewer",
                )
            }
            campaign["format"] = "school.campaign/1"
            campaign["evidence"] = [
                {"id": f"P{i}", "claim": claim, "source": source, "visual": visual}
                for i, (claim, source, visual) in enumerate(args.proof, 1)
            ]
            with args.file.open("x", encoding="utf-8") as handle:
                json.dump(campaign, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            print(f"Created {args.file}")
        else:
            brief = json.loads(args.file.read_text(encoding="utf-8"))
            if brief["format"] != "school.campaign/1":
                raise ValueError("Expected A Social Cut Kit Campaign.")
            print(f"# {brief['title']}\n\nTENG AI SCHOOL | Social Cut Kit\n")
            for field in (
                "viewer",
                "offer",
                "channel",
                "action",
                "destination",
                "metric",
                "reviewer",
            ):
                print(f"- {field.title()}: {brief[field] or 'Open Decision'}")
            print("\n## Evidence\n")
            for proof in brief["evidence"]:
                print(
                    f"- {proof['id']} | {proof['claim']} | {proof['source']} | {proof['visual']}"
                )
            if not brief["evidence"]:
                print("Request A Source Capture Before Promising A Result.")
    except (KeyError, OSError, ValueError, TypeError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
