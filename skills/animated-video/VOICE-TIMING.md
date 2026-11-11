# Voice Timing

Time The Film From The Voice. Scenes, Beats, Sound Cues, And Captions Are Tied To Spoken Phrases In The Storyboard. `tools/retime.cjs` Reads The Word Timings And Writes The Timed Storyboard, With Every Time Resolved And A Sound Cue Placed On Every Picture Event That Has A Sound. When The Recording Or A Scene Changes, Run It Again And The Whole Film Moves.

`storyboard.timed.json` Is The One Storyboard To Check, Prepare For Remotion, Review, And Export. `storyboard.json` Is Its Source. Never Edit The Timed File By Hand.

## The Loop

Keep The Film's Files Together In A Film Folder In The User's Project, As [Code Scenes](CODE-SCENES.md) Describes. Run Commands From The User's Project Folder. `$SKILL` Stands For The Path To This Skill Folder, As In The [Skill Guide](SKILL.md).

```sh
node "$SKILL/tools/standin-words.cjs" my-film/script.txt my-film/words.json --wpm 150
node "$SKILL/tools/retime.cjs" my-film/storyboard.json my-film/words.json my-film/storyboard.timed.json --overwrite
```

1. Write The Script As Plain Text. Lines That Start With `#` And Text In `[Square Brackets]` Are Directions And Are Not Spoken.
2. Before A Recording Exists, Generate Stand-In Word Timings From The Script Text. They Are Estimates At A Chosen Pace, Marked As Stand-Ins In The File, In The Timed Storyboard, In Motion Studio, And On Every Still Board.
3. Anchor The Authored Storyboard To Phrases And Run The Timing Tool. Build And Check Against The Timed Storyboard.
4. When The Recording Exists, Get Its Word Timings As Described Below And Run The Same Command With Them. Change The Authored Storyboard Or A Scene Module, Never The Timed File, And Run The Tool Again.

```sh
node "$SKILL/tools/retime.cjs" my-film/storyboard.json my-film/words.json my-film/storyboard.timed.json --voice my-film/voice.wav --lead 0.2 --tail 0.8 --overwrite
```

Running The Tool Again Is Always Safe. It Starts From The Authored Storyboard Each Time, So Event Sounds Are Never Doubled Or Lost. Cues Written By Hand In The Authored Storyboard Are Kept. A Scene's `sounds` Entries, Including `"None"`, Are Applied On Every Run. A Change Made To A Placed Cue In Motion Studio Lasts Only Until The Next Run, So Make It Permanent With A `sounds` Entry.

```text
Usage: node tools/retime.cjs Storyboard.json Words.json|Words.srt Timed.json [--voice Recording.wav] [--embed-voice] [--lead 0.2] [--offset 0] [--tail 0.6] [--strict] [--no-sounds] [--report Report.json] [--overwrite]
   Or: node tools/retime.cjs Storyboard.json --no-words Timed.json [--no-sounds] [--report Report.json] [--overwrite]
```

- When A Scene Module Is Missing Or Fails To Load, The Tool Still Writes The Times And Prints A Warning That Event Sounds Were Not Placed. Fix The Module And Run It Again Before Review.
- `--no-sounds` Leaves Event Sounds Out. Use It Only To Listen To The Voice Alone, And Run The Tool Again Without It Before Review.
- The Tool Refuses To Write Inside The Skill Folder.

## Get Word Timings From A Recording

Use The First Of These That Applies. The First Two Need No Speech Recognizer.

1. **Word Timings The User Already Has.** A Word-Timed JSON File In Any Form Listed Under **Word Timing Files**. Pass It Straight To The Timing Tool.
2. **Subtitles The User Already Has.** An `.srt` Or `.vtt` File Of The Same Recording. Pass It Straight To The Timing Tool. Word Times Inside Each Cue Are Estimated, So Check Events That Land Mid-Cue.
3. **The Video Edit Skill's Speech Tool.** It Runs A Recognizer That Is Already Installed On The Machine And Writes A Form The Timing Tool Reads.
4. **Stand-Ins.** When None Of The Above Is Possible Yet, Stay On Stand-In Timings And Tell The Owner That The Film Cannot Be Exported Until Real Timings Exist.

**Check What Is Installed.** The Video Edit Skill Sits Beside This One In The Kit. Its Setup Check Prints JSON That Lists Each Tool, Whether It Is Present, And An Install Command Suited To The Machine. It Installs Nothing. Read The Entry Named `speech-recognizer`.

