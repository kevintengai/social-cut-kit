#!/usr/bin/env python3
"""Check This Machine For The Tools The Video Editor Uses. Nothing Is Installed."""

import argparse
import importlib.util
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

MINIMUM_PYTHON = (3, 9)
OLDEST_FFMPEG = (5, 1)
CHECKED_FFMPEG = "8.1"
POLICY = "This Check Installs Nothing. Show An Install Command To The User And Run It Only After They Agree."
MANAGERS = {"Windows": ("winget", "choco", "scoop"), "Darwin": ("brew", "port"),
            "Linux": ("apt-get", "dnf", "pacman", "apk", "brew")}
RECIPES = {
    "ffmpeg": {"winget": "winget install --id Gyan.FFmpeg -e", "choco": "choco install ffmpeg-full -y",
               "scoop": "scoop install ffmpeg", "brew": "brew install ffmpeg", "port": "sudo port install ffmpeg",
               "apt-get": "sudo apt-get install -y ffmpeg", "dnf": "sudo dnf install -y ffmpeg",
               "pacman": "sudo pacman -S --needed ffmpeg", "apk": "sudo apk add ffmpeg"},
    "node": {"winget": "winget install --id OpenJS.NodeJS.LTS -e", "choco": "choco install nodejs-lts -y",
             "scoop": "scoop install nodejs-lts", "brew": "brew install node",
             "apt-get": "sudo apt-get install -y nodejs", "dnf": "sudo dnf install -y nodejs",
             "pacman": "sudo pacman -S --needed nodejs", "apk": "sudo apk add nodejs"},
    "browser": {"winget": "winget install --id Google.Chrome -e", "choco": "choco install googlechrome -y",
                "brew": "brew install --cask google-chrome", "apt-get": "sudo apt-get install -y chromium",
                "dnf": "sudo dnf install -y chromium", "pacman": "sudo pacman -S --needed chromium",
                "apk": "sudo apk add chromium"},
    "python": {"winget": "winget install --id Python.Python.3.12 -e", "choco": "choco install python -y",
               "scoop": "scoop install python", "brew": "brew install python",
               "apt-get": "sudo apt-get install -y python3", "dnf": "sudo dnf install -y python3",
               "pacman": "sudo pacman -S --needed python", "apk": "sudo apk add python3"},
}
MANUAL = {
    "ffmpeg": "No Supported Package Manager Was Found. Install A Full FFmpeg Build From ffmpeg.org And Add Its Program Folder To PATH.",
    "node": "No Supported Package Manager Was Found. Install The Node.js LTS Release From nodejs.org.",
    "browser": "No Supported Package Manager Was Found. Install Chrome, Chromium, Or Edge, Or Pass Its Path To titles.py With --browser.",
    "python": "No Supported Package Manager Was Found. Install Python 3.9 Or Later From python.org.",
    "resolve": "Download DaVinci Resolve From The Blackmagic Design Website. Native Timelines Need Resolve Studio 21.1 Or Later. No Package Manager Command Is Offered.",
}
# Each FFmpeg Feature Group Lists What The Scripts In This Folder Call.
FEATURES = [
    ("ffmpeg-delivery-encoders", "encoders", ("libx264", "aac"), True,
     "Encodes The Owner-Approved MP4 With H.264 Picture And AAC Sound."),
    ("ffmpeg-review-outputs", "encoders", ("png", "pcm_s16le"), True,
     "Writes Review Stills And Check Mixes, And Feeds Audio Analysis."),
    ("ffmpeg-composition-filters", "filters",
     ("scale", "crop", "pad", "fps", "format", "setsar", "setpts", "settb", "trim", "tpad", "concat", "overlay",
      "lutrgb", "colorchannelmixer", "color"), True,
     "Scales, Frames, Joins, And Color Adjusts Shots In The Composition Graph."),
    ("ffmpeg-sound-filters", "filters",
     ("aresample", "aformat", "atempo", "volume", "apad", "atrim", "asetpts", "adelay", "amix", "anull",
      "anullsrc", "anullsink"), True,
     "Builds The Stereo Mix From Shot Audio And Added Cues."),
    ("ffmpeg-captions", "filters", ("subtitles",), True,
     "Burns Captions Into The Picture. The Filter Comes From A Build With libass."),
    ("ffmpeg-detection", "filters", ("silencedetect", "select", "metadata", "blackdetect", "volumedetect"), True,
     "Finds Silence, Scene Changes, Black Frames, And Peak Levels."),
    ("ffmpeg-loudness", "filters", ("ebur128",), True,
     "Measures Integrated Loudness, Loudness Range, And True Peak."),
    ("ffmpeg-hdr", "filters", ("zscale", "tonemap"), False,
     "Converts HDR Phone Footage (HLG, PQ, Dolby Vision 8.4) To Standard Dynamic Range. zscale Comes From A Build With libzimg."),
    ("ffmpeg-prores", "encoders", ("prores_ks",), False,
     "Encodes The ProRes MOV Option In Camera Transfer."),
]


