# Parts

Parts Are Ready-Made Code Scenes With A Neutral Look. Four Ship With The Kit And Are Always Loaded, So A Storyboard Can Name One As A Scene's `draw` Without Listing A Module. Use A Part When It Is The Right Picture For The Claim, As [Directing](DIRECTING.md) Says, Then Redress It In The Look Chosen From [Style Frames](STYLE-FRAMES.md).

| Part | Draw Name | Source | Example Storyboard |
| --- | --- | --- | --- |
| Globe | `Globe` | [parts/globe.js](parts/globe.js) | [part-globe.json](examples/part-globe.json) |
| Phone | `Phone` | [parts/phone.js](parts/phone.js) | [part-phone.json](examples/part-phone.json) |
| Doodle Character | `Doodle Character` | [parts/character.js](parts/character.js) | [part-character.json](examples/part-character.json) |
| Chart | `Chart` | [parts/chart.js](parts/chart.js) | [part-chart.json](examples/part-chart.json) |

Open An Example In Motion Studio With **Open Storyboard**. Each Source File Begins With A Comment That Documents Every Option, Its Events, And A Sample Scene. That Comment Is The Reference. This Page Is The Overview.

## Three Ways To Use A Part

**As A Whole Scene.** Name It In The Storyboard And Set Its Options In `params`. The Scene's Backdrop, Type, And Accent Colors Give The Part Its Palette.

```json
{ "mode": "Code Scene", "draw": "Chart", "duration": 5, "background": "#f4efe6", "foreground": "#1c2630", "accent": "#e2572b",
  "params": { "kind": "Bars", "title": "Orders Per Week", "highlight": 3,
    "data": [{ "label": "Week One", "value": 120 }, { "label": "Week Two", "value": 190 }, { "label": "Week Three", "value": 260 }, { "label": "Week Four", "value": 415 }] } }
```

**Inside Your Own Scene.** Call `s.use` From A Draw Function And Give The Part A Box. Collect Its Events With `s.events` And The Same Arguments.

```js
s.use(c, "Doodle Character", { talk: true, pose: "Talk", x: 0.3, size: 0.4 });
s.use(c, "Chart", { kind: "Counter", to: 4812, label: "People Know" }, { x: 0, y: s.safe.top, w: s.width, h: s.safe.h * 0.36, key: "count" });
```

**As A Copy You Restyle.** Copy The Part's File Into The Film's Scenes Folder, Register It Under A New Name, List It In `modules`, And Change The Drawing. A Film Module May Also Keep The Part's Name, In Which Case It Replaces The Built-In For That Film. Copy A Part When Its Shapes Must Change. Options And Colors Do Not Need A Copy.

Every Time Option In Every Part Accepts Seconds Since The Scene Began, Or The Name Of A Beat In The Scene's `beats`. Tie A Part To The Voice By Naming Beats. See [Voice Timing](VOICE-TIMING.md).

```json
"beats": { "sent": "hit send", "lands": "it lands" },
"params": { "steps": [{ "at": "sent", "do": "send" }, { "at": "lands", "do": "delivered" }] }
```

## Globe

A Rotating Sphere With Markers Placed By Latitude And Longitude And Arcs That Draw On Along Great Circles.

- `style` Is `"Graticule"` For Lines Of Latitude And Longitude, Or `"Dots"` For An Abstract Dot Pattern.
- `latitude`, `longitude`, And `spin` Set The Starting View And A Steady Turn. `views` Lists Eased Moves That Bring A Point To Face The Viewer.
- `markers` Are `{ id, lat, lon, label, at }`. Each Pops In With A Pulse. Markers On The Far Side Are Hidden.
- `arcs` Are `{ from, to, at, duration, lift }`, Where `from` And `to` Are A Marker `id` Or `[lat, lon]`.
- `center`, `radius`, `step`, `seeThrough`, `dotStep`, `land`, `seed`, `labels`, `labelSize`, And `colors` Adjust The Look.
- Events: A Marker Appears, An Arc Leaves, An Arc Lands, A View Move Begins.

