"""Shared Helpers For The Script Desk Tools."""

import argparse
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile


HOME_VARIABLE = "SOCIAL_CUT_KIT_HOME"
DEFAULTS_NAME = "video-script.md"
STANDARD_PACE = 3.0
FIELD_LINE = re.compile(r"^\s*[-*]\s*([A-Za-z][A-Za-z ]*?)\s*:\s*(.*?)\s*$")


class DeskFormatter(argparse.HelpFormatter):
    def add_usage(self, usage, actions, groups, prefix=None):
        return super().add_usage(
            usage, actions, groups, "Usage: " if prefix is None else prefix
        )


class DeskParser(argparse.ArgumentParser):
    """An Argument Parser Whose Own Headings Follow The House Style."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("formatter_class", DeskFormatter)
        kwargs["add_help"] = False
        super().__init__(*args, **kwargs)
        self._positionals.title = "Arguments"
        self._optionals.title = "Options"
        self.add_argument(
            "-h",
            "--help",
            action="help",
            default=argparse.SUPPRESS,
            help="Show This Help And Exit",
        )

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: Error: {message}\n")


def guard_streams(utf8=False):
    """Keep Printing From Failing On A Console That Cannot Encode A Character.

    With utf8, Output Sent To A Pipe Or A File Is Written As UTF-8 Unless The User Set
    PYTHONIOENCODING, So A Reader Of The Pipe Receives The Text Intact.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            if utf8 and not stream.isatty() and not os.environ.get("PYTHONIOENCODING"):
                stream.reconfigure(encoding="utf-8", errors="backslashreplace")
            else:
                stream.reconfigure(errors="backslashreplace")
        except (AttributeError, ValueError):
            pass


def read_text(path):
    """Read UTF-8 Text, Accepting A Byte Order Mark Or A UTF-16 Redirect."""
    data = Path(path).read_bytes()
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16")
    return data.decode("utf-8-sig")


def read_json(path):
    """Load JSON And Report A Missing Or Malformed File In The House Style."""
    try:
        return json.loads(read_text(path))
    except FileNotFoundError as exc:
        raise ValueError(f"No File At {path}.") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path} Is Not Valid JSON Near Line {exc.lineno}, Column {exc.colno}."
        ) from exc
    except UnicodeError as exc:
        raise ValueError(f"{path} Is Not UTF-8 Text.") from exc


def read_object(path, what="A JSON Object"):
    value = read_json(path)
    if not isinstance(value, dict):
        raise ValueError(f"Expected {what} In {path}.")
    return value


def write_text(path, text):
    """Replace A File In One Step So A Stopped Run Never Leaves Half A Record."""
    path = Path(path)
    handle, temp = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as out:
            out.write(text)
        os.replace(temp, path)
    except BaseException:
        try:
            os.unlink(temp)
        except OSError:
            pass
        raise


def write_new(path, text):
    """Create A File And Refuse To Replace An Existing One."""
    path = Path(path)
    try:
        with path.open("x", encoding="utf-8", newline="\n") as out:
            out.write(text)
    except FileExistsError as exc:
        raise ValueError(f"{path} Already Exists. Choose A New Name.") from exc
    except FileNotFoundError as exc:
        raise ValueError(f"The Folder For {path} Does Not Exist.") from exc


def _scalar(value):
    return not isinstance(value, (dict, list))


def tidy_json(value, ascii_only=False, depth=0):
    """Indent Objects And Keep Rows Of Numbers Or Flat Records On One Line."""
    pad = "  " * depth
    if isinstance(value, dict):
        if not value:
            return "{}"
        rows = [
            f"{pad}  {json.dumps(str(key), ensure_ascii=ascii_only)}: "
            + tidy_json(item, ascii_only, depth + 1)
            for key, item in value.items()
        ]
        return "{\n" + ",\n".join(rows) + "\n" + pad + "}"
    if isinstance(value, list):
        if not value:
            return "[]"
        if all(_scalar(item) for item in value) or all(
            isinstance(item, list) and all(_scalar(part) for part in item)
            for item in value
        ):
            return json.dumps(value, ensure_ascii=ascii_only)
        rows = []
        for item in value:
            if isinstance(item, dict) and all(_scalar(part) for part in item.values()):
                rows.append(pad + "  " + json.dumps(item, ensure_ascii=ascii_only))
            else:
                rows.append(pad + "  " + tidy_json(item, ascii_only, depth + 1))
        return "[\n" + ",\n".join(rows) + "\n" + pad + "]"
    return json.dumps(value, ensure_ascii=ascii_only)


def clock(text):
    """Read Seconds Written As 28, 28.5, 28s, 0:28, Or 1:02.5."""
    cleaned = str(text).strip().lower()
    if cleaned.endswith("s") and ":" not in cleaned:
        cleaned = cleaned[:-1].strip()
    try:
        if ":" in cleaned:
            parts = cleaned.split(":")
            if len(parts) not in (2, 3):
                raise ValueError(cleaned)
            value = 0.0
            for part in parts:
                value = value * 60 + float(part)
        else:
            value = float(cleaned)
    except ValueError:
        value = math.nan
    if not math.isfinite(value) or value < 0:
        raise argparse.ArgumentTypeError(
            "Enter Seconds Such As 28, 28.5, Or 0:28."
        )
    return value


def number_text(value, places=1):
    """Print A Number Without A Trailing Zero Fraction."""
    rounded = round(float(value), places)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.{places}f}".rstrip("0").rstrip(".")


def kit_home():
    override = os.environ.get(HOME_VARIABLE)
    if override:
        return Path(override).expanduser()
    return Path.home() / ".social-cut-kit"


def defaults_file():
    return kit_home() / DEFAULTS_NAME


def read_defaults(path=None):
    """Return The `- Key: Value` Lines Of The Creator Defaults File, Keys In Lower Case."""
    path = Path(path) if path else defaults_file()
    try:
        text = read_text(path)
    except (OSError, UnicodeError):
        return {}
    found = {}
    for line in text.splitlines():
        match = FIELD_LINE.match(line)
        if not match:
            continue
        key = " ".join(match.group(1).lower().split())
        value = match.group(2).strip().strip("`").strip()
        if value and key not in found:
            found[key] = value
    return found


def pace_from(defaults):
    """Return Spoken Words Per Second From A Defaults Mapping, Or None."""
    match = re.search(r"\d+(?:\.\d+)?", defaults.get("pace", ""))
    if match:
        pace = float(match.group())
        if 0.5 <= pace <= 8:
            return pace
    return None
