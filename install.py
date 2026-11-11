"""Install TENG AI SCHOOL Social Cut Kit Into A Local Agent."""

import argparse
import os
from pathlib import Path
import shutil
import sys
import tempfile


PRODUCT = Path(__file__).resolve().parent
AVAILABLE = tuple(
    sorted(item.parent.name for item in (PRODUCT / "skills").glob("*/SKILL.md"))
)


def publish(folder, names, upgrade):
    folder = folder.expanduser().resolve()
    if folder == PRODUCT or PRODUCT in folder.parents:
        raise ValueError("Choose An Installation Location Outside The Product Folder.")
    folder.mkdir(parents=True, exist_ok=True)
    lock_path = folder / ".social-cut-kit-install.lock"
    try:
        lock = lock_path.open("x", encoding="utf-8")
    except FileExistsError as exc:
        raise ValueError(
            f"Install Lock Already Exists. Check For An Active Installer Before Removing {lock_path}"
        ) from exc
    try:
        with lock:
            lock.write(str(os.getpid()))
        ready = []
        for name in names:
            dest = folder / name
            if os.path.lexists(dest):
                if not upgrade:
                    print(f"Existing Skill Skipped: {name}")
                    continue
                if dest.is_symlink() or dest.resolve() != dest or not dest.is_dir():
                    raise ValueError(f"Unsafe Replacement Target: {dest}")
            ready.append(name)
        if not ready:
            return
        with tempfile.TemporaryDirectory(prefix=".school-stage-", dir=folder) as stage:
            stage = Path(stage)
            for name in ready:
                target = stage / name
                shutil.copytree(
                    PRODUCT / "skills" / name,
                    target,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
                )
                shutil.copyfile(
                    PRODUCT / "USAGE.md", target / "Social-Cut-Kit-Usage.md"
                )
            backup = None
            if any((folder / n).exists() for n in ready):
                parent = folder.parent / (folder.name + "-social-cut-kit-backups")
                parent.mkdir(exist_ok=True)
                backup = Path(tempfile.mkdtemp(prefix="previous-", dir=parent))
                print(f"Previous Versions Saved In {backup}")
            saved, installed = [], []
            try:
                for name in ready:
                    if os.path.lexists(folder / name):
                        if backup is None or not upgrade:
                            raise FileExistsError(folder / name)
                        (folder / name).rename(backup / name)
                        saved.append(name)
                    (stage / name).rename(folder / name)
                    installed.append(name)
            except OSError:
                for name in reversed(installed):
                    (folder / name).rename(stage / name)
                for name in reversed(saved):
                    (backup / name).rename(folder / name)
                raise
            for name in installed:
                print(f"Installed {name}")
    finally:
        lock_path.unlink(missing_ok=True)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    location = cli.add_mutually_exclusive_group(required=True)
    location.add_argument("--agent", choices=("codex", "claude"))
    location.add_argument("--into", type=Path, help="Custom Skills Directory")
    location.add_argument("--list", action="store_true", help="Display Included Skills")
    cli.add_argument(
        "--upgrade",
        action="store_true",
        help="Back Up And Replace Existing Selected Folders",
    )
    cli.add_argument("names", nargs="*")
    a = cli.parse_args()
    if a.list:
        print("\n".join(AVAILABLE))
        return
    chosen = list(dict.fromkeys(a.names or AVAILABLE))
    for name in chosen:
        if name not in AVAILABLE:
            cli.error(f"Unknown Skill: {name}")
    path = a.into
    if a.agent:
        key, default = (
            ("CODEX_HOME", ".codex")
            if a.agent == "codex"
            else ("CLAUDE_CONFIG_DIR", ".claude")
        )
        path = Path(os.getenv(key) or Path.home() / default) / "skills"
    try:
        publish(path, chosen, a.upgrade)
    except (OSError, ValueError) as exc:
        cli.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