def which(name):
    return shutil.which(name)


def python_version():
    return tuple(sys.version_info[:3])


def system_name():
    return platform.system()


def tool_output(args):
    try:
        done = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout + "\n" + done.stderr if done.returncode == 0 else None


def module_present(name):
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def zone_available():
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo("America/New_York")
        return True
    except Exception:
        return False


def find_browser():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from titles import browser_path
        return browser_path(None)
    except (ImportError, ValueError, OSError):
        return None


def find_resolve():
    system = system_name()
    if system == "Windows":
        root = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Blackmagic Design/DaVinci Resolve"
        data = Path(os.environ.get("ProgramData", "C:/ProgramData"))
        app, python = root / "Resolve.exe", root / "ResolvePython/ResolvePython.exe"
        sdk = data / "Blackmagic Design/DaVinci Resolve/Support/Developer/Scripting"
    elif system == "Darwin":
        app, python = Path("/Applications/DaVinci Resolve/DaVinci Resolve.app"), None
        sdk = Path("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting")
    else:
        app, python = Path("/opt/resolve/bin/resolve"), None
        sdk = Path("/opt/resolve/Developer/Scripting")
    if os.environ.get("RESOLVE_SCRIPT_API"):
        sdk = Path(os.environ["RESOLVE_SCRIPT_API"])

    def existing(path):
        return str(path) if path is not None and path.exists() else None

    return {"application": existing(app), "bundled_python": existing(python), "scripting_sdk": existing(sdk)}


def free_bytes(folder):
    return shutil.disk_usage(folder).free


def package_managers():
    return [name for name in MANAGERS.get(system_name(), ()) if which(name)]


def python_command():
    here = Path(sys.executable)
    for name in ("python", "python3"):
        found = which(name)
        try:
            if found and Path(found).resolve() == here.resolve():
                return name
        except OSError:
            continue
    text = str(here)
    return f'"{text}"' if " " in text else text


def pip_install(*packages):
    return f"{python_command()} -m pip install " + " ".join(packages)


def pip_note():
    notes = []
    if not module_present("pip"):
        notes.append("This Python Has No pip. Run The ensurepip Module First.")
    if python_command().startswith('"'):
        notes.append("In PowerShell, Put & Before The Quoted Program Path.")
    if system_name() != "Windows":
        notes.append("If pip Reports An Externally Managed Environment, Create A Virtual Environment And Use Its Python.")
    return " ".join(notes) or None


def recipe(key, managers):
    """The Install Command For The First Package Manager Present, Plus Any Alternatives."""
    table = RECIPES.get(key, {})
    if key == "browser" and system_name() != "Darwin":
        table = {name: command for name, command in table.items() if name != "brew"}
    commands = [table[name] for name in managers if name in table]
    if not commands:
        return {"install": None, "manual": MANUAL.get(key)}
    choice = {"install": commands[0]}
    if len(commands) > 1:
        choice["install_alternatives"] = commands[1:]
    return choice


def item(key, required, purpose, status, detail=None, **more):
    row = {"id": key, "required": required, "status": status, "purpose": purpose}
    if detail:
        row["detail"] = detail
    row.update({name: value for name, value in more.items() if value is not None})
    return row


def names_in(listing, kind):
    found = set()
    for line in (listing or "").splitlines():
        parts = line.split()
        if kind == "filters" and len(parts) > 2 and "->" in parts[2]:
            found.add(parts[1])
        elif kind == "encoders" and len(parts) > 1 and parts[1] != "=" and re.fullmatch(r"[VAS][A-Z.]{5}", parts[0]):
            found.add(parts[1])
    return found


