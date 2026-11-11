"""Local Versioned Asset Library For Media Files And Editable Project Folders."""

import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sqlite3
import stat
import sys
import unicodedata


APPLICATION = 0x53434B31
SCHEMA_VERSION = 1
CHUNK_SIZE = 1024 * 1024
SCHEMA = (
    "CREATE TABLE blobs (id INTEGER PRIMARY KEY, digest TEXT UNIQUE, size INTEGER NOT NULL)",
    """CREATE TABLE chunks (
        blob INTEGER REFERENCES blobs ON DELETE CASCADE, seq INTEGER, data BLOB NOT NULL,
        PRIMARY KEY(blob, seq)) WITHOUT ROWID""",
    """CREATE TABLE revisions (
        id INTEGER PRIMARY KEY, asset TEXT NOT NULL, version TEXT NOT NULL, kind TEXT NOT NULL,
        manifest TEXT, origin TEXT NOT NULL, rights TEXT NOT NULL, context TEXT NOT NULL,
        tags TEXT NOT NULL, created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(asset, version))""",
    """CREATE TABLE pins (
        project TEXT NOT NULL, slot TEXT NOT NULL, revision INTEGER NOT NULL REFERENCES revisions,
        PRIMARY KEY(project, slot)) WITHOUT ROWID""",
)


class LibraryError(ValueError):
    pass


