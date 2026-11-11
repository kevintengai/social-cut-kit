# Code Scenes

A Code Scene Is A Storyboard Scene Whose Picture Is Drawn By A JavaScript Function Written For The Film. Use It For Anything The Three Built-In Scene Kinds Cannot Show. The Same Function Draws In Motion Studio, In The Still And Motion Tools, In Node Checks, And In The Remotion Project. Plan The Film In [Directing](DIRECTING.md) First. Time It With [Voice Timing](VOICE-TIMING.md). Check It With [Review Tools](REVIEW-TOOLS.md).

## The Shape Of A Film Folder

Keep One Folder Per Film. It Lives In The User's Project, Never Inside The Skill Folder. The Bundled Examples Are Read-Only Starting Points: Copy One Out And Edit The Copy. The Tools Refuse To Write Inside The Skill Folder. The Storyboard Lists Its Scene Modules By Relative Path, And Every Tool Finds Them Beside It.

```text
my-film/
  script.txt               The Spoken Words, Or The On-Screen Words Of A Film With No Narration.
  words.json               Word Timings, Stand-In Or From The Recording.
  storyboard.json          The Authored Storyboard. Edit This One.
  storyboard.timed.json    Written By tools/retime.cjs, With Event Sounds In Place. Check, Review, And Export This One.
  scenes/intro.js          A Scene Module.
  voice.wav                The Recording, Once It Exists.
  board/                   Stills From tools/stills.cjs.
```

There Is One Storyboard To Review. `storyboard.json` Is The Source, And `storyboard.timed.json` Is What The Timing Tool Builds From It: Every Time Resolved, And A Sound Cue Placed On Every Picture Event That Has A Sound. Every Tool Reads The Timed File, The Remotion Project Is Prepared From It, And The Owner Reviews And Exports It. Never Edit It By Hand. Change The Authored Storyboard Or A Scene Module, And Run The Timing Tool Again.

To Look At A Film While Building It, Open [Motion Studio](studio/index.html), Select **Open Film Folder**, And Pick The Folder. The Editor Opens The Timed Storyboard When One Exists, Loads The Listed Modules, And Loads A Voice Recording Named In The Storyboard. **Open Storyboard** Also Accepts The JSON File And Its Module Files Selected Together. A Page Opened From Disk Cannot Fetch Files, So The Modules Always Arrive Through One Of These Pickers. Opening A Folder Again Reloads Edited Modules.

## A Complete Small Example

This Is [First Code Scene](examples/first-code-scene/storyboard.json). Copy The Folder Into The User's Project, Rename The Draw Function, And Change What It Draws.

`storyboard.json`

```json
{
  "version": 1,
  "title": "First Code Scene",
  "aspect": "Portrait",
  "fps": 30,
  "modules": ["scenes/pulse.js"],
  "scenes": [
    {
      "mode": "Code Scene",
      "draw": "First Pulse",
      "duration": 4,
      "title": "First Pulse",
      "background": "#14202b",
      "foreground": "#f4f6f9",
      "accent": "#8fefa8",
      "params": { "title": "Draw It In Code" }
    }
  ]
}
```

`scenes/pulse.js`

