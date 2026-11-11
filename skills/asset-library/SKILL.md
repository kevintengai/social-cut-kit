---
name: asset-library
description: Keep One Local Record Of Footage, Stills, Music, Effects, Voice Recordings, Characters, Animation Code, And 3D Sets, And Of The Exact Version Each Delivered Cut Used. Use To Search Before Sourcing Or Building, Add A Candidate With Its Source And Rights, Register And Validate A Reusable Folder, Pin Versions, Record And Check A Cut At Delivery, Or Keep Dated Notes.
---

# Asset Library

Use [The Local Library CLI](scripts/library.py) With Python 3.9 Or Later. An Asset Name Identifies A Reusable Item. A Revision Identifies Its Exact File Bytes Or Folder Contents By SHA-256. A Pin Records The Revision Used At A Named Place In A Project, Such As “Opening Card,” And Can Carry A Cut Label Such As `v3`. Every Command Prints JSON. A Failure Exits Non-Zero And Prints An `Error:` Line And A `Hint:` Line.

The Library Is A Record. The Video Ships Regardless Of Catalog State. A Missing Entry Or A Failed Check Is Something To Report And Fix In The Record. It Never Blocks A Delivery The Owner Approved.

## Set Up

1. If `~/.social-cut-kit/asset-library.md` Exists, Read It First. It Names The Library And Holds The User's Own Reuse Rules, Such As Which Music May Repeat Or Which Clients Keep Separate Assets. Follow Those Rules Over Any Default In This Guide.
2. The Tool Finds The Library In This Order: The `--db` Option, The `SOCIAL_CUT_KIT_LIBRARY` Environment Variable, Then A Line Of The Form ``Library: `PATH` `` In That Defaults File. With None Of These, It Stops With An Error That Lists All Three.
3. Keep The SQLite File On A Local Disk, Outside Any Folder You Capture. Install FFmpeg And FFprobe On PATH To Record Media Facts And Preview Stills. Without Them Every Command Still Works, And The Output Says Which Facts Are Empty And Why.

Run The Examples From This Skill Folder. They Use The Included [Demo Project](examples/demo-project/cut.json), Which Holds One Sound, One Still, And A Cut Declaration. Delete `demo.sqlite` And The Files The Examples Write When You Finish.

```text
python scripts/library.py --db demo.sqlite init
python scripts/library.py --db demo.sqlite stats
```

