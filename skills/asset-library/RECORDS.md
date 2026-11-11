# Asset Library Records Reference

Reference Detail For The [Asset Library Guide](SKILL.md). Every Command Takes The Optional `--db PATH` Before The Command Name.

## Commands

| Command | Usage |
| --- | --- |
| `init` | `library.py [--db PATH] init` |
| `add` | `library.py add ASSET SOURCE --origin TEXT --rights TEXT --context TEXT [--tag TAG]... [--kind KIND] [--validate COMMAND] [--validate-timeout SECONDS] [--validate-env NAME]... [--validate-later]` |
| `search` | `library.py search [TERM] [--tag TAG]... [--context TEXT] [--kind KIND] [--min-duration SECONDS] [--max-duration SECONDS] [--duplicates] [--archived]` |
| `history` | `library.py history ASSET` |
| `show` | `library.py show ASSET` |
| `kind` | `library.py kind ASSET KIND` |
| `note` | `library.py note ASSET --kind {opinion,test,rights,caveat} --text TEXT --source TEXT [--date YYYY-MM-DD]` |
| `archive` | `library.py archive ASSET [--undo]` |
| `pin` | `library.py pin PROJECT ASSET --use USE --version FULL_SHA256 [--replace FULL_SHA256] [--cut LABEL]` |
| `uses` | `library.py uses [--project PROJECT] [--asset ASSET] [--cut LABEL]` |
| `check` | `library.py check PROJECT [--asset ASSET] [--use USE] [--cut LABEL] [--path PATH]` |
| `check` | `library.py check PROJECT --declaration FILE [--scan FOLDER]` |
| `get` | `library.py get ASSET DESTINATION --version FULL_SHA256` |
| `preview` | `library.py preview ASSET DESTINATION.jpg [--version FULL_SHA256]` |
| `declare` | `library.py declare DECLARATION` |
| `deliver` | `library.py deliver DECLARATION [--scan FOLDER] [--date YYYY-MM-DD]` |
| `deliveries` | `library.py deliveries [--project PROJECT]` |
| `validate` | `library.py validate ASSET [--version FULL_SHA256] [--env NAME]... [--timeout SECONDS]` |
| `export` | `library.py export FOLDER [--with-files]` |
| `import` | `library.py import CATALOG --files FOLDER [--update NAME]...` |
| `stats` | `library.py stats` |

A Command That Fails Exits With Code 1 And Prints `Error:` And `Hint:` Lines On The Error Stream. An Unknown Option Exits With Code 2 And Prints The Usage Line. `check --declaration`, `declare`, `deliver`, And `validate` Also Print Their JSON Report When They Fail, So A Script Can Read The Problems.

## Revision Fields

| Field | Meaning |
| --- | --- |
| `asset`, `version` | The Asset Name And The SHA-256 Revision. |
| `kind` | `file` Or `bundle`. The Storage Form Of The Revision. |
| `asset_kind` | One Of `footage`, `image`, `music`, `sfx`, `voice`, `character`, `code`, `model`, `other`. |
| `kind_source` | On `add`: `given`, `inferred`, Or `existing`. |
| `origin`, `rights`, `context`, `tags` | The Source, The Terms, The Reuse Context, And Lower-Case Tags. |
| `source_name` | The File Or Folder Name At Capture. Empty For Revisions From An Earlier Edition. |
| `media` | `duration` In Seconds, `width`, `height`, `frame_rate`, `audio_channels`, `sample_rate`, And `peak_db`. Fields That Do Not Apply Are Null. The Whole Object Is Null When Nothing Was Measured. |
| `media_status`, `preview_status` | One Sentence Saying What Was Measured Or Kept, Or Why Not. |
| `has_preview` | True When A JPEG Preview Still Is Stored. |
| `archived` | The Time The Asset Was Archived, Or Null. |
| `same_bytes_as`, `duplicates` | Other Asset Names That Hold The Same Version. |
| `validation` | For A Folder Revision With A Command: `command`, `timeout`, And `env`. `show` Adds `runs` And `last_result`. |

