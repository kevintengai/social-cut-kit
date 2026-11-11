"""Local Versioned Asset Library For Footage, Images, Sound, Code, 3D Sets, And The Cuts That Used Them."""

import argparse
import contextlib
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import library_cuts as cuts
import library_exchange as exchange
import library_media as media
import library_records as records
import library_store as store
from library_store import LibraryError, clean, digest_arg


def seconds(value):
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Enter A Number Of Seconds")
    if number < 0 or number != number:
        raise argparse.ArgumentTypeError("Enter A Number Of Seconds, Zero Or More")
    return number


def positive(value):
    number = seconds(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("Enter A Number Of Seconds Above Zero")
    return number


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--db", type=Path, help=(
        "Local SQLite File. When Omitted, The Tool Reads " + store.ENV_VARIABLE
        + ", Then The Library Line In ~/.social-cut-kit/asset-library.md"))
    sub = root.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="Create Or Open The Library")

    register = sub.add_parser("add", help="Capture A File Or Folder As A Revision")
    register.add_argument("asset", type=clean)
    register.add_argument("source", type=Path)
    for field in ("origin", "rights", "context"):
        register.add_argument("--" + field, type=clean, required=True)
    register.add_argument("--tag", action="append", type=clean, default=[])
    register.add_argument("--kind", choices=media.KINDS, help="Asset Kind. Inferred From The File Type When Omitted")
    register.add_argument("--validate", type=clean, metavar="COMMAND",
                          help="Folder Revisions Only. A Command That Proves The Bundle Still Works")
    register.add_argument("--validate-timeout", type=positive, default=records.DEFAULT_TIMEOUT, metavar="SECONDS")
    register.add_argument("--validate-env", action="append", type=clean, default=[], metavar="NAME",
                          help="An Extra Environment Variable Name To Pass To The Validation Command")
    register.add_argument("--validate-later", action="store_true",
                          help="Store The Validation Command Without Running It Now")

    find = sub.add_parser("search", help="Find Matching Revisions")
    find.add_argument("term", nargs="?", default="")
    find.add_argument("--tag", action="append", type=clean, default=[])
    find.add_argument("--context", default="")
    find.add_argument("--kind", choices=media.KINDS)
    find.add_argument("--min-duration", type=seconds, metavar="SECONDS")
    find.add_argument("--max-duration", type=seconds, metavar="SECONDS")
    find.add_argument("--duplicates", action="store_true", help="Include Every Asset That Holds The Same Bytes")
    find.add_argument("--archived", action="store_true", help="Include Archived Assets")

    past = sub.add_parser("history", help="List Asset Revisions")
    past.add_argument("asset", type=clean)

    full = sub.add_parser("show", help="Print An Asset's Full Record")
    full.add_argument("asset", type=clean)

    retype = sub.add_parser("kind", help="Change An Asset's Kind")
    retype.add_argument("asset", type=clean)
    retype.add_argument("kind", choices=media.KINDS)

    remark = sub.add_parser("note", help="Append A Dated Note To An Asset")
    remark.add_argument("asset", type=clean)
    remark.add_argument("--kind", choices=records.NOTE_KINDS, required=True)
    remark.add_argument("--text", type=clean, required=True)
    remark.add_argument("--source", type=clean, required=True, help="Who Said It Or Where It Was Recorded")
    remark.add_argument("--date", type=clean, help="YYYY-MM-DD. Defaults To Today")

    shelve = sub.add_parser("archive", help="Hide An Asset From Normal Search")
    shelve.add_argument("asset", type=clean)
    shelve.add_argument("--undo", action="store_true", help="Return The Asset To Normal Search")

    link = sub.add_parser("pin", help="Record An Exact Revision For A Project Use")
    link.add_argument("project", type=clean)
    link.add_argument("asset", type=clean)
    link.add_argument("--use", type=clean, required=True)
    link.add_argument("--version", type=digest_arg, required=True)
    link.add_argument("--replace", type=digest_arg, help="Expected Previous Digest")
    link.add_argument("--cut", type=clean, help="Cut Label, Such As v3")

    usage = sub.add_parser("uses", help="List Where Revisions Are Used")
    usage.add_argument("--project", type=clean)
    usage.add_argument("--asset", type=clean)
    usage.add_argument("--cut", type=clean)

    verify = sub.add_parser("check", help="Verify Stored Pins, A Local Copy, Or A Cut Against Its Declaration")
    verify.add_argument("project", type=clean)
    verify.add_argument("--asset", type=clean)
    verify.add_argument("--use", type=clean)
    verify.add_argument("--cut", type=clean)
    verify.add_argument("--path", type=Path)
    verify.add_argument("--declaration", type=Path, help="Cut Declaration JSON To Verify Without Writing")
    verify.add_argument("--scan", type=Path, metavar="FOLDER",
                        help="With --declaration, List Library Assets In This Project Folder That Are Not Declared")

    fetch = sub.add_parser("get", help="Restore A File Or Folder")
    fetch.add_argument("asset", type=clean)
    fetch.add_argument("destination", type=Path)
    fetch.add_argument("--version", type=digest_arg, required=True)

    still = sub.add_parser("preview", help="Write An Asset's Stored JPEG Preview Still")
    still.add_argument("asset", type=clean)
    still.add_argument("destination", type=Path)
    still.add_argument("--version", type=digest_arg, help="Defaults To The Latest Revision")

    record = sub.add_parser("declare", help="Record Every Use In A Cut Declaration, Or None")
    record.add_argument("declaration", type=Path)

    ship = sub.add_parser("deliver", help="Check A Cut And Store Its Delivery Record")
    ship.add_argument("declaration", type=Path)
    ship.add_argument("--scan", type=Path, metavar="FOLDER")
    ship.add_argument("--date", type=clean, help="YYYY-MM-DD. Defaults To Today")

    shipped = sub.add_parser("deliveries", help="List Delivery Records")
    shipped.add_argument("--project", type=clean)

    prove = sub.add_parser("validate", help="Run A Folder Revision's Validation Command Again")
    prove.add_argument("asset", type=clean)
    prove.add_argument("--version", type=digest_arg, help="Defaults To The Latest Revision")
    prove.add_argument("--env", action="append", type=clean, default=[], metavar="NAME")
    prove.add_argument("--timeout", type=positive, metavar="SECONDS")

    out = sub.add_parser("export", help="Write catalog.json And index.html Into A Folder")
    out.add_argument("folder", type=Path)
    out.add_argument("--with-files", action="store_true", help="Also Write Every Revision's File Bytes")

    back = sub.add_parser("import", help="Add Assets From A Catalog And A Folder Of Files")
    back.add_argument("catalog", type=Path)
    back.add_argument("--files", type=Path, required=True, metavar="FOLDER")
    back.add_argument("--update", action="append", type=clean, default=[], metavar="NAME",
                      help="Overwrite Differing Fields For This Asset Name")

    sub.add_parser("stats", help="Count Assets, Revisions, Pins, Deliveries, And Stored Bytes")
    return root