```sh
python "$SKILL/../video-edit/scripts/edit_video.py" setup
```

**Installing Needs The User's Agreement And The Network.** When The Recognizer Is Missing, Show The User The Install Command From The Setup Check And Run It Only After They Agree. A Recognizer Model Is A Separate Download. A Model Name Such As `base` Or `small` Is Fetched On First Use, Which Also Needs The Network. A Model Folder Already On The Machine Works Offline. Never Install Or Download Anything On Your Own Initiative.

**Transcribe.** `speech.py transcribe` Takes The Recording And A New Output File. It Supports Two Recognizers, Chosen With `--backend`. Its Other Options Are `--model`, `--language`, And `--engine`. It Does Not Replace An Existing Output File.

| Recognizer | Command | Notes |
| --- | --- | --- |
| The `faster-whisper` Python Package | `--backend faster-whisper --model small` | `--model` Is A Model Name Or A Local Model Folder. |
| An Installed `whisper` Command | `--backend whisper-cli --model small` | This Is The Default Backend. `--engine` Names The Command When It Is Not Called `whisper`. |

```sh
python "$SKILL/../video-edit/scripts/speech.py" transcribe my-film/voice.wav my-film/words.json --backend faster-whisper --model small --language en
python "$SKILL/../video-edit/scripts/speech.py" transcribe my-film/voice.wav my-film/words.json --backend whisper-cli --model small --language en
```

With A Model Folder Already On The Machine, Give Its Path. Quote Paths That Contain Spaces.

```sh
python "$SKILL/../video-edit/scripts/speech.py" transcribe my-film/voice.wav my-film/words.json --backend faster-whisper --model "$HOME/models/faster-whisper-small"
```

```powershell
python "$SKILL/../video-edit/scripts/speech.py" transcribe my-film/voice.wav my-film/words.json --backend faster-whisper --model "C:/Models/faster-whisper-small"
```

**When Only The Video Edit Skill Is Missing.** The Timing Tool Does Not Depend On It. Use Timings Or Subtitles The User Already Has. If A `whisper` Command Is Installed, Run It Directly With `--word_timestamps True --output_format json` And Pass The JSON It Writes To The Timing Tool, Which Reads Recognizer Segments. Any Other Recognizer That Writes Word-Level JSON In A Listed Form, Or Subtitles, Also Works. Otherwise Ask The User Whether To Install The Kit's Video Edit Skill, And Stay On Stand-Ins Until They Decide.

Check A Transcript Against The Script Before Trusting It. A Recognizer Can Mishear A Name Or Split A Number, And A Phrase Anchor Must Match The Words As Transcribed.

## Stand-In Timing Is Not Ready For Export

Stand-In Timings Are A Guess At A Recording That Does Not Exist Yet. They Are For Building And Checking Stills. The Timed Storyboard Carries The Mark, And The Tools Enforce It.

- `adapter/prepare-remotion.cjs` Prepares The Project For Looking At, And Prints A Warning.
- The Reviewed Render Inside The Remotion Project Refuses To Run.
- Motion Studio Plays And Reviews The Storyboard, And Keeps **Export Approved Video** Off.
- The Still Boards, The Sound Check, And The Export Check All Name It.

The Mark Clears Only When The Timing Tool Runs With Word Timings That Are Not Stand-Ins. Do Not Remove It By Hand.

## A Film With No Narration

Some Films Will Never Have A Spoken Voice: A Text-Led Film Where The Viewer Reads The Words On Screen, Or A Music-Led Film Cut To A Track. Their Timings Are Decisions The Author Makes, Not Guesses At A Recording. Declare This In The Authored Storyboard.

```json
{ "version": 1, "title": "Three Steps", "narration": "None", "scenes": [{ "mode": "Code Scene", "draw": "Step One", "duration": 3 }] }
```

| Kind Of Film | How It Is Timed | Command |
| --- | --- | --- |
| Text-Led, With Phrases | Make Reading Timings From The On-Screen Text At The Pace A Viewer Reads, Then Anchor Scenes, Beats, And Captions To Those Phrases As Usual. | `standin-words.cjs` With `--wpm`, Then `retime.cjs` With The Words File |
| Timed By Numbers | Give Every Scene A `duration`, Every Beat A Time In Seconds, And Every Caption Line `at` And `end`. Use No Phrases. | `retime.cjs` With `--no-words` |

```sh
node "$SKILL/tools/retime.cjs" my-film/storyboard.json --no-words my-film/storyboard.timed.json --overwrite
```