```js
(function () {
  "use strict";
  // Times In Seconds Since The Scene Began. The Picture And The Events Both Read These.
  const LINE_STARTS = 0.4, LINE_SECONDS = 1.4, DOT_LANDS = LINE_STARTS + LINE_SECONDS;

  function draw(c, s) {
    const k = s.kit, u = s.unit, p = s.params;

    // The Title: Each Word Rises In, One After Another.
    const block = k.layoutWords(c, p.title, { width: s.safe.w, size: u * 11, weight: 800 });
    c.fillStyle = s.colors.foreground; c.textAlign = "left"; c.textBaseline = "middle";
    for (const word of block.words) {
      const q = k.stagger(s.time, word.index, { start: 0.15, each: 0.09, duration: 0.5, ease: "outCubic" });
      c.globalAlpha = q;
      c.fillText(word.text, s.safe.left + word.x, s.safe.top + u * 12 + word.y + (1 - q) * u * 3);
    }
    c.globalAlpha = 1;

    // The Line: A Smooth Curve That Draws On From Left To Right.
    const y = s.safe.top + s.safe.h * 0.62;
    const curve = k.splinePoints([[s.safe.left, y], [s.safe.left + s.safe.w * 0.3, y - u * 14], [s.safe.left + s.safe.w * 0.62, y + u * 9], [s.safe.right - u * 6, y - u * 6]]);
    c.strokeStyle = s.colors.accent; c.lineWidth = u * 1.1; c.lineCap = "round"; c.lineJoin = "round";
    const tip = k.drawOn(c, curve, k.ease.inOutCubic(k.between(s.time, LINE_STARTS, LINE_STARTS + LINE_SECONDS)));

    // The Dot: Rides The Tip Of The Line, Then Settles With A Spring When The Line Ends.
    if (tip) {
      const radius = u * 2.2 * (s.time < DOT_LANDS ? 1 : k.spring(s.time - DOT_LANDS, { from: 1.9, to: 1, stiffness: 260, damping: 14 }));
      c.fillStyle = s.colors.accent;
      c.beginPath(); c.arc(tip.x, tip.y, radius, 0, k.TAU); c.fill();
    }
    k.grain(c, s, { amount: 0.05, seed: s.seed, step: k.boilStep(s.time, 8) });
  }

  // What Happens In The Picture, For The Sound Cue Sheet.
  function events(s) {
    return [
      { id: "line-starts", at: LINE_STARTS, what: "The Line Starts To Draw", kind: "travel", pan: -0.8, sound: "Air Sweep", gain: 0.5 },
      { id: "dot-lands", at: DOT_LANDS, what: "The Dot Lands", kind: "land", pan: 0.7, sound: "Glass Point", gain: 0.6 }
    ];
  }

  MotionScenes.register("First Pulse", draw, { events, defaults: { title: "Draw It In Code" } });
})();
```

Copy It Into The User's Project And Render It There. `$SKILL` Stands For The Path To This Skill Folder, As In The [Skill Guide](SKILL.md). Stills Are Images, Not Video, So This Needs No Approval.

```sh
cp -r "$SKILL/examples/first-code-scene" my-film
node "$SKILL/tools/stills.cjs" my-film/storyboard.json my-film/board --browser "/path/to/chrome" --half --times 0.5,1.2,1.9,3
```

In PowerShell, Copy The Folder With `Copy-Item -Recurse "$SKILL/examples/first-code-scene" my-film`.

## Rules For A Scene Module

- Wrap The File In A Function, As Above, So Its Names Stay Private. Use Only The Bare Names `MotionScenes` And `MotionKit`. Do Not Use `window`, `document`, Or `globalThis`.
- Register Each Draw Function Once Under A Name. One Module May Register Several. The Scene's `draw` Field Names The One It Uses.
- A Draw Function Is A Pure Function Of Its State. The Same State Must Draw The Same Frame Every Time, In Any Order. Do Not Call `Math.random`, `Date`, `performance.now`, Or Timers. Do Not Keep Counters, Caches, Or Previous Positions Between Calls. The Checks Draw Frames Twice In Two Orders And Fail On Any Difference.
- Compute Every Position From `s.time`. Never Add A Step Per Frame.
- Draw In Output Pixels, Using `s.width` And `s.height`. The Context Is Already Scaled, So The Same Code Fills A Half-Size Still And A Full-Size Export. Size Things From `s.unit`, Which Is One Percent Of The Short Side, So The Scene Survives A Change Of Aspect Ratio.
- The Painter Fills The Scene's Backdrop Color Before Calling The Draw Function, Balances Every `save` The Function Leaves Open, And Draws Captions Afterward.
- When A Draw Function Throws, The Frame Shows A Card With The Message. The Still, Motion, And Check Tools Report It And Fail.
- Do Not Read Pixels Back From The Canvas.

## The State

