---
name: animated-video
description: Make Animated Films In Code From A Script Or Voiceover, Such As Explainers, Stories With Characters, Kinetic Type, Motion Graphics, Infographics, And Maps, In 2D Or 3D At Any Aspect Ratio. Films Are Timed From The Voice, Reviewed From Stills, And Exported Only After The Owner Approves. Also Builds Quick Editable Storyboards And Product Turntables. Not For Editing Camera Footage, Which Belongs To The Video Edit Skill.
---

# Animated Video

Two Routes Share One Storyboard Format. For A Quick Title, Process Diagram, Or Turntable, Use Motion Studio's Built-In Scenes, Described From **Motion Studio** Onward. For A Film Drawn To A Brief, Follow **Make A Film In Code**. To Cut Recorded Camera Footage, Use The Video Edit Skill Instead.

Before Anything Else, Read The User's Saved Defaults In `~/.social-cut-kit/animated-video.md` When That File Exists. The User's Stated Preferences, There Or In The Conversation, Come Before This Kit's Defaults.

## Make A Film In Code

1. **Find The Film.** Settle The One Sentence, The Audience, Story Or Explainer, And A Beat Sheet With Timings Where Each Beat Shows Something Happening. Stop For The Owner's Approval Of The Plan. [Directing](DIRECTING.md)
2. **Choose The Look From Stills.** Render The Same Beat In Two Or Three Styles And Let The Owner Pick. [Style Frames](STYLE-FRAMES.md) And The Guides In [styles/](styles/)
3. **Set Up The Film Folder.** Write The Script, Make Stand-In Word Timings If There Is No Recording Yet, And Anchor Scenes, Beats, And Captions To Spoken Phrases. [Voice Timing](VOICE-TIMING.md)
4. **Draw The Scenes.** Write Scene Modules With The Drawing Kit, And Use Or Restyle A Globe, Phone, Character, Or Chart Where It Is The Right Picture. [Code Scenes](CODE-SCENES.md) And [Parts](PARTS.md)
5. **Check From Stills And Numbers.** Render Boards And Frame Strips, Measure Motion, Check Determinism, And Place Sounds On Picture Events. No Video Is Written. [Review Tools](REVIEW-TOOLS.md)
6. **Judge It.** Read Motion From Strips, Use Independent Judges, And Run The Silent Viewing Test. [Review](REVIEW.md)
7. **Retime To The Real Voice.** When The Recording Arrives, Run The Timing Tool With Its Word Timings And Check The Stills Again. [Voice Timing](VOICE-TIMING.md)
8. **Hand The Film To The Owner.** The Owner Opens The Film Folder In Motion Studio, Watches The Whole Cut With Sound, And Approves It Before Any Video Is Exported. That Includes Test And Preview Exports. See **Review And Export** Below.

For A Revision To A Finished Film, Or An Animated Insert For A Camera Edit, Follow [Handoffs](HANDOFFS.md). When A Filmed Presenter Appears Inside The Film, Plan It From The Start With [Presenter](PRESENTER.md).

~~~sh
node tools/standin-words.cjs my-film/script.txt my-film/words.json
node tools/retime.cjs my-film/storyboard.json my-film/words.json my-film/storyboard.timed.json --overwrite
node tools/stills.cjs my-film/storyboard.timed.json my-film/board --browser "/path/to/chrome" --half --every 1 --overwrite
node tools/motion.cjs my-film/storyboard.timed.json --browser "/path/to/chrome" --determinism
node tools/events.cjs my-film/storyboard.timed.json --place my-film/storyboard.sound.json --overwrite
~~~

Run These From The Folder Containing This Guide. They Use Node.js And Its Standard Library, And The Still And Motion Tools Use A Local Chromium Browser. [An Idea Travels](examples/an-idea-travels/storyboard.json) Is A Complete Small Film To Study, And [First Code Scene](examples/first-code-scene/storyboard.json) Is The Smallest One To Copy.

## Motion Studio

Open [Motion Studio](studio/index.html) In A Desktop Browser. The Editor Runs Directly From The Extracted Folder. Its Scripts, Meshes, Marks, And Synthesized Sounds Are Local. Use **Save Storyboard** To Download An Editable JSON File. Browser Refresh Starts A New Demo.

![Three Sample Storyboard Frames](assets/storyboard-stills.png)

## Choose A Starting Point

| Starting Point | Use It For |
| --- | --- |
| [Give An Idea Shape](examples/give-an-idea-shape.json) | Build A Portrait Explainer From A Kinetic Hook, A Three-Step Sequence, And An Orbiting Ring. This Is Also The Initial Demo. |
| [Facet Turntable](examples/facet-turntable.json) | Stage Two Landscape Object Studies With Different Meshes, Surface Finishes, Camera Angles, And Audio Cues. |