- With `"narration": "None"`, Word Timings Made From The Script Are Treated As The Author's Reading Pace. The Timed Storyboard Is Not Marked As Stand-In, So It Can Be Reviewed And Exported.
- `--no-words` Needs The Declaration, And Names Every Phrase That Still Needs Word Timings.
- For A Music-Led Film, Name The Track In The Authored Storyboard As `"voice": { "file": "music.wav", "gain": 0.8 }`. It Plays Across The Whole Film, And `s.voice` Follows Its Level Only When The Timing Tool Is Run With `--voice`.
- The Declaration Is Shown To The Owner: On Still Boards, In Motion Studio, When The Remotion Project Is Prepared, And Before The Reviewed Render Asks For Approval.

**How This Differs From Stand-In Timing.** Stand-In Timing Says A Recording Is Coming And The Times Will Change. No Narration Says There Will Never Be A Recording And The Times Are Final. Only The Owner Decides Which Film This Is. Never Use It To Get Past A Missing Recording. When The Owner Intends Narration, The Film Stays On Stand-In Timing, And Stays Unexportable, Until The Recording Arrives. When Unsure, Ask.

## Word Timing Files

| Source | Form |
| --- | --- |
| The Video Edit Speech Tool | `{ "words": [{ "start": 0.42, "end": 0.61, "text": "Every" }] }` From `speech.py transcribe` |
| A Plain List | `[{ "word": "Every", "start": 0.42, "end": 0.61 }]`. `text` Works In Place Of `word`. |
| Recognizer Segments | `{ "segments": [{ "words": [...] }] }` |
| Subtitles | An `.srt` Or `.vtt` File. Word Times Inside Each Cue Are Estimated By Word Length, And The Tool Says So. |
| Stand-Ins | The Output Of `tools/standin-words.cjs`, Which Adds `"standIn": true`. |

## Anchors

An Anchor Names Spoken Words. Matching Ignores Case, Punctuation, Accents, And Apostrophes.

```json
{ "phrase": "tells three", "occurrence": 2, "edge": "end", "offset": -0.15 }
```

`occurrence` Picks One When The Phrase Repeats, Counting From One Across The Whole Recording. `edge` Is `"start"` Or `"end"` Of The Phrase. `offset` Adds Seconds. A Bare String Such As `"tells three"` Is Shorthand For An Anchor With Only A Phrase.

| Where | Field | Resolves To |
| --- | --- | --- |
| A Scene | `"start": { "phrase": "say it out loud", "offset": -0.15 }` | The Cut Into The Scene. The First Scene Always Starts At Zero. |
| A Scene | `"end": { "phrase": "knows", "offset": 1.6 }` | The Cut Out Of The Scene, At The End Of The Phrase. Use It On The Last Scene To Set The Film's Length. |
| A Beat | `"beats": { "pop": "pops up" }` | `at`, In Seconds Since The Scene Began. A Draw Function Reads It With `s.beat("pop")`. |
| A Cue | `{ "type": "Sound", "sound": "Paper Tap", "anchor": "tap" }` | The Cue's `at` Within Its Scene. |
| A Picture Event | Declared By The Scene Module, As [Code Scenes](CODE-SCENES.md) Describes | A Sound Cue Placed At The Event's Time, Replaced On Every Run. |
| A Caption Line | `{ "text": "Every Idea Starts Small." }` | `at`, `end`, And A Start Time For Each Word. |

Scenes Without An Anchor Keep Their Share. Unanchored Scenes Between Two Anchored Cuts Divide The Time Between Those Cuts In Proportion To Their Authored Durations. Scenes After The Last Anchored Cut Keep Their Authored Durations.

## When The Tool Stops

The Tool Collects Every Problem, Names Each One, And Writes Nothing.

- **Unknown Phrase.** The Words Are Not In The Timings. The Message Shows The Nearest Spoken Words And Their Time.
- **Ambiguous Phrase.** The Phrase Is Spoken More Than Once And No `occurrence` Was Given. The Message Lists The Times. A Beat Or Cue Is Not Ambiguous When Its Phrase Is Spoken Exactly Once Inside Its Own Scene.
- **Occurrence Out Of Range.** The Phrase Is Spoken Fewer Times Than The Number Asked For.
- **Cuts Out Of Order Or Too Close.** A Scene Would Start Before The One Ahead Of It, Or Last Under A Quarter Second.
- **A Cue Outside Its Scene.** Move The Cue To The Scene That Contains The Phrase.
- **A Start Anchor On The First Scene, Or Two Anchors On One Cut.**