| Field | Meaning |
| --- | --- |
| `width`, `height`, `cx`, `cy`, `min`, `max`, `unit`, `aspect`, `portrait`, `landscape` | The Frame In Output Pixels. `unit` Is One Percent Of The Short Side. |
| `safe` | The Safe Area As `{ x, y, w, h, left, top, right, bottom, cx, cy }`. It Follows The Storyboard's `safe` Setting. Keep Text And Faces Inside It. |
| `time`, `duration`, `progress`, `remaining` | Seconds Since The Scene Began, The Scene's Length, And Progress From 0 To 1. `t` Is A Short Name For `time`. |
| `globalTime`, `frame`, `fps` | Seconds Since The Film Began, The Film Frame Number, And The Frame Rate. |
| `params` | The Scene's `params` From The Storyboard, Laid Over The `defaults` Given At Registration. It Is Read-Only. |
| `colors`, `text` | The Scene's `background`, `foreground`, And `accent`, And Its `eyebrow`, `title`, And `body`. These Are Editable In Motion Studio. |
| `scene` | `{ index, id, count, name, film }`. |
| `seed`, `random()`, `rng(key)` | Deterministic Randomness. `random()` Replays The Same Sequence On Every Frame, Which Suits Placement. `rng("stars")` Gives An Independent Generator With `range`, `int`, `pick`, `sign`, `chance`, `gauss`, And `shuffle`. Set A Scene's `seed` Number To Change The Pattern. |
| `voice`, `voiceAt(seconds)` | The Speech Level From 0 To 1 Now, Or At Another Scene Time. |
| `words` | The Words Spoken During The Scene As `{ text, start, end }` In Scene Seconds. |
| `beat(name, fallback)`, `since(name)`, `when(value, fallback)` | The Phrase Cue Lookup. `beat` Returns The Scene Time Of A Named Beat From The Storyboard. `since` Is `time` Minus That. `when` Accepts Seconds Or A Beat Name, Which Lets A Parameter Hold Either. An Unknown Beat With No Fallback Is An Error. |
| `phrase(text, occurrence)` | Looks Up A Spoken Phrase Directly And Returns Scene Seconds. Prefer A Named Beat, Which The Timing Tool Checks Before Anything Is Drawn. |
| `kit`, `space` | The Drawing Kit And The 3D Helpers. |
| `use(c, name, params, box)` | Draws Another Registered Draw Function, Such As A [Part](PARTS.md), Inside A Box `{ x, y, w, h, start, duration, clip, key }`. `start` Delays It Within The Scene. |
| `events(name, params, box)` | Inside An Events Function, Returns The Events Of A Draw Function Used In A Box, With Times And Positions Mapped To This Scene. |

## Scene Fields In The Storyboard

| Field | Meaning |
| --- | --- |
| `mode`, `draw`, `params`, `seed` | `"Code Scene"`, The Registered Name, A JSON Object Of The Film's Own Values, And An Optional Number That Changes The Random Pattern. |
| `duration` | Seconds, From 0.25 To 600. The Timing Tool Rewrites It When The Scene Is Anchored. |
| `start`, `end` | Phrase Anchors For The Cut Into And Out Of The Scene. See [Voice Timing](VOICE-TIMING.md). |
| `beats` | Named Moments. `{ "pop": "pops up", "hold": 1.5 }` Ties One To A Phrase And Gives The Other A Fixed Scene Time. |
| `sounds` | Sound Choices For The Scene's Events, By Event `id` Or `kind`. `"None"` Silences One. These Survive Every Retime. |
| `cues` | Timed Sound And Voice Cues, As In Any Scene. A Cue May Carry An `anchor` Phrase And A `pan` From -1 To 1. |

At The Top Level, `modules` Lists The Scene Modules, `safe` Chooses The Safe Area, `aspect` May Be `"Custom"` With `"size": [1080, 1350]` For Any Even Size From 240 To 4096, And `captions`, `voice`, And `narration` Are Described In [Voice Timing](VOICE-TIMING.md). A Hand-Written Scene Needs Only The Fields It Uses. The Editor And Tools Fill In The Rest.

