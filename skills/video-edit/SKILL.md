---
name: video-edit
description: Edit Social Videos From Recorded Footage. Check The Machine, Apply Saved User Defaults And The Brief, Choose A Style, Cut And Caption With Phrase Timing, Convert HDR And Rotated Phone Clips, Level Sound Cues And Loudness, Transfer Camera Motion, Build Native DaVinci Resolve Timelines, And Carry Owner-Approved Media Through Posting Or Scheduling.
---

# Social Cut Kit Video Editor

Build The Edit In A JSON Timeline. Review It In The Included Browser Editor, Which Plays The Original Source Files. Keep The Timeline And Media Together So Another Editor Can Reopen The Project.

## Start Every Session

Run Commands From This Skill Folder. Substitute Your Python Launcher For `python` When Needed.

1. **Check The Machine.** Run `setup` Once On A New Machine, And Again When A Command Reports A Missing Tool. It Prints JSON Listing Each Tool, What It Is For, And An Install Command Suited To This System. It Installs Nothing. Show A Command To The User And Run It Only After They Agree. The Exit Code Is Nonzero Only When A Required Item Is Missing.
2. **Read The Saved Defaults.** `defaults` Prints The Path And Content Of `~/.social-cut-kit/video-edit.md`. The File Is Free-Form Markdown Covering Where Videos Are Posted, Usual Length, Music And Effects, Hook Headline Habits, Caption Style, The Editor The User Wants, Their Export Approval Rule, And Asset Library Locations.
3. **Name What You Apply.** When The File Exists, Begin Your First Reply By Listing, In A Single Line, The Saved Defaults In Use, So The User Can Correct One. Current Instructions Always Override Stored Defaults.
4. **Offer To Keep A Habit.** When The User Calls An Instruction A Habit, Offer To Record It. After They Agree, Add It With `defaults --add`.

```sh
python scripts/edit_video.py setup --project-folder "First Cut"
python scripts/edit_video.py defaults
python scripts/edit_video.py defaults --add "Keep Captions In The Lower Third."
```

Read [The Brief Guide](BRIEF.md) Before Asking A Question Or Applying A Correction. It Holds The Intake Questions, The Active Brief File, And Revision Discipline.

Read [The Style Index](STYLES.md) Before Planning A Cut. It Chooses Between The Talking Head, Skit And Meme, And Screen Demo Guides And Explains How Styles Mix.

## Guides

| When The Work Involves | Read |
| --- | --- |
| Probing, Frame Timing, Sync, Speed, Mixing, Safe Areas, HDR, Checks Without Export, Or Shell Pitfalls | [Technical Reference](TECHNICAL.md) |
| Word Timings, Phrase Captions, Recorder Sync, Or Quiet Dialogue | [Speech And Take Preparation](SPEECH.md) |
| A Headline Or A Highlighted Callout | [Transparent Title Overlays](TITLES.md) |
| Choosing And Leveling A Sound Cue | [Editorial Cue Bank](assets/cue-bank/README.md) |
| Repeated Takes Or A Reference Cut Pattern | [Reference And Take Analysis](RECREATION.md) |
| Giving A Clip The Camera Move Of A Reference | [Camera Motion Transfer](CAMERA.md) |
| An Editable Resolve Project As The Deliverable | [Native Resolve Assembly](RESOLVE.md) |
| Publishing Or Scheduling A Reviewed Master | [Posting And Scheduling](PUBLISH.md) |

## Start With A Working Project

Use Python 3.9 Or Later And Install FFmpeg And FFprobe Separately On Your PATH. Use A Build With The Libass Subtitles Filter For Burned Captions And Libx264 And AAC For MP4 Delivery. The Setup Check Reports Each Of These.

```sh
python scripts/edit_video.py example "First Cut"
python scripts/edit_video.py validate "First Cut/timeline.json"
python scripts/edit_video.py review "First Cut/timeline.json"
```

The Example Creates Two Original PNG Stills, A Stereo WAV, And A Four-Second Editable Timeline In A New Folder. Press Play To Hear Separate Left And Right Tones. At One Second, A Second Image Appears Over The First Shot. Select A Shot To Jump To Its Start, Or Step Through One Frame At A Time.

Place The Playhead Inside A Shot And Select **Split Shot At Playhead**. Select **Save Timeline** To Apply The Split. To Add Text, Select **Add Caption At Playhead**, Replace The Placeholder In The Editable Timeline, And Save. **Reset Unsaved Changes** Restores The Most Recent Save. The Browser Opens A Private Loopback URL. Keep The Terminal Running While Editing. Press Ctrl+C To Close The Editor.

