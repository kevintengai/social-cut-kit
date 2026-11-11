# Technical Reference

A Working Reference For The Tools In This Folder. Each Section States What The Kit Does, What To Measure, And Which Command Measures It. Run Commands From The Skill Folder. In This Kit Only Two Commands Write A Video: A Render That Carries `--owner-approved`, And A [Working Copy](#working-copies-for-review) That Carries `--owner-agreed-working-copy`. No Other Command In This Reference Does.

## Probing And Displayed Geometry

```sh
python scripts/edit_video.py probe "Footage/Phone Clip.mov"
```

`probe` Prints The Raw `video` And `audio` Streams From FFprobe, The Container `duration`, And A `picture` Summary.

| Field In `picture` | Meaning |
| --- | --- |
| `coded_size`, `displayed_size` | Stored Pixels, And The Upright Size After Rotation And Non-Square Pixels Are Applied. |
| `rotation` | Clockwise Degrees Applied For Display. A Portrait Phone Clip Is Usually Stored 3840 By 2160 With A Rotation Of 90. |
| `bit_depth`, `pixel_format`, `codec`, `frame_rate` | Sample Depth, Layout, Codec Name, And The Average Frame Rate. |
| `color_transfer`, `color_primaries`, `color_space`, `color_range` | Color Signalling As Tagged In The File, Or `unspecified`. |
| `hdr`, `peak_nits`, `dolby_vision` | `pq`, `hlg`, Or Null. The Peak Comes From Light Level Metadata When Present. Dolby Vision Lists Its Profile. |

`probe` Also Prints Two Hints Beside The Streams.

| Hint | Meaning |
| --- | --- |
| `browser_playback` | `likely` Says Whether A Common Desktop Browser Should Play The File. `reasons` Names Each Doubt, Such As HEVC, HDR, A 10-Bit Picture, Or A Large Frame At A High Rate. `advice` Points To A [Working Copy](#working-copies-for-review). |
| `canvas_fps` | The Canvas Rate That The [Canvas Frame Rate](SKILL.md#canvas-frame-rate) Rule Gives For This Source, With The Reason. |

`setup --project-folder` Lists The Same Hints Under `sources` For Each Video It Finds In The Project Folder And Up To Two Folders Below It.

- FFmpeg Turns Rotated Frames Upright Before Any Filter Runs, And The Kit Frames The Displayed Picture. Crop, `zoom`, `pan_x`, `pan_y`, And Overlay Positions All Refer To What A Viewer Sees. Never Add A Rotation To Correct A Phone Clip.
- `validate` Warns When A Source In Use Is Rotated Or HDR, And Names The Displayed Size It Framed.
- Phone Clips And Screen Recordings Often Have A Variable Frame Rate. The Kit Places Frames By Timestamp And Resamples Every Shot To The Canvas Rate, So Work In Seconds And Never In Source Frame Counts.
- Choose The Canvas Rate By The [Canvas Frame Rate](SKILL.md#canvas-frame-rate) Rule. It Gives A Rate The Main Source Divides Into Evenly, So A 60 FPS Source Plays Cleanly On A 30 FPS Canvas. A Secondary Clip That Does Not Divide Evenly Stutters On Motion. A 30 FPS Clip On A 24 FPS Canvas Drops One Frame In Five.
- A Mono Source Plays From Both Channels. A Stereo Source Keeps Its Left And Right. The Mix Is Stereo At 48 kHz.
- A Selection That Runs Past The End Of Its Source Is Refused By `validate`. Compare `out` Plus `tail` With The Probed `duration`.

## Frame-Accurate Cut Points

- Every Shot Lasts A Whole Number Of Output Frames. Its Length Is The Source Range With Handles, Divided By `speed`, Snapped To The Nearest Frame. Overlay, Cue, And Caption Times Snap The Same Way.
- Frame `n` Begins At `n` Divided By The Frame Rate. At 30 FPS, Frame 75 Begins At 2.5 Seconds. To Move A Cut By One Output Frame, Change `in` Or `out` By `speed` Divided By The Frame Rate.
- Inspect Both Sides Of A Cut With Two Stills: The Last Frame Of The Outgoing Shot And The First Frame Of The Incoming Shot.

```sh
python scripts/edit_video.py still "First Cut/timeline.json" "First Cut/Before Cut.png" --at 1.958
python scripts/edit_video.py still "First Cut/timeline.json" "First Cut/After Cut.png" --at 2.0
```

**Why Picture And Sound Segments Must Match In Length.** The Kit Builds Each Shot As One Picture Segment And One Sound Segment, Then Joins The Shots In Order. If The Sound Of One Shot Were A Few Milliseconds Longer Than Its Picture, Every Later Shot Would Start Late By That Amount, And The Error Would Grow With Each Cut Until Lips And Words Part. The Kit Therefore Trims Or Pads Each Shot's Sound To Exactly The Shot's Frame-Snapped Length, And Holds The Last Picture Frame When A Source Ends Early. `check` Confirms The Total Frame Count. When Sync Slips After A Cut, Fix The Shot Where It First Slips. Do Not Nudge Later Cues To Compensate.

At 24, 25, 30, 50, And 60 FPS One Frame Is A Whole Number Of 48 kHz Samples, So Segments Match To The Sample. The [Canvas Frame Rate](SKILL.md#canvas-frame-rate) Rule Always Lands On One Of Those Rates.

## Handles And Short Fades At Joins

- `lead` And `tail` Extend A Shot Before Its `in` And After Its `out`. Use Them To Keep The Breath Before A Word And The Consonant That Ends It. A Tenth Of A Second Is A Common Start. `python scripts/takes.py words.json --retakes` Suggests Audition Ranges With Speech-Safe Handles For Restarts And Full Retakes.
- Cut Sound Where It Is Quiet. `analyze` Lists Silences, And A Word Transcript Gives The Gap Between Two Words. A Cut Inside A Held Vowel Or A Loud Room Clicks, Because The Waveform Jumps.
- When A Click Remains, Add A Fade Of 0.005 To 0.02 Seconds: `fade_out` On The Outgoing Shot And `fade_in` On The Incoming Shot. The Fade Is A Straight Ramp On That Shot's Own Sound. It Is Opt-In, It Changes Only Those Milliseconds, And The Picture Is Untouched. Past About 0.03 Seconds A Dialogue Fade Starts To Sound Like A Dip.
- Use The Same Fields On An `audio[]` Entry To Ease Music Or A Bed In And Out Over 0.25 To 2 Seconds.
- A Click Is Heard, Not Measured. Ask The Owner To Listen At The Cut In The Editor, Which Plays The Same Fades. A Level Jump Can Be Measured. Compare Half A Second Of Speech On Each Side Of The Cut.

```sh
python scripts/edit_video.py loudness "First Cut/timeline.json" --layer voice --start 1.5 --seconds 0.5
python scripts/edit_video.py loudness "First Cut/timeline.json" --layer voice --start 2.0 --seconds 0.5
```

A Difference In `rms_dbfs` Of More Than About 3 dB Across A Cut Is Audible As A Jump. Match It With Shot `gain`, Which Is Linear: 0.5 Is 6 dB Down, And 2 Is 6 dB Up. Digital Silence Between Two Shots Sounds Like A Dropout. Lay A Quiet Room Tone From The [Cue Bank](assets/cue-bank/README.md) Under The Gap.

## Syncing A Separate Recorder

```sh
python scripts/speech.py sync camera.mp4 recorder.wav --seconds 30 --lag 5
python scripts/speech.py sync camera.mp4 recorder.wav --seconds 30 --lag 5 --start 600
```

- The Tool Compares Loudness Envelopes In 0.01 Second Steps. A Positive `secondary_event_later_by_seconds` Means The Recorder Hears Each Event That Much Later Than The Camera. Recorder Time Equals Camera Time Plus That Value.
- Trust A Result When `correlation` Is High And Clearly Above `next_distinct_correlation`. Music, Applause, And Evenly Spaced Claps Give Several Similar Peaks. Sample A Stretch With Irregular Speech Instead.
- The Search Reaches At Most 30 Seconds Either Way, And No Further Than Half The Sample Length. Start Both Devices Within That Window.
- **Check For Drift.** Two Devices Never Count Time At Exactly The Same Rate. Measure Again Late In The Take With `--start`, Which Begins Both Samples That Many Seconds In. If The Offset Moved, Divide The Change By The Seconds Between The Two Readings To Get The Drift Per Second. A Change Of One Frame Over Ten Minutes Is Common Between Separate Devices And Matters On Long Takes.
- **Use The Recorder In The Edit.** Mute The Camera Sound With Shot `gain` Set To 0. Add One `audio[]` Entry Per Shot From The Recorder. Its `at` And `end` Are The Shot's Edit Times. Its Source `in` Is The Shot's Source Start, Which Is `in` Minus `lead`, Plus The Offset For That Moment. With Drift, Use The Offset At That Shot: The Starting Offset Plus Drift Per Second Times The Shot's Source Start. Short Shots Hide Drift That A Long Take Would Reveal.
- Recorder Entries Play At Normal Speed. Keep `speed` At 1 On Shots That Use Them.
- Keep Sound Within One Frame Of Picture. Sound That Arrives Early Is Noticed Sooner Than Sound That Arrives Late. Confirm On Hard Consonants In `review`.

## Speed Changes And What To Retime

- `speed` Ranges From 0.25 To 4. Picture Is Retimed By Timestamp, With Frames Dropped Or Repeated To Meet The Canvas Rate. Sound Changes Tempo With Its Pitch Preserved.
- Slow Motion Needs Spare Frames. To Play At Half Speed Without Repeats, The Source Rate Must Be At Least Twice The Canvas Rate.
- Speech Faster Than About 1.25 Or Slower Than About 0.8 Sounds Processed. Reserve Larger Changes For Passages Without Speech, Such As A Screen Recording.
- A Speed Change Alters The Shot's Length. Later Shots Follow Automatically. Overlays, Cues, And Captions Do Not, Because Their Times Are Edit Times.

| After Changing `speed`, `in`, `out`, `lead`, Or `tail` | Do This |
| --- | --- |
| Items After The Shot | Shift `at` And `end` By The Change In The Shot's Length. |
| Items Inside The Shot | Recompute From Source Time. New Edit Time Is The Shot's Start Plus Source Seconds Into The Shot Divided By The New `speed`. |
| Captions | Run The Caption Mapper Again With `--replace-existing`. It Follows Trims, Handles, And Speed. |
| Music And Beds | They Keep Normal Speed. Recheck Where They End Against The New Total Length. |
| Loudness And Cue Levels | Measure Again. The Mix Changed. |

Run `validate` After Retiming. It Refuses Any Cue That No Longer Fits Inside The Edit.

## Mixing Cues Under Speech

The Sound Of The Shots Forms The Voice Layer. Each `audio[]` Entry Is Added On Top At Its `gain`. Levels Add: Two Layers At The Same Level Can Raise The Peak By Up To 6 dB. Nothing Is Normalized Or Limited, So A Peak Above Full Scale Clips In The Exported File.

```sh
python scripts/speech.py levels interview.wav
python scripts/edit_video.py loudness "First Cut/timeline.json"
python scripts/edit_video.py loudness "First Cut/timeline.json" --cues --cue-aim -12
python scripts/edit_video.py loudness "First Cut/timeline.json" --layer cues --start 3 --seconds 0.5
```

| Field | Meaning |
| --- | --- |
| `integrated_lufs`, `loudness_range_lu` | Programme Loudness And Its Spread. Null When The Sound Is Silent Or Shorter Than 0.4 Seconds. |
| `true_peak_dbtp` | The Highest Peak Between Samples. Above 0, The File Clips. Keep It Under The Ceiling. |
| `rms_dbfs`, `sample_peak_dbfs` | Average And Peak Sample Level. A Full-Scale Sine Reads −3 dBFS Average. |
| `gain_db`, `linear_gain` | The Single Gain That Moves The Whole Mix To The Target. |
| `breaches_ceiling`, `largest_gain_within_ceiling_db` | Whether That Gain Would Pass The True Peak Ceiling, And The Most Gain That Would Not. |

**Judge A Cue At The Cue.** A Half-Second Tap In A Forty-Second Edit Barely Moves A Whole-File Average, So The Average Cannot Say Whether The Tap Is Heard. `--cues` Measures A Short Window That Starts With Each Cue, At Most `--cue-window` Seconds Long. It Reports The Cue Alone, The Speech Under It, And The Difference.

| `cue_minus_speech_db` | Reading |
| --- | --- |
| 3 Or More | Louder Than Speech. Expect It To Cover Words. |
| −6 To 3 | Close To Speech Level. Prominent. |
| −18 To −6 | Under Speech. Audible As Support. |
| −26 To −18 | Well Under Speech. Subtle, And It May Vanish On A Phone Speaker. |
| Below −26 | Likely Masked By Speech. |

- These Bands Are Rules Of Thumb. Bright, Short Sounds Cut Through At Lower Levels Than Dull, Long Ones. The Owner's Ears Decide In `review`.
- When The Window Holds No Speech, The Cue Plays In The Clear. Compare It With A Speech Window Nearby Instead, Using `--layer voice`.
- `--cue-aim -12` Adds `gain_for_aim`, The Cue Gain That Would Place It 12 dB Under Speech. The Arithmetic Is The Current Gain Times Ten To The Power Of The Wanted Change In dB Divided By 20.
- For A Long Bed Or A Build, Measure The Moment That Matters With `--start` And `--seconds`.
- Phone Speakers Reproduce Little Below About 300 Hz. A Low Cue Can Measure Well And Still Be Inaudible On A Phone. The Cue Bank Notes Which Cues Carry A Mid Layer.
- To Stop Clipping, Lower The Cue, Not The Voice. `mix_true_peak_dbtp` Shows The Peak Of Everything Together During Each Cue.

**Loudness Target.** Social Platforms Commonly Play Near −14 LUFS. The Default Export Leaves The Mix Exactly As Reviewed. The Opt-In `--loudness-target` On `render` Applies One Constant Gain To The Whole Mix, Speech Included, With No Compression, Limiting, Or Equalization. It Refuses, Or Caps With `--if-over-ceiling cap`, When The Gain Would Pass The True Peak Ceiling, And It Reports The Measured Loudness Of The Finished File. When A Single Loud Peak Blocks The Target, Lower That Cue Or Shot And Measure Again. Lossy Encoding Can Raise Peaks By A Few Tenths Of A dB, Which Is Why The Default Ceiling Is −1.5 dBTP.

## Caption Safe Areas On Vertical Platforms

Vertical Players Draw Their Own Interface Over The Video: An Account Name And Description Along The Bottom, A Column Of Buttons Down The Right Edge, And Tabs Or A Search Bar Across The Top. The Exact Sizes Differ By Platform And Change Without Notice. Start From A Conservative Box And Confirm On The Platform's Own Preview Before Posting.

| Edge Of A 1080 By 1920 Frame | Keep Clear | In Pixels |
| --- | --- | --- |
| Top | About 12 Percent | 230 |
| Bottom | About 25 Percent | 480 |
| Left | About 6 Percent | 65 |
| Right | About 15 Percent | 160 |

The Tool Defaults Follow This Table. Explicit Values Always Override Them.

| Default | Vertical Canvas | Horizontal Or Square Canvas |
| --- | --- | --- |
| `caption_style.size` | 6 Percent Of The Canvas Width, Which Is 65 At 1080 Wide | About 7.8 Percent Of The Canvas Height, Which Is 84 At 1080 High |
| `caption_style.margin`, For Bottom Captions | 25 | 7 |
| `caption_style.top_margin`, For Top Captions | 12 | 7 |
| Phrase Words, `--max-words` | 3 | 4 |
| Phrase Characters, `--max-chars` | 20 | 28 |

- `caption_style.margin` Is A Percentage Of The Canvas Height Between A `bottom` Caption And The Bottom Edge. `caption_style.top_margin` Is The Same Measure Between A `top` Caption And The Top Edge. A Timeline That Sets `margin` Alone Uses That Value At Both Edges, As Earlier Editions Did.
- Captions Are Centered With A Side Margin Of 5.5 Percent. A Long Line Reaches Under The Button Column, So Keep Lines Short With The Phrase Options. At The Default Vertical `size` Of 65, About 20 Characters Stay Inside The Middle 70 Percent Of A 1080 Wide Canvas, Which Is Why Vertical Phrases Default To 20 Characters. At A `size` Of 80, About 17 Characters Fit.
- Place A [Title Overlay](TITLES.md) With `--margin 230` Or More At The Top Of A Vertical Frame.
- Keep The Face, The Caption, And Any Title In Separate Bands. One Caption Per Position At A Time.
- Check With A Still At Delivery Size, Viewed At The Width Of A Phone. The Browser Editor Shows The Whole Frame Without Any Platform Interface.
- Give A Phrase Time To Be Read. Fifteen To Twenty Characters Per Second Is A Comfortable Upper Limit.

```sh
python scripts/edit_video.py still "First Cut/timeline.json" "First Cut/Caption Check.png" --at 0.5
```

## Checking A Correction Without Exporting

No Check Below Creates A Video, And None Of Them Is An Approval. The Owner Still Reviews The Saved Project In The Editor Before Any Export, Including A Test Or Preview Export.

| Question | Command | What It Proves |
| --- | --- | --- |
| Is The Project Valid? | `validate` | Fields, Ranges, And Sources Are Sound. Warnings Name HDR And Rotated Sources And Any Working Copy That Disagrees With Its Original. |
| Does The Whole Edit Compose? | `check` | Every Source Decodes Through The Final Graph Into A Null Sink And The Frame Count Matches. Add `--no-burn` To Leave Captions Out. |
| Does This Frame Look Right? | `still --at` | One Composed Frame As A PNG, With Tone Mapping, Color, Overlays, And Captions, Built From The Same Graph As The Render. |
| Are Levels Right? | `loudness` | Loudness, Peaks, And Cue Against Speech, Decoded Into A Null Sink. |
| What Is Actually Heard? | `mix`, Then `speech.py transcribe` | The Composed Sound As A WAV, And The Words A Recognizer Finds In It. |
| Does It Play Right? | `review` | The Owner's Own Check In The Editor. |

```sh
python scripts/edit_video.py mix "First Cut/timeline.json" "First Cut/Check 1 To 3.wav" --start 1 --seconds 2
python scripts/speech.py transcribe "First Cut/Check 1 To 3.wav" "First Cut/Check 1 To 3.json" --backend faster-whisper --model /path/to/model
```

- `still` Decodes Only The Shot Under The Playhead, So It Stays Quick Late In A Long Edit. Its Time Snaps To The Nearest Frame, And The Report Names The Frame And The Shot.
- `mix` Accepts `--layer voice` Or `--layer cues` To Isolate One Layer, And `--start` With `--seconds` For A Window. Word Times In A Window Transcript Count From The Window Start.
- Re-Transcribing Confirms That A Removed Line Is Gone, That A Restored Line Is Present, And That Captions Match The Words In Order. It Cannot Prove A Clipped Consonant, Because A Recognizer Completes Damaged Words. Use The `clamped_words` List From The Caption Mapper And The Owner's Ears For That.
- A Check Mix And A Still Are Inspection Files. Name Them So They Are Not Mistaken For Deliverables, And Do Not Post Them.
- After Verifying, Record The Check In [The Active Brief File](BRIEF.md). Editing The JSON Alone Verifies Nothing.
- On An Approved Master, `python scripts/delivery_check.py finished.mp4 --timeline edit.json` Decodes The File And Lists Silence, Black Frames, And Mismatches.

## What May Be Reused After A Picture-Only Change

A Picture-Only Change Leaves Every Shot's Timing And All Sound As They Were. Examples Are `zoom`, `pan_x`, `pan_y`, `fit`, The Color Multipliers, `tone_map`, An Overlay's Position Or Width, And A Caption's Text, Position, Or Style.

| Still Valid | Do Again |
| --- | --- |
| The Word Transcript. It Is In Source Time. | `validate` And `check`. |
| Caption Timing, Cue Timing, And Recorder Offsets. | A Still For Each Changed Shot. |
| Loudness Readings, Cue Levels, And Any Check Mix. | The OTIO Hand-Off Or The Resolve Build, If One Was Made. |
| A Camera Motion Plan. It Is Tied To Its Target File. | The Owner's Review Of The Changed Version. |

- A Timing Change Is Different. After Any Change To `in`, `out`, `lead`, `tail`, `speed`, Or The Shot Order, Keep The Transcript, But Map Captions Again, Retime Overlays And Cues, And Measure Loudness Again.
- A Replaced Source File Invalidates Its Transcript, Its Sync Offset, Its Analysis, And Any Motion Plan, Even When The Content Looks The Same.
- Approval Is Never Reused. It Covers The Version The Owner Reviewed. A Posting Packet Records The Fingerprint Of Its Media File, So A New Export Needs A New Packet.

## HDR Handling

Phones Record HLG, Often With A Dolby Vision 8.4 Layer, Or HDR10 With A PQ Transfer. Both Use BT.2020 Primaries At 10 Bits. Shown As Ordinary Video, Their Pixels Look Flat, Gray, And Desaturated.

- **Detection.** `probe` Sets `hdr` To `hlg` Or `pq` From The Transfer Tag. `validate` Warns For Each HDR Source In Use And Says Which Shots Are Converted.
- **Conversion.** Each HDR Shot Is Converted Exactly Once, After It Is Cropped And Scaled To The Canvas And Before `brightness`, `contrast`, And `saturation`. The Chain Goes To Linear Light, Maps BT.2020 Primaries To BT.709, Rolls Off Highlights, And Returns To 8-Bit BT.709 With Dither. An HDR Overlay Is Converted The Same Way.
- **Look.** The Conversion Anchors HDR Reference White, 203 Nits, High In The Standard Range And Keeps Midtones Close To Where They Were Recorded. An HLG Signal Of 50 Percent Becomes About 56 Percent, Reference White At 75 Percent Becomes About 85 Percent, And The Peak Stays At 100 Percent. Colors Regain Their Saturation, And A Standard Midtone Color Carried In HDR Returns To Its Original Value.
- **Peak.** HLG Is Treated As A 1000 Nit Signal. PQ Uses The Content Light Level When The File Carries One, Otherwise The Mastering Display Peak, Otherwise 1000 Nits, Kept Between 400 And 10000.
- **Turning It Off.** Set `tone_map` To `false` On The Canvas, On A Shot, Or On An Overlay. The Picture Then Passes Through Unconverted, And The Export May Carry HDR Tags. Use This Only When A Clip Is Mistagged Or When The Grade Will Be Done Elsewhere.
- **A Limited Build.** The Conversion Uses The `zscale` And `tonemap` Filters. Without One, `check`, `still`, And `render` Stop With A Message Naming It, And `setup` Lists It Under `ffmpeg-hdr`.
- **Preview.** Without A Working Copy The Browser Editor Plays The Original File, So It Shows The Browser's Own HDR Conversion, Which Differs From The Kit's, And Some Browsers Cannot Play HEVC At All. Judge Converted Color On A Still, Or Make A [Working Copy](#working-copies-for-review), Which Carries The Kit's Conversion Into The Browser Editor And Remotion. The FFmpeg Checks Always Work, And The Owner Can Also Review In Resolve Through The [Native Build](RESOLVE.md).
- **Master.** The FFmpeg `render` From The Original Files Produces The Master For HDR Footage. Remotion Is The Review Route There.
- **Outside The Composition Graph.** The Native Resolve Build Imports Original Files And Leaves Color To Resolve's Color Management. [Camera Transfer](CAMERA.md) Works In 8-Bit RGB And Does Not Tone Map, So An HDR Target Looks Flat There.
- **Not Converted.** Dolby Vision Profile 5 Has No Standard Base Layer, And A BT.2020 Clip Without A PQ Or HLG Transfer Is Treated As Standard Video. Both Draw A Warning. Use A Version Recorded Or Converted As HLG, HDR10, Or Standard Video.

## Working Copies For Review

A Working Copy Is A Converted Copy Of One Untouched Source Clip, Made So The Browser Editor And Remotion Can Play Footage They Cannot Decode. It Is Not A Cut And Not An Export Of The Edit. It Is Still A Video File, So The Command Writes It Only With `--owner-agreed-working-copy`, After The Owner Has Agreed To A Working Copy Of That Source. Ask Once, In Plain Words, And Name The Clips The Answer Covers.

```sh
python scripts/edit_video.py working-copy "Footage/Phone Clip.mov" "Footage/Phone Clip Working Copy.mp4" --plan
python scripts/edit_video.py working-copy "Footage/Phone Clip.mov" "Footage/Phone Clip Working Copy.mp4" --check --seconds 5
python scripts/edit_video.py working-copy "Footage/Phone Clip.mov" "Footage/Phone Clip Working Copy.mp4" --owner-agreed-working-copy
python scripts/working_copy.py "Footage/Phone Clip.mov" "Footage/Phone Clip Working Copy.mp4" --owner-agreed-working-copy --long-side 1280
```

| Option | Effect |
| --- | --- |
| `--owner-agreed-working-copy` | Write The Working Copy. Use It Only After The Owner Agrees. It Does Not Approve Any Export Of An Edit, And `--owner-approved` Is Not Accepted Here. |
| `--plan` | Print The Planned FFmpeg Command And The Filter Chain. Nothing Is Run And Nothing Is Written. |
| `--check` | Run The Picture Conversion Into A Null Sink To Prove This FFmpeg Build Can Do It. Nothing Is Written. Add `--seconds` To Check Only The Start. |
| `--long-side 1920` | The Longest Side Of The Working Copy In Pixels. The Picture Is Never Enlarged. A 2160 By 3840 Phone Clip Becomes 1080 By 1920. |

- **Picture.** H.264 In An MP4 File, 8-Bit 4:2:0, Stored Upright At The Displayed Shape. An HDR Source Gets The Same Single Conversion That `check`, `still`, And `render` Apply, In The Same Order: Scale First, Then Convert. A Standard Source Is Only Scaled And Encoded Again.
- **Timing.** Every Source Frame Keeps Its Own Timestamp. No Frame Is Dropped, Repeated, Or Retimed, So The Copy Has The Duration And Frame Count Of The Original. The Command Probes The Result And Refuses To Publish It When Either Disagrees.
- **Sound.** AAC Sound Is Copied Bit For Bit. Any Other Codec Is Encoded As AAC With No Filter, So Level, Channels, And Sample Rate Stay As Recorded.
- **Files.** The Original Is Only Read. The Output Must Be A New MP4 Name. An Existing File Is Never Replaced, And The Original Cannot Be Named As The Output.

Name The Copy In The Timeline And Keep `path` On The Original.

```json
{"assets": {"Phone": {"path": "Footage/Phone Clip.mov", "kind": "video", "working_copy": "Footage/Phone Clip Working Copy.mp4"}}}
```

| Command | Reads |
| --- | --- |
| `review`, `remotion` | The Working Copy |
| `validate`, `check`, `still`, `loudness`, `mix`, `render`, `handoff`, `resolve` | The Original |

- `validate` Names Each Video In Use That A Browser Is Unlikely To Play And That Has No Working Copy Yet, And Notes Each Asset That Plays From One. It Warns When The Copy's Duration Or Frame Count Disagrees With Its Original, When Its Shape Differs, When It Is Itself HDR Or Rotated, And When A Browser Is Unlikely To Play It.
- Framing Still Comes From The Original's Displayed Size, So `zoom`, `pan_x`, And `pan_y` Mean The Same In Review And In The Render.
- The Working Copy Shows The Kit's Color. Fine Detail Is Softer Than The Master, Because The Copy Is Smaller And Encoded A Second Time. Judge Sharpness On A `still`, Which Reads The Original.
- **The Master Comes From The Original.** For An HDR Source, Or Any Timeline With Working Copies, The FFmpeg `render` With `--owner-approved` Produces The Master. Remotion Is For Review There, Because A Remotion Render Would Be Made From The Smaller Copies.
- The Kit's Tests Inspect The Command And The Graph, And Run The Picture Chain On Generated HDR Patterns Into A Null Sink. They Do Not Convert A File. Compare One `still` With The Same Moment In The Working Copy Before Relying On Its Color.

## FFmpeg And Shell Pitfalls

**Every Shell**

- Quote Any Path Or Text That Contains A Space. The Example Paths In These Guides Do.
- The Media, Still, Mix, And Sidecar Commands Never Overwrite A File. `Output Already Exists` Means Choose A New, Versioned Filename.
- `review` Holds The Terminal Until Ctrl+C. Add `--no-open` To Print The Local Address Without Opening A Browser.
- Negative Option Values Such As `--loudness-target -14` And `--silence-db -40` Are Typed As Shown.
- In Timeline JSON, Write Paths With Forward Slashes, Relative To The Timeline File. A Backslash Must Be Doubled Inside JSON.
- The Kit Reads And Writes UTF-8. The `setup` And `defaults` Commands Print ASCII-Safe JSON, So Parse The JSON To Recover Accented Characters.
- The Shell An Agent Runs May Have A Different PATH From The User's Terminal. `setup` Prints The Exact FFmpeg And Python It Found.
- Files Kept Online-Only By A Cloud Drive Probe Slowly Or Fail. Make Sources Available Offline Before Editing.

**Windows**

- In PowerShell, A Quoted Program Path Needs The Call Operator `&` In Front, As [The Resolve Guide](RESOLVE.md) Shows. Windows PowerShell 5.1 Has No `&&`. Run Commands One At A Time.
- The Python Launcher May Be `python` Or `py`. `setup` Prints The Path Of The Python That Ran It, And Its Install Commands Use That Same Python.
- A Colon In A Windows Path Breaks FFmpeg Filter Arguments, Because A Colon Separates Filter Options. The Kit Avoids This By Running FFmpeg Inside A Temporary Folder And Naming The Caption File Relatively. Do The Same In Any FFmpeg Command You Write By Hand.
- Keep Project Folders Shallow. Very Long Paths Can Exceed The System Limit.
- A Scanner Or A Sync Client Can Briefly Lock A New File. If A Command Fails While Cleaning Its Temporary Folder, Run It Again.
- Named Time Zones For Scheduling Need The Time Zone Package That `setup` Lists Under `time-zones`.

**macOS And Linux**

- The Launcher Is Usually `python3`.
- In `zsh` And `bash`, Text In Double Quotes Still Expands A Dollar Sign, And An Interactive `zsh` Also Expands An Exclamation Mark. Put Text Such As A Price Or An Exclaimed Title In Single Quotes.
- An Unquoted Hash Starts A Comment. Quote Hex Colors, As [The Title Guide](TITLES.md) Does.
- Square Brackets, Asterisks, And Question Marks Are Filename Patterns When Unquoted.
- Caption Fonts Must Be Installed. Where Arial Is Missing, The Renderer Substitutes Another Face And Line Breaks Shift. Check A Still.
- A System Python May Refuse Package Installs. Use A Virtual Environment For The Optional Packages `setup` Lists.

## Saved Defaults Location

The Defaults File Is `~/.social-cut-kit/video-edit.md`. Set The Environment Variable `SOCIAL_CUT_KIT_HOME` To Keep It In Another Folder, For Example In A Sandbox Without A Home Directory. `defaults --init` Creates The File With Empty Headings And Never Replaces An Existing File. `defaults --add "Text" --section "Caption Style"` Records One Dated Line Under A Heading.

```sh
python scripts/edit_video.py defaults --init
python scripts/edit_video.py defaults --add "Yellow Highlight On The Keyword." --section "Caption Style"
```
