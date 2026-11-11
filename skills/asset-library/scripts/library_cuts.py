"""Cut Declarations: Record A Delivered Cut, Check It Against The Library, And Store Deliveries."""

import datetime
import hashlib
import json
import os
from pathlib import Path

from library_store import LibraryError, capture, encode, transaction, verify_stored
from library_records import delivered


DEPENDENCY_FOLDERS = {"node_modules", "__pycache__", "site-packages", "venv", "env", "vendor",
                      "bower_components", "pods", "target"}
TEXT_SUFFIXES = {".json", ".md", ".txt", ".js", ".cjs", ".mjs", ".ts", ".tsx", ".jsx", ".py", ".html",
                 ".css", ".csv", ".srt", ".vtt", ".otio", ".xml", ".edl", ".yaml", ".yml", ".toml"}
SCAN_MAX_FILES = 5000
SCAN_MAX_HASH_BYTES = 2 * 1024 ** 3
SCAN_MAX_TEXT_BYTES = 1024 * 1024
SHORTEST_NAME = 3
DECLARATION_HINT = "See The Cut Declaration Section Of RECORDS.md For The Expected Fields."


def load(path):
    """Read And Validate A Cut Declaration. Return It With Normalised Entries."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise LibraryError(f"The Cut Declaration Was Not Found: {path}", "Check The Path To The JSON File.")
    except ValueError as problem:
        raise LibraryError(f"The Cut Declaration Is Not Valid JSON: {problem}", DECLARATION_HINT)
    if not isinstance(raw, dict):
        raise LibraryError("The Cut Declaration Must Be A JSON Object.", DECLARATION_HINT)
    result = {}
    for field in ("project", "cut"):
        value = raw.get(field)
        if not isinstance(value, str) or not value.strip():
            raise LibraryError(f"The Cut Declaration Needs A Nonempty {field} String.", DECLARATION_HINT)
        result[field] = value.strip()
    entries = raw.get("entries")
    if not isinstance(entries, list) or not entries:
        raise LibraryError("The Cut Declaration Needs A Nonempty entries List.", DECLARATION_HINT)
    result["entries"] = []
    seen = set()
    for index, item in enumerate(entries, 1):
        where = f"Entry {index}"
        if not isinstance(item, dict):
            raise LibraryError(f"{where} Must Be A JSON Object.", DECLARATION_HINT)
        entry = {}
        for field in ("asset", "use"):
            value = item.get(field)
            if not isinstance(value, str) or not value.strip():
                raise LibraryError(f"{where} Needs A Nonempty {field} String.", DECLARATION_HINT)
            entry[field] = value.strip()
        if entry["use"] in seen:
            raise LibraryError(f"{where} Repeats The Use {entry['use']}.",
                               "Give Each Entry Of One Cut A Different Use Name.")
        seen.add(entry["use"])
        version, relative = item.get("version"), item.get("path")
        if (version is None) == (relative is None):
            raise LibraryError(f"{where} Needs Either version Or path, Not Both.", DECLARATION_HINT)
        if version is not None:
            version = version.lower() if isinstance(version, str) else ""
            if len(version) != 64 or any(c not in "0123456789abcdef" for c in version):
                raise LibraryError(f"{where} Needs A Full SHA-256 Digest In version.", DECLARATION_HINT)
        elif not isinstance(relative, str) or not relative.strip():
            raise LibraryError(f"{where} Needs A Nonempty path String.", DECLARATION_HINT)
        entry["version"], entry["path"] = version, relative
        modified = item.get("modified", False)
        if not isinstance(modified, bool):
            raise LibraryError(f"{where} Needs true Or false In modified.", DECLARATION_HINT)
        entry["modified"] = modified
        cue = item.get("cue")
        if cue is not None and not isinstance(cue, str):
            raise LibraryError(f"{where} Needs Text In cue.", DECLARATION_HINT)
        entry["cue"] = cue
        moment = item.get("time")
        if moment is not None and (isinstance(moment, bool) or not isinstance(moment, (int, float)) or moment < 0):
            raise LibraryError(f"{where} Needs A Number Of Seconds, Zero Or More, In time.", DECLARATION_HINT)
        entry["time"] = float(moment) if moment is not None else None
        result["entries"].append(entry)
    return result


def resolve(db, declaration, base):
    """Pair Each Entry With Its Stored Revision Row, Or With A Problem Sentence."""
    resolved = []
    for entry in declaration["entries"]:
        version, problem = entry["version"], None
        if version is None:
            target = base / entry["path"]
            if not target.exists():
                problem = f"The Declared File Was Not Found: {entry['path']}"
            else:
                version = capture(target)[1]
        row = None
        if problem is None:
            row = db.execute("SELECT * FROM revisions WHERE asset=? AND version=?",
                             (entry["asset"], version)).fetchone()
            if row is None:
                known = db.execute("SELECT 1 FROM assets WHERE name=?", (entry["asset"],)).fetchone()
                what = "This Version Is Not A Stored Revision Of" if known else "The Library Has No Asset Named"
                problem = (f"{what} {entry['asset']}. Add It With The add Command, Then Run This Again.")
        resolved.append((entry, version, row, problem))
    return resolved


def snapshot(declaration, resolved):
    return {"project": declaration["project"], "cut": declaration["cut"],
            "entries": [{"asset": e["asset"], "use": e["use"], "version": version, "path": e["path"],
                         "modified": e["modified"], "cue": e["cue"], "time": e["time"]}
                        for e, version, _, _ in resolved]}


def refuse(message, hint, report):
    problem = LibraryError(message, hint)
    problem.report = report
    return problem


def declare(db, path):
    declaration = load(path)
    project, cut = declaration["project"], declaration["cut"]
    with transaction(db, write=True):
        resolved = resolve(db, declaration, Path(path).absolute().parent)
        problems = [{"use": e["use"], "asset": e["asset"], "problem": problem}
                    for e, _, _, problem in resolved if problem]
        report = {"project": project, "cut": cut, "recorded": 0, "problems": problems}
        if problems:
            raise refuse(f"The Cut Declaration Has {len(problems)} Unresolved Entries. Nothing Was Recorded.",
                         "Add Each Missing File With The add Command, Or Correct The Entry, Then Declare Again.",
                         report)
        current = snapshot(declaration, resolved)
        shipped = delivered(db, project, cut)
        if shipped is not None:
            if json.loads(shipped["declaration"]) == current:
                return {**current, "recorded": len(resolved), "retired": [], "status": "Already Delivered"}
            raise refuse(f"Cut {cut} Of {project} Is Already Delivered With A Different Declaration.",
                         "Record The Change Under A New Cut Label. A Delivery Record Is Kept As It Was.", report)
        for entry, _, row, _ in resolved:
            db.execute(
                """INSERT INTO cut_uses(project,cut,slot,revision,modified,cue,time) VALUES(?,?,?,?,?,?,?)
                   ON CONFLICT(project,cut,slot) DO UPDATE SET revision=excluded.revision,
                   modified=excluded.modified, cue=excluded.cue, time=excluded.time, retired=NULL""",
                (project, cut, entry["use"], row["id"], int(entry["modified"]), entry["cue"], entry["time"]))
        declared = {e["use"] for e in declaration["entries"]}
        retired = [r[0] for r in db.execute(
            "SELECT slot FROM cut_uses WHERE project=? AND cut=? AND retired IS NULL ORDER BY slot",
            (project, cut)) if r[0] not in declared]
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        for slot in retired:
            db.execute("UPDATE cut_uses SET retired=? WHERE project=? AND cut=? AND slot=?",
                       (stamp, project, cut, slot))
        return {**current, "recorded": len(resolved), "retired": retired, "status": "Recorded"}


def scan(db, folder, declared):
    """List Library Assets Found In A Project Folder By Identical Bytes Or By Name In Text Files."""
    folder = Path(folder)
    if not folder.is_dir():
        raise LibraryError(f"The Scan Folder Was Not Found: {folder}", "Name The Project Folder To Scan.")
    by_size, names = {}, []
    with transaction(db):
        for asset, version, size in db.execute(
                """SELECT r.asset, r.version, b.size FROM revisions r JOIN blobs b ON b.digest=r.version
                   WHERE r.kind='file'"""):
            by_size.setdefault(size, {}).setdefault(version, set()).add(asset)
        names = [r[0] for r in db.execute("SELECT name FROM assets") if len(r[0]) >= SHORTEST_NAME]
    found, files, hashed, texts, hashed_bytes, capped = {}, 0, 0, 0, 0, False

    def record(asset, match, path):
        if asset not in declared:
            entry = found.setdefault((asset, match), {"asset": asset, "match": match, "path": path, "places": 0})
            entry["places"] += 1

    for top, folders, members in os.walk(str(folder)):
        folders[:] = sorted(d for d in folders if not d.startswith(".") and d.lower() not in DEPENDENCY_FOLDERS)
        for name in sorted(members):
            if name.startswith("."):
                continue
            if files >= SCAN_MAX_FILES:
                capped = True
                break
            files += 1
            path = Path(top) / name
            relative = path.relative_to(folder).as_posix()
            try:
                size = path.stat().st_size
                if size in by_size and hashed_bytes + size <= SCAN_MAX_HASH_BYTES:
                    digest = hashlib.sha256()
                    with path.open("rb") as stream:
                        for data in iter(lambda: stream.read(1024 * 1024), b""):
                            digest.update(data)
                    hashed += 1
                    hashed_bytes += size
                    for asset in sorted(by_size[size].get(digest.hexdigest(), ())):
                        record(asset, "bytes", relative)
                elif size in by_size:
                    capped = True
                if path.suffix.lower() in TEXT_SUFFIXES and size <= SCAN_MAX_TEXT_BYTES:
                    text = path.read_text(encoding="utf-8", errors="replace")
                    texts += 1
                    for asset in names:
                        if asset in text:
                            record(asset, "name", relative)
            except OSError:
                continue
        if capped and files >= SCAN_MAX_FILES:
            break
    return {"folder": str(folder), "files_seen": files, "files_hashed": hashed, "text_files_read": texts,
            "capped": capped, "limits": {"files": SCAN_MAX_FILES, "hashed_bytes": SCAN_MAX_HASH_BYTES,
                                         "text_file_bytes": SCAN_MAX_TEXT_BYTES},
            "undeclared": sorted(found.values(), key=lambda e: (e["asset"], e["match"]))}


def examine(db, declaration, base):
    """Compare A Declaration With The Recorded Cut. Read Only. Return The Report And The Snapshot."""
    project, cut = declaration["project"], declaration["cut"]
    resolved = resolve(db, declaration, base)
    entries, problems, checked = [], [], set()
    for entry, version, row, problem in resolved:
        recorded = db.execute(
            """SELECT r.asset, r.version FROM cut_uses c JOIN revisions r ON r.id=c.revision
               WHERE c.project=? AND c.cut=? AND c.slot=? AND c.retired IS NULL""",
            (project, cut, entry["use"])).fetchone()
        if problem is None and recorded is None:
            problem = "No Use Is Recorded For This Entry. Run The declare Command First."
        elif problem is None and (recorded["asset"], recorded["version"]) != (entry["asset"], version):
            problem = (f"The Recorded Use Holds {recorded['asset']} At {recorded['version']}, "
                       "Which Differs From The Declaration. Declare The Final Cue Sheet Again.")
        if problem is None:
            try:
                verify_stored(db, row, checked)
            except LibraryError as missing:
                problem = f"{missing} {missing.hint}"
        entries.append({"use": entry["use"], "asset": entry["asset"], "version": version,
                        "verified": problem is None})
        if problem:
            problems.append({"use": entry["use"], "asset": entry["asset"], "problem": problem})
    declared = {e["use"] for e in declaration["entries"]}
    extra = [{"use": r["slot"], "asset": r["asset"], "version": r["version"]} for r in db.execute(
        """SELECT c.slot, r.asset, r.version FROM cut_uses c JOIN revisions r ON r.id=c.revision
           WHERE c.project=? AND c.cut=? AND c.retired IS NULL ORDER BY c.slot""", (project, cut))
        if r["slot"] not in declared]
    report = {"project": project, "cut": cut, "passed": not problems, "entries": entries,
              "problems": problems, "recorded_but_undeclared": extra}
    return report, snapshot(declaration, resolved)


def check(db, project, path, folder):
    declaration = load(path)
    if project != declaration["project"]:
        raise LibraryError(
            f"The Declaration Is For Project {declaration['project']}, Not {project}.",
            "Pass The Project Named In The Declaration. Names Match Case Exactly.")
    with transaction(db):
        report, _ = examine(db, declaration, Path(path).absolute().parent)
    if folder is not None:
        report["scan"] = scan(db, folder, {e["asset"] for e in declaration["entries"]})
    if not report["passed"]:
        raise refuse(f"Cut {report['cut']} Of {project} Does Not Match Its Declaration: "
                     f"{len(report['problems'])} Problems.",
                     "Read problems In The Report. Nothing Was Written.", report)
    return report


def deliver(db, path, folder, date):
    declaration = load(path)
    day = date or datetime.date.today().isoformat()
    try:
        datetime.date.fromisoformat(day)
    except ValueError:
        raise LibraryError(f"The Delivery Date Is Not A Calendar Date: {day}", "Use The Form YYYY-MM-DD.")
    found = scan(db, folder, {e["asset"] for e in declaration["entries"]}) if folder is not None else None
    with transaction(db, write=True):
        report, current = examine(db, declaration, Path(path).absolute().parent)
        if found is not None:
            report["scan"] = found
        if not report["passed"]:
            raise refuse(f"Cut {report['cut']} Of {report['project']} Was Not Delivered: "
                         f"{len(report['problems'])} Problems.",
                         "Read problems In The Report. No Delivery Record Was Stored. The Video Itself Can Still Ship.",
                         report)
        shipped = delivered(db, report["project"], report["cut"])
        if shipped is not None:
            if json.loads(shipped["declaration"]) != current:
                raise refuse(f"Cut {report['cut']} Of {report['project']} Is Already Delivered With A Different Declaration.",
                             "Record The Change Under A New Cut Label.", report)
            report.update(delivered=shipped["delivered"], status="Already Recorded")
        else:
            db.execute("INSERT INTO deliveries(project,cut,delivered,declaration) VALUES(?,?,?,?)",
                       (report["project"], report["cut"], day, encode(current)))
            report.update(delivered=day, status="Delivery Recorded")
        return report


def deliveries(db, project=None):
    with transaction(db):
        sql, params = "SELECT * FROM deliveries", []
        if project is not None:
            sql, params = sql + " WHERE project=?", [project]
        return [{"project": r["project"], "cut": r["cut"], "delivered": r["delivered"],
                 "recorded": r["created"], "declaration": json.loads(r["declaration"])}
                for r in db.execute(sql + " ORDER BY delivered, id", params)]