## Build A Cut From Your Footage

1. Copy The Example Timeline To Your Own Project Directory. Add Your Source Files To Its Assets List. Keep Relative Paths For Projects You Expect To Move.
2. Set The Canvas. Use 1080 By 1920 For Vertical, 1920 By 1080 For Horizontal, Or Even Dimensions For A Custom Size. Set The Output Frame Rate Before Timing The Captions.
3. Inspect A Source With `probe`. Its `picture` Entry Reports The Displayed Size, Rotation, Bit Depth, Color Transfer, Primaries, And Whether The Clip Is HDR. Use `analyze` To List Silence Intervals And Candidate Scene Changes. Check Each Candidate Against The Source Before Choosing A Take Or Making A Cut.
4. List The Shots In Playback Order. Set Each Source In And Out Point In Seconds. Use Lead And Tail Handles To Preserve Full Word Beginnings, Endings, And Natural Breaths. Keep Source Dialogue At Its Original Speed And Level Unless The Edit Calls For A Change.
5. Place Overlays, Audio, And Captions Using Time From The Start Of The Assembled Edit. Recheck Their Timing After Moving Or Deleting A Shot.
6. Run `validate`, Run `check`, And Open `review`. Read Any Warnings That `validate` Prints. Inspect Single Frames With `still`, And Measure Levels Where Cues Overlap Speech With `loudness`. The Full Composition Check Decodes To A Null Sink Without Creating A Movie.

```sh
python scripts/edit_video.py probe "Footage/Camera A.mp4"
python scripts/edit_video.py analyze "Footage/Camera A.mp4" --silence-db -40 --silence-length 0.4 --scene-threshold 0.32
python scripts/speech.py --help
python scripts/edit_video.py check "First Cut/timeline.json"
python scripts/edit_video.py still "First Cut/timeline.json" "First Cut/Frame At 2.5.png" --at 2.5
python scripts/edit_video.py loudness "First Cut/timeline.json" --cues
```

## Timeline Fields

The Root Object Requires `version` Set To `1`, A `title`, An `assets` Object, And A Nonempty `shots` List. Use `canvas`, `overlays`, `audio`, `captions`, And `caption_style` As Needed. Field Names And Enumeration Values Are Case Sensitive. Each Media Occurrence Can Use A Different Source Selection.

| Field | Meaning |
| --- | --- |
| `canvas.width`, `canvas.height`, `canvas.fps` | Even Pixel Dimensions And A Whole-Number Frame Rate. Defaults Are 1080 By 1920 At 30 FPS. |
| `canvas.fit`, `shots[].fit` | `contain` Fits The Entire Image Against Black. `cover` Fills The Frame With A Center Crop. A Shot Can Override The Canvas Setting. |
| `canvas.tone_map`, `shots[].tone_map`, `overlays[].tone_map` | `true` By Default. An HDR Source Is Converted To Standard Dynamic Range Once In `check`, `still`, And `render`. Set `false` On The Canvas For The Whole Project, Or On One Shot Or Overlay, To Pass The Picture Through Unconverted. A Shot Or Overlay Setting Overrides The Canvas. The Field Has No Effect On Standard Sources. |
| `assets` | A Map From Asset Names To Objects With A `path` And A `kind` Of `video`, `audio`, Or `image`. Use Static PNG Or JPEG Art For Portable Browser Review. |
| `shots[]` | Each Shot Requires An `asset` And Source `out`. Source `in`, `lead`, And `tail` Default To Zero. The Selected Range Runs From `in - lead` Through `out + tail`. Each Range Must Stay Inside Its Source. |
| `shots[].speed`, `shots[].gain` | Speed Ranges From 0.25 To 4 With Pitch-Preserved Audio. Linear Gain Ranges From 0 To 4. Both Default To 1. Set Gain To 0 To Mute. |
| `shots[].fade_in`, `shots[].fade_out`, `audio[].fade_in`, `audio[].fade_out` | Optional Seconds Of Straight Sound Fade At The Start Or End Of A Shot Or Cue. The Default Is 0, Which Leaves The Sound As Recorded. A Few Milliseconds Removes A Click At A Join. Longer Values Ease A Bed In Or Out. The Picture Is Not Faded. |
| `shots[].zoom`, `pan_x`, `pan_y` | Enlarge A Shot From 1× To 4×. Each Pan Axis Ranges From −1 To 1. Zero Centers The Frame, −1 Anchors The Left Or Top Edge, And 1 Anchors The Right Or Bottom Edge. Split A Shot And Set A Larger Zoom On The Second Half For An Instant Punch-In. |
| `shots[].brightness`, `contrast`, `saturation` | Use Multipliers With 1 As Neutral. Brightness And Contrast Range From 0 To 3. Saturation Ranges From 0 To 2. Zero Saturation Creates A Grayscale Shot. On An HDR Shot These Apply After The Conversion. |
| `overlays[]` | Each Cue Uses `asset`, Timeline `at` And `end`, Optional Source `in`, Optional Pixel `x` And `y`, And Optional Pixel `width`. Coordinates Begin At The Canvas Top Left. Height Follows The Asset Proportions. Later Cues Appear Above Earlier Cues. Overlay Sound Is Muted. |
| `audio[]` | Use An Audio Or Video Asset With An Audio Stream. Set Timeline `at` And `end`, Optional Source `in`, And Optional Linear `gain`. To Repeat A Cue, Add Another Entry. |
| `captions[]` | Set `at`, `end`, And `text`. Optional `position` Accepts `top`, `center`, Or `bottom`. Use A JSON Newline Escape For A Deliberate Line Break. |
| `caption_style` | Set Optional `size` And `stroke` In Canvas Pixels. Set `color` And `outline` To Six-Digit Hex Colors. Set `margin` To A Percentage Of The Canvas Height. Supported `font` Values Are `Arial`, `Georgia`, `Verdana`, `Tahoma`, And `Trebuchet MS`. Font Availability Depends On The System. |

