# Hand-Made 2D

The Viewer Should Feel That A Person Drew Each Frame With A Real Tool On A Real Surface. Choose This Look In [Style Frames](../STYLE-FRAMES.md). The Drawing Helpers Are Described In [Code Scenes](../CODE-SCENES.md). This Guide Says What To Draw With Them.

## What Makes It Read As Hand-Made

- **A Line That Varies.** Width Swells And Tapers, Corners Overshoot, And Shapes Do Not Quite Close.
- **A Material.** Pigment Sits Inside Shapes And Paper Shows Around Them. Fills Miss Their Outlines By A Little.
- **Stepped Movement.** Drawings Hold For Two Or Three Frames. Motion Advances In Poses, Not In A Glide.
- **One Tool.** The Whole Film Looks Drawn With The Same Pencil, Pen, Brush, Or Marker.

## Line

- Draw A Stroke As A Filled Ribbon Along A Path, Not As A Constant-Width Stroke. Let The Width Swell Through The Middle And Taper At Both Ends.
- Displace The Path With Seeded Noise So It Wanders Slightly. A Displacement Of A Pixel Or Two On A 1080-Wide Frame Is Enough.
- Give Each Tool Its Own Behavior. Pencil Is Thin, Grainy, And Built From A Few Light Passes. Ink Is Solid With Sharp Tapers. Marker Is Wide And Flat, And Darkens Where Strokes Overlap. Chalk Breaks Up Against The Grain Of The Surface.
- Leave Small Gaps And Overshoots Where Lines Meet. Perfect Joins Are The First Sign Of A Machine.
- Use A Dark Brown, Blue, Or Gray For Line In Place Of Pure Black.

## Boil And Frame Rate

- Work At 24 FPS Where The Delivery Allows. Hold Each Drawing For Two Frames For Most Action, Three For Slow Or Quiet Passages, And One For Fast Action.
- Step Time Itself. Compute Pose And Position From Time Rounded Down To The Held Drawing, So Nothing Slides Between Drawings.
- Boil By Changing The Noise Seed Once Per Held Drawing. A New Seed On Every Frame Buzzes. A Seed That Never Changes Looks Like Vector Art.
- Derive Every Seed From The Element And The Drawing Number. Two Renders Of One Frame Must Match Exactly. Randomness Without A Seed Shows Up As Flicker In [Review](../REVIEW.md).
- Keep Everything In A Shot On The Same Step. A Smooth Camera Over Stepped Drawings Makes The Drawings Appear To Slide.

## Fill And Texture

- Offset Fills From Their Lines By A Few Pixels And Roughen Their Edges. Let The Paper Show At The Rim.
- Vary The Tone Inside A Fill With Low-Contrast Noise, Or Build The Fill From Visible Hatching Or Brush Passes In One Direction.
- Put Paper Grain Under Everything, Multiplied, And Fixed To The Frame. It May Hold Still Or Change With The Boil. It Does Not Travel With Objects.
- Put Pigment Texture Inside Each Fill So It Travels With Its Object.
- Generate Textures From Seeded Noise At Two Scales, With Short Random Strokes For Fibers. Scans Are Fine When The Owner Has The Right To Use Them.
- One Texture Laid Over The Finished Frame Reads As A Filter. Texture Belongs To The Layer It Describes.

## Type

- Letter By Hand Where The Film Can Afford It, Using The Same Line Rules As The Drawings. Otherwise Use An Installed, Licensed Face With A Written Character And Rough It Slightly With A Small Rotation And Baseline Shift Per Letter.
- Let Titles Boil With The Drawings. Keep Reading Text Still. A Sentence That Wobbles While It Is Being Read Is Not Read.
- Hold Every Line Long Enough To Read At Phone Size.

## Color And Light

- Use A Small Palette. Four To Six Colors, An Off-White Paper, And The Line Color. Keep The Color Meanings Set In [Directing](../DIRECTING.md).
- Let Overlapping Colors Multiply, As Paint And Marker Do.
- Draw The Light. There Is No Computed Lighting In This Style. Add One Darker Tone On The Shadow Side Of A Form And Let Bare Paper Stand For The Highlight.
- Draw Cast Shadows As Simple Multiplied Shapes. Keep The Light On The Same Side Through The Whole Film.

## Camera

- Think Of A Camera Looking Down At Artwork On A Table. Pan, Push In Slowly, And Cut.
- Build Depth From A Few Flat Layers That Slide At Different Rates, From Overlap, From Scale, And From Paler Tones In The Distance.
- Avoid Orbits And Perspective Fly-Throughs. They Belong To Another Style.
- Make Transitions Drawn Events. Use A Wipe By Brush Stroke, A Page Turn, A Match Cut On A Shape, Or A Morph Through Two Or Three Smeared Drawings.

## Motion

- With Fewer Drawings, Poses Do The Work. Design Strong Key Poses, Hold Them, And Move Between Them In Two To Four Drawings.
- Show Speed With A Smear Or A Stretched Drawing In Place Of Many In-Betweens.
- Let Forms Overshoot And Settle In The Drawing Itself. Smooth Easing Curves On Stepped Drawings Look Mechanical.

## The Quality Bar

- Any Paused Frame Looks Like A Drawing One Person Could Have Made With One Tool.
- No Circle Is Perfect And No Line Is Ruled, Unless The Story Asks For It.
- Texture Stays Attached To What It Describes.
- The Boil Is Felt And Not Noticed.
- Text Holds Still And Reads At Phone Size.
- Two Renders Of The Same Frame Are Identical.

## Typical Failures

| Failure | Fix |
| --- | --- |
| Clean Vector Shapes With A Wobble Applied | Vary The Width, Taper The Ends, And Offset The Fills. |
| Buzzing Lines | Boil Once Per Held Drawing And Reduce The Displacement. |
| Texture Sitting On Top Like A Filter | Move Grain Under The Artwork And Pigment Into The Fills. |
| Drawings That Slide | Step Time. Remove Smooth Interpolation Between Held Drawings. |
| Too Clean | Replace Pure White And Pure Black, And Break Symmetry. |
| Several Tools Fighting | Choose One Or Two Tools For The Film And Record Them In The Style Sheet. |
| Detail Carrying The Look | Simplify The Shapes. Line And Texture Carry This Style. |
| Flicker Between Renders | Seed Every Random Value. |
