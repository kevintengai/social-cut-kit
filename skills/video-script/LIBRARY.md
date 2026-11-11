# The Video Library

The Library Is The Creator's Memory Across Videos. It Holds One Record Per Video, An Index, A Findings File, And A Backlog, In A Folder The Creator Chooses. `scripts/video_log.py` Writes Every File. Each Record Is JSON For Tools And Generated Markdown For Reading.

## Layout

| Path | Contents |
| --- | --- |
| `library.json` | Marks The Folder As A Library And Keeps Its Platform And Audience. |
| `index.md` | Every Video, Newest First, With The Comparable Numbers. Generated. |
| `findings.json` | Hypotheses, Their Evidence, Their Status, And Each Status Change. |
| `findings.md` | The Same Findings Grouped As Supported, Open, And Weakened. Generated. |
| `backlog.md` | One Line Per Saved Idea. Safe To Edit By Hand. |
| `videos/ID.json` | One Video: Its Details, Snapshots, And Retention Readings. |
| `videos/ID.md` | The Readable Page For That Video. Generated. |
| `captures/` | A Place For Screenshots, CSV Files, And Saved Retention Reports. The Tool Does Not Read It. |

Generated Files Are Rebuilt After Every Change. Edit The JSON, Then Run `index`, And The Markdown Follows. Edits Made To Generated Markdown Are Overwritten. A Record's `id` Must Match Its File Name. To Remove A Video, Delete Its Two Files And Run `index`.

## Start A Library

Run Commands From This Skill Folder. Pass `--library` Before Or After The Command. Once The Defaults File Names The Library, The Option Can Be Left Out.

In A First Session, Start The Library, Add The Past Video That Did Well And The One That Did Not, Record The Numbers The Creator Gave For Each, And Then Write The Defaults File.

```sh
python scripts/video_log.py --library "Practice Library" init --platform "Instagram Reels" --audience "Repair Shop Owners"
```

## Add A Video

Supply What Is Known. Anything Left Out Is Stored As `null` And Shown As Not Captured. The Tool Never Fills A Gap With A Guess, And Neither Should The Agent.

```sh
python scripts/video_log.py --library "Practice Library" add --id ready-repair --title "Your Repair Was Ready Two Days Ago" --posted 2026-11-03 --platform "Instagram Reels" --format "Screen Demo With Voiceover" --runtime 28 --stake "Customers And Shop Owners Who Wait On Finished Repairs" --first "Your Repair Was Ready Two Days Ago." --second "The Shop Just Could Not See It." --project "Projects/ready-repair" --final "Finals/ready-repair.mp4" --captions "assets/practice-captions.srt"
python scripts/video_log.py --library "Practice Library" add --id three-calls --title "Three Customers Called Before Nine" --posted 2026-10-20 --platform "Instagram Reels" --format "Screen Demo With Voiceover" --runtime 30 --first "Three Customers Called Before Nine." --second "All Three Repairs Were Already Done."
python scripts/video_log.py --library "Practice Library" add --id empty-queue --title "Why The Queue Looks Empty" --review
```

- `--stake` Holds The Stake Or The Audience: Who The Video Is For And What They Stand To Gain Or Lose.
- `--first` And `--second` Hold The First Two Spoken Sentences As Posted.
- `--project`, `--final`, And `--captions` Link The Editable Project, The Final File Or Post, And The Captions File. Give The Captions Link As A Path That Opens From Where The Commands Run, Or A Path Inside The Library, So `lineup` Can Read It.
- Without `--id`, The Record Is Named From The Posting Date And The Title, Such As `2026-11-03-your-repair-was-ready-two-days-ago`. A Review Uses The Date The Record Was Made.
- `--review` Adds An Unposted Video. Its Record Is A Review, Not Evidence. It Takes No Numbers And Cannot Be Cited In A Finding. When The Video Goes Out, Run `update ID --posted DATE`.
- `update ID` Accepts The Same Options To Correct A Record. An Empty Value Such As `--platform ""` Clears A Field. `--note` Adds A Dated Note.

## Record A Snapshot

A Snapshot Is One Dated Reading Of The Analytics Screen. Record The Date And Time With `--captured`. Without It, The Tool Uses The Present Time And Says So. [Read Analytics](INSIGHTS.md) Explains What To Capture.

