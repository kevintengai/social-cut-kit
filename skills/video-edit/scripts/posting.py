"""Track Authorized Posting Attempts And Operator Readbacks In A Local SQLite Ledger."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


PLATFORMS = ("instagram", "facebook", "tiktok", "youtube", "x", "linkedin")
MODES = {"now": "published", "schedule": "scheduled", "draft": "draft"}
READBACK = {
    "published": {"account-content", "connector-readback"},
    "scheduled": {"planner", "connector-readback"},
    "draft": {"drafts", "connector-readback"},
    "follow-up-verified": {"account-content", "connector-readback"},
}


def fail(message):
    raise ValueError(message)


def load_object(path):
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        fail("Expected A JSON Object.")
    return value


def required(data, key):
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        fail(f"Supply A Nonempty String For {key}.")
    return value


def note(data, key):
    value = required(data, key)
    if re.fullmatch(r"https?://\S+", value.strip(), flags=re.IGNORECASE):
        fail(f"Describe The Observation In {key}. A Link Alone Cannot Verify It.")
    return value


def stamp():
    return datetime.now(timezone.utc).isoformat()


def utc_time(local, zone_name):
    try:
        wall = datetime.fromisoformat(local)
    except ValueError:
        fail("Enter An ISO Local Date And Time, Such As 2030-10-08T09:30.")
    if "T" not in local and " " not in local:
        fail("Include Both The Local Date And The Clock Time.")
    if zone_name == "UTC":
        zone = timezone.utc
    else:
        try:
            zone = ZoneInfo(zone_name)
        except ZoneInfoNotFoundError:
            fail(f"Unknown Or Unavailable Time Zone {zone_name}. Check The IANA Name And Install tzdata If Needed.")
    candidates = set()
    naive = wall.replace(tzinfo=None)
    for fold in (0, 1):
        candidate = naive.replace(tzinfo=zone, fold=fold).astimezone(timezone.utc)
        actual = candidate.astimezone(zone)
        if actual.replace(tzinfo=None) == naive and (wall.tzinfo is None or wall.utcoffset() == actual.utcoffset()):
            candidates.add(candidate)
    if not candidates:
        fail("This Wall Time Does Not Exist Or Its Offset Conflicts With The Selected Zone.")
    if len(candidates) != 1:
        fail("This Clock Time Occurs Twice. Include The Intended UTC Offset In The Local Time.")
    return candidates.pop().isoformat()


def fingerprint(path):
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
            size += len(block)
    if not size:
        fail(f"Empty File: {path}")
    return digest.hexdigest()


def packet_from(path):
    data = load_object(path)
    fields = {
        "id", "platform", "account", "mode", "media", "caption", "title", "visibility",
        "audience", "cover_file", "cover_frame", "follow_up", "local", "zone", "notes", "from_draft", "repeat_of",
    }
    unknown = sorted(set(data) - fields)
    if unknown:
        fail("Unrecognized Packet Field(s): " + ", ".join(unknown))
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", required(data, "id")):
        fail("Use A Short ID With Letters, Numbers, Periods, Hyphens, Or Underscores.")
    if data.get("platform") not in PLATFORMS or data.get("mode") not in tuple(MODES):
        fail("Use A Supported Platform And Mode.")
    required(data, "account")
    required(data, "visibility")
    if not isinstance(data.get("caption"), str):
        fail("Supply The Exact Caption String, Including An Empty String For A Captionless Post.")
    for key in ("title", "audience", "follow_up", "notes", "from_draft", "repeat_of"):
        if key in data:
            required(data, key)
    if data["platform"] == "youtube":
        required(data, "title")
        required(data, "audience")
    if "cover_file" in data and "cover_frame" in data:
        fail("Choose One Cover File Or One Frame.")
    if "cover_frame" in data:
        required(data, "cover_frame")
    for key in ("media", "cover_file") if "cover_file" in data else ("media",):
        file = (Path(path).resolve().parent / required(data, key)).resolve(strict=True)
        data[key] = str(file)
        data[key + "_sha256"] = fingerprint(file)
    if data["mode"] == "schedule":
        data["utc"] = utc_time(required(data, "local"), required(data, "zone"))
    elif "local" in data or "zone" in data:
        fail("A Scheduled Time Requires Schedule Mode.")
    return data


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def initialize(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS deliveries (
            realm TEXT NOT NULL, id TEXT NOT NULL, packet TEXT NOT NULL,
            state TEXT NOT NULL, follow_state TEXT NOT NULL, PRIMARY KEY (realm, id)
        );
        CREATE TABLE IF NOT EXISTS events (
            seq INTEGER PRIMARY KEY, realm TEXT NOT NULL, id TEXT NOT NULL,
            instant TEXT NOT NULL, kind TEXT NOT NULL, detail TEXT NOT NULL
        );
    """)


def event(db, realm, key, kind, detail):
    db.execute("INSERT INTO events(realm,id,instant,kind,detail) VALUES(?,?,?,?,?)",
               (realm, key, stamp(), kind, canonical(detail)))


