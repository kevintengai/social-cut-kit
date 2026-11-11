---
name: video-script
description: Find Short-Form Video Ideas, Write Hooks And Timed Scripts, And Run Post-Mortems On Posted Videos From The Creator's Own Results. Use For Topic Lists, Openings, Two-Column Scripts, How It Works Explainers, Retention Charts, Analytics Reviews, And The Video Library That Carries Findings From One Video To The Next.
---

# Video Script

The Video Script Skill Does Three Tasks: Ideas, A Script, And The Review Of A Posted Video. Each Task Reads What Earlier Videos Taught And Leaves A Record For The Next One.

This Skill Stops Once A Script Or A Lesson Is Delivered. The Creator Does The Filming. Cutting Belongs To The Video Edit Skill And Animation To The Animated Video Skill. This Skill Never Publishes A Post And Never Exports A Video.

## Set Up

Use Python 3.9 Or Later. Run Commands From This Skill Folder. Reading A Chart Image Also Needs FFmpeg And FFprobe On PATH.

1. Read `~/.social-cut-kit/video-script.md` First If The File Is There. It Records Where The Video Library And Findings File Live, Plus Platform Notes, Voice, And Speaking Pace. `python scripts/video_log.py defaults` Prints Its Location And Values.
2. Read The Findings And The Library Index Before Proposing Anything. `python scripts/video_log.py finding list` And `python scripts/video_log.py index` Print Them. With No Library Yet, Both Commands Stop With A Message Asking For One. That Means There Is Nothing To Read. Work From The Videos The Creator Describes And Say That No Findings Exist Yet.
3. Cite The Past Videos An Idea, Opening, Or Structure Resembles. Give The Title, The Date, And The Number That Matters.
4. A Measured Finding About This Audience Outranks Every General Default In This Kit, Including The Rules Below. Say Which Finding Changed The Advice.

With No Defaults File, Ask A Single Time For The Platform, The Audience, And Two Earlier Videos With Their Numbers: A Strong One And A Weak One. Then Offer To Create The File And A Library. Create Them Only After The Creator Agrees, Following [The Library Guide](LIBRARY.md).

## Pick The Task

| The Creator Wants | Task | Read |
| --- | --- | --- |
| Topics, Hooks, Or What To Make Next | Ideas | [Find Ideas Worth Scripting](IDEAS.md) |
| A Script, An Opening, Or A Rewrite | Script | The Rules Below. For A How It Works Video, Also [Explainers](EXPLAINERS.md) |
| Why A Posted Video Did Or Did Not Hold Viewers | Review | [Review A Posted Video](REVIEW.md) And [Read Analytics](INSIGHTS.md) |

Every Task Reads And Writes The [Video Library](LIBRARY.md).

## Write The Script

1. Keep One Idea Per Video. Write It As One Sentence Before Any Line. Material That Serves A Second Idea Goes To The Backlog.
2. Settle The Payoff And The Best Proof First, And Write The Opening After. The Payoff Is What The Viewer Holds At The End: A Result They Saw Or A Decision They Can Now Make. Pick The Proof A Skeptic Would Accept. Then Write An Opening That Promises Exactly That Payoff.
3. Write At The Creator's Pace. Without A Measured Pace, Assume About Three Spoken Words Per Second, So Thirty Seconds Holds About Ninety Words Before Any Pause. Count The Words.
4. Spend The First Three Seconds On The Viewer's Stake Or On What Is On Screen. The First Sentence Ends Inside Those Three Seconds. Credentials Wait Until A Claim Needs Them.
5. Use Seconds Three To Ten To Answer The Opening Or Raise Its Stakes. Hold Back Background The Viewer Does Not Yet Need. Place It Just Before The Line That Depends On It.
6. End On The Payoff, Shown On Screen. After It, Allow A Single Brief Call To Action, Or None. Nothing Follows The Call To Action.
7. Next To Each Line, Note The Picture On Screen And The Footage Or Capture It Needs. A Line Without A Picture Is Unfinished.
8. Give Every Factual Claim An Evidence Entry With Its Source. A Claim The Creator Cannot Show Is Cut Or Reworded As Opinion.

A How It Works Script Follows The Same Rules And The Story Method In [Explainers](EXPLAINERS.md).

### Hold The Script Against This Checklist

- One Idea.
- The Stake Is Framed For A Non-Expert. A Viewer Outside The Niche Knows Why It Matters By The End Of The Second Sentence.
- Every Claim Is Shown.
- Every Promise In The Opening Is Paid Off On Screen.
- Each Sentence Is Clear When Read Alone.
- Every Line Is A Full Sentence That Can Be Spoken Aloud.
- Every Line Moves The Story On. If The Next Line Still Works Without It, Cut It.

`check` Tests The Mechanical Part: The Opening Sentence Against The Three-Second Mark At The Creator's Pace, Missing Pictures, Claims Without A Source, More Than One Call To Action Or One That Is Not Last, Runtime Over Or Well Under The Target, And Where The Ten-Second Mark Falls. Each Problem Names Its Line. The Rest Of The Checklist Is Judgment. Read The Script Aloud Against It.

```sh
python scripts/script_desk.py check assets/practice-script.json
python scripts/script_desk.py check assets/practice-script.json --pace 2.6 --target 30
```

`check` Exits With 1 When Anything Is Listed Under To Fix. Items Under To Review Need A Decision, Not Always A Change. Add `--strict` To Fail On Those Too, Or `--json` For A Machine-Readable Result.

### Check Each Claim Against Its Source