| Safe Area | Margins: Top, Right, Bottom, Left |
| --- | --- |
| `"Title Safe"` (Used When None Is Set) | 5%, 5%, 5%, 5% |
| `"Vertical Feed"` | 13%, 14%, 24%, 6% |
| `"TikTok"` | 8%, 13%, 24%, 6% |
| `"Reels"` | 13%, 10%, 22%, 6% |
| `"Shorts"` | 12%, 14%, 24%, 6% |
| `"None"` | 0% |

The Platform Rows Are Conservative Estimates Written For This Kit, Not Published Figures. Platform Interfaces Change. Check A Still On A Phone, Or Set Your Own Margins With `"safe": { "top": 0.1, "right": 0.1, "bottom": 0.2, "left": 0.06 }`.

## The Drawing Kit

Reach The Kit As `s.kit`. Every Helper Is A Pure Function. [kit.js](studio/kit.js) Holds The Source And A Comment On Each One.

| Group | Helpers |
| --- | --- |
| Numbers | `clamp`, `lerp`, `unlerp`, `remap`, `between(t, start, end)`, `smooth`, `wrap`, `snap`, `rad`, `deg`, `pulse`, `TAU` |
| Easing | `ease.outCubic` And 29 More Curves, `easing(name)`, `bezier(x1, y1, x2, y2)`, `steps(count)`, `tween(t, start, duration, from, to, ease)` |
| Spring | `spring(t, { from, to, stiffness, damping, mass, velocity })`, Or A Preset Name: `soft`, `smooth`, `snappy`, `bouncy`, `heavy`. It Is A Closed Form, So Any Frame Can Be Computed Alone. |
| Stagger | `stagger(t, index, { start, each, duration, ease })` |
| Random And Noise | `rng(seed)`, `rand(...keys)`, `hash(...keys)`, `noise(x, seed)`, `noise2(x, y, seed)`, `fbm(x, y, options)` |
| Keyframe Tracks | `track(keys, t)` With Keys As `[time, value, ease]`. Values May Be Numbers, Lists, Objects Of Numbers, Or Colors. The Easing On A Key Shapes The Move That Arrives At It. |
| Camera | `camera(s, { x, y, zoom, rotate }, ...extras)` With `begin(c, depth)`, `end(c)`, `layer(c, depth, paint)`, `toScreen`, `toWorld`, And `bounds`. Add `drift(t, options)` For A Hand-Held Wander And `shake(t, { at, duration, amount })` For A Hit. Depth 1 Follows The Camera, Depth 0 Stays Pinned To The Frame, And Values Between Give Parallax. Use `track` For Eased Camera Moves. |
| Paths | A Path Is A List Of `[x, y]` Points. Build One With `linePoints`, `arcPoints`, `circlePoints`, `ellipsePoints`, `quadPoints`, `cubicPoints`, `splinePoints`, `polygonPoints`, `starPoints`, `rectPoints`, Or `tornRect`. Measure And Cut With `pathLength`, `pointAt`, `slicePath`, And `resample`. Draw With `tracePath`, `drawOn(c, points, progress)`, `ribbon(c, points, options)`, `roundRect`, And `arrowHead`. |
| Hand-Made Looks | `boilPath(points, { amount, seed, step })`, `boilStep(time, rate)`, `stepTime(time, fps, frames)` For Held Drawings, `grain(c, s, options)`, `vignette(c, s, options)` |
| Limbs | `joint(ax, ay, bx, by, upper, lower, bend)` Finds A Knee Or Elbow From Two Ends And Fixed Bone Lengths. |
| Text | `font(size, weight, family)`, `wrapText(c, text, width)`, `fitText(c, text, { width, height, size, maxLines })`, `drawText(c, layout, x, y, { align, valign })`, `layoutWords(c, text, box)` For Word-By-Word Animation, `typeOn(text, progress)` |
| Counters | `count(from, to, progress, ease)`, `formatNumber(value, { decimals, group, prefix, suffix, pad })` |
| Color | `parseColor`, `rgba(color, alpha)`, `mixColor(a, b, t)`, `lighten`, `darken`, `hsl`, `toHsl`, `shiftHue`, `luminance`, `contrast`, `readable(background)`, `ramp(colors, t)` |

