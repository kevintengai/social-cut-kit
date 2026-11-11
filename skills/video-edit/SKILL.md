---
name: video-edit
description: Assemble, Inspect, And Review An Editable Local Video Timeline. Use For Multi-Source Cuts, Dialogue Handles, Captions, Reframing, Color, Overlays, Music, Sound Effects, And Approved MP4 Delivery.
---

# Social Cut Kit Video Editor

Build The Edit In A JSON Timeline. Review It In The Included Browser Editor, Which Plays The Original Source Files. Keep The Timeline And Media Together So Another Editor Can Reopen The Project.

For Repeated Takes, Camera Reference Tracking, Or Speech Recovery, Use The [Reference Tools](RECREATION.md) And [Speech Tools](SPEECH.md). For A Text-Overlay Skit Or A Highlighted Callout, Build A [Transparent Title](TITLES.md) And Place It On The Overlay Track. Choose Audio Cues From The [Included Sound Bank](assets/cue-bank/README.md).

## Start With A Working Project

Use Python 3.9 Or Later And Install FFmpeg And FFprobe Separately On Your PATH. Use A Build With The Libass Subtitles Filter For Burned Captions And Libx264 And AAC For MP4 Delivery. Run Commands From This Skill Folder. Substitute Your Python Launcher For `python` When Needed.

```sh
python scripts/edit_video.py example "First Cut"
python scripts/edit_video.py validate "First Cut/timeline.json"
python scripts/edit_video.py review "First Cut/timeline.json"
```

The Example Creates Two Original PNG Stills, A Stereo WAV, And A Four-Second Editable Timeline In A New Folder. Press Play To Hear Separate Left And Right Tones. At One Second, A Second Image Appears Over The First Shot. Select A Shot To Jump To Its Start, Or Step Through One Frame At A Time.

Place The Playhead Inside A Shot And Select **Split Shot At Playhead**. Select **Save Timeline** To Apply The Split. To Add Text, Select **Add Caption At Playhead**, Replace The Placeholder In The Editable Timeline, And Save. **Reset Unsaved Changes** Restores The Most Recent Save. The Browser Opens A Private Loopback URL. Keep The Terminal Running While Editing. Press Ctrl+C To Close The Editor.

For Word Timings, External Recorder Sync, And Quiet Dialogue, See [Speech And Take Preparation](SPEECH.md). For Reference Tracking And Repeated-Take Detection, See [Reference And Take Analysis](RECREATION.md). For Ready-To-Use Sound Effects, See The [Editorial Cue Bank](assets/cue-bank/README.md).

## Build A Cut From Your Footage

1. Copy The Example Timeline To Your Own Project Directory. Add Your Source Files To Its Assets List. Keep Relative Paths For Projects You Expect To Move.
2. Set The Canvas. Use 1080 By 1920 For Vertical, 1920 By 1080 For Horizontal, Or Even Dimensions For A Custom Size. Set The Output Frame Rate Before Timing The Captions.
3. Inspect A Source With `probe`. Use `analyze` To List Silence Intervals And Candidate Scene Changes. Check Each Candidate Against The Source Before Choosing A Take Or Making A Cut.
4. List The Shots In Playback Order. Set Each Source In And Out Point In Seconds. Use Lead And Tail Handles To Preserve Full Word Beginnings, Endings, And Natural Breaths. Keep Source Dialogue At Its Original Speed And Level Unless The Edit Calls For A Change.
5. Place Overlays, Audio, And Captions Using Time From The Start Of The Assembled Edit. Recheck Their Timing After Moving Or Deleting A Shot.
6. Run `validate`, Run `check`, And Open `review`. Listen Across Each Cut, Review Text Placement At The Delivery Aspect Ratio, And Check Levels Where Cues Overlap Speech. The Full Composition Check Decodes To A Null Sink Without Creating A Movie.

```sh
python scripts/edit_video.py probe "Footage/Camera A.mp4"
python scripts/edit_video.py analyze "Footage/Camera A.mp4" --silence-db -40 --silence-length 0.4 --scene-threshold 0.32
python scripts/speech.py --help
python scripts/edit_video.py check "First Cut/timeline.json"
```

## Timeline Fields

The Root Object Requires `version` Set To `1`, A `title`, An `assets` Object, And A Nonempty `shots` List. Use `canvas`, `overlays`, `audio`, `captions`, And `caption_style` As Needed. Field Names And Enumeration Values Are Case Sensitive. Each Media Occurrence Can Use A Different Source Selection.