Have A Separate Agent Check Each Claim As Worded Against Its Source. Give It Only The Claim Text And The Source. Ask For One Of Three Answers: The Source Says This, The Source Says Something Narrower, Or The Source Could Not Be Opened. Reword A Narrower Claim To Match Its Source. Set `opened` To `false` For A Source That Could Not Be Opened And Tell The Creator That Claim Is Unverified. When A Source Cannot Be Opened, Still Run The Check. Give The Separate Agent Each Claim And The Creator's Own Statement, And Ask Whether The Line Says More Than The Creator Said. Narrow Every Line That Does. Absolute Wording Such As All, Only, Any, And Never Is Where A Line Most Often Overreaches. With No Separate Agent Available, Make The Check In A Pass That Reads Only Claims And Sources, And Say It Was Not Independent.

### Deliver

Give The Creator Six Things: The Timed Script, The Capture List, A Draft Post Caption That Holds Caveats And Links Which Do Not Fit In Speech, The Estimated Runtime, Alternative Openings Each With Its Own Second Sentence, And The Claims To Verify With Their Sources. `sheet` Prints All Six From One Script File.

```sh
python scripts/script_desk.py sheet assets/practice-script.json
```

### When The Creator Rewrites Lines

Keep Their Wording Exactly. Study What They Changed: Sentence Length, Word Choice, How They Address The Viewer. Carry That Style Into The Lines Still Owned By The Agent. Run `check` Again, Since A Rewritten Opening Can Cross The Three-Second Mark.

## Script File Fields

A Script Is One JSON File With `format` Set To `school.script/1`. The Director Skill Reads The Same File. `outline` Drafts One From A Campaign Brief, Taking The Viewer, The Proof, And The Next Action From It. Without A Brief, Write The File Directly.

```sh
python scripts/script_desk.py outline assets/practice-brief.json my-draft.json --seconds 30
python scripts/script_desk.py read assets/practice-script.json
```

| Field | Meaning |
| --- | --- |
| `title`, `reviewer` | The Working Title And Who Approves The Script. |
| `idea`, `goal` | The One Idea As A Sentence, And Reach, Follows, Saves, Or Shares. Optional. |
| `pace`, `target_seconds` | Spoken Words Per Second And The Runtime To Hold. Optional. |
| `caption` | The Draft Post Caption. Optional, And Reported When Missing. |
| `openings[]` | Alternative Openings. Each Has `angle` And `first_frame`, Plus `first_sentence` And `second_sentence`. |
| `evidence[]` | Claims To Verify. Each Has `id`, `claim`, `source`, And `visual`. Add `opened` As `true` Or `false` And `checked` With Who Checked It And When. |
| `beats[]` | The Lines In Order. Each Has `id`, `purpose`, `seconds`, `voice`, `picture`, `proof`, `media`, And `source_in`. |
| `beats[].capture` | What Must Be Recorded For The Picture. Optional Once `media` Names A File. |
| `beats[].proof` | The `id` Of The Evidence Entry This Line Shows, Or An Empty String. |
| `beats[].purpose`, `beats[].cta` | A Purpose Of `Invitation`, `CTA`, Or `Call To Action` Marks The Call To Action. So Does `cta` Set To `true`. |

Pace Comes From `--pace`, Then The Script's `pace`, Then The Defaults File, Then Three Words Per Second. The Report Says Which One Was Used.

## Command Reference

| Command | Result |
| --- | --- |
| `python scripts/script_desk.py outline BRIEF OUTPUT [--seconds 30]` | A Timed Draft With Two Opening Treatments From A Campaign Brief. |
| `python scripts/script_desk.py read SCRIPT` | A Table Read. |
| `python scripts/script_desk.py check SCRIPT [--pace WORDS] [--target SECONDS] [--json] [--strict]` | The Checklist's Mechanical Tests With Line References. |
| `python scripts/script_desk.py sheet SCRIPT [--pace WORDS]` | The Delivery Sheet. |
| `python scripts/retention.py csv FILE` | A Retention Report From `seconds` And `retention_pct` Columns. See [Read Analytics](INSIGHTS.md). |
| `python scripts/retention.py image FILE --seconds SECONDS` | A Retention Report From A Chart Screenshot, Calibrated Automatically Or By Hand. |
| `python scripts/retention.py --selftest` | Draws Practice Charts And Reads Them Back Within A Stated Tolerance. |
| `python scripts/video_log.py [--library FOLDER] COMMAND` | The Video Library: `init`, `add`, `update`, `snapshot`, `attach`, `index`, `show`, `compare`, `lineup`, `finding`, `backlog`, And `defaults`. See [The Library Guide](LIBRARY.md). |

Every Command Accepts `--help`. `outline`, `--output`, `init`, And `defaults write` Refuse To Replace An Existing File.

## Practice Files

The `assets` Folder Holds Invented Practice Material: A Campaign Brief, A Complete Script That Passes `check`, A Retention CSV, And A Drawn Retention Chart. The Examples In These Guides Run Against Them.

## Where The Work Stops

The Video Script Skill Hands Over A Script With Its Delivery Sheet, A List Of Ideas, Or A Review With Its Library Records. The Creator Films. The Director Skill Plans Shots From The Same Script File. The Video Edit Skill Cuts The Footage, And The Animated Video Skill Builds Animated Inserts. Nothing Here Posts To A Platform, Schedules A Post, Or Exports A Video File.

## Verification

```sh
python -B -m unittest discover -s tests -v
python scripts/retention.py --selftest
```

The Tests Run Offline With Temporary Files And A Temporary Defaults Folder. Tests That Decode Image Files Are Skipped When FFmpeg Is Not Installed. The Self Test Reads Its Own Drawn Charts Within 1.5 Retention Points At Each Fixed Second.
