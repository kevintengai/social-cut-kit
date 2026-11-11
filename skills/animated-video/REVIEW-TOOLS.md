# Review Tools

Five Tools Let An Agent Inspect A Film Without Exporting It. They Render Individual PNG Stills, Measure Frames In Memory, List Picture Events, Measure The Sound Mix, And Check A Finished Export. None Of Them Writes A Video. [Review](REVIEW.md) Explains How To Judge What They Show.

Run Them With Node.js From The User's Project Folder, Where The Film Folder Lives. `$SKILL` Stands For The Path To This Skill Folder, As In The [Skill Guide](SKILL.md). Every Tool Reads `storyboard.timed.json`, The One Storyboard That Is Reviewed And Exported, Together With The Scene Modules It Lists. Every Tool Refuses To Write Inside The Skill Folder.

| Tool | Needs | Writes |
| --- | --- | --- |
| `tools/stills.cjs` | A Local Chrome, Chromium, Or Edge | PNG Stills, A Board Page, A Contact Sheet, And A JSON List |
| `tools/motion.cjs` | A Local Chrome, Chromium, Or Edge | An Optional JSON Report |
| `tools/events.cjs` | Node.js Only | An Optional Cue Sheet, Or The Storyboard's Own Event Cues With `--update` |
| `tools/audio.cjs` | FFmpeg On PATH | An Optional JSON Report And An Optional WAV Check Mix |
| `tools/export-check.cjs` | FFmpeg And FFprobe On PATH | An Optional JSON Report |

Pass The Browser Path With `--browser`, Or Set It In The `MOTION_STUDIO_BROWSER` Environment Variable. FFmpeg Is An External Tool That The Kit Does Not Install. The Sound Tools Find It On PATH, Or Take Its Path From `--ffmpeg`, And Say So Plainly When It Is Missing. Installing It Needs The User's Agreement And The Network.

## Stills And Boards

```text
Usage: node tools/stills.cjs Storyboard.json OutputFolder --browser BrowserPath [--times 1,2.5,7] [--every 2] [--scenes] [--strip 3.2] [--strip-frames 7] [--no-captions] [--silent] [--half] [--columns 4] [--overwrite]
```

| Option | Effect |
| --- | --- |
| `--times 1,2.5,7` | Stills At Listed Seconds. Each Time Snaps To A Real Frame. |
| `--every 2` | A Still Every Two Seconds. |
| `--scenes` | One Still Per Scene, Three Fifths Of The Way Through It. This Is The Default When No Times Are Chosen. |
| `--strip 3.2` | A Strip Of Consecutive Frames Centered On A Moment, For Judging Motion. List Several Moments With Commas. `--strip-frames` Sets The Count From 2 To 60. |
| `--no-captions` | Hides The Caption Track In The Pictures. |
| `--silent` | For The Silent Viewing Test. Hides Captions And Leaves Spoken Lines Off The Board. |
| `--half` | Renders At Half Size For Speed. Use Full Size To Judge Type And Edges. |
| `--columns 4` | Columns On The Contact Sheet. |
| `--overwrite` | Replaces Stills This Tool Wrote Earlier In The Same Folder. |

The Output Folder Receives:

- `still-001-1.80s.png` And So On, One PNG Per Still.
- `contact-sheet.png`, One Image Of Every Still With Its Time, Frame, Scene, And Its Caption Or Spoken Line.
- `board.html`, The Same Board As A Page To Open In A Browser.
- `stills.json`, The List Of Stills, Times, Lines, And Any Scene Problems.

The Board Is Marked When The Storyboard Uses Stand-In Voice Timing, And When It Declares No Narration. When A Scene Fails To Draw, The Still Shows An Error Card, The Tool Prints The Message, And It Exits With An Error.

```sh
node "$SKILL/tools/stills.cjs" my-film/storyboard.timed.json my-film/board --browser "/path/to/chrome" --half --every 1
node "$SKILL/tools/stills.cjs" my-film/storyboard.timed.json my-film/strip --browser "/path/to/chrome" --strip 6.6 --strip-frames 9
node "$SKILL/tools/stills.cjs" my-film/storyboard.timed.json my-film/silent --browser "/path/to/chrome" --half --every 1 --silent
```

To Try The Tool On A Bundled Example, Read The Example From The Skill And Write The Stills Into The User's Project.

```sh
node "$SKILL/tools/stills.cjs" "$SKILL/examples/an-idea-travels/storyboard.timed.json" idea-board --browser "/path/to/chrome" --half --every 1
```

Read The Contact Sheet As An Image. Look At Individual Stills At Full Size Before Judging Type, Faces, Or Edges.

## Motion And Determinism

```text
Usage: node tools/motion.cjs Storyboard.json --browser BrowserPath [--still 0.75] [--threshold 0.05] [--with-captions] [--determinism] [--report Motion.json] [--overwrite]
```

