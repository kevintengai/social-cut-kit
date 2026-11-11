---
name: animated-video
description: Create Editable Offline Motion Storyboards With Kinetic Titles, Animated Process Diagrams, Lit 3D Objects, Timed Voice Cues, And Original Sound Effects. Use For Animated Explainers, Title Sequences, Or Product Turntables.
---

# Animated Video

Open [Motion Studio](studio/index.html) In A Desktop Browser. The Editor Runs Directly From The Extracted Folder. Its Scripts, Meshes, Marks, And Synthesized Sounds Are Local. Use **Save Storyboard** To Download An Editable JSON File. Browser Refresh Starts A New Demo.

![Three Sample Storyboard Frames](assets/storyboard-stills.png)

## Choose A Starting Point

| Starting Point | Use It For |
| --- | --- |
| [Give An Idea Shape](examples/give-an-idea-shape.json) | Build A Portrait Explainer From A Kinetic Hook, A Three-Step Sequence, And An Orbiting Ring. This Is Also The Initial Demo. |
| [Facet Turntable](examples/facet-turntable.json) | Stage Two Landscape Object Studies With Different Meshes, Surface Finishes, Camera Angles, And Audio Cues. |

Select **Open Storyboard** To Load Either Example Or A Previously Saved JSON File. Set **Frame** To Portrait, Square, Or Landscape. Set **Frame Rate** To 24, 30, Or 60 FPS.

## Build The Storyboard

1. Write The One Sentence The Viewer Should Remember. Choose A Single Visible Change For Each Scene.
2. Select A Scene In The Left Column. Set Its Duration, Headline, Mark, Colors, And Text Motion. Use **Add Scene**, **Duplicate**, **Move Up**, **Move Down**, Or **Remove** To Arrange The Cut.
3. Choose **Kinetic Type** For A Headline And Supporting Line. **Word Rise** Staggers Individual Words Upward. **Side Sweep** Moves Each Word In From The Left. **Scale Pulse** Expands Each Word Into Place.
4. Choose **Process Diagram** For Up To Five Steps. Enter One Step Per Line. The Editor Spaces The Nodes Vertically And Reveals Them In Order. On Landscape Frames, It Places The Headline Beside The Diagram.
5. Choose **3D Object** For A Prism, Crystal, Or Orbit Ring. Adjust Camera Yaw And Elevation For The Opening Angle. Camera Orbit Sets The Total Camera Travel In Degrees. Object Spin Sets A Separate Rotation Over The Scene. Distance Changes Framing. Set The Key Light’s Color, Yaw, Elevation, And Intensity, Then Adjust The Surface Color And Gloss.
6. Use **Play** For Ordinary In-Editor Playback. Drag The Timeline To Inspect A Frame. Download The Storyboard And Cue Sheet For Handoff.

## Direct A 3D Shot

For A Faceted Crystal, Try A Camera Yaw Of −48°, An Elevation Of 18°, A Distance Of 6.4, A Camera Orbit Of 86°, An Object Spin Of −24°, And Gloss Of 0.84. A Cool Surface Under A Warm Key Light Makes The Changing Highlight Easy To Follow. Open The Landscape Example To Try These Values.

The Renderer Projects Polygon Meshes Through A Perspective Camera And Shades Their Faces Using The Surface Color, A Directional Key Light, A View-Dependent Highlight, And Rim Lighting. The Mesh Selector Offers The Three Built-In Geometries. To Author Another Geometry In Code, Extend The Face Builder In [space.js](studio/space.js) And The Shape List In [project.js](studio/project.js).

## Time Voice And Sound

- Add A **Sound** Cue And Set Its Start Time In Seconds Relative To Its Scene. Use Gain From 0 To 1. Room Air Plays Once For Four Seconds. Add Another Cue Four Seconds Later For A Longer Bed.
- Add A **Voice** Cue, Enter The Spoken Line, And Attach The Speaker’s Recorded Audio. The Script Alone Stays Silent. A Short WAV Is A Portable Input. Other Decoders Depend On The Browser.
- The Project Embeds Attached Audio In Its JSON. Save After Attaching A Recording. Each Cue Ends At The Earlier Of Its Recording End Or Scene End. Extend The Scene To Retain The Whole Spoken Phrase And Its Natural Tail.
- **Download Cue Sheet** Writes A Text Handoff With Absolute Scene Boundaries, Spoken Lines, Sound Names, Cue Start Times, And Recording Status.

## Original Asset Library

