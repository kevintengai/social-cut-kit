# Social Cut Kit

<img src="brand/school-mark.png" alt="TENG AI SCHOOL" width="235">

Eight TENG AI SCHOOL Skills For Turning A Brief, A Recording, Or An Animation Idea Into An Editable Social Video. The Kit Includes A Local Footage Editor, An Offline Motion Studio, An Asset Library, And An Example You Can Open Before Installing Any Skills.

## Try An Edit

Unzip The Download. In A Terminal At The Product Root, Run The Following With Python 3.10 Or Later. The Footage Editor Uses FFmpeg And FFprobe From Your System Path.

```sh
python skills/video-edit/scripts/edit_video.py review examples/repair-desk/timeline.json
```

An Eight-Second Vertical Edit Opens In Your Browser. Scrub Across The Three-Second Mark To See The Filter Change And Hear The Confirmation Cue. Edit A Caption Or Cut Point, Save The Timeline, And Play It Again. The Source Is An Included [Fictional Repair Queue](examples/repair-desk/demo.html). [Example Project](examples/repair-desk/README.md)

For Animation, Open [Motion Studio](skills/animated-video/studio/index.html) From The Unzipped Folder. Try A Kinetic Title, A Process Diagram, Or A Lit 3D Turntable. The Browser Opens The Included Scene Without A Package Install. For Reusable Visuals, Open The [Icon And Overlay Gallery](art/index.html).

To Continue In A Production Application, Take A Saved Storyboard Into [Remotion](skills/animated-video/adapter/README.md), Or Open The Included [Pulse Dial Blender Scene](skills/animated-video/blender/Pulse%20Dial.blend) To Edit Its Materials, Lighting, Camera Move, And Animated Controls.

## Install The Skills

Choose The Command For Your Agent. Replace `python` With `python3` On Systems That Use That Name. Restart Or Reload The Agent After Installation.

```sh
python install.py --agent codex
python install.py --agent claude
```

To Install Specific Skills, Append Their Folder Names. For Example, `python install.py --agent codex director video-edit` Installs The Shot Planner And Editor. Existing Same-Name Folders Are Skipped By Default. When Upgrading From An Earlier Edition, Run `python install.py --agent codex --upgrade` Or Its Claude Equivalent. This Backs Up Each Replaced Folder Beside The Agent’s Skills Directory And Prints The Backup Location.

## Pick A Starting Point

| Task | Tool | First Result |
| --- | --- | --- |
| Define An Offer And Its Proof | [Campaign Brief](skills/teng-campaign-brief/SKILL.md) | A Structured Brief With Sources, A Viewer Action, And A Measurable Response |
| Write A Short And Read Its Analytics | [Script Desk](skills/video-script/SKILL.md) | A Timed Two-Column Script Or A Retention Report From CSV Or A Chart Image |
| Plan Pictures And Sound | [Director’s Desk](skills/director/SKILL.md) | An Offline Shot Board And A Timeline Built From Sourced Beats |
| Cut Recorded Footage | [Video Edit](skills/video-edit/SKILL.md) | A Local Editable Timeline With Source Sound, Overlays, Captions, And Speed Changes |
| Build An Animated Explainer | [Animated Video](skills/animated-video/SKILL.md) | A Reopenable Storyboard With Motion, Camera, Lighting, And Sound Cues |
| Find Or Reuse A Project Asset | [Asset Library](skills/asset-library/SKILL.md) | A Searchable Local Record With Source Rights And Exact Version Pins |
| Review A Finished Session | [Reflect](skills/reflect/SKILL.md) | An Evidence-Based Account Of The Result And The Work That Produced It |
| Test A Better Editing Method | [Workflow Trials](skills/rsi/SKILL.md) | A Paired Comparison With A Measurable Improvement Threshold |

## Work With Your Footage

- Inspect A Source, Find Silences And Scene Changes, And Assemble Selected Takes In Timeline Order. Use The Original Recording For Speech And Keep Audio Handles On The Cut.
- Transcribe With A Separately Installed Local Recognizer, Or Import Existing Word Timings, SRT, Or WebVTT. The Caption Mapper Follows Trims, Handles, Repeated Shots, And Speed Changes. [Speech Tools](skills/video-edit/SPEECH.md)
- Track A Detail Across An Authorized Reference Or Audition Repeated Attempts In A Recording. [Reference And Take Tools](skills/video-edit/RECREATION.md)
- Build A Transparent Title With A Highlighted Keyword, Or Add One Of The 40 Original Sound Cues Across The Footage And Animation Tools. [Title Overlays](skills/video-edit/TITLES.md) · [Editorial Cues](skills/video-edit/assets/cue-bank/README.md)
- Use The Timeline Helper To Hand An OTIO Cut List And SRT Captions To Another Editor. The Optional Resolve Import Command Targets A Named Open Project. Confirm Effect Translation, Media Links, And Audio Levels In The Receiving Editor.
- For School Productions, Let The Owner Personally Review The Saved Edit In Its Editor Before Any Video Export. A Source Check Or Still Image Can Help Diagnose An Issue During Preparation.

## What The Download Contains

The Code, Skill Instructions, Editing Example, Procedural Sounds, And Vector Art Were Built For This Edition. The Logo Is TENG AI SCHOOL’s Supplied Artwork. FFmpeg, FFprobe, Optional Transcription Models, And Optional Production Applications Are Installed Separately. Purchasers Can Use The Included Assets In Their Own And Their Clients’ Commercial Videos. [Usage Terms](USAGE.md)

| Included Assets | How They Were Made |
| --- | --- |
| 48 Static Icons And Six Animated Overlays | Hand-Authored Vector Geometry And Motion In The [Art Catalog](art/catalog.json) |
| 33 Editorial WAVs | Seeded Synthesis From The [Cue Bank Generator](skills/video-edit/assets/cue-bank/build.py) |
| Seven Motion Studio WAVs, Six Marks, And Two Overlays | Procedural Sound And Original Drawing Instructions In The [Motion Asset Builder](skills/animated-video/tools/build-assets.cjs) |
| Two Repair Queue Stills | Captured From The Two Filter States Of The Included [Demo](examples/repair-desk/demo.html) |

Run `python checks/test_pipeline.py` For A Local Test Of The Brief, Storyboard, Timeline Handoff, Caption Mapping, Retention Analysis, Audio Alignment, And Installer. The Checks Use Temporary Files And Do Not Export A Video.
