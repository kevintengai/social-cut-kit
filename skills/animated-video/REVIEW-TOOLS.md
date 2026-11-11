# Review Tools

Three Tools Let An Agent Inspect A Film Without Exporting It. They Render Individual PNG Stills, Measure Frames In Memory, And List Picture Events. None Of Them Writes A Video. [Review](REVIEW.md) Explains How To Judge What They Show.

Run Them From The Skill Folder With Node.js. The Still And Motion Tools Need The Path To A Local Chrome, Chromium, Or Edge, Passed With `--browser` Or Set In The `MOTION_STUDIO_BROWSER` Environment Variable. Each Tool Reads The Storyboard And The Scene Modules It Lists.

## Stills And Boards

```sh
node tools/stills.cjs Storyboard.json OutputFolder --browser BrowserPath [--times 1,2.5,7] [--every 2] [--scenes] [--strip 3.2] [--strip-frames 7] [--no-captions] [--silent] [--half] [--columns 4] [--overwrite]
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

The Board Is Marked When The Storyboard Uses Stand-In Voice Timing. When A Scene Fails To Draw, The Still Shows An Error Card, The Tool Prints The Message, And It Exits With An Error.

```sh
node tools/stills.cjs examples/an-idea-travels/storyboard.timed.json Board --browser "/path/to/chrome" --half --every 1
node tools/stills.cjs examples/an-idea-travels/storyboard.timed.json Strip --browser "/path/to/chrome" --strip 6.6 --strip-frames 9
node tools/stills.cjs examples/an-idea-travels/storyboard.timed.json Silent --browser "/path/to/chrome" --half --every 1 --silent
```

Read The Contact Sheet As An Image. Look At Individual Stills At Full Size Before Judging Type, Faces, Or Edges.

## Motion And Determinism

```sh
node tools/motion.cjs Storyboard.json --browser BrowserPath [--still 0.75] [--threshold 0.05] [--with-captions] [--determinism] [--report Motion.json] [--overwrite]
```

The Tool Draws Every Frame Small, Compares Each With The One Before It, And Prints The Mean Change For Each Second As A Percentage Of Full Scale. Then It Lists The Stillest Stretches: Runs Where The Change Stays At Or Below `--threshold` For `--still` Seconds Or Longer. Captions Are Hidden Unless `--with-captions` Is Set, So The Numbers Describe The Picture.

- A Long Still Stretch Is A Place Where Nothing Happens On Screen. Decide Whether It Is A Deliberate Hold Or A Stall.
- A Tall Spike In One Second Is A Cut Or A Fast Move. A Spike Where No Cut Is Planned Is A Pop.
- Boiling Grain Or Line Counts As Change. Raise `--threshold` For A Film With A Constant Boil.

`--determinism` Draws A Sample Of Frames From Every Scene Twice, The Second Time In Reverse Order, And Compares The Pixels. Any Difference Fails The Run And Names The Frames. `--report` Saves The Numbers As JSON. Frames Are Compared In Memory And No Image Or Video Is Written.

## Picture Events And Sound

```sh
node tools/events.cjs Storyboard.json [--sheet Events.txt] [--json Events.json] [--place WithSounds.json] [--overwrite]
```

Code Scenes Declare Events From The Same Constants That Draw Them, As Described In [Code Scenes](CODE-SCENES.md). This Tool Gathers Them In Film Order With Times, Positions, And Sounds. With No Options It Prints The Cue Sheet. `--sheet` And `--json` Save It.

`--place` Writes A New Storyboard In Which Every Event With A Sound Is A Timed Sound Cue, Panned To The Event's Position. The Sound Comes From The Scene's `sounds` Entry For The Event `id`, Then For Its `kind`, Then From The Module's Own Suggestion. `"None"` Silences An Event.

```json
"sounds": { "second-ring": { "sound": "Paper Tap", "gain": 0.25 }, "count.count-start": "None" }
```

Moving A Beat Moves Its Event. Run The Tool Again On The Result And The Placed Cues Are Replaced At Their New Times. Cues Added By Hand Are Kept. Use This Order After Any Change To The Voice Or The Scenes:

```sh
node tools/retime.cjs my-film/storyboard.json my-film/words.json my-film/storyboard.timed.json --overwrite
node tools/events.cjs my-film/storyboard.timed.json --place my-film/storyboard.sound.json --overwrite
```

Open The Storyboard With Sounds In Motion Studio To Hear It. An Agent Cannot Hear The Mix. Check That Each Event Has The Sound Intended, And Leave The Listening To The Owner.

## The Kit's Own Checks

```sh
node tools/check.cjs
node tools/check-browser.cjs "/path/to/chrome"
```

`check.cjs` Needs Only Node. It Tests The Kit's Maths, Phrase Resolution And Its Error Cases, Caption Checking, Event Collection, The Remotion Painter, And The Determinism Of Every Example Code Scene And Part. It Draws Chosen Frames Twice Into A Recording Context And Compares The Calls. It Fails If A Scene Module Touches `Math.random` Or The Clock. It Also Validates `scenarios/scenarios.json`. `check-browser.cjs` Opens Motion Studio, Runs The Editor, And Opens A Code Scene Film With Its Module. Neither Records A Video.

To Run The Same Determinism Check On A Film From Node:

```js
const Film = require("./tools/lib/film.cjs");
const { scope, project } = Film.openFilm("my-film/storyboard.timed.json");
console.log(Film.determinism(scope, project));
```

An Empty List Means Every Sampled Frame Drew Identically Twice, No Scene Threw, And No Module Used Randomness Or The Clock. Text Is Measured By A Fixed Estimate In Node, So Judge Layout From Browser Stills.

## What These Tools Do Not Replace

Stills, Numbers, And Cue Sheets Are Evidence For The Agent. They Are Not The Owner's Review. Before Any Video Is Exported, The Project Owner Personally Reviews The Editable Storyboard In Motion Studio With Sound. That Includes Test And Preview Exports. See The [Skill Guide](SKILL.md).
