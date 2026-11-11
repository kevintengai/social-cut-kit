"""Export A Catalog With A Browsable Index, And Import Assets From A Catalog And A Folder Of Files."""

import datetime
import html
import json
import os
from pathlib import Path

import library_media as media
from library_records import REVISIONS, describe, holders, notes, use_rows, validation_runs
from library_store import (SCHEMA_VERSION, LibraryError, capture, encode, materialize, transaction)


FORMAT = "social-cut-kit-asset-catalog"
FIELDS = ("origin", "rights", "context")
PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Asset Library Catalog</title>
<style>
body{font:15px/1.45 system-ui,sans-serif;margin:24px;color:#1b1f24;background:#fafafa}
input{font:inherit;padding:8px 10px;width:min(480px,100%);margin:8px 0 16px;border:1px solid #9aa3ad;border-radius:6px}
table{border-collapse:collapse;width:100%;background:#fff}
th,td{border:1px solid #d5dae0;padding:8px;text-align:left;vertical-align:top}
th{background:#eef1f4}
img{max-width:140px;max-height:140px;display:block}
code{font-size:12px;word-break:break-all}
.archived{color:#7a828c}
</style></head><body>
<h1>Asset Library Catalog</h1>
<p>__SUMMARY__</p>
<input id="filter" type="search" placeholder="Filter By Any Text" aria-label="Filter By Any Text">
<table><thead><tr><th>Preview</th><th>Asset</th><th>Kind</th><th>Latest Version</th><th>Media Facts</th>
<th>Rights</th><th>Context And Tags</th><th>Notes</th><th>Uses</th></tr></thead>
<tbody id="rows">
__ROWS__
</tbody></table>
<script>
const box = document.getElementById("filter");
box.addEventListener("input", () => {
  const term = box.value.toLowerCase();
  for (const row of document.getElementById("rows").rows) {
    row.hidden = !row.textContent.toLowerCase().includes(term);
  }
});
</script>
</body></html>
"""


def write_text(path, text):
    staged = path.with_name(path.name + ".part")
    staged.write_text(text, encoding="utf-8", newline="\n")
    os.replace(staged, path)


def gather(db):
    """Collect Every Record In The Library As Plain Data."""
    assets = []
    for base in db.execute("SELECT * FROM assets ORDER BY name").fetchall():
        revisions = []
        for row in db.execute(REVISIONS + " WHERE r.asset=? ORDER BY r.id", (base["name"],)).fetchall():
            record = describe(row)
            for field in ("asset", "asset_kind", "archived"):
                record.pop(field)
            record["members"] = json.loads(row["manifest"]) if row["manifest"] else None
            record["same_bytes_as"] = holders(db, row["version"], base["name"])
            if "validation" in record:
                record["validation"]["results"] = validation_runs(db, row["id"])
            record["_row"] = row
            revisions.append(record)
        assets.append({"name": base["name"], "asset_kind": base["asset_kind"], "archived": base["archived"],
                       "created": base["created"], "revisions": revisions, "notes": notes(db, base["name"])})
    uses = [{"project": r["project"], "cut": r["cut"], "use": r["use"], "asset": r["asset"],
             "version": r["version"], "modified": bool(r["modified"]), "cue": r["cue"], "time": r["time"],
             "retired": r["retired"]} for r in use_rows(db, retired=True)]
    shipped = [{"project": r["project"], "cut": r["cut"], "delivered": r["delivered"], "recorded": r["created"],
                "declaration": json.loads(r["declaration"])}
               for r in db.execute("SELECT * FROM deliveries ORDER BY delivered, id")]
    return assets, uses, shipped


def facts_line(facts):
    if not facts:
        return ""
    parts = []
    if facts.get("duration") is not None:
        parts.append(f"{facts['duration']:g} s")
    if facts.get("width") and facts.get("height"):
        parts.append(f"{facts['width']}x{facts['height']}")
    if facts.get("frame_rate"):
        parts.append(f"{facts['frame_rate']:g} fps")
    if facts.get("audio_channels"):
        parts.append(f"{facts['audio_channels']} ch")
    if facts.get("sample_rate"):
        parts.append(f"{facts['sample_rate']} Hz")
    if facts.get("peak_db") is not None:
        parts.append(f"Peak {facts['peak_db']:g} dB")
    return ", ".join(parts)


def page(assets, uses, summary):
    rows = []
    text = lambda value: html.escape(str(value), quote=True)
    for asset in assets:
        latest = asset["revisions"][-1] if asset["revisions"] else None
        if latest is None:
            continue
        picture = (f'<img src="{text(latest["preview"])}" alt="Preview Of {text(asset["name"])}">'
                   if latest.get("preview") else "")
        mine = [u for u in uses if u["asset"] == asset["name"] and not u["retired"]]
        where = "<br>".join(text(" / ".join(p for p in (u["project"], u["cut"], u["use"]) if p)) for u in mine)
        said = "<br>".join(text(f'{n["date"]} {n["kind"]}: {n["text"]} ({n["source"]})') for n in asset["notes"])
        state = ' class="archived"' if asset["archived"] else ""
        label = text(asset["name"]) + (" (Archived)" if asset["archived"] else "")
        rows.append(
            f"<tr{state}><td>{picture}</td><td>{label}<br>{len(asset['revisions'])} Revisions</td>"
            f"<td>{text(asset['asset_kind'])}<br>{text(latest['kind'])}</td>"
            f"<td><code>{text(latest['version'])}</code><br>{text(latest['created'])}</td>"
            f"<td>{text(facts_line(latest['media']))}</td>"
            f"<td>{text(latest['rights'])}<br>Origin: {text(latest['origin'])}</td>"
            f"<td>{text(latest['context'])}<br>{text(', '.join(latest['tags']))}</td>"
            f"<td>{said}</td><td>{where}</td></tr>")
    return PAGE.replace("__SUMMARY__", html.escape(summary)).replace("__ROWS__", "\n".join(rows))


def export(db, folder, with_files):
    folder = folder.absolute()
    if folder.exists():
        if not folder.is_dir():
            raise LibraryError("The Export Destination Is Not A Folder.", "Name A New Or Empty Folder.")
        if any(folder.iterdir()) and not (folder / "catalog.json").is_file():
            raise LibraryError("The Export Folder Holds Other Files.",
                               "Name A New Or Empty Folder, Or A Folder That Holds An Earlier Export.")
    elif not folder.parent.is_dir():
        raise LibraryError("Create The Export Parent Folder First.", f"Create {folder.parent} And Run The Command Again.")
    folder.mkdir(exist_ok=True)
    previews = 0
    files = 0
    with transaction(db):
        assets, uses, shipped = gather(db)
        for asset in assets:
            for record in asset["revisions"]:
                row = record.pop("_row")
                record["preview"] = None
                if record["has_preview"]:
                    (folder / "previews").mkdir(exist_ok=True)
                    name = f"previews/{row['version']}.jpg"
                    data = db.execute("SELECT preview FROM media WHERE revision=?", (row["id"],)).fetchone()[0]
                    (folder / name).write_bytes(bytes(data))
                    record["preview"] = name
                    previews += 1
                record["file"] = None
                if with_files:
                    holder = folder / "files" / row["version"]
                    holder.mkdir(parents=True, exist_ok=True)
                    name = row["source_name"] or ("bundle" if row["kind"] == "bundle" else "asset")
                    if not (holder / name).exists():
                        materialize(db, row, holder / name)
                    record["file"] = f"files/{row['version']}/{name}"
                    files += 1
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    catalog = {"format": FORMAT, "format_version": 1, "schema_version": SCHEMA_VERSION, "exported": stamp,
               "contains_file_bytes": bool(with_files), "assets": assets, "uses": uses, "deliveries": shipped}
    write_text(folder / "catalog.json", json.dumps(catalog, ensure_ascii=True, indent=2) + "\n")
    summary = (f"Exported {stamp}. {len(assets)} Assets, {sum(len(a['revisions']) for a in assets)} Revisions, "
               f"{len(uses)} Recorded Uses, {len(shipped)} Deliveries. Each Row Shows The Latest Revision. "
               "The Full Record Is In catalog.json.")
    write_text(folder / "index.html", page(assets, uses, summary))
    return {"folder": str(folder), "catalog": str(folder / "catalog.json"), "index": str(folder / "index.html"),
            "assets": len(assets), "revisions": sum(len(a["revisions"]) for a in assets), "uses": len(uses),
            "deliveries": len(shipped), "previews": previews, "contains_file_bytes": bool(with_files),
            "files": files}


def entries(catalog):
    """Yield Asset Entries With A Normalised Revision List."""
    listed = catalog.get("assets") if isinstance(catalog, dict) else catalog
    if not isinstance(listed, list):
        raise LibraryError("The Catalog Needs An assets List.",
                           "See The Import Catalog Section Of RECORDS.md For The Expected Fields.")
    for item in listed:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not item["name"].strip():
            raise LibraryError("Every Catalog Asset Needs A Nonempty name String.",
                               "See The Import Catalog Section Of RECORDS.md For The Expected Fields.")
        revisions = item.get("revisions")
        if not isinstance(revisions, list):
            revisions = [item]
        kind = item.get("asset_kind") or (item.get("kind") if item.get("kind") in media.KINDS else None)
        if kind is not None and kind not in media.KINDS:
            raise LibraryError(f"Unknown Kind For {item['name']}: {kind}",
                               "Use One Of: " + ", ".join(media.KINDS) + ".")
        yield item["name"].strip(), kind, [r for r in revisions if isinstance(r, dict)], item


def import_one(db, db_path, name, kind, rev, source, update, report):
    relative = rev.get("file")
    if not isinstance(relative, str) or not relative:
        report["skipped"].append({"asset": name, "reason": "The Catalog Names No File For This Revision."})
        return
    path = source / relative
    if not path.exists():
        report["missing"].append({"asset": name, "file": relative})
        return
    storage, version, _ = capture(path)
    if isinstance(rev.get("version"), str) and rev["version"].lower() != version:
        report["skipped"].append({"asset": name, "file": relative,
                                  "reason": "The File Differs From The Version In The Catalog."})
        return
    tags = rev.get("tags") if isinstance(rev.get("tags"), list) else []
    wanted = {f: rev[f].strip() for f in FIELDS if isinstance(rev.get(f), str) and rev[f].strip()}
    wanted["tags"] = encode(sorted({str(t).casefold() for t in tags}))
    with transaction(db):
        existing = db.execute("SELECT * FROM revisions WHERE asset=? AND version=?", (name, version)).fetchone()
        known = db.execute("SELECT * FROM assets WHERE name=?", (name,)).fetchone()
        others = holders(db, version, name)
    if existing is not None:
        differing = {f: {"library": existing[f], "catalog": wanted[f]} for f in wanted if existing[f] != wanted[f]}
        if kind and kind != known["asset_kind"]:
            differing["asset_kind"] = {"library": known["asset_kind"], "catalog": kind}
        entry = {"asset": name, "version": version}
        if not differing:
            report["unchanged"].append(entry)
        elif name in update:
            with transaction(db, write=True):
                for field, values in differing.items():
                    if field == "asset_kind":
                        db.execute("UPDATE assets SET asset_kind=? WHERE name=?", (kind, name))
                    else:
                        db.execute(f"UPDATE revisions SET {field}=? WHERE id=?", (values["catalog"], existing["id"]))
            report["updated"].append({**entry, "fields": differing})
        else:
            report["differing"].append({**entry, "fields": differing})
        return
    if known is None and others:
        report["duplicates"].append({"asset": name, "version": version, "held_by": others})
        return
    if any(f not in wanted for f in FIELDS):
        report["skipped"].append({"asset": name, "file": relative,
                                  "reason": "The Catalog Entry Needs origin, rights, And context."})
        return
    facts, status = media.probe(path, storage)
    still, still_status = media.preview(path, storage, facts)
    check = rev.get("validation") if isinstance(rev.get("validation"), dict) and storage == "bundle" else {}
    with transaction(db, write=True):
        previous = db.execute("SELECT kind FROM revisions WHERE asset=? LIMIT 1", (name,)).fetchone()
        if previous and previous["kind"] != storage:
            report["skipped"].append({"asset": name, "file": relative,
                                      "reason": "The Name Already Holds A Different Storage Form."})
            return
        storage, version, manifest = capture(path, db, db_path.stat())
        if db.execute("SELECT 1 FROM assets WHERE name=?", (name,)).fetchone() is None:
            db.execute("INSERT INTO assets(name, asset_kind) VALUES(?,?)",
                       (name, kind or media.infer_kind(path, storage, facts)))
        rev_id = db.execute(
            """INSERT OR IGNORE INTO revisions(asset,version,kind,manifest,origin,rights,context,tags,
               source_name,validation_command,validation_timeout,validation_env)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (name, version, storage, manifest, wanted["origin"], wanted["rights"], wanted["context"],
             wanted["tags"], path.name, check.get("command"), check.get("timeout"),
             encode(sorted(check.get("env") or [])) if check.get("command") else None)).lastrowid
        if db.execute("SELECT changes()").fetchone()[0]:
            db.execute("INSERT INTO media VALUES(?,?,?,?,?)",
                       (rev_id, encode(facts) if facts else None, status, still, still_status))
    report["added"].append({"asset": name, "version": version, "same_bytes_as": others})


def import_catalog(db, db_path, catalog_path, source, update):
    try:
        catalog = json.loads(Path(catalog_path).read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise LibraryError(f"The Catalog Was Not Found: {catalog_path}", "Check The Path To The JSON File.")
    except ValueError as problem:
        raise LibraryError(f"The Catalog Is Not Valid JSON: {problem}", "Export A Fresh Catalog, Or Correct The File.")
    source = Path(source).absolute()
    if not source.is_dir():
        raise LibraryError(f"The Files Folder Was Not Found: {source}", "Name The Folder That Holds The Catalog's Files.")
    if source.resolve() in (db_path, *db_path.parents):
        raise LibraryError("Keep The Library Database Outside The Files Folder.", "Move The Database Or The Files.")
    report = {"catalog": str(Path(catalog_path).absolute()), "files": str(source), "added": [], "unchanged": [],
              "duplicates": [], "missing": [], "skipped": [], "differing": [], "updated": [], "notes_added": 0}
    for name, kind, revisions, item in entries(catalog):
        for rev in revisions:
            import_one(db, db_path, name, kind, rev, source, update, report)
        with transaction(db, write=True):
            if db.execute("SELECT 1 FROM assets WHERE name=?", (name,)).fetchone() is None:
                continue
            added_here = any(a["asset"] == name for a in report["added"])
            had_before = db.execute("SELECT COUNT(*) FROM revisions WHERE asset=?", (name,)).fetchone()[0] > \
                sum(1 for a in report["added"] if a["asset"] == name)
            if added_here and not had_before and item.get("archived"):
                db.execute("UPDATE assets SET archived=? WHERE name=?", (str(item["archived"]), name))
            for entry in item.get("notes") or []:
                if not isinstance(entry, dict):
                    continue
                key = tuple(str(entry.get(k) or "") for k in ("kind", "text", "source", "date"))
                if key[0] not in ("opinion", "test", "rights", "caveat") or not all(key):
                    continue
                if db.execute("SELECT 1 FROM notes WHERE asset=? AND kind=? AND text=? AND source=? AND noted=?",
                              (name, *key)).fetchone() is None:
                    db.execute("INSERT INTO notes(asset,kind,text,source,noted) VALUES(?,?,?,?,?)", (name, *key))
                    report["notes_added"] += 1
    return report
