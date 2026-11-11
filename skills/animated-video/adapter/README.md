# Remotion Project Adapter

Convert A Saved Motion Studio Storyboard Into A Standalone Remotion Project. The Preparation Command Uses Node.js And Its Standard Library, Copies The Original Frame Painter, Extracts Attached Voice Recordings, And Includes Only The Sound Files Used By The Cut.

From The Animated Video Skill Folder, Pass The Saved Storyboard And A New Output Directory.

~~~sh
node adapter/prepare-remotion.cjs examples/facet-turntable.json My-Facet-Project
~~~

Inside The Generated Project, Install The Declared Remotion And React Packages Separately, Then Open Remotion Studio For Editable Review. The Dependency Installation Requires Network Access Or A Complete Local Package Cache.

~~~sh
cd My-Facet-Project
npm install
npm run studio
~~~

Open **MotionStoryboard**. Scrub Frame By Frame Or Play The Entire Composition With Audio. The Composition Reads Frame Time From Remotion And Sends It To The Same Painter Used By The Offline Editor.

## What Transfers

| Element | Remotion Representation |
| --- | --- |
| Storyboard And Framing | Original Scene Order, Duration, Aspect Ratio, Resolution, And Frame Rate |
| 2D Animation | Kinetic Headlines, Supporting Lines, Marks, Colors, And Sequential Diagram Steps |
| 3D Animation | Mesh Geometry, Camera Yaw, Elevation, Orbit, Distance, Object Spin, Surface, Key Light, And Gloss |
| Sound Design | Individual Local WAV Assets, Cue Starts Rounded To The Nearest Frame, And Cue Gain |
| Voice | Original Attached Audio Bytes In Local Media Files, Spoken Lines In The Cue Manifest, And A Scene-End Cutoff |
| Editable Source | The Self-Contained Source Storyboard, The Visual Scene JSON, Cue Manifest, And React Composition |

The Remotion Audio Engine Handles Decoding And Mixing. The Browser Editor’s Master Compressor And Subframe Gain Ramps Are Specific To Its Interactive Playback. Review The Audio Mix In The Destination Runtime. Room Air Is A Single Four-Second Cue. Script-Only Voice Lines Remain Notes.

## Make Changes

Open The Generated Project’s **source-storyboard.json** In Motion Studio To Edit Cues, Text, Meshes, Camera Motion, And Lighting Together. Save A New Storyboard And Prepare A New Output Directory. This Rebuilds The Remotion Timeline Consistently.

For Direct Composition Work, Edit **src/frame-project.json** For Visual Parameters, **src/timeline.json** For Audio Timing And Composition Dimensions, And **src/index.jsx** For React Composition Changes. The Source Storyboard Remains A Snapshot Of The Handoff. When Changing Scene Lengths, Frame Rate, Or Aspect Ratio, Regenerate From Motion Studio To Recalculate The Related Timeline Values.

## Export An Approved Composition

Have The Project Owner Personally Review The Current Cut In Remotion Studio. Wait For Their Explicit Go-Ahead Before Creating Any Video File. After Review, The Supplied Interactive Export Command Requests Personal Confirmation And Writes An MP4 To A New File. Review Again After Editing The Composition.

~~~sh
npm run render-reviewed -- Final-Cut.mp4
~~~

The Preparation And Verification Commands Only Assemble Project Files Or Check Stills. The Remotion Runtime And Its Dependencies Are Installed Separately From This Kit.
