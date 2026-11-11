# Pulse Dial Product Scene

Open **Pulse Dial.blend** In Blender And Press Space In The 3D Viewport. A Monitor Key Depresses, An Aluminum Dial Sweeps To Its Peak, And A Segmented Light Ring Follows The Level. The Camera Moves Around The Housing As The Indicator Settles. The Supplied Five-Second Edit Uses A 1080 × 1350 Portrait Canvas At 30 FPS.

## Edit The Scene

- Select **Dial Pivot** In **02 | Rotary Assembly** To Adjust Its Rotation Keys In The Dope Sheet. Its Crown, Pointer, And Grip Flutes Follow The Pivot.
- Select **Monitor Key Travel** For The Press And Release. Jump Between The Four Timeline Markers To Inspect The Action Beats.
- Expand **03 | Segmented Indicator** To Adjust A Cell. Its Principled Material Has Keyframes On Emission Strength. Match Those Keys To The Dial If You Change The Sweep.
- Select **Travelling Product Camera** To Adjust Its Location Keys Or Focal Length. Move **Camera Focus** To Change The Aim And Depth-Of-Field Target.
- In The Material Editor, Change The Housing Finish, Dial Metal, Rubber, Printed Legends, Or Light Color. The Procedural Grain Uses Built-In Noise And Bump Nodes. Use Material Preview To Inspect Surface Finishes. Press Numpad 0 To Toggle The Camera View.

## Build A Variation

Use A Separately Installed Blender. The Included Project And Builder Were Verified In Blender 5.2.2 LTS. All Geometry, Materials, Lighting, Animation, And Lettering Are Built Locally. A Variation Belongs In The User's Project, Never Inside The Skill Folder. Make A Folder There, Copy `direction.json` Into It, And Edit The Copy. Run The Commands From The User's Project Folder In A Fresh Background Process. `$SKILL` Stands For The Path To The Animated Video Skill Folder, As In The [Skill Guide](../SKILL.md). If Blender Is Outside Your PATH, Use Its Full Executable Path. The Builder Does Not Check Where It Writes, So Check The Output Path Yourself.

```sh
blender --background --factory-startup --python-exit-code 1 --python "$SKILL/blender/build_scene.py" -- --config my-dial/direction.json --output "my-dial/My Pulse Dial.blend"
blender --background "my-dial/My Pulse Dial.blend" --python-exit-code 1 --python "$SKILL/blender/verify_scene.py"
```

The Builder Requires A New Output Filename. The Verifier Opens The Project, Samples The Four Story Markers, Checks Product Framing, And Reports Dial Angles, Key Travel, Illuminated Cells, Camera Positions, And Scene Counts. Both Commands Leave An Editable Scene For In-Editor Review.

Edit Your Copy Of `direction.json` Before Building A Variation.

| Setting | Effect |
| --- | --- |
| `body_color`, `dial_color`, `accent_color` | Six-Digit Hex Colors For The Housing, Knob, And Luminous Index. |
| `initial_level`, `peak_level`, `final_level` | Values From 0 To 1. Start At Or Below The Final Level And Keep The Peak At Or Above The Final Level. |
| `width`, `height` | Canvas Dimensions From 64 To 4096 Pixels. The Builder Adjusts Camera Distance To Fit The Canvas. |
| `fps`, `seconds` | A Whole-Number Rate From 12 To 60 FPS And A Duration From 2 To 30 Seconds. |
| `camera_travel` | Position Travel From 0 To 1.5. Set It To Zero For A Fixed Camera Position With The Existing Lens Move. |

Save Your Edits In Blender And Have The Project Owner Review The Scene Before Any Video Export.