All Seven WAV Files Are 48 kHz, 16-Bit, Mono PCM. Their Waveforms Come From The Included Synthesis Code.

| Sound | Length | Suggested Placement |
| --- | ---: | --- |
| [Paper Tap](assets/sounds/paper-tap.wav) | 0.19 Seconds | A Soft Tactile Cut Or A Label Appearing |
| [Glass Point](assets/sounds/glass-point.wav) | 0.82 Seconds | A Reveal Or A Bright Specular Highlight |
| [Air Sweep](assets/sounds/air-sweep.wav) | 0.78 Seconds | A Lateral Transition Or Camera Move |
| [Low Bloom](assets/sounds/low-bloom.wav) | 1.46 Seconds | A Weighted Landing Or Opening Beat |
| [Twin Tick](assets/sounds/twin-tick.wav) | 0.39 Seconds | A Step Marker Or Interface Confirmation |
| [Orbit Rise](assets/sounds/orbit-rise.wav) | 1.32 Seconds | A Rising Title Or Turntable Entrance |
| [Room Air](assets/sounds/room-air.wav) | 4.00 Seconds | A Subtle Tonal Bed With A Periodic Waveform For Looping |

Use The Six Transparent SVG Marks In The Editor Or Import Their Individual Files Into Another Tool. The Set Includes [Aperture](assets/marks/aperture.svg), [Signal](assets/marks/signal.svg), [Focus](assets/marks/focus.svg), [Route](assets/marks/route.svg), [Spark](assets/marks/spark.svg), And [Orbit](assets/marks/orbit.svg).

Two Transparent 1080 × 1920 Overlays Are Included For Compositing In An Editor That Imports SVG Artwork. [Edge Register](assets/overlays/edge-register.svg) Adds Corner Brackets And Side Ticks. [Orbit Contour](assets/overlays/orbit-contour.svg) Places Nested Ellipses In The Lower Corner.

## Review And Export

Give The Editable Storyboard To The Human Project Owner. For Personal Review, They Select **Review From Start**, Keep The Tab Visible, And Watch The Entire Cut With Sound. Check Word Boundaries, Readability, Mesh Framing, And The Timing Of Every Cue. Revise The Storyboard And Repeat The Review Whenever An Edit Changes The Cut.

Wait For The Owner’s Explicit Approval Before Creating Any Video File, Including A Test Render Or Preview Export. Once They Approve The Current Cut, They Can Check The Review Confirmation And Select **Export Approved Video**. Editing Or Reopening A Storyboard Clears Approval.

A Desktop Browser With Canvas Stream Capture And WebM Recording Support Can Record The Approved Cut In Real Time. Keep Its Tab Visible Until The WebM Download Starts. The Recording Mixes The Timed Audio With The Canvas Frames At The Selected Frame Rate. Portrait Output Is 1080 × 1920, Square Is 1080 × 1080, And Landscape Is 1920 × 1080. Recording Speed And Frame Delivery Depend On The Device. The Editor Exports WebM In Supported Browsers.

## Optional Remotion Handoff

For A Native Editable 3D Product Scene, Open [Pulse Dial](blender/Pulse%20Dial.blend) In Blender. Use The [Blender Guide](blender/README.md) To Change Its Materials, Camera, And Animated Parts Or Rebuild It From The Included Geometry Generator.

Use The [Remotion Project Adapter](adapter/README.md) To Prepare A Standalone Remotion Composition From A Saved Storyboard. It Reuses The Same 2D And 3D Painter And Transfers Frame Timing, Materials, Camera Motion, Timed Sounds, And Recorded Voice. The Adapter Writes An Editable Project Without Producing A Video.

~~~sh
node adapter/prepare-remotion.cjs examples/facet-turntable.json My-Facet-Project
~~~

## Rebuild And Check

The Supplied Editor And Assets Are Ready To Use. For Asset Maintenance, Run These Optional Commands From The Folder Containing This Guide. They Use Node.js And Its Standard Library.

~~~sh
node tools/build-assets.cjs
node tools/make-examples.cjs
node tools/check.cjs
~~~

Run The Optional Browser Check With A Local Chromium Executable. It Exercises Scene Editing, Voice Import, Playback, Storyboard Save/Open, And Review Invalidation. The Optional Stills Flag Regenerates The Three-Frame PNG Above.

~~~powershell
node tools/check-browser.cjs "C:/Program Files/Google/Chrome/Application/chrome.exe" --stills
~~~
