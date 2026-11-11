# Remotion Review And Render

Turn A Timeline Into A Standalone Remotion Project. The Owner Reviews The Whole Cut In Remotion Studio, And An Approval-Gated Command Renders The MP4. This Is The Default Route For Review And Delivery. The [FFmpeg Render](../SKILL.md#render-with-ffmpeg-without-node-packages) Stays Available And Needs No Node Packages.

Preparation Writes Project Files And Media Copies. It Never Writes A Video. Build And Verify The Edit First With The Browser Editor And The Non-Exporting Checks `validate`, `check`, `still`, `loudness`, And `mix`. Those Checks Describe The FFmpeg Route, So Read [What Differs From The FFmpeg Route](#what-differs-from-the-ffmpeg-route) Before Relying On Them For A Remotion Render.

## Prepare A Project

Run These From The Video Edit Skill Folder. Pass The Timeline And A New Folder. The Folder Must Not Exist.

```sh
python scripts/edit_video.py remotion "First Cut/timeline.json" "First Cut Remotion"
node remotion/prepare-remotion.cjs "First Cut/timeline.json" "First Cut Remotion"
```

Both Commands Build The Same Project. The Python Command Validates The Timeline With The Editor's Own Rules First And Prints A JSON Summary. The Node Command Prints One Line Per Warning And A Status Line, Or The Same Summary With `--json`. Both Need Node.js And FFprobe On Your PATH.

| Option | Effect |
| --- | --- |
| `--allow-hdr` | Prepare A Timeline That Uses HDR Sources. Without It, Preparation Stops. See [HDR Sources](#hdr-sources). |
| `--link-media` | Hard Link Each Source File Into The Project Instead Of Copying It, Where The Disk Allows. A Linked File Is The Original File, So Never Edit It In Place. |

Read Every Warning. Each One Names Something In This Timeline That Remotion Reproduces Differently From The FFmpeg Route. The Warnings Are Also Saved In `src/cut.json` And Printed Again Before The Render Asks For Approval.

## What The Project Contains

| File | Purpose |
| --- | --- |
| `src/cut.json` | The Cut In Whole Output Frames And Canvas Pixels: Canvas Size, Frame Rate, Total Frames, Shots, Overlays, Audio Cues, Captions, Caption Style, And Warnings. |
| `src/cut-plan.cjs` | The Timing And Layout Rules. It Imports Nothing And Is The Same File The Kit Tests In Node. |
| `src/index.jsx` | The Remotion Composition **VideoEdit**. It Only Places What `cut.json` Describes. |
| `public/media/` | A Copy Of Every Source File The Timeline Names, So The Project Opens Without The Original Folders. |
| `source-timeline.json` | A Copy Of The Timeline Whose Asset Paths Point At `public/media/`. The Kit's `validate`, `review`, And `still` Open It From The Project Folder. |
| `render-reviewed.cjs` | The Approval-Gated Render. |
| `package.json` | The Pinned Remotion And React Versions, `npm run studio`, And `npm run render-reviewed`. |

| Timeline Element | Remotion Representation |
| --- | --- |
| Canvas | Composition Width, Height, Frame Rate, And Duration In Frames |
| Shots | Source In And Out With Lead And Tail Handles, Speed, Gain, Sound Fades, Fit, Zoom, Pan, Brightness, Contrast, And Saturation |
| Overlays | Position, Width, Even Height, Timing, Source In, And Stacking Order. Later Overlays Sit Above Earlier Ones. Overlay Sound Is Muted. |
| Audio Cues | Start, Length, Source Offset, Gain, And Fades |
| Captions | Text, Timing, Position, Font, Size, Colors, Outline Width, And Margins |

Frame Snapping Uses The Editor's Rule, So Every Cut, Cue, And Caption Starts On The Same Output Frame In Both Routes. Shot Framing Uses The Same Crop, Scale, And Pad Numbers As The FFmpeg Graph.

## Review In Remotion Studio

Each Generated Project Needs Node.js And Its Own `npm install`. The Install Downloads The Declared Packages, So It Needs Network Access Or A Complete Local Package Cache. Remotion Has Its Own License Terms, Including Paid Company Licenses For Larger Teams. Check The Current Terms On Remotion's Website Before Using It In Your Business.

```sh
cd "First Cut Remotion"
npm install
npm run studio
```

Open **VideoEdit**. The Owner Personally Watches The Entire Cut With Sound And Steps Through Each Cut Point Before Any Video Export, Including Test And Preview Exports. An Agent Reading Stills Or Running Checks Does Not Grant Approval.

Remotion Studio Has Its Own Render Button, And Remotion Has Its Own `render` Command. Neither Asks For Approval. Do Not Use Them. Use Only The Gated Command Below.

## Make Changes

Change The Timeline, Not The Generated Project. Edit The Original Timeline, Or Open `source-timeline.json` From The Project Folder In The Kit's Browser Editor. Run The Checks Again, Prepare A Fresh Project In A New Folder, And Have The Owner Review It Again. An Earlier Approval Does Not Carry Over To A Changed Cut.

For Direct Composition Work, `src/cut.json` Holds Every Number And `src/index.jsx` Holds The React Layout. A Hand Edit There Is Not Checked By The Kit And Is Lost When The Project Is Prepared Again.

## Render After Approval

After The Owner Approves The Current Cut, The Owner Runs The Gated Render In An Interactive Terminal. It Prints The Project's Warnings, Asks The Owner To Type APPROVE, And Writes An MP4 To A New File. It Refuses To Run Without A Terminal, Refuses A Name That Is Not MP4, And Refuses To Replace An Existing File.

```sh
npm run render-reviewed -- "Approved Cut.mp4"
```

The Render Uses Remotion's Default H.264 And AAC Settings. It Does Not Run The Editor's Export Verification, So Check The Result From The Video Edit Skill Folder.

```sh
python scripts/edit_video.py probe "First Cut Remotion/Approved Cut.mp4"
python scripts/delivery_check.py "First Cut Remotion/Approved Cut.mp4" --timeline "First Cut/timeline.json"
```

## What Differs From The FFmpeg Route

The Kit Compared Remotion Stills With `still` Frames From The Same Timelines On One Windows Computer With Chrome. It Did Not Render A Video, So **Sound In The Remotion Route Is Unverified**. Every Statement About Sound Below Comes From Reading Remotion 4.0.535, Not From Listening.

### HDR Sources

Preparation Refuses A Timeline Whose Shots Or Overlays Use A PQ Or HLG Source, Or Dolby Vision Profile 5, And Points To The FFmpeg Render. The FFmpeg Route Converts HDR To Standard Dynamic Range Once, With One Known Curve, And `still` Shows That Exact Result. Remotion Does Not Use That Conversion.

With `--allow-hdr` The Project Is Prepared With A Warning. The Render Then Uses Remotion's Own Tone Mapping For Video Frames, Or Passes The Picture Through Unconverted Where The Timeline Sets `tone_map` To `false`. Remotion Studio Shows Whatever Conversion The Browser Applies. Neither Matches The Kit's Stills, And The Kit Has Not Verified Either. Use `--allow-hdr` To Review Timing And Framing, And Deliver HDR Edits Through The FFmpeg Render.

### Speed Changes And Pitch

The Project Passes Each Shot's Speed To Remotion As A Playback Rate On A Muted Video Element For The Picture And On A Separate Audio Element For The Sound.

- **Sound.** The Render Retimes Sound With Remotion's FFmpeg Tempo Filter, Which Keeps The Pitch. Remotion Studio Plays Through The Browser, Which Also Keeps The Pitch. The FFmpeg Route Keeps The Pitch Too, With Its Own Filter Chain, So A Retimed Shot Can Sound Slightly Different In Each. Preparation Warns About Every Retimed Shot That Plays Sound. Keep Dialogue At Its Original Speed.
- **Picture.** Each Output Frame Shows The Source Frame Nearest Its Retimed Time, As The FFmpeg Route Does. At Speed 1, 0.5, And 1.5 The Measured Frames Matched Exactly. At Speed 2 The Two Routes Chose Neighboring Source Frames On Some Output Frames, Because A Source Frame Falls Exactly Between Two Output Frames. Preparation Warns About Every Retimed Video Shot.
- **First Frame.** When An In Point Falls Exactly Halfway Between Two Source Frames, The First Output Frame Of That Shot Can Show The Neighboring Source Frame. Later Frames Matched.
- **Mixed Frame Rates.** A 24 FPS Source On A 30 FPS Canvas Matched On Every Frame Sampled. Preparation Still Warns, Because Other Rate Pairs Can Round Differently.

### Sound Levels And Fades

- Shot And Cue Gain Above 1 Is Applied In The Render. Remotion Studio Plays Media No Louder Than Its Recorded Level, So The Boost Is Not Heard During Review.
- Fades Are Straight Lines, As In The FFmpeg Route, But Remotion Changes Level Once Per Frame. A Fade Shorter Than Two Frames Becomes A Single Step. The FFmpeg Route Fades Sample By Sample, So Use It When A Few Milliseconds Must Remove A Click.
- When A Shot's Length Rounds Up To A Whole Frame, The FFmpeg Route Fills The Last Fraction With Silence. Remotion Plays Source Sound Past The Out Point For Up To Half A Frame.
- The Loudness Options Of The FFmpeg Render, `--loudness-target`, `--true-peak-ceiling`, And `--if-over-ceiling`, Have No Remotion Equivalent. The Remotion Render Exports The Sound As Mixed. `loudness` And `mix` Measure The FFmpeg Mix, Not Remotion's.
- Sources With More Than Two Audio Channels Are Mixed To Stereo By Remotion's Rules, Which May Differ.

### Caption Fonts

Captions Are HTML Text Drawn By Chrome With The Fonts Installed On The Computer That Runs Studio Or The Render. The Project Bundles No Font Files. The Five Supported Fonts Are Arial, Georgia, Verdana, Tahoma, And Trebuchet MS. When One Is Missing, Chrome Falls Back To Another Font Without A Message, So Review And Render On A Computer That Has The Font.

The Text Height Is Scaled So The Caption Size Means The Same As In The FFmpeg Route. With All Five Fonts Installed, Caption Edges Landed Within 3 Pixels Of The FFmpeg Stills On A 1080 By 1920 Canvas, With The Same Line Breaks In The Cases Tried. Long Captions Can Still Break At A Different Word, And Outline Corners Are Drawn Slightly Differently. Captions Are Always Drawn. There Is No Equivalent Of `--no-burn`, So Deliver Separate Captions Through The FFmpeg Render Or Prepare From A Timeline Without Them.

### Media Formats

Remotion Studio Plays Media With The Browser's Decoders. The Render Decodes Video Frames With Remotion's Own FFmpeg And Is Not Limited To Browser Formats, But It Draws Images Through Chrome.

| Media | Works In Studio And Render | Needs Care |
| --- | --- | --- |
| Video | H.264, VP8, VP9, Or AV1 In MP4, MOV, Or WebM | HEVC Plays In Studio Only With Hardware Support. ProRes, DNxHR, And Other Editing Formats Show No Picture In Studio. |
| Audio | WAV, MP3, AAC, Opus, Or FLAC | AIFF And Other Formats May Be Silent In Studio. |
| Images | PNG, JPEG, WebP, GIF, Or BMP | TIFF, HEIC, PSD, And Other Formats Fail In Studio And In The Render. Convert Them To PNG Or JPEG. |

Preparation Warns About Each Source Outside The Middle Column. The Kit Verified Only H.264 MP4 Video, PNG Images, And WAV Audio In Remotion. For A Format That Studio Cannot Play, Review With The Kit's Browser Editor And Stills, Or Deliver Through The FFmpeg Render.

### Picture

- **Chroma.** The FFmpeg Route Composes In 4:2:0 Color. Remotion Composes In Full-Resolution RGB. A Remotion Still Of An Unscaled Image Was Identical To Its Source, And Identical To The FFmpeg Still Once Given The Same 4:2:0 Conversion.
- **Scaling.** The FFmpeg Route Scales With A Bicubic Filter And Chrome Uses Its Own. Fine Detail And Hard Edges Differ Slightly, Most Of All When Small Art Is Enlarged Many Times.
- **Color Adjustments.** Brightness, Contrast, And Saturation Use CSS Filters In The Same Order And With The Same Weights As The FFmpeg Graph.
- **Rotated Phone Clips.** The Layout Uses The Displayed, Upright Size. The Kit Has Not Verified That Remotion Turns A Rotated Clip Upright, So Preparation Warns, And The Owner Should Check Framing In Studio.

### Disk Space And Speed

Preparation Copies Every Source File Into The Project. Use `--link-media` To Avoid A Second Copy On The Same Disk. Remotion Also Copies The Project's `public` Folder Each Time It Bundles A Render, So Allow Space For Large Footage.

## Measured Still Comparison

These Figures Compare `npx remotion still` With `edit_video.py still` At The Same Frames. PSNR Is The Average Over Red, Green, And Blue.

| Timeline | Frames | PSNR | Reason For The Gap |
| --- | --- | --- | --- |
| Repair Desk Example, No Caption On Screen | 2, 89, 90, 239 | 38.1 To 39.2 dB | 4:2:0 Color In The FFmpeg Route. Identical After Matching The Color Conversion. |
| Repair Desk Example, Caption On Screen | 10, 45, 150, 200 | 25.4 To 27.0 dB | Caption Edges Within 3 Pixels |
| Generated Example Folder, Images, Overlay, And Captions | Nine Frames From 0 To 95 | 28.3 To 36.4 dB | Small Art Enlarged 6.4 Times With Different Scaling Filters, Plus Captions |
| H.264 Video Shots At Speed 1 And 0.5, Cover And Contain, 30 And 24 FPS Sources | Eight Frames | 46.5 To 57.4 dB | Scaling And 4:2:0 Color. One More Frame Was Identical. |
| H.264 Video Shots With Zoom, Pan, Speed, And Color Adjustments | Seven Frames | 37.2 To 42.4 dB | Scaling And Filter Rounding |
| H.264 Video Under A Caption And Two Overlays | 10, 20 | 28.2 dB | Caption Edges |
| First Frame Of A Shot At 2× Speed, And Of A Shot With A Halfway In Point | 45, 200 | 23.5 To 24.2 dB | A Neighboring Source Frame, As Described Above |

A Separate Check Matched Each Still To Its Source Frame For Six Shots Cut From One 30 FPS Clip. Both Routes Showed The Same Source Frame On Every Frame Sampled At Speed 1, 0.5, And 1.5, With In Points On And Between Source Frames. At Speed 2 They Differed By One Source Frame On Three Of Four Frames Sampled.

## Verification

```sh
node --test tests/test_remotion_plan.cjs tests/test_remotion_project.cjs
python -B -m unittest tests.test_remotion -v
```

The Node Tests Check Frame Snapping, Framing, Fades, Caption Layout, Warnings, And Project Generation Without Remotion Installed. The Python Test Compares A Generated Project With The Editor's Own Timeline Model. None Of Them Installs A Package Or Writes A Video.
