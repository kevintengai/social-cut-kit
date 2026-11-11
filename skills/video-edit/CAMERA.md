# Transfer Camera Motion Between Clips

Measure A Reference Shot's Pan, Zoom, And Rotation, Then Apply That Movement To A Different Clip. The Second Clip Supplies The Picture, Audio, Framing Dimensions, And Duration. Review The Motion On The Original Target File Before Approving Any Video Export.

## Measure A Reference

Run These Commands From The Video Editing Skill Folder. Install FFmpeg And FFprobe On Your PATH. The Camera Tracker Also Uses NumPy And OpenCV.

```sh
python -m pip install numpy opencv-python-headless
python scripts/camera_transfer.py analyze reference.mp4 target.mp4 motion.json
python scripts/camera_transfer.py review motion.json
```

Open `motion.review.html` In A Browser And Choose The Original Target File. Play Or Scrub To Check The Result With The Target Audio. Toggle The Original Picture To Compare The Same Moment. The Browser Must Support The Target's Original Video And Audio Codecs. H.264 And AAC In An MP4 Are A Practical Choice For Browser Review.

Change Strength, Horizontal Anchor, Vertical Anchor, Timing, Or Edge Handling In The Review Page. Save The Adjusted Plan As JSON. Review Those Exact Settings Before Export. The Player Reads Your Files Locally. Its Save Control Writes An Editable Motion Plan.

## Adjust The Motion

| Option | Effect |
| --- | --- |
| `--strength 0.65` | Apply 65% Of The Displacement, Rotation, And Logarithmic Zoom. Zero Restores The Original Framing. The Range Is Zero Through Three. |
| `--anchor-x 0.35 --anchor-y 0.4` | Place The Zoom And Rotation Pivot At 35% Of The Width And 40% Of The Height. The Default Is The Center. |
| `--edge-mode cover` | Increase Magnification As Needed On Each Frame To Keep All Four Output Corners Within The Source. |
| `--edge-mode reflect` | Retain The Measured Zoom And Fill Exposed Edges With Mirrored Picture Content. |
| `--timing stretch` | Fit The Entire Reference Movement To The Target Duration. This Is The Default. |
| `--timing hold` | Play The Measured Movement At Its Original Speed. Hold The Last Pose When The Reference Ends First. |
| `--fps 30` | Set The Constant Output Frame Rate. The Default Uses The Target's Average Frame Rate. |
| `--analysis-size 960` | Raise The Longest Analysis Dimension From The Default Of 720 Pixels For A More Detailed Reference. Rendering Uses The Target's Full Display Dimensions. |

The JSON Plan Stores One Sample Per Decoded Reference Frame At Its Presentation Time In Seconds. Each Sample Contains Horizontal And Vertical Displacement As Fractions Of The Frame Span, A Zoom Multiplier, A Clockwise Angle In Degrees, And A Confidence Score From Zero Through One. You Can Edit These Values Or Remove Intermediate Samples In A Text Editor. Keep The First Timestamp At Zero And The Remaining Timestamps In Ascending Order. The Renderer Interpolates Position And Rotation Linearly And Zoom On A Logarithmic Scale.

The Tracker Samples Features Across The Image And Rejects Inconsistent Matches. The `tracked` Status Identifies A Supported Pan, Zoom, And Rotation Estimate. The `translation` Status Identifies A Pan Recovered From Image Correlation. The `held` Status Marks An Unreliable Transition, Including Blank Frames And Some Cuts. The Previous Pose Stays In Place Across That Transition, And Tracking Resumes On The Next Supported Pair. A Moving Subject That Fills Most Of The Reference Can Dominate The Estimate. Review Such Sections Or Select A Reference With More Visible Background.

## Check And Deliver A Reviewed Plan

```sh
python scripts/camera_transfer.py check adjusted.json
```

The Check Applies The Actual Transforms And Prints A SHA-256 Digest For Each Decoded Output Stream. It Creates No Video File. If You Move The Target Clip, Supply Its New Location With `--source`. The CLI Verifies Its Content Hash Against The Plan. To Create A Fresh Review Page, Supply A New Filename With `review adjusted.json --output adjusted.review.html`.

Only After The Owner Has Personally Reviewed This Edit And Explicitly Approved Its Export, Choose One Delivery Format And A New Output Filename.

```sh
python scripts/camera_transfer.py render adjusted.json final.mp4 --owner-approved
python scripts/camera_transfer.py render adjusted.json final.mov --owner-approved
```

MP4 Uses H.264. MOV Uses ProRes 422 HQ. Both Use The Same Subpixel Transform And Map All Original Target Audio Streams. Compatible Compressed Audio Is Copied. Other Audio Is Encoded As AAC For MP4 Or PCM For MOV. Output Frames Follow The Chosen Rate. When The Target Ends Between Frame Boundaries, The Last Packet Uses The Remaining Duration. Frames Use An Eight-Bit RGB Processing Path, Including When The Delivery Codec Uses A Ten-Bit Pixel Format. An HDR Target Is Not Tone Mapped In This Path And Looks Flat. See [HDR Handling](TECHNICAL.md#hdr-handling).
