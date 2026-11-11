"""Import An Editable OTIO Timeline Into The Named Open Resolve Project."""

import argparse
import importlib
import json
import os
from pathlib import Path
import sys


def resolve_app():
    try:
        module = importlib.import_module("DaVinciResolveScript")
    except ImportError:
        api = os.getenv("RESOLVE_SCRIPT_API")
        if not api:
            raise ValueError(
                "Enable Local Resolve Scripting And Set RESOLVE_SCRIPT_API To The SDK Folder."
            )
        sys.path.insert(0, str(Path(api) / "Modules"))
        module = importlib.import_module("DaVinciResolveScript")
    app = module.scriptapp("Resolve")
    if not app:
        raise ValueError("Open Resolve With Local Scripting Available.")
    return app


def import_cut(app, path, project_name, timeline_name):
    project = app.GetProjectManager().GetCurrentProject()
    if not project or project.GetName() != project_name:
        raise ValueError("Open The Named Destination Project Before Import.")
    for idx in range(1, project.GetTimelineCount() + 1):
        existing = project.GetTimelineByIndex(idx)
        if existing and existing.GetName().casefold() == timeline_name.casefold():
            raise ValueError(
                "That Timeline Name Already Exists. Choose A New Revision Name."
            )
    timeline = project.GetMediaPool().ImportTimelineFromFile(
        str(path), {"timelineName": timeline_name, "importSourceClips": True}
    )
    if not timeline:
        raise ValueError(
            "Resolve Could Not Import The OTIO. Check Its Media Paths And Installed Resolve Version."
        )
    return {"project": project.GetName(), "imported_timeline": timeline.GetName()}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("otio", type=Path)
    cli.add_argument("--project", required=True, help="Exact Name Of The Open Project")
    cli.add_argument("--name", required=True, help="New Timeline Name")
    cli.add_argument(
        "--inspect",
        action="store_true",
        help="Show Intended Import Without Connecting To Resolve",
    )
    a = cli.parse_args()
    try:
        src = a.otio.resolve(strict=True)
        obj = json.loads(src.read_text(encoding="utf-8"))
        if (
            src.suffix.lower() != ".otio"
            or obj.get("OTIO_SCHEMA", "").split(".")[0] != "Timeline"
        ):
            raise ValueError("Expected An OpenTimelineIO Timeline.")
        if not a.name.strip() or not a.project.strip():
            raise ValueError("Supply A Project Name And A New Timeline Name.")
        result = (
            {"source": str(src), "project": a.project, "new_timeline": a.name}
            if a.inspect
            else import_cut(resolve_app(), src, a.project, a.name)
        )
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, ImportError, KeyError) as exc:
        cli.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
