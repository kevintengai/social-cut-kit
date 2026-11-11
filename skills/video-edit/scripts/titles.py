"""Create A Transparent Multiline Title Or Callout PNG With A Local Chromium Browser."""

import argparse
import html
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile


def positive(value):
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("Enter A Positive Integer")
    return result


def nonnegative(value):
    result = int(value)
    if result < 0:
        raise argparse.ArgumentTypeError("Enter Zero Or A Positive Integer")
    return result


def color(value):
    if not re.fullmatch(r"#[a-fA-F0-9]{6}", value):
        raise argparse.ArgumentTypeError("Enter A Six-Digit Hex Color Beginning With #")
    return value


def browser_path(override):
    if override:
        if not override.is_file():
            raise ValueError("The Supplied Browser Path Does Not Exist")
        return str(override.resolve())
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "brave-browser"):
        if shutil.which(name):
            return shutil.which(name)
    candidates = [
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
        Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
    ]
    for key in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        if key in os.environ:
            root = Path(os.environ[key])
            candidates.extend([root / "Google/Chrome/Application/chrome.exe",
                               root / "Microsoft/Edge/Application/msedge.exe"])
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    raise ValueError("Install A Local Chromium Browser Or Provide Its Executable With --browser")


def mark_text(text, phrase):
    if not text.strip():
        raise ValueError("Enter Visible Text For The Title")
    if phrase is None:
        return html.escape(text), 0
    if not phrase.strip():
        raise ValueError("Enter A Nonempty Highlight")
    rule = re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", re.IGNORECASE)
    pieces, start, count = [], 0, 0
    for match in rule.finditer(text):
        pieces.extend([html.escape(text[start:match.start()]), "<em>", html.escape(match.group()), "</em>"])
        start = match.end()
        count += 1
    if not count:
        raise ValueError("The Highlight Was Not Found As A Whole Word Or Phrase")
    pieces.append(html.escape(text[start:]))
    return "".join(pieces), count


def page(args, markup):
    if not re.fullmatch(r"[\w -]+", args.font_family):
        raise ValueError("Use A Single Installed Font Family Name With Letters, Numbers, Spaces, Or Hyphens")
    alignment = {"left": "flex-start", "center": "center", "right": "flex-end"}[args.align]
    position = {"top": "flex-start", "center": "center", "bottom": "flex-end"}[args.position]
    if args.style == "box":
        treatment = f"background:{args.plate_color};padding:{args.padding}px;border-radius:{args.radius}px"
    else:
        treatment = f"-webkit-text-stroke:{max(1, args.size / 16):.2f}px #10141c;paint-order:stroke fill"
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
* {{ box-sizing:border-box }}
html, body {{ margin:0; background:transparent; overflow:hidden }}
main {{ width:{args.width}px;height:{args.height}px;padding:{args.margin}px;display:flex;
  flex-direction:column;align-items:{alignment};justify-content:{position} }}
section {{ flex:none;max-width:100%;min-width:0;width:max-content;text-align:{args.align};
  white-space:pre-wrap;overflow-wrap:anywhere;color:{args.ink};{treatment};
  font:700 {args.size}px/1.22 "{args.font_family}",Arial,"Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif }}
em {{ color:{args.accent};font-style:normal }}
</style></head><body><main><section>{markup}</section></main>
<script>
document.fonts.ready.then(() => {{
  const s = document.querySelector("section");
  const b = s.getBoundingClientRect();
  const margin = {args.margin};
  const fits = b.left >= margin - .5 && b.top >= margin - .5 &&
    b.right <= {args.width} - margin + .5 && b.bottom <= {args.height} - margin + .5 &&
    s.scrollWidth <= s.clientWidth + 1 && s.scrollHeight <= s.clientHeight + 1;
  document.documentElement.dataset.layout = fits ? "fits" : "overflow";
}});
</script></body></html>"""


def render(args):
    out = args.out.absolute()
    if out.suffix.casefold() != ".png" or not out.parent.is_dir():
        raise ValueError("Choose A PNG Path In An Existing Folder")
    if out.exists() and not args.overwrite:
        raise ValueError("Output Exists. Choose A Fresh Path Or Supply --overwrite")
    if args.margin * 2 >= min(args.width, args.height):
        raise ValueError("The Margin Leaves No Space For The Title")
    text = args.text if args.text is not None else args.text_file.read_text(encoding="utf-8-sig").rstrip("\r\n")
    markup, hits = mark_text(text, args.highlight)
    source = page(args, markup)
    browser = browser_path(args.browser)
    with tempfile.TemporaryDirectory(dir=out.parent) as temp:
        work = Path(temp)
        document = work / "title.html"
        png = work / "title.png"
        document.write_text(source, encoding="utf-8")
        command = [browser, "--headless", "--disable-gpu", "--hide-scrollbars", "--disable-extensions",
                   "--no-first-run", "--disable-background-networking", "--disable-sync",
                   "--no-default-browser-check", "--force-device-scale-factor=1",
                   "--default-background-color=00000000", "--user-data-dir=" + str(work / "profile"),
                   f"--window-size={args.width},{args.height}", "--virtual-time-budget=1000",
                   "--dump-dom", "--screenshot=" + str(png), document.as_uri()]
        proc = subprocess.run(command, capture_output=True, timeout=60,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if proc.returncode or not png.is_file():
            raise ValueError("The Local Browser Could Not Render The Title. Check The Browser Path And Output Size")
        if b'data-layout="fits"' not in proc.stdout:
            raise ValueError("The Title Did Not Fit. Reduce The Font Size Or Margin, Or Increase The Canvas")
        with png.open("rb") as stream:
            header = stream.read(29)
        if (header[:8] != b"\x89PNG\r\n\x1a\n" or header[16:24] != struct.pack(">II", args.width, args.height)
                or header[25:26] != b"\x06"):
            raise ValueError("The Browser Did Not Produce The Requested RGBA PNG Dimensions")
        if args.overwrite:
            os.replace(png, out)
        else:
            with out.open("xb") as destination:
                try:
                    with png.open("rb") as stream:
                        shutil.copyfileobj(stream, destination)
                except BaseException:
                    destination.close()
                    out.unlink(missing_ok=True)
                    raise
    return {"path": str(out), "width": args.width, "height": args.height, "highlight_matches": hits}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    text = parser.add_mutually_exclusive_group(required=True)
    text.add_argument("--text", help="Title Text With Optional Literal Line Breaks")
    text.add_argument("--text-file", type=Path, help="Multiline UTF-8 Text File")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--width", type=positive, default=1080)
    parser.add_argument("--height", type=positive, default=1920)
    parser.add_argument("--size", type=positive, default=76, help="Font Size In Pixels")
    parser.add_argument("--font-family", default="Arial")
    parser.add_argument("--highlight", help="Whole Word Or Phrase To Accent")
    parser.add_argument("--style", choices=("box", "plain"), default="box")
    parser.add_argument("--align", choices=("left", "center", "right"), default="center")
    parser.add_argument("--position", choices=("top", "center", "bottom"), default="top")
    parser.add_argument("--margin", type=nonnegative, default=72)
    parser.add_argument("--padding", type=nonnegative, default=22)
    parser.add_argument("--radius", type=nonnegative, default=18)
    parser.add_argument("--ink", type=color, default="#FFFFFF")
    parser.add_argument("--accent", type=color, default="#FFD664")
    parser.add_argument("--plate-color", type=color, default="#14181F")
    parser.add_argument("--browser", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(render(args), indent=2))
        return 0
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