The Globe Ships No Map Data And Traces None. The Dot Pattern Is Seeded Noise. It Is Illustrative And Not Geographic, So Never Describe It As Showing Actual Geography. Markers And Arcs Are Still Placed By True Latitude And Longitude. A Film That Needs Real Coastlines Or Borders Needs Map Data The Owner Has The Right To Use.

## Phone

A Generic Handset Whose Screen Shows A Chat Thread Driven By A Plain List Of State Changes.

| Step | What Happens |
| --- | --- |
| `{ "at": 0.4, "do": "message", "from": "them", "text": "..." }` | A Bubble Appears. `from` Is `"them"` Or `"me"`. |
| `{ "at": 1.6, "do": "typing", "for": 1.2 }` | The Other Person's Typing Dots Show Until Their Next Message. |
| `{ "at": 3.0, "do": "compose", "text": "...", "for": 1.0 }` | Text Types Into The Message Field. |
| `{ "at": 4.1, "do": "send" }` | The Composed Text Becomes An Outgoing Bubble. |
| `{ "at": 4.8, "do": "delivered" }` | A Label Appears Under The Last Outgoing Bubble. |
| `{ "at": 6.0, "do": "notify", "title": "...", "text": "...", "for": 2.2 }` | A Banner Drops From The Top. |

`contact`, `center`, `height`, `tilt`, `enter`, `placeholder`, `deliveredText`, `textSize`, And `colors` Adjust The Rest. The Thread Scrolls To Keep The Newest Item In View. Each Step Declares An Event.

The Handset And Its Interface Are Original And Generic. They Copy No Real App, Operating System, Or Brand. Do Not Dress Them As A Real Product Unless The Owner Has The Right To Show It. The Screen Color Follows The Scene's Type Color, So Set `colors.screen` When A Light Screen Is Wanted On A Light Backdrop.

## Doodle Character

A Simple Hand-Drawn Figure Built From One Definition, So It Stays On Model In Every Shot. [Characters](styles/characters.md) Explains How To Pose And Act With It.

- `pose` And `poses` Choose From Stand, Wave, Point, Think, Cheer, Shrug, And Talk. Each Change Blends From The Pose Before It.
- `walk` Lists Walks As `{ at, from, to, duration }` In Shares Of The Frame Width. Feet Stay Planted While On The Ground, And Leg Bones Keep Their Length.
- `talk` Moves The Mouth With The Voice Level And Closes It Between Words. It Needs A Timed Storyboard, With Stand-In Or Real Word Timings.
- The Figure Blinks At Uneven Seeded Intervals. `look`, `mood`, And `brows` Set The Face.
- `drawings` Sets Held Drawings Per Second, With 12 As The Default And 0 For Smooth Motion. `boil` Sets The Line Shimmer.
- `x`, `ground`, `size`, `line`, `shadow`, And `colors` Place And Style It.
- Events: Each Footfall And Each Pose Change.

For A Different Cast, Copy The File Once Per Character And Change The Proportions And Shapes At The Top. Keep Each Character To One Definition.

## Chart

An Animated Bar Chart, Line Chart, Or Counter.

- `kind` Is `"Bars"`, `"Line"`, Or `"Counter"`.
- Bars And Line Take `data` As `{ label, value }` Entries Or Plain Numbers, With `title`, `max`, `min`, `ticks`, `values`, `decimals`, `prefix`, And `suffix`. Bars Add `each`, `grow`, And `highlight`. Line Adds `duration`, `area`, And `dots`.
- Counter Takes `from`, `to`, `duration`, And `label`.
- `at` Starts The Build.
- Events: Each Bar Landing, The Line Starting And Ending, The Count Starting And Ending.

Every Figure On Screen Must Come From A Source The Owner Supplied. The Sample Numbers In The Examples Are Invented.

## Checks

`node tools/check.cjs` Draws Every Part And Every Example Twice And Fails If A Frame Differs Or A Part Uses Randomness Or The Clock. After Restyling A Copy, Render Stills With [Review Tools](REVIEW-TOOLS.md) At The Delivery Aspect Ratio, And At The Smallest Size The Film Uses. The Parts Were Verified From Stills In Portrait And Landscape. Check Any Other Frame Shape, And Any Part Placed In A Small Box, Before Relying On It.