def version_of(text):
    line = (text or "").strip().splitlines()[0] if (text or "").strip() else ""
    found = re.search(r"version\s+(\S+)", line)
    label = found[1] if found else None
    digits = re.match(r"n?(\d+)\.(\d+)(?:\.(\d+))?", label or "")
    return label, tuple(int(part) for part in digits.groups(0)) if digits else None


def media_items(managers):
    rows = []
    paths = {name: which(name) for name in ("ffmpeg", "ffprobe")}
    purposes = {"ffmpeg": "Decodes, Composes, Checks, And Encodes Every Edit.",
                "ffprobe": "Reads Source Streams, Durations, Rotation, And Color Signalling."}
    listings = {}
    for name in ("ffmpeg", "ffprobe"):
        if not paths[name]:
            note = "FFprobe Ships In The Same Package As FFmpeg." if name == "ffprobe" else None
            rows.append(item(name, True, purposes[name], "missing", install_note=note, **recipe("ffmpeg", managers)))
            continue
        label, numbers = version_of(tool_output([paths[name], "-version"]))
        note = None
        if numbers and numbers[:2] < OLDEST_FFMPEG:
            note = (f"This Kit Was Checked With FFmpeg {CHECKED_FFMPEG}. Versions Before "
                    f"{OLDEST_FFMPEG[0]}.{OLDEST_FFMPEG[1]} Lack Options It Uses.")
        rows.append(item(name, True, purposes[name], "present", f"{label or 'Unknown Version'} At {paths[name]}",
                         version=label, path=paths[name], note=note))
    if paths["ffmpeg"]:
        for kind in ("encoders", "filters"):
            listings[kind] = names_in(tool_output([paths["ffmpeg"], "-hide_banner", "-" + kind]), kind)
    for key, kind, names, required, purpose in FEATURES:
        if not paths["ffmpeg"]:
            rows.append(item(key, required, purpose, "unknown", "Unknown Until FFmpeg Is Installed.", names=list(names)))
            continue
        absent = [name for name in names if name not in listings[kind]]
        if not absent:
            rows.append(item(key, required, purpose, "present", names=list(names)))
            continue
        rows.append(item(key, required, purpose, "missing",
                         f"The Installed FFmpeg Build Lacks {', '.join(absent)}.", names=list(names),
                         missing_names=absent,
                         install_note="A Full Build Adds The Missing Pieces. Make Sure It Comes First On PATH.",
                         **recipe("ffmpeg", managers)))
    return rows


def optional_items(managers):
    rows = []
    purpose = "Transcribes Speech To Word Timings For Captions And Take Selection."
    engines = [name for name, found in (("whisper Command", which("whisper")),
                                        ("faster-whisper Package", module_present("faster_whisper"))) if found]
    if engines:
        rows.append(item("speech-recognizer", False, purpose, "present", " And ".join(engines) + " Found."))
    else:
        rows.append(item("speech-recognizer", False, purpose, "missing",
                         "Neither A whisper Command Nor The faster-whisper Package Was Found.",
                         install=pip_install("faster-whisper"),
                         install_alternatives=[pip_install("openai-whisper")],
                         install_note=" ".join(filter(None, ["Speech Models Download Separately On First Use Unless A Local Model Folder Is Supplied.", pip_note()]))))
    purpose = "Tracks Reference Camera Motion For Camera Transfer."
    absent = [name for name, module in (("numpy", "numpy"), ("opencv", "cv2")) if not module_present(module)]
    if absent:
        packages = [{"numpy": "numpy", "opencv": "opencv-python-headless"}[name] for name in absent]
        rows.append(item("camera-vision", False, purpose, "missing", f"Missing {' And '.join(absent)}.",
                         missing_names=absent, install=pip_install(*packages), install_note=pip_note()))
    else:
        rows.append(item("camera-vision", False, purpose, "present", "numpy And opencv Found."))
    purpose = "Resolves Named Time Zones When A Post Is Scheduled."
    if zone_available():
        rows.append(item("time-zones", False, purpose, "present"))
    else:
        rows.append(item("time-zones", False, purpose, "missing", "This Python Cannot Load The IANA Time Zone Database.",
                         install=pip_install("tzdata"), install_note=pip_note()))
    purpose = "Renders Transparent Title Overlays With A Chromium-Family Browser."
    browser = find_browser()
    if browser:
        rows.append(item("browser", False, purpose, "present", path=browser))
    else:
        rows.append(item("browser", False, purpose, "missing", "No Chrome, Chromium, Edge, Or Brave Was Found.",
                         **recipe("browser", managers)))
    purpose = "Builds Native Editable Timelines In DaVinci Resolve Studio."
    resolve = find_resolve()
    if resolve["application"]:
        note = None if resolve["bundled_python"] else (
            "No Bundled ResolvePython Was Found. Use A Python Connected To The Scripting SDK As RESOLVE.md Describes.")
        rows.append(item("resolve", False, purpose, "present", note=note, **resolve))
    else:
        rows.append(item("resolve", False, purpose, "missing", "DaVinci Resolve Was Not Found In Its Usual Location.",
                         install=None, manual=MANUAL["resolve"]))
    purpose = "Runs The Review Player Identity Tests And The Animated Video Tools."
    node = which("node")
    if node:
        label = (tool_output([node, "--version"]) or "").strip() or None
        rows.append(item("node", False, purpose, "present", version=label, path=node))
    else:
        rows.append(item("node", False, purpose, "missing", **recipe("node", managers)))
    return rows