Media Facts Come From FFprobe For Recognised Video, Audio, And Image File Types. The Peak Level Comes From FFmpeg And Applies To Audio Files. Images Have No Duration Or Frame Rate. Folders Carry No Media Facts. Revisions From An Earlier Edition Keep Empty Facts. Add The Source Again Under A New Revision To Measure It.

## Cut Declaration

A Declaration Is A JSON File Kept With The Project. Paths Resolve Relative To The Declaration File.

```json
{
  "project": "School Promo",
  "cut": "v1",
  "entries": [
    {
      "asset": "title-card",
      "use": "Opening Card",
      "path": "media/title-card.png",
      "modified": false,
      "cue": "Holds Under The First Line",
      "time": 0
    }
  ]
}
```

| Field | Meaning |
| --- | --- |
| `project`, `cut` | Required. The Project Name And The Cut Label. |
| `entries[].asset`, `entries[].use` | Required. Each Use Appears Once In A Cut. |
| `entries[].version` Or `entries[].path` | Exactly One. A Full SHA-256, Or A File Or Folder That Is Hashed And Must Match A Stored Revision Of That Asset. |
| `entries[].modified` | Optional. True When The Project Changed The Asset For This Cut. Add The Changed Copy As Its Own Revision First. |
| `entries[].cue`, `entries[].time` | Optional Cue Text And Timeline Seconds From The Final Cue Sheet. |

`declare` Validates Every Entry Before It Writes. One Unresolved Entry Means Nothing Is Recorded, And The Report Lists Each Problem. Declaring A Cut Again Updates Its Uses And Retires Any Use The New Declaration Leaves Out. Retired Uses Stay In The Database And Appear In `show`. After `deliver`, The Same Declaration Can Be Declared Or Delivered Again Without Change, And A Different One Is Refused. `pin --cut` On A Delivered Cut Is Refused For The Same Reason.

The Declaration Check Passes When Every Declared Entry Resolves To A Stored Revision, The Recorded Use For That Cut Holds The Same Asset And Version, And Every Stored Byte Behind It Reads Back With The Right Digest. `recorded_but_undeclared` Lists Recorded Uses Of The Cut That The Declaration Leaves Out. It Is Informational.

## Project Scan

`--scan FOLDER` Walks The Project Folder And Reports Library Assets That The Declaration Does Not Name. A `bytes` Match Is A File Identical To A Stored File Revision. A `name` Match Is An Asset Name, Three Characters Or Longer, Found In A Text File. Each Result Gives The First Path And The Number Of Places.

The Scan Skips Hidden Files And Folders, And The Dependency Folders `node_modules`, `__pycache__`, `site-packages`, `venv`, `env`, `vendor`, `bower_components`, `pods`, And `target`. It Stops After 5,000 Files, Hashes Only Files Whose Size Matches A Stored Revision Up To 2 GiB In Total, And Reads Text Files Up To 1 MiB Each. `capped` Is True When A Limit Was Reached. The Scan Never Changes The Result Of The Check.

## Bundle Validation

The Command Is Split Into Arguments With POSIX Quoting Rules And Started Directly, Without A Shell. Use Double Quotes Around An Argument With Spaces. A Command That Begins With `python` Or `python3` Runs With The Interpreter That Is Running The Library. Any Other Program Is Found On PATH. The Working Folder Is The Root Of A Fresh Temporary Copy Of The Stored Snapshot, Removed When The Command Ends.

The Environment Holds Only These Variables, When They Are Set: `PATH`, The Home Variables `HOME`, `USERPROFILE`, `HOMEDRIVE`, `HOMEPATH`, `APPDATA`, And `LOCALAPPDATA`, The Temporary Folder Variables `TEMP`, `TMP`, And `TMPDIR`, `SYSTEMROOT` On Windows, And The Locale Variables `LANG`, `LC_ALL`, And `LC_CTYPE`. Names Stored With `--validate-env` And Names Passed To `validate --env` Are Added. `environment` In The Result Lists What Was Passed.

