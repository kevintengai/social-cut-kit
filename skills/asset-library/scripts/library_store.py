"""Storage Layer For The Asset Library: Database Location, Schema, Upgrade, Capture, And Restore."""

import argparse
import contextlib
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sqlite3
import stat
import unicodedata


APPLICATION = 0x53434B31
SCHEMA_VERSION = 2
CHUNK_SIZE = 1024 * 1024
ENV_VARIABLE = "SOCIAL_CUT_KIT_LIBRARY"
DEFAULTS_FILE = Path(".social-cut-kit") / "asset-library.md"
BASE_SCHEMA = (
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
ADDED_TABLES = (
    """CREATE TABLE IF NOT EXISTS assets (
        name TEXT PRIMARY KEY, asset_kind TEXT NOT NULL, archived TEXT,
        created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP) WITHOUT ROWID""",
    """CREATE TABLE IF NOT EXISTS media (
        revision INTEGER PRIMARY KEY REFERENCES revisions, facts TEXT, status TEXT NOT NULL,
        preview BLOB, preview_status TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY, asset TEXT NOT NULL, kind TEXT NOT NULL, text TEXT NOT NULL,
        source TEXT NOT NULL, noted TEXT NOT NULL, created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""",
    """CREATE TABLE IF NOT EXISTS cut_uses (
        project TEXT NOT NULL, cut TEXT NOT NULL, slot TEXT NOT NULL,
        revision INTEGER NOT NULL REFERENCES revisions, modified INTEGER NOT NULL DEFAULT 0,
        cue TEXT, time REAL, retired TEXT,
        PRIMARY KEY(project, cut, slot)) WITHOUT ROWID""",
    """CREATE TABLE IF NOT EXISTS deliveries (
        id INTEGER PRIMARY KEY, project TEXT NOT NULL, cut TEXT NOT NULL, delivered TEXT NOT NULL,
        declaration TEXT NOT NULL, created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(project, cut))""",
    """CREATE TABLE IF NOT EXISTS validations (
        id INTEGER PRIMARY KEY, revision INTEGER NOT NULL REFERENCES revisions, status TEXT NOT NULL,
        exit_code INTEGER, output TEXT NOT NULL, seconds REAL NOT NULL, detail TEXT NOT NULL,
        ran TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""",
)
ADDED_COLUMNS = (
    ("revisions", "source_name", "TEXT"),
    ("revisions", "validation_command", "TEXT"),
    ("revisions", "validation_timeout", "REAL"),
    ("revisions", "validation_env", "TEXT"),
)


class LibraryError(ValueError):
    def __init__(self, message, hint=None):
        super().__init__(message)
        self.hint = hint or "Run The Command With --help To See Its Options."


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


def defaults_path():
    return Path.home() / DEFAULTS_FILE


def locate(explicit):
    """Return The Database Path And Where It Was Named."""
    if explicit is not None:
        return Path(explicit).expanduser().resolve(), "--db"
    named = os.environ.get(ENV_VARIABLE, "").strip()
    if named:
        return Path(named).expanduser().resolve(), ENV_VARIABLE
    defaults = defaults_path()
    if defaults.is_file():
        text = defaults.read_text(encoding="utf-8", errors="replace")
        found = re.search(r"^[ \t]*(?:[-*][ \t]+)?Library:[ \t]*`([^`\r\n]+)`", text, re.MULTILINE)
        if found:
            return Path(found.group(1).strip()).expanduser().resolve(), str(defaults)
        raise LibraryError(
            f"The Defaults File Has No Library Line: {defaults}",
            "Add A Line Of The Form Library: `PATH` To That File, Or Pass --db.")
    raise LibraryError(
        "No Asset Library Was Named.",
        f"Pass --db PATH, Set {ENV_VARIABLE}, Or Add A Line Of The Form Library: `PATH` To {defaults}.")


def connect(path, create):
    mode = "rwc" if create else "rw"
    if not path.parent.is_dir():
        raise LibraryError("Create The Database Parent Folder First.",
                           f"Create {path.parent} And Run The Command Again.")
    if not create and not path.is_file():
        raise LibraryError(f"The Library Database Does Not Exist: {path}",
                           "Run The init Command To Create It, Or Correct The Path.")
    db = sqlite3.connect(path.as_uri() + "?mode=" + mode, uri=True, timeout=30, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    return db


@contextlib.contextmanager
def transaction(db, write=False):
    db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
    try:
        yield db
        db.execute("COMMIT")
    except BaseException:
        with contextlib.suppress(sqlite3.Error):
            db.execute("ROLLBACK")
        raise


def identity(db):
    return (db.execute("PRAGMA application_id").fetchone()[0],
            db.execute("PRAGMA user_version").fetchone()[0])


def backup_copy(path, version):
    """Write A Timestamped Copy With The SQLite Backup API Before An Upgrade."""
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = path.suffix or ".sqlite"
    target = path.with_name(f"{path.stem}.backup-v{version}-{stamp}{suffix}")
    if target.exists():
        target = path.with_name(f"{path.stem}.backup-v{version}-{stamp}-{os.getpid()}{suffix}")
    source = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=30)
    try:
        copy = sqlite3.connect(str(target))
        try:
            source.backup(copy)
        finally:
            copy.close()
    finally:
        source.close()
    return target


def apply_additions(db):
    for statement in ADDED_TABLES:
        db.execute(statement)
    for table, column, kind in ADDED_COLUMNS:
        present = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
        if column not in present:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {kind}")
    db.execute("""INSERT OR IGNORE INTO assets(name, asset_kind, created)
                  SELECT asset, 'other', MIN(created) FROM revisions GROUP BY asset""")
    db.execute(f"PRAGMA application_id={APPLICATION}")
    db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")


def ensure_schema(db, path, create):
    """Create, Accept, Or Upgrade The Schema. Return Facts About Any Upgrade."""
    app, version = identity(db)
    if app == APPLICATION and version == SCHEMA_VERSION:
        return {}
    if app == APPLICATION and version > SCHEMA_VERSION:
        raise LibraryError(
            f"This Library Was Written By A Newer Version (Schema {version}). It Was Left Untouched.",
            "Use The Newer Social Cut Kit That Created It, Or Name A Different Library.")
    if app == APPLICATION and 1 <= version < SCHEMA_VERSION:
        saved = backup_copy(path, version)
        with transaction(db, write=True):
            if identity(db)[1] == version:
                apply_additions(db)
        return {"upgraded_from": version, "backup": str(saved)}
    exists = db.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone()
    if not create or app or version or exists:
        raise LibraryError("Select A Supported Asset Library Database.",
                           "Name A File Created By The init Command.")
    with transaction(db, write=True):
        if identity(db) == (0, 0) and not db.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone():
            for statement in BASE_SCHEMA:
                db.execute(statement)
            apply_additions(db)
    return {}


def plain_mode(path):
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise LibraryError(f"Linked Paths Cannot Be Captured Or Restored: {path}",
                           "Replace The Link With A Real File Or Folder.")
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
        raise LibraryError(f"Choose A Portable Bundle Member Name: {name}",
                           "Rename The Member So It Works On Windows, macOS, And Linux.")


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
        raise LibraryError("The Source Contains A Link To The Library Database.",
                           "Keep The Library Database Outside The Source Asset.")
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
        raise LibraryError(f"Source Changed During Capture: {path}",
                           "Close Or Save The Source And Run The Command Again.")
    return digest.hexdigest(), size


def capture_file(path, db=None, excluded=None):
    version, size = read_file(path, excluded=excluded)
    if db is None or db.execute("SELECT 1 FROM blobs WHERE digest=?", (version,)).fetchone():
        return version
    blob_id = db.execute("INSERT INTO blobs(digest,size) VALUES(?,?)", (version, size)).lastrowid

    def store_chunk(seq, data):
        db.execute("INSERT INTO chunks VALUES(?,?,?)", (blob_id, seq, data))

    if read_file(path, store_chunk, excluded) != (version, size):
        raise LibraryError(f"Source Changed Before Storage: {path}",
                           "Close Or Save The Source And Run The Command Again.")
    return version


def bundle_version(manifest):
    return hashlib.sha256(b"SocialCutKit.Bundle.1\0" + manifest.encode("ascii")).hexdigest()


def capture(path, db=None, excluded=None):
    """Return The Storage Form, Version, And Manifest Of A File Or Folder."""
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
        raise LibraryError(f"Bundle Changed During Capture: {path}",
                           "Close The Project That Owns The Folder And Run The Command Again.")
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
        raise LibraryError(f"Asset Or Revision Was Not Found: {asset}",
                           "Run search Or history To List Asset Names And Full Versions. Names Match Case Exactly.")
    return row


def stream_blob(db, digest, destination=None):
    row = db.execute("SELECT id,size FROM blobs WHERE digest=?", (digest,)).fetchone()
    if row is None:
        raise LibraryError(f"Missing Stored File: {digest}",
                           "Restore The Library From A Backup, Or Add The Source Again.")
    hash_ = hashlib.sha256()
    size = 0
    for chunk in db.execute("SELECT data FROM chunks WHERE blob=? ORDER BY seq", (row["id"],)):
        data = chunk[0]
        hash_.update(data)
        size += len(data)
        if destination is not None:
            destination.write(data)
    if hash_.hexdigest() != digest or row["size"] != size:
        raise LibraryError(f"Stored File Failed Verification: {digest}",
                           "Restore The Library From A Backup, Or Add The Source Again.")


def members(row):
    if row["kind"] == "file":
        return [("", "file", row["version"])]
    if row["kind"] != "bundle" or bundle_version(row["manifest"]) != row["version"]:
        raise LibraryError("Stored Bundle Manifest Failed Verification.",
                           "Restore The Library From A Backup.")
    result = []
    for item in json.loads(row["manifest"]):
        name = item["path"]
        parts = name.split("/")
        for p in parts:
            portable_name(p)
        if name != PurePosixPath(*parts).as_posix() or item["kind"] not in ("dir", "file"):
            raise LibraryError("Invalid Stored Bundle Member.", "Restore The Library From A Backup.")
        result.append((name, item["kind"], item.get("digest")))
    return result


def verify_stored(db, row, checked=None):
    """Read Every Stored Byte Of A Revision And Confirm Its Digests."""
    checked = set() if checked is None else checked
    for _, kind, digest in members(row):
        if kind == "file" and digest not in checked:
            stream_blob(db, digest)
            checked.add(digest)


def materialize(db, row, dest):
    """Write A Stored Revision To A Fresh Path, Removing Partial Output On Failure."""
    entries = members(row)
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


def restore(db, asset, version, destination):
    row = revision(db, asset, version)
    dest = destination.absolute()
    members(row)
    if dest.exists() or dest.is_symlink():
        kind, digest, _ = capture(dest)
        if (kind, digest) != (row["kind"], row["version"]):
            raise LibraryError("Destination Already Contains Different Content.", "Choose A Fresh Path.")
        return {"path": str(dest), "version": digest, "status": "Already Present"}
    if not dest.parent.is_dir():
        raise LibraryError("Create The Destination Parent Folder First.",
                           f"Create {dest.parent} And Run The Command Again.")
    materialize(db, row, dest)
    return {"path": str(dest), "version": row["version"], "status": "Restored"}