The Tool Draws Every Frame Small, Compares Each With The One Before It, And Prints The Mean Change For Each Second As A Percentage Of Full Scale. Then It Lists The Stillest Stretches: Runs Where The Change Stays At Or Below `--threshold` For `--still` Seconds Or Longer. Captions Are Hidden Unless `--with-captions` Is Set, So The Numbers Describe The Picture.

- A Long Still Stretch Is A Place Where Nothing Happens On Screen. Decide Whether It Is A Deliberate Hold Or A Stall.
- A Tall Spike In One Second Is A Cut Or A Fast Move. A Spike Where No Cut Is Planned Is A Pop.
- Boiling Grain Or Line Counts As Change. Raise `--threshold` For A Film With A Constant Boil.

`--determinism` Draws A Sample Of Frames From Every Scene Twice, The Second Time In Reverse Order, And Compares The Pixels. Any Difference Fails The Run And Names The Frames. `--report` Saves The Numbers As JSON. Frames Are Compared In Memory And No Image Or Video Is Written.

## Picture Events And Their Sounds

```text
Usage: node tools/events.cjs Storyboard.json [--sheet Events.txt] [--json Events.json] [--update] [--place Copy.json] [--overwrite]
```

Code Scenes Declare Events From The Same Constants That Draw Them, As Described In [Code Scenes](CODE-SCENES.md). The Timing Tool Places A Sound Cue On Every Event That Has A Sound, Inside `storyboard.timed.json`, Panned To The Event's Position. This Tool Gathers The Events In Film Order With Times, Positions, And Sounds. With No Options It Prints The Cue Sheet And Says Whether The Placed Sounds Are Current. `--sheet` And `--json` Save It.

The Sound Comes From The Scene's `sounds` Entry For The Event `id`, Then For Its `kind`, Then From The Module's Own Suggestion. `"None"` Silences An Event. These Entries Live In The Authored Storyboard And Are Applied On Every Run.

```json
"sounds": { "second-ring": { "sound": "Paper Tap", "gain": 0.25 }, "count.count-start": "None" }
```

Moving A Beat Moves Its Event. After Any Change To The Voice Or The Scenes, Run The Timing Tool Again. It Replaces The Placed Cues At Their New Times, Keeps Cues Written By Hand, And Never Doubles Or Drops One.

```sh
node "$SKILL/tools/retime.cjs" my-film/storyboard.json my-film/words.json my-film/storyboard.timed.json --overwrite
node "$SKILL/tools/events.cjs" my-film/storyboard.timed.json
```

| The Tool Prints | Meaning | What To Do |
| --- | --- | --- |
| The Storyboard Carries All Its Event Sounds | The Placed Cues Match The Scenes | Nothing |
| No Scene Declares An Event With A Sound | There Is Nothing To Place | Nothing, Unless Sounds Were Intended |
| None Are Placed | The Storyboard Was Written Without Its Event Sounds | Run The Timing Tool Again |
| Out Of Date | A Scene Module Or A `sounds` Entry Changed After The Last Run | Run The Timing Tool Again |

`--update` Refreshes The Placed Cues Inside The Storyboard Named On The Command Line, With A Safe Write, And Changes Nothing Else In It. It Gives The Same Result As Running The Timing Tool Again, And It Writes Nothing When The Cues Are Already Current. `--place Copy.json` Writes A Separate Copy For Experiments. No Other Tool Or Guide Reads That Copy, So Never Review Or Export It. Preparing A Remotion Project Also Warns When The Placed Sounds Are Missing Or Out Of Date.

## The Sound Mix

```text
Usage: node tools/audio.cjs Storyboard.json [--target -14] [--peak -1.5] [--window 0.4] [--margin 6] [--all-words] [--wav CheckMix.wav] [--report Audio.json] [--strict] [--ffmpeg Path] [--overwrite]
```

An Agent Cannot Hear The Mix, But It Can Measure It. This Tool Builds The Film's Sound In Memory From The Storyboard: The Voice Recording At Its Gain And Offset, Voice Cues With Recordings, And Every Sound Cue With Its Gain And Pan, Each Starting On A Whole Frame As In The Remotion Project. It Measures That Mix With FFmpeg's `ebur128` Filter Through The Null Sink. No Video Is Written, And Nothing Is Changed.

```sh
node "$SKILL/tools/audio.cjs" my-film/storyboard.timed.json --report my-film/audio.json
node "$SKILL/tools/audio.cjs" my-film/storyboard.timed.json --wav my-film/check-mix.wav --overwrite
```

It Reports:

- **Integrated Loudness, Loudness Range, And True Peak** Of The Whole Mix. The Default Targets Are About -14 LUFS Integrated And A True-Peak Ceiling Of -1.5 dBTP. Change Them With `--target` And `--peak` When The Destination Asks For Something Else.
- **Each Cue Against The Voice Under It.** The RMS Level Of The Cue Alone And Of The Voice Alone Over The First Part Of The Cue, And The Difference In Decibels. `--window` Sets That Length In Seconds.
- **Cues On Key Spoken Words.** A Key Word Is A Word That A Scene Cut, A Beat, Or An Anchored Cue Is Tied To. `--all-words` Checks Every Spoken Word Instead. A Cue That Sits On A Key Word And Is Less Than `--margin` Decibels Under The Voice Is Listed To Check, Because It May Mask The Word.
- **The State Of The Event Sounds,** As The Events Tool Reports It.