| Result Field | Meaning |
| --- | --- |
| `status` | `passed` For Exit Code Zero, `failed` For Any Other Exit Or A Timeout, `not_run` When The Program Was Not Found Or `--validate-later` Was Used. |
| `exit_code` | The Exit Code, Or Null When The Command Did Not Finish. |
| `output_tail` | The Last 2,000 Characters Of Combined Output. |
| `seconds`, `detail` | The Time Taken And One Sentence About The Outcome. |

`add` With A Failing Command Still Stores The Revision And Exits Zero, With The Failure In `validation_result`. `validate` Exits Non-Zero Unless The Status Is `passed`. The Default Timeout Is 120 Seconds. A Stored Revision Keeps Its Original Command. Register The Folder Under A New Revision To Change It.

## Export And Import

`export FOLDER` Writes `catalog.json`, `index.html`, And A `previews` Folder Of JPEG Stills. The Catalog Holds Every Asset, Revision, Folder Manifest, Media Fact, Note, Validation Result, Pin, Cut Use, And Delivery. It Holds No File Bytes, And `contains_file_bytes` Is False. With `--with-files`, Each Revision Is Also Written Under `files/VERSION/`, And Its `file` Field Names That Path. The Destination Must Be New, Empty, Or An Earlier Export.

`import CATALOG --files FOLDER` Reads A Catalog And Looks For Each Revision's `file` Under The Folder. A Hand-Written Catalog Can Be Short:

```json
{
  "assets": [
    {
      "name": "street-ambience",
      "kind": "sfx",
      "file": "audio/street.wav",
      "origin": "Recorded On Location",
      "rights": "Owned",
      "context": "City Scenes",
      "tags": ["ambience"]
    }
  ]
}
```

| Report List | Meaning |
| --- | --- |
| `added` | A New Name, Or A New Revision Of An Existing Name, Was Stored. |
| `unchanged` | The Name Already Holds This Version With The Same Fields. |
| `duplicates` | A New Name Whose Bytes Another Asset Already Holds. Not Added. `held_by` Names The Holder. |
| `missing` | The Named File Is Not In The Folder. Skipped. |
| `skipped` | No File Was Named, The File Differs From The Catalog Version, Or `origin`, `rights`, Or `context` Is Absent. |
| `differing` | An Existing Name And Version With Different Fields. Shown With Both Values And Left As It Was. |
| `updated` | The Same, For A Name Passed To `--update`. The Catalog Values Replaced The Stored Ones. |

Import Adds Notes That Are Not Already Present. It Stores A Validation Command Without Running It. It Does Not Import Pins, Cut Uses, Or Deliveries, Which Belong To The Projects That Made Them.

## Upgrades And Backups

The Database Carries A Schema Version, Shown By `init`. This Edition Writes Version 2. Opening A Version 1 Library With Any Command First Writes A Copy Named `NAME.backup-v1-TIMESTAMP.sqlite` Beside It With SQLite's Backup API, Then Adds The New Tables And Columns In One Transaction. No Existing Row Is Dropped Or Rewritten. Assets From Version 1 Get The Kind `other` Until You Set One With `kind`. A Library Written By A Newer Edition Is Refused And Left Untouched.

## Storage Rules

- File Revisions Use SHA-256 Of The Original Bytes. Bundle Revisions Hash A Versioned Manifest Of File Digests, Directory Entries, And Relative Names. Empty Folders And Hidden Files Are Included. Timestamps, Permissions, And The Outer Folder Name Are Excluded. Repeated File Contents Share Storage Across Revisions And Bundles.
- Capture Requires Regular Files, Portable Names, And Directories. Resolve Symbolic Links, Junctions, Case-Colliding Names, And External Dependencies Before Capturing A Bundle. Editor Relinking May Still Be Necessary For Absolute Media References After A Restore.
- Every Write Commits In A SQLite Transaction. An Identical `add` With Identical Metadata Returns The Same Revision. Conflicting Metadata Produces An Error So Source And Rights Records Remain Intact.
- Restoring Requires An Existing Parent Folder. An Identical Destination Is Accepted On Retry. A Different Destination Is Protected. If A Process Stops During Restoration, Retry Into A Fresh Path.
- Store The Database On A Local Filesystem With SQLite Locking Support. Media Probing And Validation Run Outside The Write Lock.