## Captions

Captions Are A Project-Level Track Of Hand-Written Lines. The Painter Draws Them Over Every Scene Kind, Inside The Storyboard's Safe Area.

```json
"captions": {
  "style": { "mode": "Word Highlight", "position": "Bottom", "highlight": "#ffd166" },
  "lines": [
    { "text": "Every Idea Starts Small." },
    { "text": "3 Friends Hear It.", "phrase": "one friend tells three" },
    { "text": "A Sign On Screen", "at": 6.2, "end": 7.4 }
  ]
}
```

- A Line With Only `text` Is Anchored To Its Own Words.
- A Line With `phrase` Is Anchored To Those Spoken Words And May Show Different Text. Add `until` With A Closing Phrase To Stretch It.
- A Line With `at` And `end` And No `phrase` Is A Fixed Time Range That The Tool Leaves Alone.
- Lines Are Matched In Order. A Repeated Phrase Takes Its First Occurrence After The Line Above. Add `occurrence` To Override.
- A Line Ends A Short Hold After Its Last Word And Never Overlaps The Next Line.

The Tool Checks Each Anchored Line's Words Against The Words Spoken In Its Range. It Prints Every Mismatch With The Shown And Spoken Text, And Lists Words Spoken With No Caption. Mismatches Do Not Stop The Run Unless `--strict` Is Set. Read Them All. A Deliberate Difference, Such As A Numeral For A Spoken Number, Is Fine. An Unplanned One Is A Typo Or A Changed Script.

| Style Option | Values |
| --- | --- |
| `mode` | `"Line"` Shows The Whole Line. `"Word Build"` Adds Each Word As It Is Spoken. `"Word Highlight"` Colors The Word Being Spoken. |
| `position` | `"Bottom"`, `"Center"`, `"Top"`, Measured From The Safe Area |
| `motion` | `"Pop"`, `"Rise"`, `"None"` |
| `case` | `"As Written"`, `"Upper"` |
| `font`, `weight` | `"Arial"`, `"Georgia"`, `"Verdana"`, `"Tahoma"`, `"Trebuchet MS"`. Weights 400 To 900. Availability Depends On The Machine. |
| `size`, `stroke` | Output Pixels. The Default Size Is 5.2% Of The Short Side. |
| `color`, `outline`, `highlight`, `plate`, `plateOpacity` | Six-Digit Hex Colors. `plate` Draws A Rounded Panel Behind The Text. |
| `width`, `maxLines`, `margin` | The Share Of The Safe Width A Line May Use, The Most Rows Before The Text Shrinks, And Extra Distance From The Safe Edge As A Share Of Frame Height |
| `hold`, `minimum` | Seconds A Line Stays After Its Last Word, And Its Shortest Time On Screen |

Captions Can Be Switched Off For Silent Review. In Motion Studio, Clear **Show Captions**. In The Still And Motion Tools, Use `--no-captions` Or `--silent`. A Storyboard With No `captions` Entry Draws None.

## The Film Voice

The Timed Storyboard Carries A `voice` Entry With The Words, A Level Track, And The Recording.

- `--voice Recording.wav` Names The Recording Beside The Timed Storyboard. It Travels Into The Remotion Project, And Motion Studio Loads It When The Film Folder Is Opened. It Plays Across Every Scene. Add `--embed-voice` To Store A Recording Under 20 MiB Inside The JSON Instead.
- The Level Track Feeds `s.voice` In Code Scenes, Such As A Character's Mouth. It Is Measured From An Uncompressed WAV. For Other Formats, And For Stand-Ins, It Is Estimated From The Word Timings, And The Tool Says So.
- `--lead 0.2` Starts The Film So The First Word Lands At 0.2 Seconds, Skipping Leading Silence In The Recording. `--offset` Sets The Recording's Start In The Film Directly. `--tail 0.8` Ends The Film 0.8 Seconds After The Last Word When The Last Scene Has No `end` Anchor.
- `--report Report.json` Saves The Scene Times, Mismatches, And Notes.

Run The Stills Again After Every Retime. A New Recording Changes Where Every Event Lands. Before Any Export, The Project Owner Personally Reviews The Film Prepared From The Timed Storyboard In Remotion Studio, With The Real Recording, As Described In The [Skill Guide](SKILL.md). That Includes Test And Preview Exports. Motion Studio Is The Owner's Review Route Only When Node.js Packages Cannot Be Installed. Stand-In Timing Is For Building, Not For Export.
