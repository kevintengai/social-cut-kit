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
| Code Scenes | The Film's Scene Modules, The Drawing Kit, And The Kit's Parts, Compiled Into The Painter. The Modules Are Also Copied Beside The Source Storyboard. |
| Captions | The Caption Track, Drawn By The Painter On Every Frame |
| 3D Animation | Mesh Geometry, Camera Yaw, Elevation, Orbit, Distance, Object Spin, Surface, Key Light, And Gloss |
| Sound Design | Individual Local WAV Assets, Cue Starts Rounded To The Nearest Frame, And Cue Gain |
| Voice | Original Attached Audio Bytes In Local Media Files, Spoken Lines In The Cue Manifest, And A Scene-End Cutoff. A Film Voice Recording Plays Across Every Scene From Its Offset. |
| Sound Position | A Panned Sound Cue Becomes A Stereo WAV Made At Preparation Time |
| Editable Source | The Self-Contained Source Storyboard, The Visual Scene JSON, Cue Manifest, And React Composition |

The Remotion Audio Engine Handles Decoding And Mixing. The Browser Editor’s Master Compressor And Subframe Gain Ramps Are Specific To Its Interactive Playback. Review The Audio Mix In The Destination Runtime. Room Air Is A Single Four-Second Cue. Script-Only Voice Lines Remain Notes.

Prepare A Film With Scene Modules From Its Saved Storyboard File, So The Modules And Voice Recording Listed Beside It Can Be Found. The Painter With Code Scenes Is Checked Against The Studio Painter In Node And In A Browser. This Kit's Checks Do Not Run It Inside An Installed Remotion Project, So Step Through The Composition In Remotion Studio Before Relying On It. A Film Voice That Skips Into The Recording Relies On The Audio Component's `trimBefore` Setting. Confirm The Voice Stays In Step In Remotion Studio.

## Make Changes

Open The Generated Project’s Folder In Motion Studio With **Open Film Folder**, Or Its **source-storyboard.json** With **Open Storyboard**, To Edit Cues, Text, Meshes, Camera Motion, And Lighting Together. Save A New Storyboard And Prepare A New Output Directory. This Rebuilds The Remotion Timeline Consistently.

For Direct Composition Work, Edit **src/frame-project.json** For Visual Parameters, **src/timeline.json** For Audio Timing And Composition Dimensions, And **src/index.jsx** For React Composition Changes. The Source Storyboard Remains A Snapshot Of The Handoff. When Changing Scene Lengths, Frame Rate, Or Aspect Ratio, Regenerate From Motion Studio To Recalculate The Related Timeline Values.

## Export An Approved Composition

Have The Project Owner Personally Review The Current Cut In Remotion Studio. Wait For Their Explicit Go-Ahead Before Creating Any Video File. After Review, The Supplied Interactive Export Command Requests Personal Confirmation And Writes An MP4 To A New File. Review Again After Editing The Composition.

~~~sh
npm run render-reviewed -- Final-Cut.mp4
~~~

The Preparation And Verification Commands Only Assemble Project Files Or Check Stills. The Remotion Runtime And Its Dependencies Are Installed Separately From This Kit.

Remotion Has Its Own License Terms, Including Paid Company Licenses For Larger Teams. Check The Current Terms On Remotion's Website Before Using It In Your Business.
