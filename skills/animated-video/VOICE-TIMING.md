# Voice Timing

Time The Film From The Voice. Scenes, Beats, Sound Cues, And Captions Are Tied To Spoken Phrases In The Storyboard. `tools/retime.cjs` Reads The Word Timings And Writes A New Storyboard With Every Time Resolved. When The Recording Changes, Run It Again And The Whole Film Moves.

## The Loop

Run Commands From The Skill Folder. Keep The Film's Files Together As Described In [Code Scenes](CODE-SCENES.md).

```sh
node tools/standin-words.cjs my-film/script.txt my-film/words.json --wpm 150
node tools/retime.cjs my-film/storyboard.json my-film/words.json my-film/storyboard.timed.json --overwrite
```

1. Write The Script As Plain Text. Lines That Start With `#` And Text In `[Square Brackets]` Are Directions And Are Not Spoken.
2. Before A Recording Exists, Generate Placeholder Word Timings From The Script Text. They Are Estimates At A Chosen Pace, Marked As Stand-Ins In The File, In The Timed Storyboard, In Motion Studio, And On Every Still Board.
3. Anchor The Authored Storyboard To Phrases And Retime It. Build And Review Against The Timed Storyboard.
4. When The Recording Exists, Get Its Word Timings And Run The Same Retime Command With Them. Never Edit The Timed Storyboard By Hand. Change The Authored One And Run The Tool Again.

```sh
python ../video-edit/scripts/speech.py transcribe my-film/voice.wav my-film/words.json --backend faster-whisper --model /path/to/model
node tools/retime.cjs my-film/storyboard.json my-film/words.json my-film/storyboard.timed.json --voice my-film/voice.wav --lead 0.2 --tail 0.8 --overwrite
```

Check A Transcript Against The Script Before Trusting It. A Recognizer Can Mishear A Name Or Split A Number, And A Phrase Anchor Must Match The Words As Transcribed.

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

- `--voice Recording.wav` Names The Recording Beside The Timed Storyboard. Motion Studio Loads It When The Film Folder Is Opened, And Plays It Across Every Scene. Add `--embed-voice` To Store A Recording Under 20 MiB Inside The JSON Instead.
- The Level Track Feeds `s.voice` In Code Scenes, Such As A Character's Mouth. It Is Measured From An Uncompressed WAV. For Other Formats, And For Stand-Ins, It Is Estimated From The Word Timings, And The Tool Says So.
- `--lead 0.2` Starts The Film So The First Word Lands At 0.2 Seconds, Skipping Leading Silence In The Recording. `--offset` Sets The Recording's Start In The Film Directly. `--tail 0.8` Ends The Film 0.8 Seconds After The Last Word When The Last Scene Has No `end` Anchor.
- `--report Report.json` Saves The Scene Times, Mismatches, And Notes.

Run The Stills Again After Every Retime. A New Recording Changes Where Every Event Lands. Before Any Export, The Project Owner Personally Reviews The Timed Storyboard In Motion Studio With The Real Recording, As Described In The [Skill Guide](SKILL.md). Stand-In Timing Is For Building, Not For Export.
