"""Asset Records: Add, Search, Notes, Show, Archive, Pins, Previews, Validation, And Stats."""

import datetime
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

import library_media as media
from library_store import (LibraryError, capture, encode, materialize, revision, transaction,
                           verify_stored)


NOTE_KINDS = ("opinion", "test", "rights", "caveat")
START_VARIABLES = ("PATH", "HOME", "USERPROFILE", "HOMEDRIVE", "HOMEPATH", "APPDATA", "LOCALAPPDATA",
                   "TEMP", "TMP", "TMPDIR", "SYSTEMROOT", "LANG", "LC_ALL", "LC_CTYPE")
INTERPRETER_NAMES = ("python", "python3")
DEFAULT_TIMEOUT = 120.0
OUTPUT_TAIL = 2000
REVISIONS = """SELECT r.*, a.asset_kind, a.archived, m.facts, m.status AS media_status,
               m.preview IS NOT NULL AS has_preview, m.preview_status
               FROM revisions r JOIN assets a ON a.name=r.asset LEFT JOIN media m ON m.revision=r.id"""


def describe(row):
    record = dict(row)
    for field in ("id", "manifest", "revision", "slot"):
        record.pop(field, None)
    record["tags"] = json.loads(record["tags"])
    facts = record.pop("facts", None)
    record["media"] = json.loads(facts) if facts else None
    record["media_status"] = record.get("media_status") or "No Media Facts Were Recorded For This Revision."
    record["has_preview"] = bool(record.get("has_preview"))
    record["preview_status"] = record.get("preview_status") or "No Preview Still Was Kept For This Revision."
    command = record.pop("validation_command", None)
    timeout = record.pop("validation_timeout", None)
    names = record.pop("validation_env", None)
    if command:
        record["validation"] = {"command": command, "timeout": timeout, "env": json.loads(names or "[]")}
    return record


def full(db, asset, version=None):
    row = revision(db, asset, version)
    return db.execute(REVISIONS + " WHERE r.id=?", (row["id"],)).fetchone()


def asset_row(db, name):
    row = db.execute("SELECT * FROM assets WHERE name=?", (name,)).fetchone()
    if row is None:
        raise LibraryError(f"Asset Was Not Found: {name}",
                           "Run search --archived To List Every Asset Name. Names Match Case Exactly.")
    return row


def holders(db, version, besides):
    return [r[0] for r in db.execute(
        "SELECT DISTINCT asset FROM revisions WHERE version=? AND asset<>? ORDER BY asset",
        (version, besides))]


def delivered(db, project, cut):
    return db.execute("SELECT * FROM deliveries WHERE project=? AND cut=?", (project, cut)).fetchone()