| Field | Meaning |
| --- | --- |
| `canvas.width`, `canvas.height`, `canvas.fps` | Even Pixel Dimensions And A Whole-Number Frame Rate. Defaults Are 1080 By 1920 At 30 FPS. |
| `canvas.fit`, `shots[].fit` | `contain` Fits The Entire Image Against Black. `cover` Fills The Frame With A Center Crop. A Shot Can Override The Canvas Setting. |
| `assets` | A Map From Asset Names To Objects With A `path` And A `kind` Of `video`, `audio`, Or `image`. Use Static PNG Or JPEG Art For Portable Browser Review. |
| `shots[]` | Each Shot Requires An `asset` And Source `out`. Source `in`, `lead`, And `tail` Default To Zero. The Selected Range Runs From `in - lead` Through `out + tail`. Each Range Must Stay Inside Its Source. |
| `shots[].speed`, `shots[].gain` | Speed Ranges From 0.25 To 4 With Pitch-Preserved Audio. Linear Gain Ranges From 0 To 4. Both Default To 1. Set Gain To 0 To Mute. |
| `shots[].zoom`, `pan_x`, `pan_y` | Enlarge A Shot From 1× To 4×. Each Pan Axis Ranges From −1 To 1. Zero Centers The Frame, −1 Anchors The Left Or Top Edge, And 1 Anchors The Right Or Bottom Edge. Split A Shot And Set A Larger Zoom On The Second Half For An Instant Punch-In. |
| `shots[].brightness`, `contrast`, `saturation` | Use Multipliers With 1 As Neutral. Brightness And Contrast Range From 0 To 3. Saturation Ranges From 0 To 2. Zero Saturation Creates A Grayscale Shot. |
| `overlays[]` | Each Cue Uses `asset`, Timeline `at` And `end`, Optional Source `in`, Optional Pixel `x` And `y`, And Optional Pixel `width`. Coordinates Begin At The Canvas Top Left. Height Follows The Asset Proportions. Later Cues Appear Above Earlier Cues. Overlay Sound Is Muted. |
| `audio[]` | Use An Audio Or Video Asset With An Audio Stream. Set Timeline `at` And `end`, Optional Source `in`, And Optional Linear `gain`. To Repeat A Cue, Add Another Entry. |
| `captions[]` | Set `at`, `end`, And `text`. Optional `position` Accepts `top`, `center`, Or `bottom`. Use A JSON Newline Escape For A Deliberate Line Break. |
| `caption_style` | Set Optional `size` And `stroke` In Canvas Pixels. Set `color` And `outline` To Six-Digit Hex Colors. Set `margin` To A Percentage Of The Canvas Height. Supported `font` Values Are `Arial`, `Georgia`, `Verdana`, `Tahoma`, And `Trebuchet MS`. Font Availability Depends On The System. |

All Timeline Cue Times Snap To The Nearest Output Frame. Each Shot Duration Snaps After Applying The Speed Change. Use One Caption At A Time Per Position. The MP4 Mix Uses Stereo At 48 kHz. A Stereo Source Retains Distinct Left And Right Channels. Monitor Additive Audio Layers For Clipping And Adjust Their Gains As Needed.

## Review And Handoff

The Editable Browser Project Includes Cuts, Retiming, Reframing, Color Adjustments, Overlays, Audio Layers, And Captions. Its Player Uses Browser Codecs And System Fonts. MP4/H.264 With AAC, PNG, JPEG, And WAV Work Well For Source Playback In Common Desktop Browsers. Browser Seeking, Font Layout, Color Management, And Device Performance Can Affect Live Playback. The FFmpeg Check Exercises The Final Composition Graph.

```sh
python scripts/edit_video.py captions "First Cut/timeline.json" "First Cut/Dialogue.srt"
python scripts/edit_video.py handoff "First Cut/timeline.json" "First Cut/Assembly.otio"
python scripts/resolve_import.py --help
```

The SRT Uses Millisecond Timing. The OpenTimelineIO Handoff Includes Picture Cuts, Source Sound, Overlay And Audio Tracks, Source References, And Caption Markers. Import Support Varies By Editor. Check Retime Interpretation, Reapply Reframing, Color, Overlay Geometry, And Levels From The JSON Metadata, And Import The SRT For Editable Captions. Source References In The OTIO File Use Absolute File URIs. Regenerate It After Moving A Project. The Included Browser Editor Uses The Project JSON Directly.

## Approved Delivery

Save The Editable Project And Have Its Owner Personally Review This Version In The Editor. Wait For Explicit Approval Before Any Video Export, Including Preview Or Test Files. An Agent Running Validation Or Viewing The Edit Does Not Grant Approval. After Approval, Supply A New Output Filename.

```sh
python scripts/edit_video.py render "First Cut/timeline.json" "First Cut/Approved Cut.mp4" --owner-approved
python scripts/edit_video.py probe "First Cut/Approved Cut.mp4"
```

The Export Uses H.264 Picture And AAC Sound And Checks Dimensions, Duration, And Audio Channels Before Publishing The File. Add `--no-burn` When Delivering Captions Separately. Both Media Delivery And Sidecar Commands Protect Existing Output Files.

On An Existing Master, Run `python scripts/delivery_check.py finished.mp4 --timeline edit.json` To Decode The File, Check Timing And Frame Size, And List Silence And Black Intervals. Audition The Flagged Moments To Distinguish A Deliberate Pause From A Missing Clip.

## Verification

```sh
python -B -m unittest discover -s tests -p test_edit.py -v
```

The Tests Build Disposable PNG And WAV Fixtures. They Exercise Validation, Audio Analysis, Browser Saving And Media Range Requests, Stereo Routing, Retiming, Reframing, Color, Captions, Interchange Structure, Output Protection, And The Full FFmpeg Filter Graph Without Writing A Video File.
