---
name: video-edit
description: Edit Social Videos From Recorded Footage. Check The Machine, Apply Saved User Defaults And The Brief, Choose A Style, Cut And Caption With Phrase Timing, Convert HDR And Rotated Phone Clips, Make An Owner-Agreed Working Copy For Review, Find Retakes Against A Script, Level Sound Cues And Loudness, Transfer Camera Motion, Build Native DaVinci Resolve Timelines, Prepare A Remotion Project For Owner Review And The Approved Render, And Carry Owner-Approved Media Through Posting Or Scheduling.
---

# Video Edit

Build The Edit In A JSON Timeline. Review It In The Included Browser Editor, Which Plays The Source Files, Or A Working Copy Where A Browser Cannot Decode The Original. Keep The Timeline And Media Together So Another Editor Can Reopen The Project. When The Cut Is Ready, Hand It To Its Owner As A Remotion Project, Which Is The Default Route For Owner Review And The Approved Render.

## Start Every Session

Run Commands From This Skill Folder. Substitute Your Python Launcher For `python` When Needed.

1. **Check The Machine.** Run `setup` Once On A New Machine, And Again When A Command Reports A Missing Tool. It Prints JSON Listing Each Tool, What It Is For, And An Install Command Suited To This System. It Installs Nothing. Show A Command To The User And Run It Only After They Agree. The Exit Code Is Nonzero Only When A Required Item Is Missing.
2. **Read The Saved Defaults.** `defaults` Prints The Path And Content Of `~/.social-cut-kit/video-edit.md`. The File Is Free-Form Markdown Covering Where Videos Are Posted, Usual Length, Music And Effects, Hook Headline Habits, Caption Style, The Editor The User Wants, Their Export Approval Rule, And Asset Library Locations.
3. **Name What You Apply.** When The File Exists, Begin Your First Reply By Listing, In A Single Line, The Saved Defaults In Use, So The User Can Correct One. Current Instructions Always Override Stored Defaults.
4. **Offer To Keep A Habit.** When The User Calls An Instruction A Habit, Offer To Record It. After They Agree, Add It With `defaults --add`.
5. **Look For A Script.** Search The Project Folder For A Script Or Outline, Such As `script.txt`, Before Choosing Takes. It Is The Reference For Story Order, Take Choice, Caption Spellings, And Claims. It Is Not A Word List To Enforce. [The Script Or Outline](BRIEF.md#the-script-or-outline) Says What To Do When The Spoken Words Depart From It.

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
| Restarts, Full Retakes, Script Alignment, Or A Reference Cut Pattern | [Reference And Take Analysis](RECREATION.md) |
| A Source A Browser Cannot Play, Or HDR Footage Reviewed In Remotion | [Working Copies For Review](TECHNICAL.md#working-copies-for-review) |
| Giving A Clip The Camera Move Of A Reference | [Camera Motion Transfer](CAMERA.md) |
| Owner Review Or The Approved Render In Remotion, And What Differs There | [Remotion Review And Render](remotion/README.md) |
| An Editable Resolve Project As The Deliverable | [Native Resolve Assembly](RESOLVE.md) |
| Publishing Or Scheduling A Reviewed Master | [Posting And Scheduling](PUBLISH.md) |
| A Graphic That Has To Be Drawn And Animated | [Animated Inserts](INSERTS.md) |

When The Owner Asks For Animated Graphics, Or A Beat Needs Movement That A Screenshot Or A Title Cannot Carry, Follow [Animated Inserts](INSERTS.md). It Has You List Those Beats, Write A Shot Brief For Each, And Hand Them To The Animated Video Skill Without Being Asked Again.

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
2. Inspect Each Source With `probe`. Its `picture` Entry Reports The Displayed Size, Rotation, Bit Depth, Color Transfer, Primaries, And Whether The Clip Is HDR. Its `browser_playback` Entry Says Whether A Browser Is Likely To Play The File, And Its `canvas_fps` Entry Suggests A Canvas Rate. When A Browser Is Unlikely To Play A Source, Follow [When A Browser Cannot Play The Source](#when-a-browser-cannot-play-the-source) Before Opening `review`.
3. Set The Canvas. Use 1080 By 1920 For Vertical, 1920 By 1080 For Horizontal, Or Even Dimensions For A Custom Size. Set The Frame Rate By The [Canvas Frame Rate](#canvas-frame-rate) Rule Before Timing The Captions.
4. Find The Material. Use `analyze` To List Silence Intervals And Candidate Scene Changes. Transcribe The Speech, Then Run `takes.py` With `--retakes`, And With `--script` When The Project Has A Script. It Groups Every Attempt At The Same Line, However Far Apart, Hints At Which Attempts Are Complete, And Lists Script Lines With No Complete Take. It Cannot Hear Performance. When Attempts Are Equally Complete, Offer The Owner The Choice. Check Each Candidate Against The Source Before Choosing A Take Or Making A Cut.
5. List The Shots In Playback Order. Set Each Source In And Out Point In Seconds. Use Lead And Tail Handles To Preserve Full Word Beginnings, Endings, And Natural Breaths. Keep Source Dialogue At Its Original Speed And Level Unless The Edit Calls For A Change.
6. Place Overlays, Audio, And Captions Using Time From The Start Of The Assembled Edit. Recheck Their Timing After Moving Or Deleting A Shot.
7. Run `validate`, Run `check`, And Open `review`. Read Any Warnings That `validate` Prints. Inspect Single Frames With `still`, And Measure Levels Where Cues Overlap Speech With `loudness`. The Full Composition Check Decodes To A Null Sink Without Creating A Movie.
8. Prepare A Remotion Project For The Owner, As [Approved Delivery](#approved-delivery) Describes. Preparation Writes No Video.

```sh
python scripts/edit_video.py probe "Footage/Camera A.mp4"
python scripts/edit_video.py analyze "Footage/Camera A.mp4" --silence-db -40 --silence-length 0.4 --scene-threshold 0.32
python scripts/speech.py --help
python scripts/takes.py words.json --retakes --script script.txt
python scripts/edit_video.py check "First Cut/timeline.json"
python scripts/edit_video.py still "First Cut/timeline.json" "First Cut/Frame At 2.5.png" --at 2.5
python scripts/edit_video.py loudness "First Cut/timeline.json" --cues
```

## Canvas Frame Rate

The Canvas Rate Is A Whole Number. This Is The One Rule For Choosing It, And Every Other Guide Points Here.

1. **Find The Main Source.** It Is The Clip That Carries Most Of The Dialogue Or Screen Time. Read Its `frame_rate` From `probe`.
2. **Take The Nearest Standard Rate.** The Standard Rates Are 24, 25, 30, 48, 50, 60, 100, And 120. A 23.976 Source Counts As 24, 29.97 As 30, And 59.94 As 60.
3. **Halve It While It Is Above 30.** 60 Becomes 30, 50 Becomes 25, 48 Becomes 24, And 120 Becomes 30. The Canvas Then Shows Every Second Source Frame, Which Plays Evenly. The Result Is Always 24, 25, Or 30.
4. **Keep A Higher Rate Only On Request.** Use 50 Or 60 Only When The Owner Asks For That Delivery Rate And The Main Source Was Shot At It.
5. **Mixed Sources Follow The Main Source.** Every Other Clip Is Resampled To The Canvas Rate By Timestamp. When A Secondary Clip Does Not Divide Evenly Into The Canvas Rate, Such As A 25 FPS Clip On A 30 FPS Canvas, Its Motion Stutters Slightly. Tell The Owner, And Keep The Main Source's Rate.

| Main Source | Canvas |
| --- | --- |
| 23.976 Or 24 | 24 |
| 25 Or 50 | 25 |
| 29.97, 30, 59.94, 60, Or 120 | 30 |
| A Variable Rate, Such As A Phone Or Screen Recording | The Same Rule Applied To Its Average Rate |

`probe` Prints This Suggestion As `canvas_fps`, And `setup --project-folder` Lists It For Every Video In The Project Folder. Set The Rate Before Timing Captions, Because Every Cue Snaps To The Frame Grid.

## Timeline Fields

The Root Object Requires `version` Set To `1`, A `title`, An `assets` Object, And A Nonempty `shots` List. Use `canvas`, `overlays`, `audio`, `captions`, And `caption_style` As Needed. Field Names And Enumeration Values Are Case Sensitive. Each Media Occurrence Can Use A Different Source Selection.

| Field | Meaning |
| --- | --- |
| `canvas.width`, `canvas.height`, `canvas.fps` | Even Pixel Dimensions And A Whole-Number Frame Rate. Defaults Are 1080 By 1920 At 30 FPS. |
| `canvas.fit`, `shots[].fit` | `contain` Fits The Entire Image Against Black. `cover` Fills The Frame With A Center Crop. A Shot Can Override The Canvas Setting. |
| `canvas.tone_map`, `shots[].tone_map`, `overlays[].tone_map` | `true` By Default. An HDR Source Is Converted To Standard Dynamic Range Once In `check`, `still`, And `render`. Set `false` On The Canvas For The Whole Project, Or On One Shot Or Overlay, To Pass The Picture Through Unconverted. A Shot Or Overlay Setting Overrides The Canvas. The Field Has No Effect On Standard Sources. |
| `assets` | A Map From Asset Names To Objects With A `path` And A `kind` Of `video`, `audio`, Or `image`. A Video Asset May Also Name A `working_copy`, A Converted Copy That The Browser Editor And Remotion Play. `path` Stays On The Original, Which Every Check And The FFmpeg Render Read. Use Static PNG Or JPEG Art For Portable Browser Review. |
| `shots[]` | Each Shot Requires An `asset` And Source `out`. Source `in`, `lead`, And `tail` Default To Zero. The Selected Range Runs From `in - lead` Through `out + tail`. Each Range Must Stay Inside Its Source. |
| `shots[].speed`, `shots[].gain` | Speed Ranges From 0.25 To 4 With Pitch-Preserved Audio. Linear Gain Ranges From 0 To 4. Both Default To 1. Set Gain To 0 To Mute. |
| `shots[].fade_in`, `shots[].fade_out`, `audio[].fade_in`, `audio[].fade_out` | Optional Seconds Of Straight Sound Fade At The Start Or End Of A Shot Or Cue. The Default Is 0, Which Leaves The Sound As Recorded. A Few Milliseconds Removes A Click At A Join. Longer Values Ease A Bed In Or Out. The Picture Is Not Faded. |
| `shots[].zoom`, `pan_x`, `pan_y` | Enlarge A Shot From 1× To 4×. Each Pan Axis Ranges From −1 To 1. Zero Centers The Frame, −1 Anchors The Left Or Top Edge, And 1 Anchors The Right Or Bottom Edge. Split A Shot And Set A Larger Zoom On The Second Half For An Instant Punch-In. |
| `shots[].brightness`, `contrast`, `saturation` | Use Multipliers With 1 As Neutral. Brightness And Contrast Range From 0 To 3. Saturation Ranges From 0 To 2. Zero Saturation Creates A Grayscale Shot. On An HDR Shot These Apply After The Conversion. |
| `overlays[]` | Each Cue Uses `asset`, Timeline `at` And `end`, Optional Source `in`, Optional Pixel `x` And `y`, And Optional Pixel `width`. Coordinates Begin At The Canvas Top Left. Height Follows The Asset Proportions. Later Cues Appear Above Earlier Cues. Overlay Sound Is Muted. |
| `audio[]` | Use An Audio Or Video Asset With An Audio Stream. Set Timeline `at` And `end`, Optional Source `in`, And Optional Linear `gain`. To Repeat A Cue, Add Another Entry. |
| `captions[]` | Set `at`, `end`, And `text`. Optional `position` Accepts `top`, `center`, Or `bottom`. Use A JSON Newline Escape For A Deliberate Line Break. |
| `caption_style` | Set Optional `size` And `stroke` In Canvas Pixels. Set `color` And `outline` To Six-Digit Hex Colors. Set `margin` To A Percentage Of The Canvas Height Between A `bottom` Caption And The Bottom Edge, And Optional `top_margin` To The Same Measure Between A `top` Caption And The Top Edge. On A Vertical Canvas The Defaults Are A `size` Of 6 Percent Of The Canvas Width, Which Is 65 On A 1080 Wide Canvas, A `margin` Of 25, And A `top_margin` Of 12. On A Horizontal Or Square Canvas The Default `size` Is About 7.8 Percent Of The Height And Both Margins Are 7. A Timeline That Sets `margin` Alone Uses It At Both Edges. Supported `font` Values Are `Arial`, `Georgia`, `Verdana`, `Tahoma`, And `Trebuchet MS`. Font Availability Depends On The System. |

All Timeline Cue Times Snap To The Nearest Output Frame. Each Shot Duration Snaps After Applying The Speed Change. Use One Caption At A Time Per Position. The MP4 Mix Uses Stereo At 48 kHz. A Stereo Source Retains Distinct Left And Right Channels. Monitor Additive Audio Layers For Clipping And Adjust Their Gains As Needed.

## HDR And Rotated Phone Footage

Phone Clips Recorded As HLG, Dolby Vision 8.4, Or HDR10 Look Flat And Desaturated When Their Pixels Are Used Unconverted. `probe` Flags Them, And `validate` Prints A Warning For Each HDR Or Rotated Source In Use. By Default Every HDR Shot Is Tone Mapped To Standard Dynamic Range Exactly Once, So The Check, The Stills, And The Approved Render Agree. Framing, Crop, And Pan Always Use The Displayed, Upright Picture.

The Conversion Needs The `zscale` And `tonemap` Filters. When The FFmpeg Build Lacks One, `check`, `still`, And `render` Stop With A Message That Names It. Install A Fuller Build, Or Set `tone_map` To `false`. See [HDR Handling](TECHNICAL.md#hdr-handling).

**The FFmpeg Render From The Original Files Produces The Master For HDR Footage.** It Applies The Single Conversion At Full Quality, And `still` Shows Exactly What It Will Deliver. Remotion Is The Review Route There, Through A Working Copy.

### When A Browser Cannot Play The Source

Many Browsers Cannot Decode 4K HEVC HDR Phone Footage, And Remotion Does Not Apply The Kit's Conversion. `probe` And `setup` Report This Under `browser_playback`, `validate` Warns About Each Such Source In Use, The Browser Editor Names The Fix When A Source Fails To Load, And The `remotion` Command Refuses An HDR Source That Has No Working Copy. Do Not Stop There. Do This.

1. **Ask The Owner Once, In Plain Words.** For Example: "Your Browser Cannot Play This Phone Clip. May I Make A Smaller Standard Copy Of It For Review Only? Your Original Stays Untouched, And The Final Video Is Still Made From It." A Working Copy Is A Converted Copy Of Raw Footage, Not A Cut. It Is Still A Video File, So It Waits For That Yes. One Yes Covers The Clips Named In The Question.
2. **Make The Working Copy.** Add `--owner-agreed-working-copy` Only After The Owner Agrees. `--plan` Prints The Conversion And `--check` Runs It Into A Null Sink. Neither Writes A File, And Neither Needs The Flag.
3. **Name It In The Timeline.** Set The Asset's `working_copy` To The New File And Leave `path` On The Original.
4. **Review.** The Browser Editor And The Remotion Project Now Play The Working Copy, Which Carries The Kit's Conversion And Is Stored Upright. `validate`, `check`, `still`, `loudness`, `mix`, And `render` Keep Reading The Original. `validate` Warns When The Copy's Duration Or Frame Count Disagrees With Its Original.
5. **Deliver From The Original.** After The Owner Approves The Edit, Render The Master With [The FFmpeg Route](#render-with-ffmpeg-without-node-packages) And `--owner-approved`. A Remotion Render Of A Timeline With Working Copies Would Be Made From The Smaller Copies, So Do Not Use It For The Master.

```sh
python scripts/edit_video.py working-copy "Footage/Phone Clip.mov" "Footage/Phone Clip Working Copy.mp4" --plan
python scripts/edit_video.py working-copy "Footage/Phone Clip.mov" "Footage/Phone Clip Working Copy.mp4" --owner-agreed-working-copy
```

`--owner-agreed-working-copy` Never Approves An Export, And `--owner-approved` Never Makes A Working Copy. If The Owner Declines, Review With Stills And A Check Mix, Or In Resolve Through The [Native Build](RESOLVE.md). See [Working Copies For Review](TECHNICAL.md#working-copies-for-review).

## Captions

`speech.py captions` Maps A Word Transcript Onto The Cut. Its Phrase Options Group Words Into Short On-Screen Phrases By Word Count, Character Count, Pauses, And Sentence Ends. They Rejoin Split Numbers, Apply Caption-Only Spelling Fixes, Hold A Minimum Time On Screen, And Never Let A Phrase Cross A Cut. Every Word Trimmed By A Cut Is Reported For A Listening Check. See [Phrase Captions](SPEECH.md#phrase-captions).

The Tool Defaults Follow The Canvas. On A Vertical Canvas A Phrase Holds Up To 3 Words And 20 Characters, The Caption `size` Is 6 Percent Of The Canvas Width, And Bottom Captions Sit 25 Percent Above The Bottom Edge, Clear Of The Platform's Description And Buttons. On A Horizontal Or Square Canvas A Phrase Holds Up To 4 Words And 28 Characters And The Margin Is 7 Percent. An Explicit Option Or `caption_style` Value Always Overrides A Default. Take Spellings Of Names And Keywords From The Script When There Is One.

```sh
python scripts/speech.py captions words.json edit.json --asset interview --phrases --with-timeline --output captioned.json
```

## Sound And Loudness

The [Editorial Cue Bank](assets/cue-bank/README.md) Holds 56 Original Sounds. Its Index Lists Tags, A Suggested Use, The Duration, And Measured Peak And RMS Levels For Each One.

`loudness` Decodes Only The Sound Of The Edit Into A Null Sink. It Reports Integrated Loudness, Loudness Range, True Peak, And The Single Linear Gain That Would Reach A Target. The Default Target Is −14 LUFS With A True Peak Ceiling Of −1.5 dBTP. Add `--cues` To Compare Each Cue With The Speech Under It In A Short Window At The Cue. A Whole-File Average Hides A Short Cue.

The Owner's Dialogue Stays As Recorded By Default. Shot Gain, Sound Fades, And The Render Loudness Option Are Opt-In. Each Changes Only What Its Field Or Flag Names, And The Render Reports The Gain It Applied. See [Mixing Cues Under Speech](TECHNICAL.md#mixing-cues-under-speech).

## Review And Handoff

The Editable Browser Project Includes Cuts, Retiming, Reframing, Color Adjustments, Overlays, Audio Layers, Sound Fades, And Captions. Its Player Uses Browser Codecs And System Fonts. MP4/H.264 With AAC, PNG, JPEG, And WAV Work Well For Source Playback In Common Desktop Browsers. A Video Asset That Names A `working_copy` Plays That Copy. Browser Seeking, Font Layout, Color Management, And Device Performance Can Affect Live Playback. Source Warnings Appear Under The Editor Status. The FFmpeg Check Exercises The Final Composition Graph.

```sh
python scripts/edit_video.py captions "First Cut/timeline.json" "First Cut/Dialogue.srt"
python scripts/edit_video.py handoff "First Cut/timeline.json" "First Cut/Assembly.otio"
python scripts/edit_video.py mix "First Cut/timeline.json" "First Cut/Check Mix.wav"
python scripts/resolve_import.py --help
```

The SRT Uses Millisecond Timing. The OpenTimelineIO Handoff Includes Picture Cuts, Source Sound, Overlay And Audio Tracks, Source References, And Caption Markers. Import Support Varies By Editor. Check Retime Interpretation, Reapply Reframing, Color, Overlay Geometry, Fades, And Levels From The JSON Metadata, And Import The SRT For Editable Captions. Source References In The OTIO File Use Absolute File URIs. Regenerate It After Moving A Project. The Included Browser Editor Uses The Project JSON Directly.

`still` Writes One Composed Frame As A PNG, And `mix` Writes The Composed Sound As A WAV. Both Are Inspection Files For Checking A Correction. Neither Is A Video Export. See [Checking A Correction Without Exporting](TECHNICAL.md#checking-a-correction-without-exporting).

## Approved Delivery

Remotion Is The Default Route For Owner Review And The Finished Video. The Browser Editor And The Non-Exporting Checks `validate`, `check`, `still`, `loudness`, And `mix` Stay Exactly As They Are, And They Remain The Way To Verify An Edit Before Approval. The FFmpeg Render Below Stays Available And Needs No Node Packages. When A Source Is HDR Or Plays From A Working Copy, Remotion Is For Review, And The FFmpeg Render From The Originals Produces The Master.

1. **Verify The Edit.** Run The Checks, Read Every Warning, And Fix The Timeline Until They Pass.
2. **Prepare The Project.** The `remotion` Command Writes A Standalone Project Folder With The Media, A Copy Of The Timeline, And No Video. Read Its Warnings. Each One Names Something Remotion Reproduces Differently From The Checks, Such As A Retimed Shot, A Very Short Fade, Or A Format The Browser Cannot Play. It Refuses An HDR Source That Has No Working Copy And Says How To Make One. With A Working Copy It Prepares The Project And Warns That Picture Color In Remotion Comes From That Copy.
3. **Install And Open.** Each Generated Project Needs Node.js And Its Own `npm install`, Which Uses The Network. Remotion Has Its Own License Terms. `npm run studio` Opens Remotion Studio.
4. **Owner Review.** Save The Editable Project And Have Its Owner Personally Review This Version In The Editor. By Default That Editor Is Remotion Studio, Where The Owner Opens **VideoEdit**, Watches The Entire Cut With Sound, And Checks Word Beginnings And Endings At Every Cut. Wait For Explicit Approval Before Any Video Export, Including Preview Or Test Files. An Agent Running Validation, Viewing Stills, Or Measuring Loudness Does Not Grant Approval. After Any Change, Prepare A Fresh Project And Repeat The Review.
5. **Render.** After Approval, The Owner Runs The Gated Render In An Interactive Terminal. It Asks For Personal Confirmation And Refuses To Replace A File. Never Use Remotion Studio's Own Render Button Or Remotion's `render` Command, Because Neither Asks For Approval. For A Timeline With Working Copies, Render The Master With The FFmpeg Route Below Instead.

```sh
python scripts/edit_video.py remotion "First Cut/timeline.json" "First Cut Remotion"
cd "First Cut Remotion"
npm install
npm run studio
npm run render-reviewed -- "Approved Cut.mp4"
```

Sound In The Remotion Route Has Not Been Verified By This Kit, So The Owner's Listening Review Is The Check. Read [Remotion Review And Render](remotion/README.md) For Every Known Difference In HDR, Retimed Sound, Caption Fonts, And Media Formats.

### Render With FFmpeg Without Node Packages

Use This Route When Node Packages Cannot Be Installed, For HDR Sources And Any Timeline With Working Copies, For A Loudness Target, For Separate Captions, Or When The Result Must Match The Checks Exactly. It Always Reads The Original Files, Never A Working Copy. The Owner Reviews The Saved Timeline In The Browser Editor, And The Same Approval Rule Applies. After Approval, Supply A New Output Filename.

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
node --test tests/test_camera_identity.cjs tests/test_review_player.cjs tests/test_remotion_plan.cjs tests/test_remotion_project.cjs
```

The Tests Exercise Editing, Setup Checks, Saved Defaults, HDR And Rotated Sources, Working Copies, Caption Defaults, Take Detection, Loudness, Fades, Phrase Captions, The Sound Bank, Camera Tracking, Native Timeline Assembly, Remotion Project Preparation, And Posting Receipts With Temporary Fixtures. They Decode Into A Null Sink And Write Only Stills And WAV Files. The Working Copy Tests Inspect The Command, The Graph, And The Refusals, And Run The Picture Chain Into A Null Sink. They Never Convert A File. The Node.js Tests Check That The Camera Review Player Opens The Exact Target File, That The Editor Follows Fades And Shows Source Warnings, And That The Remotion Adapter Snaps Frames, Frames Shots, And Builds A Project As The Timeline Describes. They Do Not Install Remotion. Install The Optional Dependencies Listed In The Workflow Guides To Run The Vision And Named-Time-Zone Checks.