def add(db, args, db_path):
    path = args.source.absolute()
    resolved = path.resolve()
    if resolved in (db_path, *db_path.parents) or (path.is_file() and path.samefile(db_path)):
        raise LibraryError("Keep The Library Database Outside The Source Asset.",
                           "Move The Database, Or Name A Source That Does Not Contain It.")
    storage = "bundle" if path.is_dir() else "file"
    if args.validate and storage != "bundle":
        raise LibraryError("A Validation Command Applies To A Folder Revision Only.",
                           "Remove --validate, Or Register The Folder That Holds The File.")
    facts, status = media.probe(path, storage)
    still, still_status = media.preview(path, storage, facts)
    names = encode(sorted(set(args.validate_env)))
    with transaction(db, write=True):
        kind, version, manifest = capture(path, db, db_path.stat())
        tags = encode(sorted({tag.casefold() for tag in args.tag}))
        meta = (args.origin, args.rights, args.context, tags)
        previous = db.execute("SELECT kind FROM revisions WHERE asset=? LIMIT 1", (args.asset,)).fetchone()
        if previous and previous["kind"] != kind:
            raise LibraryError("Choose A Separate Asset Name For A File And A Folder.",
                               "An Asset Name Holds Either File Revisions Or Folder Revisions.")
        known = db.execute("SELECT * FROM assets WHERE name=?", (args.asset,)).fetchone()
        if known is None:
            asset_kind = args.kind or media.infer_kind(path, kind, facts)
            kind_source = "given" if args.kind else "inferred"
            db.execute("INSERT INTO assets(name, asset_kind) VALUES(?,?)", (args.asset, asset_kind))
        elif args.kind and args.kind != known["asset_kind"]:
            raise LibraryError(
                f"Asset {args.asset} Already Has Kind {known['asset_kind']}.",
                "Omit --kind, Or Change The Kind With The kind Command.")
        else:
            kind_source = "existing"
        existing = db.execute("SELECT * FROM revisions WHERE asset=? AND version=?",
                              (args.asset, version)).fetchone()
        created = existing is None
        if existing is not None:
            if tuple(existing[k] for k in ("origin", "rights", "context", "tags")) != meta:
                raise LibraryError(
                    "Existing Revision Has Different Metadata.",
                    "Inspect Its History, Or Choose Another Asset Name For The Same Bytes Under Different Terms.")
            if args.validate and args.validate != existing["validation_command"]:
                raise LibraryError("Existing Revision Has A Different Validation Command.",
                                   "Inspect It With show. A Stored Revision Keeps Its Original Command.")
        else:
            rev_id = db.execute(
                """INSERT INTO revisions(asset,version,kind,manifest,origin,rights,context,tags,
                   source_name,validation_command,validation_timeout,validation_env)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (args.asset, version, kind, manifest, *meta, path.name, args.validate,
                 args.validate_timeout if args.validate else None,
                 names if args.validate else None)).lastrowid
            db.execute("INSERT INTO media VALUES(?,?,?,?,?)",
                       (rev_id, encode(facts) if facts else None, status, still, still_status))
        record = describe(full(db, args.asset, version))
        record["kind_source"] = kind_source
        record["same_bytes_as"] = holders(db, version, args.asset)
    if created and args.validate:
        if args.validate_later:
            record["validation_result"] = store_result(db, args.asset, version, {
                "status": "not_run", "exit_code": None, "seconds": 0.0, "output_tail": "",
                "detail": "Registered Without Running. Run The validate Command When Ready.",
                "environment": []})
        else:
            record["validation_result"] = validate(db, args.asset, version, [], None, strict=False)
    return record


def search(db, args):
    found = []
    with transaction(db):
        rows = db.execute(REVISIONS + " ORDER BY r.asset, r.id DESC").fetchall()
        for row in rows:
            record = describe(row)
            haystack = " ".join([record[k] for k in ("asset", "context", "origin", "rights")]
                                + record["tags"]).casefold()
            duration = (record["media"] or {}).get("duration")
            if (args.term.casefold() not in haystack
                    or args.context.casefold() not in record["context"].casefold()
                    or not all(t.casefold() in record["tags"] for t in args.tag)
                    or (args.kind and record["asset_kind"] != args.kind)
                    or (record["archived"] and not args.archived)
                    or (args.min_duration is not None and (duration is None or duration < args.min_duration))
                    or (args.max_duration is not None and (duration is None or duration > args.max_duration))):
                continue
            record["duplicates"] = holders(db, record["version"], record["asset"])
            found.append((row["id"], record))
    if not args.duplicates:
        first = {}
        for rev_id, record in found:
            first[record["version"]] = min(rev_id, first.get(record["version"], rev_id))
        found = [(rev_id, record) for rev_id, record in found if first[record["version"]] == rev_id]
    return [record for _, record in found]


def history(db, asset):
    with transaction(db):
        return [describe(r) for r in db.execute(REVISIONS + " WHERE r.asset=? ORDER BY r.id DESC", (asset,))]


def set_kind(db, asset, kind):
    with transaction(db, write=True):
        before = asset_row(db, asset)["asset_kind"]
        db.execute("UPDATE assets SET asset_kind=? WHERE name=?", (kind, asset))
    return {"asset": asset, "asset_kind": kind, "previous_kind": before}


def archive(db, asset, undo):
    stamp = None if undo else datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with transaction(db, write=True):
        current = asset_row(db, asset)["archived"]
        if not undo and current:
            stamp = current
        db.execute("UPDATE assets SET archived=? WHERE name=?", (stamp, asset))
        pins = len(use_rows(db, asset=asset))
    return {"asset": asset, "archived": stamp, "status": "Restored To Search" if undo else "Archived",
            "pins_kept": pins}


def note(db, args):
    noted = args.date or datetime.date.today().isoformat()
    try:
        datetime.date.fromisoformat(noted)
    except ValueError:
        raise LibraryError(f"The Note Date Is Not A Calendar Date: {noted}", "Use The Form YYYY-MM-DD.")
    with transaction(db, write=True):
        asset_row(db, args.asset)
        note_id = db.execute("INSERT INTO notes(asset,kind,text,source,noted) VALUES(?,?,?,?,?)",
                             (args.asset, args.kind, args.text, args.source, noted)).lastrowid
    return {"asset": args.asset, "note": note_id, "kind": args.kind, "text": args.text,
            "source": args.source, "date": noted}


def notes(db, asset):
    return [{"note": r["id"], "kind": r["kind"], "text": r["text"], "source": r["source"],
             "date": r["noted"], "recorded": r["created"]}
            for r in db.execute("SELECT * FROM notes WHERE asset=? ORDER BY noted, id", (asset,))]


def use_rows(db, project=None, asset=None, slot=None, cut=None, retired=False):
    """Return Plain Pins And Cut Uses As One List Of Rows."""
    def where(prefix):
        sql, params = "", []
        for name, value in ((prefix + ".project", project), ("r.asset", asset), (prefix + ".slot", slot)):
            if value is not None:
                sql += f" AND {name}=?"
                params.append(value)
        return sql, params

    rows = []
    if cut is None:
        sql, params = where("p")
        rows += db.execute(
            """SELECT p.project, NULL AS cut, p.slot AS 'use', 0 AS modified, NULL AS cue, NULL AS time,
               NULL AS retired, v.* FROM pins p JOIN revisions r ON p.revision=r.id
               JOIN (""" + REVISIONS + ") v ON v.id=r.id WHERE 1=1" + sql, params).fetchall()
    sql, params = where("c")
    if cut is not None:
        sql += " AND c.cut=?"
        params.append(cut)
    if not retired:
        sql += " AND c.retired IS NULL"
    rows += db.execute(
        """SELECT c.project, c.cut, c.slot AS 'use', c.modified, c.cue, c.time, c.retired, v.*
           FROM cut_uses c JOIN revisions r ON c.revision=r.id
           JOIN (""" + REVISIONS + ") v ON v.id=r.id WHERE 1=1" + sql, params).fetchall()
    return sorted(rows, key=lambda r: (r["project"], r["cut"] or "", r["use"]))


def describe_use(row):
    record = describe(row)
    record["modified"] = bool(record["modified"])
    if record.get("retired") is None:
        record.pop("retired", None)
    return record


def uses(db, project=None, asset=None, cut=None):
    with transaction(db):
        return [describe_use(r) for r in use_rows(db, project, asset, cut=cut)]


def pin(db, args):
    with transaction(db, write=True):
        target = revision(db, args.asset, args.version)
        if args.cut is None:
            key = (args.project, args.use)
            existing = db.execute("""SELECT r.* FROM pins p JOIN revisions r ON r.id=p.revision
                                     WHERE project=? AND slot=?""", key).fetchone()
        else:
            key = (args.project, args.cut, args.use)
            if delivered(db, args.project, args.cut):
                raise LibraryError(f"Cut {args.cut} Of {args.project} Is Already Delivered.",
                                   "Record The Change Under A New Cut Label. A Delivery Record Is Kept As It Was.")
            existing = db.execute("""SELECT r.* FROM cut_uses c JOIN revisions r ON r.id=c.revision
                                     WHERE project=? AND cut=? AND slot=? AND retired IS NULL""", key).fetchone()
        if not (existing and existing["id"] == target["id"]):
            if (existing and existing["version"] != args.replace) or (not existing and args.replace):
                raise LibraryError("Pin Changed Or Already Exists.",
                                   "Inspect uses And Supply Its Current Digest With --replace.")
            if args.cut is None:
                db.execute("""INSERT INTO pins VALUES(?,?,?) ON CONFLICT(project,slot)
                              DO UPDATE SET revision=excluded.revision""", (*key, target["id"]))
            else:
                db.execute("""INSERT INTO cut_uses(project,cut,slot,revision) VALUES(?,?,?,?)
                              ON CONFLICT(project,cut,slot) DO UPDATE SET revision=excluded.revision,
                              retired=NULL""", (*key, target["id"]))
        return {"project": args.project, "cut": args.cut, "use": args.use,
                **describe(full(db, args.asset, args.version))}


def check(db, args):
    with transaction(db):
        selected = use_rows(db, args.project, args.asset, args.use, args.cut)
        if not selected or (args.path and len(selected) != 1):
            raise LibraryError("Select An Existing Project Pin. Checking A Local Path Requires Exactly One Match.",
                               "Run uses --project To List The Recorded Uses, Then Narrow With --use Or --cut.")
        result = []
        checked = set()
        for row in selected:
            verify_stored(db, row, checked)
            if args.path:
                kind, actual, _ = capture(args.path)
                if kind != row["kind"] or actual != row["version"]:
                    raise LibraryError(
                        f"Local Path Differs From Its Pin. Expected {row['version']}, Found {actual}.",
                        "Restore The Pinned Revision With get, Or Add The Changed Copy And Replace The Pin.")
            result.append({"project": row["project"], "cut": row["cut"], "use": row["use"],
                           "asset": row["asset"], "version": row["version"], "verified": True})
        return result


def write_preview(db, asset, version, destination):
    dest = destination.absolute()
    if dest.suffix.lower() not in (".jpg", ".jpeg"):
        raise LibraryError("A Preview Is A JPEG Still.", "Name The Output File With A .jpg Extension.")
    with transaction(db):
        row = revision(db, asset, version)
        stored = db.execute("SELECT preview, preview_status FROM media WHERE revision=?", (row["id"],)).fetchone()
    if stored is None or stored["preview"] is None:
        reason = stored["preview_status"] if stored else "This Revision Was Added Before Previews Were Kept."
        raise LibraryError(f"No Preview Still Is Stored For {asset}.", reason)
    data = bytes(stored["preview"])
    if dest.exists():
        if dest.is_file() and dest.read_bytes() == data:
            return {"path": str(dest), "version": row["version"], "bytes": len(data), "status": "Already Present"}
        raise LibraryError("Destination Already Contains Different Content.", "Choose A Fresh Path.")
    if not dest.parent.is_dir():
        raise LibraryError("Create The Destination Parent Folder First.",
                           f"Create {dest.parent} And Run The Command Again.")
    with dest.open("xb") as stream:
        stream.write(data)
    return {"path": str(dest), "version": row["version"], "bytes": len(data), "status": "Written"}


def validation_runs(db, rev_id):
    return [{"status": r["status"], "exit_code": r["exit_code"], "seconds": r["seconds"],
             "output_tail": r["output"], "detail": r["detail"], "ran": r["ran"]}
            for r in db.execute("SELECT * FROM validations WHERE revision=? ORDER BY id DESC", (rev_id,))]


def store_result(db, asset, version, result):
    with transaction(db, write=True):
        row = revision(db, asset, version)
        db.execute("INSERT INTO validations(revision,status,exit_code,output,seconds,detail) VALUES(?,?,?,?,?,?)",
                   (row["id"], result["status"], result["exit_code"], result["output_tail"],
                    result["seconds"], result["detail"]))
    return {"asset": asset, "version": version, "command": row["validation_command"], **result}


def start_environment(names):
    """Build The Minimal Environment: Start Variables Plus Names The User Passed."""
    wanted = list(START_VARIABLES) + list(names)
    env = {}
    for name in wanted:
        value = os.environ.get(name)
        if value is not None:
            env[name.upper() if os.name == "nt" else name] = value
    return env


def validate(db, asset, version, extra_env, timeout, strict=True):
    with transaction(db):
        row = revision(db, asset, version)
    command = row["validation_command"]
    if row["kind"] != "bundle" or not command:
        raise LibraryError(f"Revision {row['version'][:12]} Of {asset} Has No Validation Command.",
                           "Register The Folder Again With --validate To Create A Revision That Carries One.")
    limit = timeout or row["validation_timeout"] or DEFAULT_TIMEOUT
    names = sorted(set(json.loads(row["validation_env"] or "[]")) | set(extra_env))
    env = start_environment(names)
    result = {"status": "not_run", "exit_code": None, "seconds": 0.0, "output_tail": "",
              "detail": "", "environment": sorted(env)}
    try:
        argv = shlex.split(command)
    except ValueError:
        argv = []
    if argv and argv[0] in INTERPRETER_NAMES:
        program = sys.executable
    else:
        program = shutil.which(argv[0], path=env.get("PATH", "")) if argv else None
    if program is None and argv and Path(argv[0]).is_absolute() and Path(argv[0]).is_file():
        program = argv[0]
    if program is None:
        result["detail"] = "The Command Could Not Be Started Because Its Program Was Not Found On PATH."
    else:
        with tempfile.TemporaryDirectory(prefix="asset-library-validate-") as work:
            copy = Path(work) / "bundle"
            with transaction(db):
                materialize(db, row, copy)
            began = time.monotonic()
            try:
                done = subprocess.run([program] + argv[1:], cwd=str(copy), env=env, timeout=limit,
                                      stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, check=False)
                output = done.stdout.decode("utf-8", "replace")
                result.update(status="passed" if done.returncode == 0 else "failed",
                              exit_code=done.returncode,
                              detail="The Command Exited Successfully." if done.returncode == 0
                              else f"The Command Exited With Code {done.returncode}.")
            except subprocess.TimeoutExpired as late:
                output = (late.stdout or b"").decode("utf-8", "replace")
                result.update(status="failed", detail=f"The Command Was Stopped After {limit:g} Seconds.")
            except OSError as problem:
                output = str(problem)
                result["detail"] = "The Command Could Not Be Started."
            result["seconds"] = round(time.monotonic() - began, 3)
            result["output_tail"] = output[-OUTPUT_TAIL:]
    report = store_result(db, asset, row["version"], result)
    if strict and report["status"] != "passed":
        problem = LibraryError(f"Validation Did Not Pass For {asset}: {report['detail']}",
                               "Read output_tail In The Report. The Result Was Stored On The Revision.")
        problem.report = report
        raise problem
    return report


def show(db, asset):
    with transaction(db):
        base = asset_row(db, asset)
        revisions = []
        for row in db.execute(REVISIONS + " WHERE r.asset=? ORDER BY r.id DESC", (asset,)):
            record = describe(row)
            for field in ("asset", "asset_kind", "archived"):
                record.pop(field)
            record["same_bytes_as"] = holders(db, row["version"], asset)
            if row["kind"] == "bundle":
                record["members"] = sum(1 for item in json.loads(row["manifest"]) if item["kind"] == "file")
            if "validation" in record:
                runs = validation_runs(db, row["id"])
                record["validation"]["runs"] = len(runs)
                record["validation"]["last_result"] = runs[0] if runs else None
            revisions.append(record)
        appearances = []
        for row in use_rows(db, asset=asset, retired=True):
            entry = {k: row[k] for k in ("project", "cut", "use", "version", "cue", "time")}
            entry["modified"] = bool(row["modified"])
            entry["retired"] = row["retired"]
            shipped = delivered(db, row["project"], row["cut"]) if row["cut"] else None
            entry["delivered"] = shipped["delivered"] if shipped else None
            appearances.append(entry)
        shipped = []
        for row in db.execute("SELECT * FROM deliveries ORDER BY delivered, id"):
            snapshot = json.loads(row["declaration"])
            for item in snapshot.get("entries", []):
                if item.get("asset") == asset:
                    shipped.append({"project": row["project"], "cut": row["cut"], "delivered": row["delivered"],
                                    "use": item.get("use"), "version": item.get("version")})
        return {"asset": asset, "asset_kind": base["asset_kind"], "archived": base["archived"],
                "created": base["created"], "revisions": revisions, "notes": notes(db, asset),
                "uses": appearances, "deliveries": shipped}


def stats(db, db_path):
    with transaction(db):
        one = lambda sql: db.execute(sql).fetchone()[0]
        by_kind = dict.fromkeys(media.KINDS, 0)
        for kind, count in db.execute("SELECT asset_kind, COUNT(*) FROM assets GROUP BY asset_kind"):
            by_kind[kind] = count
        return {
            "database": str(db_path),
            "assets": one("SELECT COUNT(*) FROM assets"),
            "by_kind": by_kind,
            "archived": one("SELECT COUNT(*) FROM assets WHERE archived IS NOT NULL"),
            "revisions": one("SELECT COUNT(*) FROM revisions"),
            "pins": one("SELECT COUNT(*) FROM pins"),
            "cut_uses": one("SELECT COUNT(*) FROM cut_uses WHERE retired IS NULL"),
            "deliveries": one("SELECT COUNT(*) FROM deliveries"),
            "notes": one("SELECT COUNT(*) FROM notes"),
            "stored_files": one("SELECT COUNT(*) FROM blobs"),
            "stored_bytes": one("SELECT COALESCE(SUM(size),0) FROM blobs"),
            "preview_bytes": one("SELECT COALESCE(SUM(LENGTH(preview)),0) FROM media"),
            "database_bytes": db_path.stat().st_size,
        }
