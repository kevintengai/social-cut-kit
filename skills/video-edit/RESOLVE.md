# Build An Editable DaVinci Resolve Timeline

The Native Builder Reads The Kit's `timeline.json`, Imports The Original Files Into A New Media Pool Bin, And Builds A New Timeline In The Named Open Project. The Live Workflow Uses DaVinci Resolve Studio 21.1 Or Later. The Offline Plan Requires Python And FFprobe.

## Inspect The Plan

From The Kit's Root Folder, Run The Following Command. It Lists The Source Selections, Record Frames, Track Numbers, Transforms, Caption Text, Audio Gains, And Speeds.

```shell
python skills/video-edit/scripts/resolve_native.py examples/repair-desk/timeline.json --dry-run
```

Record Frame Zero Is The First Frame Of The New Timeline. Frame Counts Specify The Number Of Included Frames. Source In And Out Use Seconds. The Out Point Is Exclusive.

## Assemble In Resolve Studio

Open The Destination Project. In Preferences, Select System, General, Then Set External Scripting To Local. Use The Bundled ResolvePython Interpreter, Or Configure Your External Python Runtime With Blackmagic's Installed Scripting SDK. Keep FFprobe On PATH.

On Windows PowerShell, Run The Following Command With Your Open Project Name And A Fresh Timeline Name.

```powershell
& "C:/Program Files/Blackmagic Design/DaVinci Resolve/ResolvePython/ResolvePython.exe" skills/video-edit/scripts/resolve_native.py examples/repair-desk/timeline.json --project "My Edit Project" --name "Repair Desk V01"
```

On macOS Or Linux, Use The Same Script Arguments With Your Resolve-Connected Python Interpreter. Blackmagic Documents Interpreter Locations And Environment Variables In The Installed Developer/Scripting README.

The New Timeline Opens At Its First Frame. The JSON Receipt Identifies The Project, Timeline, Source Bin, Clip Count, Duration In Frames, And Resolve Version. Keep The Original Files Available At Their Imported Paths.

## Edit The Result

- **Picture And Sound.** Picture Cuts, Overlays, Original Audio, And Sound Cues Have Separate Clips. Original Audio And Picture Remain Linked. Change A Source Clip's Speed In Resolve's Clip Speed Controls. Gain Uses The Inspector's Decibel Scale. Zero Gain Disables The Audio Clip. The Source Files Retain Their Audio Channels. Project Track And Bus Routing Determine Monitoring.
- **Timing.** The Builder Uses The Source Timebase For Trims And The Timeline Timebase For Record Placement. It Verifies Every Clip's Frame Position, Duration, And Track Before Saving. Source Bounds Are Checked Within One Frame At The Relevant Playback Rate. Fractional Source Frames And Variable-Frame-Rate Footage Follow Resolve's Conform Behavior.
- **Stills And Framing.** The Builder Sets The Frame Rate And In/Out Marks On Its Private Media Pool Copies Of Stills. Fit, Cover, Zoom, And Position Are Editable In The Inspector. Overlapping Overlays Follow Their Order In The Project File.
- **Color.** A Shot With Color Adjustments Has A Fusion Custom Tool With Brightness, Contrast, And Saturation Controls. Its RGB Expressions Apply The Kit's Operations In Order. Source Interpretation And Project Color Management Affect The Viewed Result.
- **Captions.** Open A Caption's Text+ Inspector To Change Text, Font, Outline, Or Position. An Additional Overlapping Caption Uses A Native Compound Clip. Right-Click That Clip, Choose Open In Timeline, Then Select Its Text+ Title. Text+ Uses The Installed Font And Its Own Shaping And Line Wrapping. Review Long Lines In Resolve. Image Overlays Remain Image Assets.
- **Sound Sources With A Different Timebase.** Resolve Uses The Project Frame Rate For Standalone Audio. When It Differs From The Cut, The Builder Creates A Full-Source Audio Compound At The Cut's Frame Rate. Choose Open In Timeline To Reach The Original Audio Inside. The Main Timeline Exposes Each Cue's Timing And Gain.

## Revisions And Partial Builds

Choose A New Name For Each Revision. The Builder Checks The Exact Open Project And Checks The Timeline Name Both Before Assembly And Before Saving. It Builds In A Unique Staging Bin And Removes Its Own Staging Items If Resolve Rejects An Operation. A Disconnected App, A Project Switch, Or A Failed Cleanup Can Leave A Bin Named With The Revision And A Unique Suffix. Inspect That Bin Before Removing It. A Retry Creates A Fresh Staging Bin.

Resolve Determines Which Canvas Dimensions, Frame Rates, Formats, And Inspector Ranges It Accepts. A Rejected Or Altered Setting Ends The Build With A Diagnostic. Positive Audio Gain Values Below Resolve's −100 dB Limit Require A Different Level Or A True Mute In The Edit Plan.

## Share The Native Timeline

Select The Finished Timeline In The Media Pool, Open Resolve's Export Timeline Dialog, And Choose The DaVinci Resolve Timeline Format (`.drt`). The Timeline File Contains Edit Metadata. Send The Original Source Files Alongside It And Preserve Their Folder Structure. In The Receiving Project, Import The Timeline And Use Relink Selected Clips In The Media Pool If Resolve Requests The Media.

The Windows Integration Check Used Resolve Studio 21.1.0.14. It Verified A Saved Native Timeline With Mixed Frame Rates, Linked Retimed Sound, Two Overlapping Graphics, Overlapping Editable Captions, And A Native DRT Metadata Export. The Offline Tests Run Without Resolve.
