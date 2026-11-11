# Remotion Project Adapter

Convert A Storyboard Into A Standalone Remotion Project. The Owner's Approval Review Happens In This Project, In Remotion Studio. The Preparation Command Uses Node.js And Its Standard Library, Copies The Original Frame Painter, Extracts Attached Voice Recordings, And Includes Only The Sound Files Used By The Cut. It Writes No Video.

For A Film In Code, Prepare From `storyboard.timed.json`, The One Storyboard That Is Checked, Reviewed, And Exported. It Already Carries The Placed Event Sounds. For A Quick Storyboard Built In Motion Studio, Prepare From The Saved Storyboard. Run The Command From The User's Project Folder And Pass A New Output Directory There. `$SKILL` Stands For The Path To The Animated Video Skill Folder, As In The [Skill Guide](../SKILL.md). The Command Refuses To Write Inside The Skill Folder.

~~~sh
node "$SKILL/adapter/prepare-remotion.cjs" my-film/storyboard.timed.json my-film-remotion
~~~

Read What The Command Prints. Each Line That Starts With `WARNING` Names Something To Settle Before The Owner Reviews.

| Warning | Meaning | What To Do |
| --- | --- | --- |
| Stand-In Voice Timing | The Times Are A Guess At A Recording That Does Not Exist Yet | Retime To The Real Recording And Prepare Again. The Reviewed Render Refuses This Project. |
| Event Sounds Missing Or Out Of Date | The Scenes Declare Sounds That The Storyboard Does Not Carry | Run `tools/retime.cjs` Again, Then Prepare Again |
| No Narration Declared | The Storyboard Says The Film Will Never Have A Spoken Voice | Confirm That With The Owner |

Inside The Generated Project, Install The Declared Remotion And React Packages Separately, With The Owner's Agreement, Then Open Remotion Studio For Editable Review. The Dependency Installation Requires Network Access Or A Complete Local Package Cache.

~~~sh
cd my-film-remotion
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
| Sound Design | Individual Local WAV Assets, Cue Starts Rounded To The Nearest Frame, And Cue Gain. This Includes Every Event Sound Placed In The Timed Storyboard. |
| Voice | Original Attached Audio Bytes In Local Media Files, Spoken Lines In The Cue Manifest, And A Scene-End Cutoff. A Film Voice Recording Plays Across Every Scene From Its Offset. |
| Sound Position | A Panned Sound Cue Becomes A Stereo WAV Made At Preparation Time |
| Editable Source | The Self-Contained Source Storyboard, The Visual Scene JSON, Cue Manifest, And React Composition |

The Remotion Audio Engine Handles Decoding And Mixing. The Browser Editor’s Master Compressor And Subframe Gain Ramps Are Specific To Its Interactive Playback. Review The Audio Mix In The Destination Runtime. Room Air Is A Single Four-Second Cue. Script-Only Voice Lines Remain Notes.

Prepare A Film With Scene Modules From Its Saved Storyboard File, So The Modules And Voice Recording Listed Beside It Can Be Found. The Painter With Code Scenes Is Checked Against The Studio Painter In Node And In A Browser. This Kit's Checks Do Not Run It Inside An Installed Remotion Project, So Step Through The Composition In Remotion Studio Before Relying On It. A Film Voice That Skips Into The Recording Relies On The Audio Component's `trimBefore` Setting. Confirm The Voice Stays In Step In Remotion Studio.

## Make Changes

For A Film In Code, Change The Authored Storyboard Or A Scene Module In The Film Folder, Run The Timing Tool Again, And Prepare A New Output Directory From The New `storyboard.timed.json`. For A Quick Storyboard, Open The Generated Project’s **source-storyboard.json** In Motion Studio With **Open Storyboard**, Edit Cues, Text, Meshes, Camera Motion, And Lighting Together, Save A New Storyboard, And Prepare A New Output Directory. Either Way The Remotion Timeline Is Rebuilt Consistently, And The Owner Reviews The New Project.

For Direct Composition Work, Edit **src/frame-project.json** For Visual Parameters, **src/timeline.json** For Audio Timing And Composition Dimensions, And **src/index.jsx** For React Composition Changes. The Source Storyboard Remains A Snapshot Of The Handoff. When Changing Scene Lengths, Frame Rate, Or Aspect Ratio, Regenerate From Motion Studio To Recalculate The Related Timeline Values.

## Export An Approved Composition

Have The Project Owner Personally Review The Current Cut In Remotion Studio. Wait For Their Explicit Go-Ahead Before Creating Any Video File, Including A Test Or Preview Export. After Review, The Supplied Interactive Export Command Requests Personal Confirmation And Writes An MP4 To A New File. Review Again After Editing The Composition.

~~~sh
npm run render-reviewed -- Final-Cut.mp4
~~~

The Command Refuses To Run When The Project Was Prepared From A Storyboard On Stand-In Voice Timing. It Says So Before It Asks For Anything. Retime The Storyboard To The Real Recording, Prepare A Fresh Project, And Have The Owner Review That One. When The Storyboard Declares No Narration, The Command Tells The Owner Before Asking For Approval.

After The Export, Check The File Against The Storyboard From The User's Project Folder. The Check Reads The File And Changes Nothing. See [Review Tools](../REVIEW-TOOLS.md).

~~~sh
node "$SKILL/tools/export-check.cjs" my-film-remotion/Final-Cut.mp4 my-film/storyboard.timed.json
~~~

The Preparation And Verification Commands Only Assemble Project Files, Check Stills, Or Measure Sound. The Remotion Runtime And Its Dependencies Are Installed Separately From This Kit.

Remotion Has Its Own License Terms, Including Paid Company Licenses For Larger Teams. Check The Current Terms On Remotion's Website Before Using It In Your Business.