Opening A Library Made By An Earlier Edition Upgrades It In Place. The Tool First Writes A Timestamped Backup Beside It And Names That File On The Error Stream. [Records Reference](RECORDS.md#upgrades-and-backups)

## Search Before Sourcing Or Building

Search The Library Before You License, Generate, Record, Or Build Anything. Combine Free Text, Exact Tags, A Context Substring, A Kind, And A Duration Range In Seconds. Multiple Tags Must All Match. Read The Rights And Notes Of A Result Before You Choose It.

```text
python scripts/library.py --db demo.sqlite search --kind sfx --max-duration 5
python scripts/library.py --db demo.sqlite search card --tag title --context promo
```

On A New Library These Return An Empty List. Run Them Again After The Examples In The Next Section.

- The Kinds Are `footage`, `image`, `music`, `sfx`, `voice`, `character`, `code`, `model`, And `other`. In Output, `asset_kind` Holds This Kind, And `kind` Says Whether The Revision Is A `file` Or A `bundle`.
- Search Returns Historical Revisions As Well As The Latest. A Duration Filter Leaves Out Revisions Without A Measured Duration.
- When Several Asset Names Hold The Same Bytes, Search Shows The Earliest One And Lists The Others In `duplicates`. Add `--duplicates` To See Each Of Them. Archived Assets Stay Hidden Unless You Add `--archived`.
- `show` Prints One Asset's Full Record: Revisions, Media Facts, Rights, Notes, Validation Results, And Every Project, Cut, And Use It Appears In.

## Add When Something Becomes A Candidate

Add An Item As Soon As It Becomes A Candidate For A Cut, Not After Delivery. Supply The Actual Source, The Rights Evidence Or Restrictions, And The Reuse Context. Record Unknown Rights As “Unverified.” Give The Kind With `--kind` When The File Type Does Not Settle It. Audio Is Inferred As `sfx` Under Fifteen Seconds And `music` Otherwise, So Name `voice` Yourself.

```text
python scripts/library.py --db demo.sqlite add title-card examples/demo-project/media/title-card.png --origin "Drawn For The School Promo" --rights "Owned By The School" --context "Promo Opening" --tag title --tag promo
python scripts/library.py --db demo.sqlite add chime examples/demo-project/media/chime.wav --origin "Synthesised For The School Promo" --rights "Owned By The School" --context "Promo Reveal Cue" --kind sfx --tag reveal
python scripts/library.py --db demo.sqlite history chime
python scripts/library.py --db demo.sqlite show title-card
python scripts/library.py --db demo.sqlite preview title-card title-card-preview.jpg
```

- For A Media File, `media` Holds Duration, Picture Size, Frame Rate, Audio Channels, And Sample Rate. Audio Files Also Get `peak_db`. `media_status` Says What Was Measured, Or Why Nothing Was.
- Video And Image Assets Keep One JPEG Preview Still, With Its Longest Side At Most 560 Pixels. `preview` Writes It To A `.jpg` Path. The Library Never Writes Video.
- Adding Bytes That Another Asset Name Already Holds Still Works. The Output Lists Those Names In `same_bytes_as`. Use A Separate Name Only When The Same Bytes Carry Different Terms.
- After Editing A Source, Run `add` Again With The Same Asset Name To Create A New Revision. Older Pins Keep Their Exact Bytes. Change A Wrong Kind With `kind ASSET KIND`.

## Register A Bundle Before A Second Project Borrows It

A Bundle Is A Self-Contained Folder: Animation Code, A Character Rig, A 3D Set, Or An Editable Project With Its Media. Register It At The Moment A Second Project Is About To Reuse It. Close Or Save The Source Project First, And Put Member-Specific Rights In A File Inside The Folder.

```text
python scripts/library.py --db demo.sqlite add tool-folder scripts --origin "Bundled Helper Folder" --rights "Local Workflow Test" --context "Editable Workflow Bundle" --kind code --validate "python -B library.py --help" --validate-timeout 60
python scripts/library.py --db demo.sqlite validate tool-folder
```

- `--validate` Stores A Command On The Folder Revision And Runs It Once. `validate` Runs It Again. Each Result Records `passed`, `failed`, Or `not_run`, The Exit Code, The Tail Of The Output, And The Seconds Taken. `show` Displays The Latest Result.
- The Command Runs Inside A Throwaway Copy Made From The Stored Snapshot, Never In Your Working Folder. Its Environment Holds Only What A Process Needs To Start, Plus Any Variable You Name With `--validate-env NAME` Or `--env NAME`. [Records Reference](RECORDS.md#bundle-validation)
- This Executes A Command Supplied By Whoever Registered The Bundle. Only Validate Bundles You Trust. Read The Stored Command With `show` Before You Run It On A Library Someone Else Filled.
- A Pass Proves The Command Exited Successfully. It Does Not Prove The Result Looks Right. Look At The Output Yourself Before You Rely On It.

## Pin And Restore

Use The Full `version` From The Chosen Revision Wherever An Example Shows `FULL_SHA256`. Asset Names, Projects, Cuts, And Uses Match Case Exactly. Tags And Search Filters Ignore Case.

```text
python scripts/library.py --db demo.sqlite pin "School Promo" chime --use "Button Hit" --version FULL_SHA256 --cut v2
python scripts/library.py --db demo.sqlite uses --project "School Promo"
python scripts/library.py --db demo.sqlite get chime restored-chime.wav --version FULL_SHA256
python scripts/library.py --db demo.sqlite check "School Promo" --cut v2 --use "Button Hit" --path restored-chime.wav
```

To Replace A Pin, Supply The New Digest With `--version` And The Current Pinned Digest With `--replace`. If Another Writer Changed The Pin, Inspect `uses` Before Trying Again. A Pin Without `--cut` Is A Working Pin For The Project As A Whole.

## Record The Cut At Delivery

Record Uses From The Final Cue Sheet After The Last Swap, Not From The Plan. Write A Cut Declaration Beside The Project That Lists What The Delivered Cut Used. Each Entry Names The Asset, Its Use, And Either The Exact `version` Or A `path` Relative To The Declaration. [Declaration Fields](RECORDS.md#cut-declaration)

```text
python scripts/library.py --db demo.sqlite declare examples/demo-project/cut.json
python scripts/library.py --db demo.sqlite check "School Promo" --declaration examples/demo-project/cut.json --scan examples/demo-project
python scripts/library.py --db demo.sqlite deliver examples/demo-project/cut.json --scan examples/demo-project
python scripts/library.py --db demo.sqlite deliveries --project "School Promo"
```

- `declare` Records Every Entry Or None. A `path` Is Hashed And Must Match A Stored Revision Of That Asset. Otherwise The Error Says To Add It First. Declaring The Same Cut Again Replaces Its Uses, And Uses Left Out Are Retired, Not Deleted.
- `deliver` Runs The Declaration Check And, Only When It Passes, Stores A Delivery Record With The Date And A Snapshot Of The Declaration. A Delivered Cut Is Closed. Record Later Changes Under A New Cut Label.
- If The Check Fails At Delivery Time, Ship The Approved Video Anyway, Tell The Owner The Catalog Was Not Updated, And Fix The Record Afterwards.

## Check The Record

`check PROJECT` Verifies The Stored Bytes Behind Every Pin, And `--path` Compares One Working Copy With Its Pin. `check PROJECT --declaration FILE` Verifies A Cut And Writes Nothing: Each Entry In The Declaration Must Match A Recorded Use With An Identical Version, And Nothing Points At Missing Data. With `--scan FOLDER` It Also Lists, For Information Only, Library Assets Found In The Project Folder By Identical Bytes Or By Name In Text Files That The Declaration Leaves Out. Treat That List As Questions To Ask, Not As Errors. [Scan Limits](RECORDS.md#project-scan)

## Notes

Append A Dated Note When You Learn Something About An Asset That The Next Project Needs.

```text
python scripts/library.py --db demo.sqlite note chime --kind opinion --text "Too Bright Under The Voice" --source "Owner, Review Call" --date 2026-03-04
python scripts/library.py --db demo.sqlite note chime --kind caveat --text "Agent Heard A Click In The Tail" --source "Agent Listening Pass"
python scripts/library.py --db demo.sqlite note title-card --kind rights --text "School Confirmed Reuse In Paid Ads" --source "Email From The School Office"
python scripts/library.py --db demo.sqlite note tool-folder --kind test --text "Help Command Exits Zero" --source "validate Run"
```

- An `opinion` Is Only Ever The Owner's Own Words, With A Date And A Source. Never Paraphrase One, And Never Write One On The Owner's Behalf.
- An Agent's Or Reviewer's Reading Is A `caveat`, However Confident It Is.
- A Passing Validation Is A `test`. A `rights` Note Records Evidence Or A Restriction And Where It Came From.

## Keep The Library Tidy

```text
python scripts/library.py --db demo.sqlite archive chime
python scripts/library.py --db demo.sqlite archive chime --undo
python scripts/library.py --db demo.sqlite export demo-export --with-files
python scripts/library.py --db demo.sqlite import demo-export/catalog.json --files demo-export
```

- `archive` Hides An Asset From Normal Search. Nothing Is Ever Deleted, Existing Pins Stay Valid, And `--undo` Brings It Back.
- `export` Writes `catalog.json`, A Complete Copy Of Every Record, And A Browsable `index.html`. It Holds Metadata And Preview Stills, Not File Bytes, Unless You Add `--with-files`.
- `import` Adds Assets From A Catalog And A Folder Of Files. It Only Adds. It Reports Duplicates, Missing Files, And Differing Fields, And Overwrites A Field Only For A Name Passed To `--update`. [Import Rules](RECORDS.md#export-and-import)

## Working Without The Library

When No Library Is Configured, Or It Cannot Be Opened, Keep Working. Write A Project Manifest Beside The Edit, In The Cut Declaration Format With A `path` For Every Entry, And Add The Source And Rights Of Each Item In Your Handoff Notes. Tell The Owner Plainly That The Catalog Was Not Updated. When The Library Is Available Again, Add The Files And Run `declare` On That Manifest.

## Storage And Recovery

Revisions, Folder Manifests, Metadata, Notes, Pins, And Deliveries All Travel In One SQLite File. Close Active Library Processes Before Copying It For Backup. A Busy Writer Waits Up To 30 Seconds Before Returning An Error. [Records Reference](RECORDS.md) Covers Hashing, Capture Limits, Restore Behaviour, And Every Output Field.

## Verification

```text
python -B -m unittest discover -s tests -v
```

The Tests Exercise Every Command With Temporary Files And Never Write A Video. The Checks That Need FFmpeg Skip When It Is Missing.