Everything Is Reported And Never Applied. The Tool Does Not Normalize, Limit, Or Change A Gain. To Act On A Finding, Change A Gain Or A `sounds` Entry In The Authored Storyboard And Run The Timing Tool Again, Or Tell The Owner What The Numbers Show. `--strict` Exits With An Error When Anything Is Listed To Check. `--wav` Writes The Mix As A Stereo WAV For The Owner To Listen To. It Is Sound Only, And It Does Not Replace The Owner's Review.

- Before A Recording Is Attached, The Loudness Is Of The Sound Cues Alone And Is Not Compared With The Target, And Cue Levels Against The Voice Cannot Be Measured. The Report Says So.
- On Stand-In Timing, Word Times Are Estimates, So The Overlaps Move When The Recording Arrives. Run The Tool Again After Retiming.
- The Mix Follows The Remotion Route. Motion Studio Adds A Master Compressor During Its Own Playback And Export, So A Motion Studio Export Can Measure Differently.

## A Finished Export

```text
Usage: node tools/export-check.cjs ExportedFile Storyboard.json [--target -14] [--peak -1.5] [--tolerance 0.15] [--report Check.json] [--strict] [--ffmpeg Path] [--ffprobe Path] [--overwrite]
```

After The Owner Has Approved And Exported, Check The File They Made Against The Storyboard It Came From. The Tool Only Reads The File.

```sh
node "$SKILL/tools/export-check.cjs" my-film-remotion/Final-Cut.mp4 my-film/storyboard.timed.json --report my-film/export-check.json
```

| Check | Passes When |
| --- | --- |
| File Size | The File Is Not Empty |
| Frame Size | The Picture Is The Storyboard's Width And Height |
| Frame Rate | The Average Rate Is Within Half A Frame Per Second Of The Storyboard's |
| Length | The Length Is Within `--tolerance` Seconds Of The Storyboard's, Which Is 0.15 By Default. A Browser Recording That States No Length Is Measured From Its Last Frame. |
| Sound | A Sound Stream Is Present And Not Silent When The Storyboard Has Sound Cues Or A Voice |
| Timing | The Storyboard Is Not On Stand-In Voice Timing |

A Failed Check Exits With An Error And Names What Differs. Loudness Is Measured The Same Way As In The Sound Mix Check And Compared With The Same Defaults, About -14 LUFS And -1.5 dBTP. A Level Outside Them Is Listed To Check, Not Failed, Unless `--strict` Is Set. It Is Reported And Never Applied. A Motion Studio WebM Is Recorded In Real Time, So Allow A Larger `--tolerance` For It And Report The Difference.

## The Kit's Own Checks

These Two Check The Kit Itself, So They Are Run From The Skill Folder.

```sh
node tools/check.cjs
node tools/check-browser.cjs "/path/to/chrome"
```

`check.cjs` Needs Only Node. It Tests The Kit's Maths, Phrase Resolution And Its Error Cases, Caption Checking, Event Collection, The Remotion Painter, And The Determinism Of Every Example Code Scene And Part. It Draws Chosen Frames Twice Into A Recording Context And Compares The Calls. It Fails If A Scene Module Touches `Math.random` Or The Clock. It Runs The Tools On A Film In A Temporary Folder To Prove That The Timed Storyboard And A Remotion Project Prepared From It Carry Their Event Sounds, That Retiming Twice Changes Nothing, That Stand-In Timing Cannot Be Rendered, And That No Tool Writes Into The Skill Folder. It Measures Loudness When FFmpeg Is On PATH And Says So When It Is Not. It Checks That The Guides Agree With Each Other, And It Validates `scenarios/scenarios.json`. `check-browser.cjs` Opens Motion Studio, Runs The Editor, Checks That Export Stays Off On Stand-In Timing, And Opens A Code Scene Film With Its Module. Neither Records A Video.

To Run The Same Determinism Check On A Film From Node, In The User's Project Folder With `SKILL` Set In The Environment:

```js
const Film = require(process.env.SKILL + "/tools/lib/film.cjs");
const { scope, project } = Film.openFilm("my-film/storyboard.timed.json");
console.log(Film.determinism(scope, project));
```

An Empty List Means Every Sampled Frame Drew Identically Twice, No Scene Threw, And No Module Used Randomness Or The Clock. Text Is Measured By A Fixed Estimate In Node, So Judge Layout From Browser Stills.

## What These Tools Do Not Replace

Stills, Numbers, Cue Sheets, And Loudness Figures Are Evidence For The Agent. They Are Not The Owner's Review. Before Any Video Is Exported, The Project Owner Personally Reviews The Editable Project In Remotion Studio With Sound. That Includes Test And Preview Exports. Motion Studio Is The Owner's Review Route Only When Node.js Packages Cannot Be Installed. See The [Skill Guide](SKILL.md).