```sh
python scripts/video_log.py --library "Practice Library" snapshot ready-repair --captured "2026-11-05 09:30" --views 12840 --viewers 11020 --average-watch 14.2 --follows 31 --likes 402 --comments 18 --shares 55 --saves 61 --rate "Skip Rate" 41.2% --source Feed 71% --source Explore 18% --source Profile 6% --non-follower-share 87.5%
python scripts/video_log.py --library "Practice Library" snapshot three-calls --captured "2026-10-27 08:00" --views 9410 --viewers 8102 --average-watch 14.9 --follows 9 --non-follower-share 80
```

- Counts: `--views`, `--viewers`, `--follows`, `--likes`, `--comments`, `--shares`, `--saves`, `--reposts`. Write `12840`, `"12,840"`, Or A Rounded Figure As The App Shows It, Such As `12.8K`. A Rounded Entry Is Kept With Its Rounded Form Beside It.
- `--average-watch` Takes Seconds As `14.2` Or `0:14`.
- `--rate LABEL PERCENT` Records Any Rate Under The Platform's Own Label. Repeat It For Each Rate.
- `--source LABEL VALUE` Records Views From One Source As A Count Or As A Percent Ending In `%`. Repeat It For Each Source.
- `--non-follower-share`, Or `--follower-share` When The App Shows Only That Side.
- A Second Snapshot With The Same Capture Time Needs `--replace`. Snapshots At Different Times Are All Kept, So A Video Can Be Read At Fixed Ages.

## Attach Retention

Read The Curve With `scripts/retention.py`, Save The Report With `--output`, And Attach It. The Record Keeps The Readings At Fixed Seconds, The Curve, The Area-Based Average, The Drop From Three To Ten Seconds, The Steep Drops, The Flat Stretches, And Any Warning.

```sh
python scripts/retention.py csv assets/practice-retention.csv --reported-average 14.2 --output "Practice Library/captures/ready-repair.json"
python scripts/video_log.py --library "Practice Library" attach ready-repair "Practice Library/captures/ready-repair.json" --captured "2026-11-05 09:30"
python scripts/retention.py image assets/practice-chart.png --seconds 30 --top 100 --bottom 0 --reported-average 14.9 --output "Practice Library/captures/three-calls.json"
python scripts/video_log.py --library "Practice Library" attach three-calls "Practice Library/captures/three-calls.json" --captured "2026-10-27 08:00"
```

`attach` Warns When The Report's Duration And The Record's Runtime Disagree, And It Repeats Any Warning The Report Carries.

## Read The Index

```sh
python scripts/video_log.py --library "Practice Library" index
python scripts/video_log.py --library "Practice Library" show ready-repair
```

`index` Rebuilds Every Generated File And Prints The Table, Newest First. Its Derived Columns:

| Column | How It Is Derived |
| --- | --- |
| Average Watch Share | Average Watch Time Divided By Runtime, From The Latest Snapshot. |
| Watching At 10 Seconds | The Latest Attached Retention, Read At Ten Seconds. Past The End When The Video Is Shorter. |
| Non-Follower Share | The Non-Follower Share Of Views, Or 100 Minus The Follower Share. |
| Follows Per 1,000 Viewers | Follows Divided By Viewers, Times 1,000, From The Latest Snapshot. |
| Status | Review, Not Evidence. Posted, No Numbers. Retention Only. Or Measured Day N, Counted From Posting To The Latest Snapshot. |

Every Snapshot Number In A Row Comes From The Latest Snapshot, So A Row Never Mixes Two Ages. When That Snapshot Lacks An Input, The Column Says Not Captured. Earlier Snapshots Stay On The Video's Page.

## Compare Retention

```sh
python scripts/video_log.py --library "Practice Library" compare ready-repair three-calls
python scripts/video_log.py --library "Practice Library" compare ready-repair three-calls --at 3 10 25
```

`compare` Reads Each Video's Latest Retention At The Same Seconds And Adds The Drop From Three To Ten Seconds, The Average Watch Share, And The Runtime. It Interpolates Along The Stored Curve. A Second Beyond A Video's Runtime Reads Past The End. It Notes When The Videos Use Different Formats.

## Line Up Retention With Captions

```sh
python scripts/video_log.py --library "Practice Library" lineup ready-repair
```

`lineup` Takes Each Steep Drop And Flat Stretch From The Latest Attached Retention And Prints The Caption Lines Spoken In The Three Seconds Before It And While It Lasts, With Their Times. It Reads The SRT Or WebVTT File Linked In The Record, Or The One Named With `--captions`. `--before` Changes The Three Seconds. The Shown And Reading Columns Are Left Empty For The Review.

## Manage Findings

A Finding Starts As An Open Hypothesis: One Sentence A Video Could Support Or Weaken. Each Evidence Entry Names One Posted Video With Recorded Numbers, Says Whether It Supports Or Weakens The Hypothesis, And States The Number In `--note`.