def encode(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def clean(value):
    value = value.strip()
    if not value:
        raise argparse.ArgumentTypeError("Enter A Nonempty Value")
    return value


def digest_arg(value):
    value = value.lower()
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise argparse.ArgumentTypeError("Enter A Full SHA-256 Digest")
    return value


def connect(path, create):
    mode = "rwc" if create else "rw"
    if not path.parent.is_dir():
        raise LibraryError("Create The Database Parent Folder First")
    db = sqlite3.connect(path.as_uri() + "?mode=" + mode, uri=True, timeout=30, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


def check_schema(db, create):
    app = db.execute("PRAGMA application_id").fetchone()[0]
    version = db.execute("PRAGMA user_version").fetchone()[0]
    if app == APPLICATION and version == SCHEMA_VERSION:
        return
    exists = db.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone()
    if not create or app or version or exists:
        raise LibraryError("Select A Supported Asset Library Database")
    for statement in SCHEMA:
        db.execute(statement)
    db.execute(f"PRAGMA application_id={APPLICATION}")
    db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")


def plain_mode(path):
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise LibraryError(f"Linked Paths Cannot Be Captured Or Restored: {path}")
    if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
        raise LibraryError(f"Expected A Regular File Or Directory: {path}")
    return info


def portable_name(name):
    device = name.split(".")[0].rstrip(" ").upper()
    reserved = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    reserved.update(prefix + digit for prefix in ("COM", "LPT") for digit in "123456789¹²³")
    invalid = '<>:"/\\|?*'
    if (not name or name in (".", "..") or name[-1] in " ." or device in reserved
            or any(c in invalid or ord(c) < 32 for c in name)
            or unicodedata.normalize("NFC", name) != name):
        raise LibraryError(f"Choose A Portable Bundle Member Name: {name}")


def inventory(root):
    members = []

    def visit(folder):
        names = set()
        for child in sorted(folder.iterdir(), key=lambda p: p.name):
            portable_name(child.name)
            if child.name.casefold() in names:
                raise LibraryError(f"Case-Colliding Bundle Members: {child}")
            names.add(child.name.casefold())
            info = plain_mode(child)
            path = child.relative_to(root).as_posix()
            if stat.S_ISDIR(info.st_mode):
                members.append((path, "dir", None))
                visit(child)
            else:
                members.append((path, "file", (info.st_size, info.st_mtime_ns)))

    visit(root)
    return sorted(members)


def read_file(path, write_chunk=None, excluded=None):
    first = plain_mode(path)
    if not stat.S_ISREG(first.st_mode):
        raise LibraryError(f"Expected A File: {path}")
    if excluded is not None and os.path.samestat(first, excluded):
        raise LibraryError("The Source Contains A Link To The Library Database")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for seq, data in enumerate(iter(lambda: stream.read(CHUNK_SIZE), b"")):
            digest.update(data)
            size += len(data)
            if write_chunk is not None:
                write_chunk(seq, data)
    last = plain_mode(path)
    if (first.st_mtime_ns != last.st_mtime_ns or size != first.st_size or size != last.st_size
            or not os.path.samestat(first, last)):
        raise LibraryError(f"Source Changed During Capture: {path}")
    return digest.hexdigest(), size


def capture_file(path, db=None, excluded=None):
    version, size = read_file(path, excluded=excluded)
    if db is None or db.execute("SELECT 1 FROM blobs WHERE digest=?", (version,)).fetchone():
        return version
    blob_id = db.execute("INSERT INTO blobs(digest,size) VALUES(?,?)", (version, size)).lastrowid

    def store_chunk(seq, data):
        db.execute("INSERT INTO chunks VALUES(?,?,?)", (blob_id, seq, data))

    if read_file(path, store_chunk, excluded) != (version, size):
        raise LibraryError(f"Source Changed Before Storage: {path}")
    return version


def bundle_version(manifest):
    return hashlib.sha256(b"SocialCutKit.Bundle.1\0" + manifest.encode("ascii")).hexdigest()


def capture(path, db=None, excluded=None):
    mode = plain_mode(path).st_mode
    if stat.S_ISREG(mode):
        return "file", capture_file(path, db, excluded), None
    before = inventory(path)
    items = []
    for name, kind, _ in before:
        entry = {"path": name, "kind": kind}
        if kind == "file":
            entry["digest"] = capture_file(path / name, db, excluded)
        items.append(entry)
    if before != inventory(path):
        raise LibraryError(f"Bundle Changed During Capture: {path}")
    manifest = encode(items)
    return "bundle", bundle_version(manifest), manifest


def revision(db, asset, version=None):
    sql = "SELECT * FROM revisions WHERE asset=?"
    params = [asset]
    if version is not None:
        sql += " AND version=?"
        params.append(version)
    row = db.execute(sql + " ORDER BY id DESC LIMIT 1", params).fetchone()
    if row is None:
        raise LibraryError(f"Asset Or Revision Was Not Found: {asset}")
    return row


def describe(row):
    record = dict(row)
    for field in ("id", "manifest"):
        record.pop(field, None)
    record["tags"] = json.loads(record["tags"])
    return record


def add(db, args, db_path):
    path = args.source.absolute()
    resolved = path.resolve()
    if resolved in (db_path, *db_path.parents) or (path.is_file() and path.samefile(db_path)):
        raise LibraryError("Keep The Library Database Outside The Source Asset")
    kind, version, manifest = capture(path, db, db_path.stat())
    tags = encode(sorted({tag.casefold() for tag in args.tag}))
    meta = (args.origin, args.rights, args.context, tags)
    previous = db.execute("SELECT kind FROM revisions WHERE asset=? LIMIT 1", (args.asset,)).fetchone()
    if previous and previous["kind"] != kind:
        raise LibraryError("Choose A Separate Asset Name For A Different Asset Kind")
    existing = db.execute("SELECT * FROM revisions WHERE asset=? AND version=?", (args.asset, version)).fetchone()
    if existing is not None:
        if tuple(existing[k] for k in ("origin", "rights", "context", "tags")) != meta:
            raise LibraryError("Existing Revision Has Different Metadata. Inspect Its History Or Choose Another Asset Name")
        return describe(existing)
    db.execute("""INSERT INTO revisions(asset,version,kind,manifest,origin,rights,context,tags)
                  VALUES(?,?,?,?,?,?,?,?)""", (args.asset, version, kind, manifest, *meta))
    return describe(revision(db, args.asset, version))


def search(db, args):
    found = []
    for row in db.execute("SELECT * FROM revisions ORDER BY asset, id DESC"):
        record = describe(row)
        haystack = " ".join([record[k] for k in ("asset", "context", "origin", "rights")] + record["tags"]).casefold()
        if (args.term.casefold() in haystack and args.context.casefold() in record["context"].casefold()
                and all(t.casefold() in record["tags"] for t in args.tag)):
            found.append(record)
    return found


def pin(db, args):
    target = revision(db, args.asset, args.version)
    key = (args.project, args.use)
    existing = db.execute("""SELECT r.* FROM pins p JOIN revisions r ON r.id=p.revision
                             WHERE project=? AND slot=?""", key).fetchone()
    if existing and existing["id"] == target["id"]:
        return {"project": args.project, "use": args.use, **describe(target)}
    if (existing and existing["version"] != args.replace) or (not existing and args.replace):
        raise LibraryError("Pin Changed Or Already Exists. Inspect Uses And Supply Its Current Digest With --replace")
    db.execute("""INSERT INTO pins VALUES(?,?,?) ON CONFLICT(project,slot)
                  DO UPDATE SET revision=excluded.revision""", (*key, target["id"]))
    return {"project": args.project, "use": args.use, **describe(target)}


def pins(db, project=None, asset=None, slot=None):
    sql = """SELECT p.project, p.slot AS 'use', r.* FROM pins p
             JOIN revisions r ON p.revision=r.id WHERE 1=1"""
    params = []
    for name, value in (("p.project", project), ("r.asset", asset), ("p.slot", slot)):
        if value is not None:
            sql += f" AND {name}=?"
            params.append(value)
    return db.execute(sql + " ORDER BY p.project, p.slot", params).fetchall()


def stream_blob(db, digest, destination=None):
    row = db.execute("SELECT id,size FROM blobs WHERE digest=?", (digest,)).fetchone()
    if row is None:
        raise LibraryError(f"Missing Stored File: {digest}")
    hash_ = hashlib.sha256()
    size = 0
    for chunk in db.execute("SELECT data FROM chunks WHERE blob=? ORDER BY seq", (row["id"],)):
        data = chunk[0]
        hash_.update(data)
        size += len(data)
        if destination is not None:
            destination.write(data)
    if hash_.hexdigest() != digest or row["size"] != size:
        raise LibraryError(f"Stored File Failed Verification: {digest}")


def members(row):
    if row["kind"] == "file":
        return [("", "file", row["version"])]
    if row["kind"] != "bundle" or bundle_version(row["manifest"]) != row["version"]:
        raise LibraryError("Stored Bundle Manifest Failed Verification")
    result = []
    for item in json.loads(row["manifest"]):
        name = item["path"]
        parts = name.split("/")
        for p in parts:
            portable_name(p)
        if name != PurePosixPath(*parts).as_posix() or item["kind"] not in ("dir", "file"):
            raise LibraryError("Invalid Stored Bundle Member")
        result.append((name, item["kind"], item.get("digest")))
    return result


def check(db, args):
    selected = pins(db, args.project, args.asset, args.use)
    if not selected or (args.path and len(selected) != 1):
        raise LibraryError("Select An Existing Project Pin. Checking A Local Path Requires Exactly One Match")
    result = []
    checked = set()
    for row in selected:
        for _, kind, digest in members(row):
            if kind == "file" and digest not in checked:
                stream_blob(db, digest)
                checked.add(digest)
        if args.path:
            kind, actual, _ = capture(args.path)
            if kind != row["kind"] or actual != row["version"]:
                raise LibraryError(f"Local Path Differs From Its Pin. Expected {row['version']}, Found {actual}")
        result.append({"project": row["project"], "use": row["use"], "asset": row["asset"],
                       "version": row["version"], "verified": True})
    return result


def restore(db, args):
    row = revision(db, args.asset, args.version)
    dest = args.destination.absolute()
    entries = members(row)
    if dest.exists() or dest.is_symlink():
        kind, digest, _ = capture(dest)
        if (kind, digest) != (row["kind"], row["version"]):
            raise LibraryError("Destination Already Contains Different Content. Choose A Fresh Path")
        return {"path": str(dest), "version": digest, "status": "Already Present"}
    if not dest.parent.is_dir():
        raise LibraryError("Create The Destination Parent Folder First")
    created = []
    try:
        if row["kind"] == "bundle":
            dest.mkdir()
            created.append((dest, "dir"))
        for name, kind, digest in entries:
            target = dest / name if name else dest
            if kind == "dir":
                target.mkdir()
                created.append((target, kind))
            else:
                with target.open("xb") as stream:
                    created.append((target, kind))
                    stream_blob(db, digest, stream)
    except BaseException:
        for target, kind in reversed(created):
            with contextlib.suppress(OSError):
                target.rmdir() if kind == "dir" else target.unlink()
        raise
    return {"path": str(dest), "version": row["version"], "status": "Restored"}


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--db", type=Path, required=True, help="Local SQLite File")
    sub = root.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Create Or Open The Library")
    register = sub.add_parser("add", help="Capture A File Or Folder")
    register.add_argument("asset", type=clean)
    register.add_argument("source", type=Path)
    for field in ("origin", "rights", "context"):
        register.add_argument("--" + field, type=clean, required=True)
    register.add_argument("--tag", action="append", type=clean, default=[])
    find = sub.add_parser("search", help="Find Matching Revisions")
    find.add_argument("term", nargs="?", default="")
    find.add_argument("--tag", action="append", type=clean, default=[])
    find.add_argument("--context", default="")
    history = sub.add_parser("history", help="List Asset Revisions")
    history.add_argument("asset", type=clean)
    link = sub.add_parser("pin", help="Record An Exact Revision For A Project Use")
    link.add_argument("project", type=clean)
    link.add_argument("asset", type=clean)
    link.add_argument("--use", type=clean, required=True)
    link.add_argument("--version", type=digest_arg, required=True)
    link.add_argument("--replace", type=digest_arg, help="Expected Previous Digest")
    usage = sub.add_parser("uses", help="List Where Revisions Are Used")
    usage.add_argument("--project", type=clean)
    usage.add_argument("--asset", type=clean)
    verify = sub.add_parser("check", help="Verify Stored Pins And Optionally A Local Copy")
    verify.add_argument("project", type=clean)
    verify.add_argument("--asset", type=clean)
    verify.add_argument("--use", type=clean)
    verify.add_argument("--path", type=Path)
    fetch = sub.add_parser("get", help="Restore A File Or Folder")
    fetch.add_argument("asset", type=clean)
    fetch.add_argument("destination", type=Path)
    fetch.add_argument("--version", type=digest_arg, required=True)
    return root


def main():
    args = parser().parse_args()
    path = args.db.resolve()
    command = args.command
    try:
        with contextlib.closing(connect(path, command == "init")) as db:
            db.execute("BEGIN IMMEDIATE" if command in ("init", "add", "pin") else "BEGIN")
            check_schema(db, command == "init")
            if command == "init":
                result = {"database": str(path), "schema_version": SCHEMA_VERSION}
            elif command == "add":
                result = add(db, args, path)
            elif command == "search":
                result = search(db, args)
            elif command == "history":
                result = [describe(r) for r in db.execute(
                    "SELECT * FROM revisions WHERE asset=? ORDER BY id DESC", (args.asset,))]
            elif command == "pin":
                result = pin(db, args)
            elif command == "uses":
                result = [describe(r) for r in pins(db, args.project, args.asset)]
            elif command == "check":
                result = check(db, args)
            else:
                result = restore(db, args)
            db.commit()
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except (LibraryError, sqlite3.Error, OSError, RecursionError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