Text Uses Fonts Installed On The Machine. Name A Family With A Fallback, Such As `"Georgia, serif"`, And Check The Stills On The Machine That Will Export.

## 3D In A Code Scene

`s.space` Is The Same Software Renderer That Draws The Built-In 3D Object, With Helpers For A Scene's Own Geometry And Camera. Y Points Up.

```js
const space = s.space;
const view = space.view({ cx: s.cx, cy: s.cy, size: s.min * 0.5, yaw: -30 + 40 * s.progress, pitch: 30, distance: 9 });
space.render(c, view, [
  { mesh: space.plane(6, 6), color: "#d8d2c4", flat: true, twoSided: true },
  { mesh: space.box(1, 2, 1), color: s.colors.accent, gloss: 0.3, place: { position: [0, 1, 0], rotate: [0, 25, 0] } }
], { yaw: -50, elevation: 52, color: "#fff4dc", intensity: 1 });
```

| Helper | Use |
| --- | --- |
| `box`, `plane`, `sphere`, `cylinder`, `torus`, `extrude(outline, depth)`, `faces(name)` | Meshes. A Cylinder With A Top Radius Of Zero Is A Cone. `faces` Returns A Built-In Prism, Orbit Ring, Or Crystal. |
| `place({ position, rotate, scale })` | Positions A Mesh. Rotation Is In Degrees Around X, Then Y, Then Z. |
| `view({ cx, cy, size, yaw, pitch, distance, target })` | A Perspective Camera With `project(point)` And `scaleAt(point)`. |
| `light({ yaw, elevation, color, intensity, ambient })` | A Directional Key Light. |
| `render(c, view, items, light)` | Draws Lit Faces From Far To Near. An Item Takes `mesh`, `color`, `gloss`, `place`, `flat`, `twoSided`, `opacity`, And `outline`. |
| `path(c, view, points, closed)` | Strokes A Line Through 3D Points. |

Faces Are Sorted Whole, So Keep Meshes From Passing Through Each Other. For A Physical Product That Must Look Real, Use The [Blender Scene](blender/README.md).

## Events

An Events Function Returns What Happens In The Picture: `{ id, at, what, kind, pan, sound, gain }`. `at` Is Scene Seconds, `what` Is A Plain Description, `pan` Runs From -1 At The Left Edge To 1 At The Right, And `sound` Suggests One Of The Seven Bank Sounds. Compute `at` From The Same Constants And Beats The Draw Function Uses. The Timing Tool Then Places A Sound Cue On Each Event In `storyboard.timed.json`, And The Sounds Move When The Picture Moves. `tools/events.cjs` Lists Them And Says Whether They Are Current. See [Review Tools](REVIEW-TOOLS.md).

## A Larger Example

[An Idea Travels](examples/an-idea-travels/storyboard.json) Is A Twelve-Second Voiced Film In Four Scenes. Its [Scene Module](examples/an-idea-travels/scenes/idea.js) Shows Words Rising In Time With Speech, A Part Used Inside A Scene, A Camera Pull-Back With A Parallax Layer, Custom 3D Geometry, Beats, Events, And Captions. Open The Folder In Motion Studio With **Open Film Folder** To Study It. It Is A Bundled Example, So Copy It Out Before Changing Anything.

## Before Any Export

Run `node "$SKILL/tools/check.cjs"` For The Kit, And The Still, Motion, Event, And Sound Tools For The Film. Then Prepare A Remotion Project From `storyboard.timed.json` And Give It To The Project Owner. The Owner Personally Reviews The Editable Project In Remotion Studio Before Any Video Is Exported. That Includes Test And Preview Exports. Motion Studio Is The Owner's Review Route Only When Node.js Packages Cannot Be Installed. Follow The Review And Export Section Of The [Skill Guide](SKILL.md).