Select **Open Storyboard** To Load Either Example Or A Previously Saved JSON File. For A Film With Scene Modules, Select **Open Film Folder** And Pick The Film's Folder, Or Select The Storyboard And Its Module Files Together. Set **Frame** To Portrait, Square, Landscape, Or Custom With Any Even Width And Height. Set **Frame Rate** To 24, 30, Or 60 FPS.

## Build The Storyboard

1. Write The One Sentence The Viewer Should Remember. Choose A Single Visible Change For Each Scene.
2. Select A Scene In The Left Column. Set Its Duration, Headline, Mark, Colors, And Text Motion. Use **Add Scene**, **Duplicate**, **Move Up**, **Move Down**, Or **Remove** To Arrange The Cut.
3. Choose **Kinetic Type** For A Headline And Supporting Line. **Word Rise** Staggers Individual Words Upward. **Side Sweep** Moves Each Word In From The Left. **Scale Pulse** Expands Each Word Into Place.
4. Choose **Process Diagram** For Up To Five Steps. Enter One Step Per Line. The Editor Spaces The Nodes Vertically And Reveals Them In Order. On Landscape Frames, It Places The Headline Beside The Diagram.
5. Choose **Code Scene** To Use A Built-In Part Or A Loaded Scene Module. Pick Its Draw Function And Edit Its Parameters As JSON. [Parts](PARTS.md) Lists The Options.
6. Choose **3D Object** For A Prism, Crystal, Or Orbit Ring. Adjust Camera Yaw And Elevation For The Opening Angle. Camera Orbit Sets The Total Camera Travel In Degrees. Object Spin Sets A Separate Rotation Over The Scene. Distance Changes Framing. Set The Key Light’s Color, Yaw, Elevation, And Intensity, Then Adjust The Surface Color And Gloss.
7. Use **Play** For Ordinary In-Editor Playback. Drag The Timeline To Inspect A Frame. Download The Storyboard And Cue Sheet For Handoff.

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

Give The Editable Storyboard To The Human Project Owner. For A Film In Code, Give The Whole Film Folder, And Have The Owner Open It With **Open Film Folder** So The Scene Modules And Voice Recording Load. A Storyboard Marked As Using Stand-In Voice Timing Is Not Ready For Export. For Personal Review, They Select **Review From Start**, Keep The Tab Visible, And Watch The Entire Cut With Sound. Check Word Boundaries, Readability, Mesh Framing, And The Timing Of Every Cue. Revise The Storyboard And Repeat The Review Whenever An Edit Changes The Cut.

Wait For The Owner’s Explicit Approval Before Creating Any Video File, Including A Test Render Or Preview Export. Once They Approve The Current Cut, They Can Check The Review Confirmation And Select **Export Approved Video**. Editing Or Reopening A Storyboard Clears Approval.

A Desktop Browser With Canvas Stream Capture And WebM Recording Support Can Record The Approved Cut In Real Time. Keep Its Tab Visible Until The WebM Download Starts. The Recording Mixes The Timed Audio With The Canvas Frames At The Selected Frame Rate. Portrait Output Is 1080 × 1920, Square Is 1080 × 1080, Landscape Is 1920 × 1080, And A Custom Frame Uses Its Own Size. Recording Speed And Frame Delivery Depend On The Device. The Editor Exports WebM In Supported Browsers.

## Optional Remotion Handoff

For A Native Editable 3D Product Scene, Open [Pulse Dial](blender/Pulse%20Dial.blend) In Blender. Use The [Blender Guide](blender/README.md) To Change Its Materials, Camera, And Animated Parts Or Rebuild It From The Included Geometry Generator.

Use The [Remotion Project Adapter](adapter/README.md) To Prepare A Standalone Remotion Composition From A Saved Storyboard. It Reuses The Same 2D And 3D Painter And Transfers Frame Timing, Materials, Camera Motion, Code Scenes With Their Modules, Parts, Captions, Timed Sounds, And Recorded Voice. The Adapter Writes An Editable Project Without Producing A Video.

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

The Node Check Covers The Storyboard Format, The Drawing Kit, Voice Timing, Captions, Events, The Remotion Painter, And The Determinism Of Every Example Code Scene And Part.

Run The Optional Browser Check With A Local Chromium Executable. It Exercises Scene Editing, Voice Import, Playback, Storyboard Save/Open, Review Invalidation, And Opening A Code Scene Film With Its Module. The Optional Stills Flag Regenerates The Three-Frame PNG Above.

~~~powershell
node tools/check-browser.cjs "C:/Program Files/Google/Chrome/Application/chrome.exe" --stills
~~~