def run(db, args, path, found_by, upgrade):
    command = args.command
    if command == "init":
        return {"database": str(path), "schema_version": store.SCHEMA_VERSION, "found_by": found_by, **upgrade}
    if command == "add":
        return records.add(db, args, path)
    if command == "search":
        return records.search(db, args)
    if command == "history":
        return records.history(db, args.asset)
    if command == "show":
        return records.show(db, args.asset)
    if command == "kind":
        return records.set_kind(db, args.asset, args.kind)
    if command == "note":
        return records.note(db, args)
    if command == "archive":
        return records.archive(db, args.asset, args.undo)
    if command == "pin":
        return records.pin(db, args)
    if command == "uses":
        return records.uses(db, args.project, args.asset, args.cut)
    if command == "check":
        if args.declaration is None:
            if args.scan is not None:
                raise LibraryError("--scan Needs --declaration.", "Name The Cut Declaration To Compare Against.")
            return records.check(db, args)
        if args.asset or args.use or args.cut or args.path:
            raise LibraryError("--declaration Checks A Whole Cut.", "Remove --asset, --use, --cut, And --path.")
        return cuts.check(db, args.project, args.declaration, args.scan)
    if command == "get":
        with store.transaction(db):
            return store.restore(db, args.asset, args.version, args.destination)
    if command == "preview":
        return records.write_preview(db, args.asset, args.version, args.destination)
    if command == "declare":
        return cuts.declare(db, args.declaration)
    if command == "deliver":
        return cuts.deliver(db, args.declaration, args.scan, args.date)
    if command == "deliveries":
        return cuts.deliveries(db, args.project)
    if command == "validate":
        return records.validate(db, args.asset, args.version, args.env, args.timeout)
    if command == "export":
        return exchange.export(db, args.folder, args.with_files)
    if command == "import":
        return exchange.import_catalog(db, path, args.catalog, args.files, set(args.update))
    return records.stats(db, path)


def fail(message, hint):
    print(f"Error: {message}", file=sys.stderr)
    print(f"Hint: {hint}", file=sys.stderr)
    return 1


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        path, found_by = store.locate(args.db)
        with contextlib.closing(store.connect(path, args.command == "init")) as db:
            upgrade = store.ensure_schema(db, path, args.command == "init")
            if upgrade and args.command != "init":
                print(f"Upgraded The Library From Schema {upgrade['upgraded_from']}. "
                      f"A Backup Was Written To {upgrade['backup']}.", file=sys.stderr)
            result = run(db, args, path, found_by, upgrade)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except LibraryError as error:
        report = getattr(error, "report", None)
        if report is not None:
            print(json.dumps(report, ensure_ascii=True, indent=2))
        return fail(str(error), error.hint)
    except sqlite3.Error as error:
        return fail(f"The Library Database Reported: {error}",
                    "Close Other Library Processes And Try Again. If It Persists, Restore A Backup Copy.")
    except (OSError, RecursionError) as error:
        return fail(str(error), "Check That The Named Paths Exist And Can Be Read Or Written.")


if __name__ == "__main__":
    sys.exit(main())