def get_row(db, realm, key):
    row = db.execute("SELECT * FROM deliveries WHERE realm=? AND id=?", (realm, key)).fetchone()
    if row is None:
        fail("No Delivery With This ID In The Selected Ledger And Run Mode.")
    return row


def last_verified_item(db, realm, key, state):
    for row in db.execute("SELECT detail FROM events WHERE realm=? AND id=? AND kind='receipt' ORDER BY seq DESC", (realm, key)):
        proof = json.loads(row["detail"])
        if proof["state"] == state:
            return proof["item"]
    return None


def prepare(db, realm, packet):
    key = packet["id"]
    body = canonical(packet)
    row = db.execute("SELECT * FROM deliveries WHERE realm=? AND id=?", (realm, key)).fetchone()
    if row and row["packet"] == body:
        return
    draft = last_verified_item(db, realm, key, "draft")
    if packet.get("from_draft") != draft:
        fail("Use The Existing Delivery ID And Its Verified Draft Item In from_draft.")
    if row:
        prior = json.loads(row["packet"])
        promote = row["state"] == "draft" and packet["mode"] in {"now", "schedule"} and draft
        if row["state"] not in {"prepared", "rejected"} and not promote:
            fail("The Existing Delivery Has An Attempt Or Receipt. Reconcile It Before Changing The Plan.")
        if (prior["platform"], prior["account"]) != (packet["platform"], packet["account"]):
            fail("This ID Already Belongs To A Different Destination.")
    follow_state = "pending" if packet.get("follow_up") else "none"
    db.execute("INSERT OR REPLACE INTO deliveries VALUES(?,?,?,?,?)", (realm, key, body, "prepared", follow_state))
    event(db, realm, key, "prepared", packet)


def set_state(db, realm, key, state, follow=False):
    column = "follow_state" if follow else "state"
    db.execute(f"UPDATE deliveries SET {column}=? WHERE realm=? AND id=?", (state, realm, key))


def check_other_attempts(db, realm, key, packet):
    rows = db.execute("SELECT id,packet,state FROM deliveries WHERE realm=? AND id<>? AND state IN "
                      "('attempting','unknown','scheduled','draft','published') ORDER BY rowid DESC", (realm, key))
    fields = ("platform", "media_sha256", "title", "caption")
    previous_publication = None
    for row in rows:
        other = json.loads(row["packet"])
        if other["account"] != packet["account"] or any(other.get(f) != packet.get(f) for f in fields):
            continue
        if packet["mode"] == other["mode"] == "schedule" and packet["utc"] != other["utc"]:
            continue
        same_slot = packet.get("utc") == other.get("utc") and packet["mode"] == other["mode"]
        if row["state"] in {"attempting", "unknown"} or (same_slot and row["state"] in {"scheduled", "draft"}):
            fail(f"An Equivalent Delivery Exists Under {row['id']}. Reconcile That Item Before Acting.")
        if same_slot and row["state"] == "published" and previous_publication is None:
            previous_publication = row["id"]
    if previous_publication and packet.get("repeat_of") != previous_publication:
        fail(f"This Post Was Already Recorded Under {previous_publication}. An Intended New Repeat Can Reference It In repeat_of.")


def begin(db, realm, key, authority, follow):
    row = get_row(db, realm, key)
    packet = json.loads(row["packet"])
    if not authority.strip():
        fail("Record The Existing Authorization Reference.")
    if follow:
        if row["state"] != "published" or row["follow_state"] not in {"pending", "rejected"}:
            fail("Check The Published Item And Its Existing Follow-Up Receipt Before Acting.")
    else:
        if row["state"] not in {"prepared", "rejected"}:
            fail("A Prior Attempt Or Receipt Exists. Reconcile Using Read-Only Checks.")
        check_other_attempts(db, realm, key, packet)
        for field in ("media", "cover_file"):
            if field in packet and fingerprint(Path(packet[field])) != packet[field + "_sha256"]:
                fail(f"The {field} Changed. Review The New Asset And Prepare Its Packet Before Acting.")
        if packet["mode"] == "schedule" and datetime.fromisoformat(packet["utc"]) <= datetime.now(timezone.utc):
            fail("The Scheduled Time Has Passed. Reconcile The Requested Slot Before Submitting.")
    set_state(db, realm, key, "attempting", follow)
    event(db, realm, key, "begin-follow-up" if follow else "begin", {"authorization": authority})


