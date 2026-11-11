"""Exercise Local Posting Receipts Without Connecting To Any Platform."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "posting.py"
SPEC = importlib.util.spec_from_file_location("posting", SCRIPT)
posting = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(posting)


class PostingTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.command = [sys.executable, str(SCRIPT), "--ledger", str(self.root / "campaign.sqlite3")]
        (self.root / "fixture.bin").write_bytes(b"Synthetic Test Input")
        self.data = {"id": "qa-one", "account": "Synthetic Channel", "platform": "youtube",
                     "mode": "now", "visibility": "Public", "caption": "A Sample Caption",
                     "title": "Sample", "audience": "General Audience", "media": "fixture.bin"}

    def cli(self, *args, succeeds=True, dry=True):
        command = self.command + (["--dry-run"] if dry else []) + list(map(str, args))
        proc = subprocess.run(command, text=True, capture_output=True, check=False)
        if succeeds:
            self.assertEqual(proc.returncode, 0, proc.stderr)
            return json.loads(proc.stdout)
        self.assertNotEqual(proc.returncode, 0)
        return proc.stderr

    def save(self, name, data):
        path = self.root / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def prepare(self, succeeds=True):
        return self.cli("prepare", self.save("packet.json", self.data), succeeds=succeeds)

    def begin(self, *options, succeeds=True):
        return self.cli("begin", self.data["id"], "--authorization", "Synthetic Test", *options, succeeds=succeeds)

    def proof(self, state="published", **changes):
        proof = {"state": state, "account": self.data["account"], "source": "account-content",
                 "item": "item-01", "visibility": self.data["visibility"], "copy_sample": "Sample",
                 "media_detail": "The Opening Slate Shows The Sample Clip",
                 "observation": "Reopened The Matching Account Item And Checked Its Displayed State."}
        proof.update(changes)
        return proof

    def record(self, proof, succeeds=True):
        return self.cli("record", self.data["id"], self.save("proof.json", proof), succeeds=succeeds)

    def test_duplicate_prepare_begin_and_receipt(self):
        self.assertEqual(self.prepare()["run"], "simulation")
        self.assertEqual(len(self.prepare()["history"]), 1)
        self.begin()
        self.begin(succeeds=False)
        record = self.record(self.proof())
        self.assertEqual(record["state"], "published")
        self.assertEqual(self.record(self.proof()), record)
        self.begin(succeeds=False)
        self.assertEqual(self.cli("show", dry=False)["deliveries"], [])
        self.data["caption"] = "A Change After Publication"
        self.prepare(succeeds=False)

    def test_readback_proves_preexisting_item_without_submitting(self):
        self.prepare()
        self.assertEqual(self.record(self.proof())["state"], "published")
        self.begin(succeeds=False)

    def test_parallel_begins_only_one_claim(self):
        self.prepare()
        command = self.command + ["--dry-run", "begin", self.data["id"], "--authorization", "Synthetic Test"]
        workers = [subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
        for worker in workers:
            worker.communicate(timeout=20)
        self.assertEqual(sorted(worker.returncode for worker in workers), [0, 2])

    def test_ambiguous_attempt_and_new_id_cannot_retry(self):
        self.prepare()
        self.begin()
        self.record(self.proof("unknown", source="timeout"))
        self.begin(succeeds=False)
        self.data["id"] = "accidental-second-id"
        self.prepare()
        self.begin(succeeds=False)
        self.data["id"] = "qa-one"
        self.record(self.proof())
        self.data["id"] = "accidental-second-id"
        self.begin(succeeds=False)
        self.data["repeat_of"] = "qa-one"
        self.prepare()
        self.begin()

    def test_positive_rejection_and_reconciliation_before_retry(self):
        self.prepare()
        self.begin()
        proof = self.proof("rejected", source="terminal-response")
        self.record(proof, succeeds=False)
        proof["reconciliation"] = "Terminal Job Failure And Account Queue Checked."
        self.record(dict(proof, source="planner"), succeeds=False)
        self.record(proof)
        self.begin()
        self.assertEqual(self.record(proof)["state"], "rejected")

    def test_evidence_requires_observed_item_account_content_and_source(self):
        self.prepare()
        self.begin()
        for changes in ({"account": "Another Channel"}, {"source": "composer"},
                        {"item": ""}, {"visibility": "Private"}, {"copy_sample": "Missing Text"},
                        {"media_detail": "https://example.invalid/clip"}, {"observation": "https://example.invalid/clip"}):
            with self.subTest(changes=changes):
                self.record(self.proof(**changes), succeeds=False)
        self.record({"state": "published", "url": "https://example.invalid/clip"}, succeeds=False)
        self.assertEqual(self.cli("show", self.data["id"])["state"], "attempting")

    def test_schedule_readback_and_later_publication(self):
        self.data.update(mode="schedule", local="2099-10-08T13:30", zone="UTC")
        self.assertEqual(self.prepare()["packet"]["utc"], "2099-10-08T13:30:00+00:00")
        self.begin()
        proof = self.proof("scheduled", source="planner")
        for bad in ("2099-10-08T09:30", "2099-10-08T13:30+02:00"):
            self.record(dict(proof, scheduled_for=bad), succeeds=False)
        self.assertEqual(self.record(dict(proof, scheduled_for="2099-10-08T09:30-04:00"))["state"], "scheduled")
        self.begin(succeeds=False)
        self.assertEqual(self.record(self.proof())["state"], "published")

    def test_already_passed_slot(self):
        self.data.update(mode="schedule", local="2000-01-01T12:00", zone="UTC")
        self.prepare()
        self.begin(succeeds=False)

    def test_unresolved_scheduled_delivery_and_separate_slot(self):
        self.data.update(mode="schedule", local="2099-10-08T13:30", zone="UTC")
        self.prepare()
        self.begin()
        self.record(self.proof("scheduled", source="planner", scheduled_for="2099-10-08T13:30+00:00"))
        self.record(self.proof("unknown", source="planner", observation="The Job Reports An Unresolved Processing Delay."))
        self.begin(succeeds=False)
        self.data.update(id="qa-another-day", local="2099-10-09T13:30")
        self.prepare()
        self.begin()

    def test_draft_and_promotion_use_original_item(self):
        self.data["mode"] = "draft"
        self.prepare()
        self.begin()
        self.record(self.proof(), succeeds=False)
        self.record(self.proof("draft", source="drafts"))
        self.assertEqual(self.prepare()["state"], "draft")
        self.data.update(mode="now")
        self.prepare(succeeds=False)
        self.data["from_draft"] = "item-01"
        self.prepare()
        self.begin()
        self.assertEqual(self.record(self.proof())["state"], "published")

    def test_follow_up_reconciles_without_second_new_comment(self):
        self.data["follow_up"] = "Pin The Owner's Supplied Invitation."
        self.prepare()
        self.begin()
        self.begin("--follow-up", succeeds=False)
        self.record(self.proof())
        self.begin("--follow-up")
        self.record(self.proof("follow-up-unknown", source="timeout"))
        self.begin("--follow-up", succeeds=False)
        proof = self.proof("follow-up-verified", item="comment-02", parent_item="wrong-parent",
                           observation="Reopened The Item And Saw The Owner Pin On The Exact Comment.")
        self.record(proof, succeeds=False)
        proof["parent_item"] = "item-01"
        receipt = self.record(proof)
        self.assertEqual((receipt["state"], receipt["follow_up_state"]), ("published", "verified"))
        self.assertEqual(self.record(proof), receipt)

    def test_media_or_cover_changed_after_preparation(self):
        self.data["cover_file"] = "cover.bin"
        cover = self.root / "cover.bin"
        cover.write_bytes(b"One")
        self.prepare()
        cover.write_bytes(b"Two")
        self.begin(succeeds=False)
        self.prepare()
        (self.root / "fixture.bin").write_bytes(b"Different")
        self.begin(succeeds=False)

    def test_zone_fold_gap_and_offset_mismatch(self):
        try:
            ZoneInfo("America/New_York")
        except ZoneInfoNotFoundError:
            self.skipTest("Install tzdata To Exercise Named Zone Transitions.")
        convert = lambda time: posting.utc_time(time, "America/New_York")
        self.assertEqual(convert("2024-11-03T01:30-04:00"), "2024-11-03T05:30:00+00:00")
        self.assertEqual(convert("2024-11-03T01:30-05:00"), "2024-11-03T06:30:00+00:00")
        self.assertEqual(convert("2024-06-01T12:00"), "2024-06-01T16:00:00+00:00")
        for invalid in ("2024-03-10T02:30", "2024-11-03T01:30", "2024-06-01T12:00-05:00"):
            with self.assertRaises(ValueError):
                convert(invalid)

    def test_all_destination_types_and_captionless_asset(self):
        for platform in posting.PLATFORMS:
            with self.subTest(platform=platform):
                self.data.update(id=platform, platform=platform)
                self.prepare()
        self.data.update(id="bare-asset", caption="")
        del self.data["title"]
        self.prepare()
        self.begin()
        self.record(self.proof(copy_sample=""))


if __name__ == "__main__":
    unittest.main()