All Timeline Cue Times Snap To The Nearest Output Frame. Each Shot Duration Snaps After Applying The Speed Change. Use One Caption At A Time Per Position. The MP4 Mix Uses Stereo At 48 kHz. A Stereo Source Retains Distinct Left And Right Channels. Monitor Additive Audio Layers For Clipping And Adjust Their Gains As Needed.

## HDR And Rotated Phone Footage

Phone Clips Recorded As HLG, Dolby Vision 8.4, Or HDR10 Look Flat And Desaturated When Their Pixels Are Used Unconverted. `probe` Flags Them, And `validate` Prints A Warning For Each HDR Or Rotated Source In Use. By Default Every HDR Shot Is Tone Mapped To Standard Dynamic Range Exactly Once, So The Check, The Stills, And The Approved Render Agree. Framing, Crop, And Pan Always Use The Displayed, Upright Picture.

The Conversion Needs The `zscale` And `tonemap` Filters. When The FFmpeg Build Lacks One, `check`, `still`, And `render` Stop With A Message That Names It. Install A Fuller Build, Or Set `tone_map` To `false`. The Browser Editor Plays The Original File With The Browser's Own Conversion, So Judge Converted Color On A Still. See [HDR Handling](TECHNICAL.md#hdr-handling).

## Captions