def record(db, realm, key, proof):
    row = get_row(db, realm, key)
    packet = json.loads(row["packet"])
    state = required(proof, "state")
    if proof.get("account") != packet["account"]:
        fail("The Observed Account Must Match The Packet Exactly.")
    # Replaying An Identical Receipt Keeps Both The Current State And History Intact.
    follow = state.startswith("follow-up-")
    start_kind = "begin-follow-up" if follow else "begin"
    if db.execute("SELECT 1 FROM events WHERE realm=? AND id=? AND kind='receipt' AND detail=? AND seq > "
                  "(SELECT COALESCE(MAX(seq),0) FROM events WHERE realm=? AND id=? AND kind=?)",
                  (realm, key, canonical(proof), realm, key, start_kind)).fetchone():
        return
    prior = row["follow_state"] if follow else row["state"]
    if follow and (row["state"] != "published" or prior == "none"):
        fail("This Delivery Requires A Published Item And A Requested Follow-Up.")
    source = required(proof, "source")
    note(proof, "observation")
    if state in READBACK:
        if source not in READBACK[state]:
            fail("Read Back The Matching Item From The Account Or A Fresh Connector Query.")
        required(proof, "item")
        if follow:
            if prior not in {"pending", "attempting", "unknown", "rejected"}:
                fail("The Follow-Up Already Has A Final Receipt.")
            if required(proof, "parent_item") != last_verified_item(db, realm, key, "published"):
                fail("The Follow-Up Must Belong To The Verified Published Item.")
            outcome = "verified"
        else:
            expected = MODES[packet["mode"]]
            if state != expected and not (packet["mode"] == "schedule" and state == "published"):
                fail("The Observed State Conflicts With The Authorized Mode. Record The Discrepancy As Unknown.")
            if prior not in {"prepared", "attempting", "unknown", "rejected"} and not (prior == "scheduled" and state == "published"):
                fail("This Delivery Already Has A Final Receipt.")
            note(proof, "media_detail")
            if proof.get("visibility") != packet["visibility"]:
                fail("The Observed Visibility Must Match The Packet.")
            sample = proof.get("copy_sample")
            copy = [packet["caption"], packet.get("title", "")]
            if not isinstance(sample, str) or (any(copy) and not sample.strip()) or not any(sample in value for value in copy):
                fail("Record An Exact Excerpt From The Displayed Caption Or Title.")
            if state == "scheduled":
                observed = datetime.fromisoformat(required(proof, "scheduled_for"))
                if observed.tzinfo is None or observed.astimezone(timezone.utc).isoformat() != packet["utc"]:
                    fail("The Scheduled Readback Must Include An Offset And Match The Intended Instant.")
            outcome = state
    elif state in {"unknown", "follow-up-unknown", "rejected", "follow-up-rejected"}:
        if prior not in {"attempting", "unknown", "scheduled"}:
            fail("Only An Outstanding Attempt Can Receive This Receipt.")
        outcome = "rejected" if state.endswith("rejected") else "unknown"
        if outcome == "rejected":
            if source != "terminal-response":
                fail("Reopening An Attempt Requires An Authoritative Terminal Rejection.")
            note(proof, "reconciliation")
    else:
        fail("Unknown Receipt State.")
    set_state(db, realm, key, outcome, follow)
    event(db, realm, key, "receipt", proof)


def report(db, realm, key):
    if key is None:
        rows = db.execute("SELECT id,state,follow_state FROM deliveries WHERE realm=? ORDER BY id", (realm,))
        return {"run": realm, "deliveries": [dict(row) for row in rows]}
    row = get_row(db, realm, key)
    events = db.execute("SELECT instant,kind,detail FROM events WHERE realm=? AND id=? ORDER BY seq", (realm, key))
    return {"run": realm, "state": row["state"], "follow_up_state": row["follow_state"],
            "packet": json.loads(row["packet"]),
            "history": [{"at": entry["instant"], "event": entry["kind"], "detail": json.loads(entry["detail"])} for entry in events]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True, help="One Shared Local Campaign SQLite File")
    parser.add_argument("--dry-run", action="store_true", help="Use Isolated Simulated Records")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("prepare", help="Stage One Destination Packet").add_argument("packet", type=Path)
    commands.add_parser("show", help="Read Campaign Status Or A Full Delivery Receipt").add_argument("id", nargs="?")
    start = commands.add_parser("begin", help="Claim One Authorized Attempt Before Using The Platform")
    start.add_argument("id")
    start.add_argument("--authorization", required=True)
    start.add_argument("--follow-up", action="store_true")
    receipt = commands.add_parser("record", help="Save Observed Evidence From The Platform")
    receipt.add_argument("id")
    receipt.add_argument("proof", type=Path)
    args = parser.parse_args(argv)
    realm = "simulation" if args.dry_run else "operator"
    if args.command != "prepare" and not args.ledger.is_file():
        fail("The Requested Ledger File Does Not Exist.")
    packet = packet_from(args.packet) if args.command == "prepare" else None
    proof = load_object(args.proof) if args.command == "record" else None
    db = sqlite3.connect(args.ledger, timeout=15)
    db.row_factory = sqlite3.Row
    try:
        initialize(db)
        key = packet["id"] if packet else args.id
        with db:
            if args.command != "show":
                db.execute("BEGIN IMMEDIATE")
            if args.command == "prepare":
                prepare(db, realm, packet)
            elif args.command == "begin":
                begin(db, realm, key, args.authorization, args.follow_up)
            elif args.command == "record":
                record(db, realm, key, proof)
            result = report(db, realm, key)
        print(json.dumps(result, ensure_ascii=True, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, sqlite3.Error) as error:
        print(str(error), file=sys.stderr)
        sys.exit(2)