def disk_report(folder, minimum_gb):
    target = Path(folder).expanduser().resolve()
    probe = target
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    try:
        free = free_bytes(probe)
    except OSError as exc:
        return {"folder": str(target), "free_bytes": None, "enough": None, "note": f"Could Not Read Free Space. {exc}"}
    report = {"folder": str(target), "measured_at": str(probe), "free_bytes": free,
              "free_gb": round(free / 1e9, 2), "minimum_gb": minimum_gb, "enough": free >= minimum_gb * 1e9}
    if not report["enough"]:
        report["note"] = "Free Space Is Below The Minimum. Sources, Caches, And An Approved Export Need Room."
    return report


def check(folder=".", minimum_gb=2.0):
    """Inspect The Machine And Return The Report With Its Exit Code."""
    managers = package_managers()
    current = python_version()
    version = ".".join(str(part) for part in current)
    purpose = "Runs Every Script In This Folder."
    if current >= MINIMUM_PYTHON:
        rows = [item("python", True, purpose, "present", f"{version} At {sys.executable}",
                     version=version, path=sys.executable)]
    else:
        rows = [item("python", True, purpose, "missing",
                     f"Python {version} Is Older Than {MINIMUM_PYTHON[0]}.{MINIMUM_PYTHON[1]}.",
                     version=version, path=sys.executable, **recipe("python", managers))]
    rows += media_items(managers) + optional_items(managers)
    required = [row["id"] for row in rows if row["required"] and row["status"] == "missing"]
    optional = [row["id"] for row in rows if not row["required"] and row["status"] == "missing"]
    disk = disk_report(folder, minimum_gb)
    if required:
        summary = f"{len(required)} Required Item{'s Are' if len(required) > 1 else ' Is'} Missing."
    else:
        summary = "Every Required Item Is Present."
    if optional:
        summary += f" {len(optional)} Optional Item{'s Are' if len(optional) > 1 else ' Is'} Missing."
    if disk.get("enough") is False:
        summary += " Free Disk Space Is Low."
    report = {"check": "social-cut-kit video-edit setup", "ready": not required, "summary": summary,
              "system": {"os": system_name(), "release": platform.release(), "machine": platform.machine(),
                         "package_managers": managers},
              "missing_required": required, "missing_optional": optional, "items": rows, "disk": disk,
              "install_policy": POLICY}
    return report, 1 if required else 0


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--project-folder", type=Path, default=Path("."),
                     help="Folder Whose Drive Is Checked For Free Space. The Default Is The Current Folder.")
    cli.add_argument("--min-free-gb", type=float, default=2.0,
                     help="Free Space Below This Many Gigabytes Is Reported As Low. The Default Is 2.")
    return cli


def main(argv=None):
    cli = parser()
    args = cli.parse_args(argv)
    if not 0 <= args.min_free_gb <= 100000:
        cli.error("Choose A Minimum Between 0 And 100000 Gigabytes.")
    report, code = check(args.project_folder, args.min_free_gb)
    print(json.dumps(report, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
