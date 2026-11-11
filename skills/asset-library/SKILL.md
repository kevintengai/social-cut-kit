---
name: asset-library
description: Store, Find, Restore, And Verify Exact Revisions Of Local Media And Reusable Editable Project Folders. Use For Tag Search, Source And Usage Rights, Or Tracking Which Version A Project Uses.
---

# Asset Library

Use [The Local Library CLI](scripts/library.py) With Python 3.9 Or Later. An Asset Name Identifies A Reusable Item. A Revision Identifies Its Exact File Bytes Or Folder Contents. A Project Pin Records The Revision Used At A Named Place In An Edit, Such As “Opening Card.”

## Capture And Find

1. Select A Local Disk For The SQLite File. Keep It Outside Any Folder Being Captured. Close Or Save The Source Project Before Capturing An Editable Folder. Include Media Dependencies In That Folder If The Editor Uses External References.
2. Supply The Actual Source, The Rights Evidence Or Restrictions, And The Reuse Context. Record Unknown Rights As “Unverified” When Appropriate. Check The Recorded Terms Before Reusing Assets. A Bundle Shares One Rights Record, So Include Member-Specific Restrictions Or A Rights Inventory Inside The Folder.
3. Search By Any Combination Of Free Text, Exact Tags, And A Context Substring. Multiple Tags Must All Match. Search Returns Historical Revisions As Well As The Latest. Inspect The Revision's Context And Rights Before Choosing Its Full Digest.

Run These Commands From This Skill Folder. The Example Stores This Skill's Own Text As A Small Test Fixture. Substitute An Actual Media File Or A Self-Contained Editable Project Folder During Production.

```text
python scripts/library.py --db demo.sqlite init
python scripts/library.py --db demo.sqlite add review-notes SKILL.md --origin "Bundled Skill Documentation" --rights "Local Workflow Test" --context "Editor Handoff" --tag handoff
python scripts/library.py --db demo.sqlite search --tag handoff --context editor
python scripts/library.py --db demo.sqlite history review-notes
```

For A Reusable Folder, Supply Its Path In The Same Position As The File. The Following Example Captures The Included Scripts Folder.

```text
python scripts/library.py --db demo.sqlite add tool-folder scripts --origin "Bundled Helper Folder" --rights "Local Workflow Test" --context "Editable Workflow Bundle" --tag bundle
```

## Pin And Restore

Use The Full `version` From The Chosen Revision Wherever The Example Shows `FULL_SHA256`. Asset Names, Projects, And Uses Match Case Exactly. Tags And Search Filters Ignore Case.

```text
python scripts/library.py --db demo.sqlite pin "School Promo" review-notes --use "Editor Notes" --version FULL_SHA256
python scripts/library.py --db demo.sqlite uses --project "School Promo"
python scripts/library.py --db demo.sqlite uses --asset review-notes
python scripts/library.py --db demo.sqlite get review-notes restored-notes.md --version FULL_SHA256
python scripts/library.py --db demo.sqlite check "School Promo" --use "Editor Notes" --path restored-notes.md
python scripts/library.py --db demo.sqlite check "School Promo"
```

After Editing A Source, Run `add` Again With The Same Asset Name. Older Pins Continue To Refer To Their Exact Bytes. To Replace A Pin, Supply The New Digest With `--version` And The Current Pinned Digest With `--replace`. If Another Writer Changed The Pin, Inspect `uses` Before Trying Again.

## Storage And Recovery

- Media Revisions Use SHA-256 Of The Original Bytes. Bundle Revisions Hash A Versioned Manifest Of File Digests, Directory Entries, And Relative Names. Empty Folders And Hidden Files Are Included. Timestamps, Permissions, And The Outer Folder Name Are Excluded. Repeated File Contents Share Storage Across Revisions And Bundles.
- Capture Requires Regular Files, Portable Names, And Directories. Resolve Symbolic Links, Junctions, Case-Colliding Names, And External Dependencies Before Capturing A Bundle. Restoring The Bytes Preserves Their Contents. Editor Relinking May Still Be Necessary For Absolute Media References.
- Imports And Pin Updates Commit In SQLite Transactions. An Identical Retry With Identical Metadata Returns The Same Revision. Conflicting Metadata Produces An Error So Source And Rights Records Remain Intact. Use A Separate Asset Name For The Same Bytes Under Different Terms.
- Restoring Requires An Existing Parent Folder. An Identical Destination Is Accepted On Retry. A Different Destination Is Protected. If A Process Stops During Restoration And Leaves An Incomplete Copy, Retry Into A Fresh Path. Use `check --path` To Compare A Working Copy With Its Exact Pin.
- Close Active Library Processes Before Copying The Database For Backup. File Contents, Folder Manifests, Metadata, And Pins All Travel In The Database. Store It On A Local Filesystem With SQLite Locking Support. A Busy Writer Waits Up To 30 Seconds Before Returning An Error.