```sh
python scripts/video_log.py --library "Practice Library" finding add "Opening On The Viewer's Own Wait Holds More Viewers At Ten Seconds Than Opening On The Shop's Morning."
python scripts/video_log.py --library "Practice Library" finding evidence F01 ready-repair supports --note "57.0 Percent Still Watching At 10 Seconds Against 51.9 For The Morning Opening In Three Customers Called Before Nine."
python scripts/video_log.py --library "Practice Library" finding list
```

The Tool Enforces These Rules:

1. Evidence Is A Posted Video With A Snapshot Or Attached Retention. A Review Is Refused, And A Cited Record That Is Later Removed Stops Counting.
2. A Video Counts Once Per Finding. `--replace` Corrects Its Entry.
3. `finding status ID supported` Needs At Least Two Videos That Support And More Of Them Than Videos That Weaken. `weakened` Is The Mirror Image.
4. `finding status ID open` Reopens A Settled Finding Once Two Videos Go Against It.
5. When A Correction Leaves A Settled Finding With Fewer Than Two Agreeing Videos, It Returns To Open And The Tool Says So.

Name The Video That Carried The Tested Choice. The Video It Was Compared With Goes In The Note. One Comparison Is One Video Of Evidence. After The Commands Above, `finding status F01 supported` Is Refused, Because Only One Video Agrees So Far. A Second Video With The Same Kind Of Opening Has To Agree First.

## Keep A Backlog

```sh
python scripts/video_log.py --library "Practice Library" backlog add "Show The Short List Before Explaining The Filter" --tests F01
python scripts/video_log.py --library "Practice Library" backlog list
python scripts/video_log.py --library "Practice Library" backlog done 1
```

`backlog list` Numbers The Open Lines. `backlog done NUMBER` Marks One As Used And Keeps It In The File. `backlog list --all` Also Prints Used Lines.

## The Defaults File

`~/.social-cut-kit/video-script.md` Tells Every Session Where The Library Is And How The Creator Speaks. Create It Once, After The Creator Agrees And After The Library Exists. It Is Markdown, Meant To Be Edited By Hand Afterward.

```sh
python scripts/video_log.py --library "Practice Library" defaults write --platform "Instagram Reels" --audience "Repair Shop Owners" --pace 3 --voice "Plain And Direct, First Person, Short Sentences" --platform-note "Views Count Replays. Checked In The App On 2026-11-05."
python scripts/video_log.py defaults
```

The Tools Read Its `- Key: Value` Lines: `Library`, `Findings`, `Platform`, `Audience`, `Pace`, And `Voice`. `Pace` Is Spoken Words Per Second And Sets The Default For `script_desk.py check`. The Platform Notes Section Keeps The Labels And Definitions The App Uses, With The Date Each Was Checked. `defaults write` Refuses To Replace An Existing File. Set The `SOCIAL_CUT_KIT_HOME` Environment Variable To Keep The Folder Somewhere Other Than `~/.social-cut-kit`.

## Record Fields

| Field In `videos/ID.json` | Meaning |
| --- | --- |
| `id`, `title` | The Record Name And The Working Title. |
| `kind`, `posted` | `posted` With A Date, Or `review` With `null` For An Unposted Video. |
| `platform`, `video_format`, `runtime_seconds`, `stake` | The Details Given To `add`. `null` Means Not Captured. |
| `opening.first`, `opening.second` | The First Two Spoken Sentences. |
| `links.project`, `links.final`, `links.captions` | Where The Project, The Final File, And The Captions Live. |
| `snapshots[]` | Each Has `captured`, The Eight Counts, `average_watch_seconds`, `non_follower_share_pct`, `follower_share_pct`, `rates[]`, `sources[]`, `shown` For Rounded Entries, And `note`. Every Key Is Present, With `null` For A Number That Was Not Captured, And `not_captured` Lists Those Numbers By Name. |
| `retention[]` | Each Has `captured`, `report`, `duration_seconds`, `readings[]`, `curve`, `average_watch_seconds`, `average_watch_share_pct`, `drop_3_to_10_points`, `steepest_drops[]`, `flattest_stretches[]`, `warnings[]`, And `calibration`. |
| `notes[]` | Dated Notes. |

In `findings.json`, Each Finding Has `id`, `hypothesis`, `status`, `created`, `evidence[]` With `video`, `direction`, `note`, And `added`, And `history[]` With Each Status Change And The Videos On Each Side At That Moment.