`speech.py captions` Maps A Word Transcript Onto The Cut. Its Phrase Options Group Words Into Short On-Screen Phrases By Word Count, Character Count, Pauses, And Sentence Ends. They Rejoin Split Numbers, Apply Caption-Only Spelling Fixes, Hold A Minimum Time On Screen, And Never Let A Phrase Cross A Cut. Every Word Trimmed By A Cut Is Reported For A Listening Check. See [Phrase Captions](SPEECH.md#phrase-captions).

```sh
python scripts/speech.py captions words.json edit.json --asset interview --phrases --with-timeline --output captioned.json
```

## Sound And Loudness

The [Editorial Cue Bank](assets/cue-bank/README.md) Holds 56 Original Sounds. Its Index Lists Tags, A Suggested Use, The Duration, And Measured Peak And RMS Levels For Each One.

`loudness` Decodes Only The Sound Of The Edit Into A Null Sink. It Reports Integrated Loudness, Loudness Range, True Peak, And The Single Linear Gain That Would Reach A Target. The Default Target Is −14 LUFS With A True Peak Ceiling Of −1.5 dBTP. Add `--cues` To Compare Each Cue With The Speech Under It In A Short Window At The Cue. A Whole-File Average Hides A Short Cue.

The Owner's Dialogue Stays As Recorded By Default. Shot Gain, Sound Fades, And The Render Loudness Option Are Opt-In. Each Changes Only What Its Field Or Flag Names, And The Render Reports The Gain It Applied. See [Mixing Cues Under Speech](TECHNICAL.md#mixing-cues-under-speech).

## Review And Handoff

The Editable Browser Project Includes Cuts, Retiming, Reframing, Color Adjustments, Overlays, Audio Layers, Sound Fades, And Captions. Its Player Uses Browser Codecs And System Fonts. MP4/H.264 With AAC, PNG, JPEG, And WAV Work Well For Source Playback In Common Desktop Browsers. Browser Seeking, Font Layout, Color Management, And Device Performance Can Affect Live Playback. Source Warnings Appear Under The Editor Status. The FFmpeg Check Exercises The Final Composition Graph.

```sh
python scripts/edit_video.py captions "First Cut/timeline.json" "First Cut/Dialogue.srt"
python scripts/edit_video.py handoff "First Cut/timeline.json" "First Cut/Assembly.otio"
python scripts/edit_video.py mix "First Cut/timeline.json" "First Cut/Check Mix.wav"
python scripts/resolve_import.py --help
```

The SRT Uses Millisecond Timing. The OpenTimelineIO Handoff Includes Picture Cuts, Source Sound, Overlay And Audio Tracks, Source References, And Caption Markers. Import Support Varies By Editor. Check Retime Interpretation, Reapply Reframing, Color, Overlay Geometry, Fades, And Levels From The JSON Metadata, And Import The SRT For Editable Captions. Source References In The OTIO File Use Absolute File URIs. Regenerate It After Moving A Project. The Included Browser Editor Uses The Project JSON Directly.

`still` Writes One Composed Frame As A PNG, And `mix` Writes The Composed Sound As A WAV. Both Are Inspection Files For Checking A Correction. Neither Is A Video Export. See [Checking A Correction Without Exporting](TECHNICAL.md#checking-a-correction-without-exporting).

## Approved Delivery

Save The Editable Project And Have Its Owner Personally Review This Version In The Editor. Wait For Explicit Approval Before Any Video Export, Including Preview Or Test Files. An Agent Running Validation, Viewing Stills, Or Measuring Loudness Does Not Grant Approval. After Approval, Supply A New Output Filename.

```sh
python scripts/edit_video.py render "First Cut/timeline.json" "First Cut/Approved Cut.mp4" --owner-approved
python scripts/edit_video.py probe "First Cut/Approved Cut.mp4"
```

The Export Uses H.264 Picture And AAC Sound And Checks Dimensions, Duration, And Audio Channels Before Publishing The File. Add `--no-burn` When Delivering Captions Separately. Both Media Delivery And Sidecar Commands Protect Existing Output Files.

The Sound Is Exported As Mixed. To Opt In To A Loudness Target, Add `--loudness-target -14`. The Render Then Multiplies The Whole Mix By One Constant Gain, With No Compression Or Limiting, And Reports The Measured Loudness Of The Finished File. If That Gain Would Push The True Peak Past The Ceiling, The Render Is Refused Before Anything Is Written. Add `--if-over-ceiling cap` To Apply The Largest Gain That Fits Instead. Change The Ceiling With `--true-peak-ceiling`.

```sh
python scripts/edit_video.py render "First Cut/timeline.json" "First Cut/Approved Cut Loud.mp4" --owner-approved --loudness-target -14 --true-peak-ceiling -1.5 --if-over-ceiling cap
```

On An Existing Master, Run `python scripts/delivery_check.py finished.mp4 --timeline edit.json` To Decode The File, Check Timing And Frame Size, And List Silence And Black Intervals. Audition The Flagged Moments To Distinguish A Deliberate Pause From A Missing Clip.

## After The Edit

When Asked To Reflect On The Session, Follow The Kit's [Reflect Skill](../reflect/SKILL.md). It Reviews The Session From Evidence And Changes An Instruction File Only After The User Approves That Edit. File Each Approved Lesson Where The Next Session Will Find It.

| The Lesson Is | Record It In |
| --- | --- |
| Right For Every Edit | This File |
| Craft For One Style | That Style's Guide Under [The Style Index](STYLES.md) |
| A Command, A Measurement, Or A Tool Pitfall | [Technical Reference](TECHNICAL.md) |
| One Person's Taste | Their Defaults File, With `defaults --add` |

## Verification

```sh
python -B -m unittest discover -s tests -v
node --test tests/test_camera_identity.cjs tests/test_review_player.cjs
```

The Tests Exercise Editing, Setup Checks, Saved Defaults, HDR And Rotated Sources, Loudness, Fades, Phrase Captions, The Sound Bank, Camera Tracking, Native Timeline Assembly, And Posting Receipts With Temporary Fixtures. They Decode Into A Null Sink And Write Only Stills And WAV Files. The Node.js Tests Check That The Camera Review Player Opens The Exact Target File And That The Editor Follows Fades And Shows Source Warnings. Install The Optional Dependencies Listed In The Workflow Guides To Run The Vision And Named-Time-Zone Checks.
