# Luminous Dark 3D

A Dark Stage Where Light Is The Subject. Glowing Lines, Points, And Thin Surfaces Sit In Deep Space, Seen By A Slow Camera. It Suits Systems Nobody Can Photograph, Such As Networks, Data, Energy, And Flows Of Money. Choose This Look In [Style Frames](../STYLE-FRAMES.md). The Drawing Helpers Are Described In [Code Scenes](../CODE-SCENES.md).

## What Makes It Read As Luminous 3D

- **Emission.** Shapes Are Seen Because They Give Off Light, Not Because Light Falls On Them.
- **Depth.** Near And Far Are Separated By Size, Brightness, Sharpness, And Haze.
- **A Hierarchy Of Brightness.** One Thing Is Brightest. Everything Else Is Dimmer By Clear Steps.
- **A Camera That Is Always Moving A Little.** The Parallax Is What Tells The Eye This Is Space.

## The Stage

- Make The Background Nearly Black With A Hue, Such As A Deep Blue, Violet, Or Green. Pure Black Looks Like A Missing Layer.
- Lift The Background Softly Behind The Subject So The Subject Has A Place To Be.
- Anchor The Scene With A Hint Of Ground. A Faint Grid, A Horizon Glow, Or A Soft Reflection Gives Scale And A Sense Of Up.

## Glow

- Build Each Glowing Element From Three Layers. A Thin, Bright Core Tinted Toward White. A Tight Halo In The Element's Color. A Wide, Faint Bloom.
- Composite Glow Additively So Overlaps Brighten.
- The Core Carries The Shape. Glow Without A Core Is Fog.
- Budget The Glow. The Hero Runs At Full Strength, Supporting Elements At About Half, And Context At A Quarter Or Less. Most Of The Frame Stays Dark.
- Watch Where Additive Layers Stack. Keep Saturated Colors Below Full Strength So Overlaps Shift Toward A Lighter Hue Before They Reach White. Let Something Go White Only When That Is The Event.

## Depth

- Project Everything Through One Lens For The Whole Shot. A Moderately Wide View Feels Immersive. A Very Wide One Distorts.
- Sort And Draw From Far To Near.
- Fade Distant Elements Toward The Background Color. Make Them Dimmer, Thinner, And Cooler As They Recede.
- Soften Stray Elements Close To The Lens And Far Behind The Subject. Keep The Subject Sharp.
- Scatter Small Particles At Several Depths With A Slow Drift. They Reveal Parallax When The Camera Moves.

## Geometry

- Use Thin Lines, Points, Wireframes, Rings, Ribbons, And Planes That Fade Along Their Length.
- Build Complexity By Repeating Simple Elements With Seeded Variation. A Field Of Nodes And Links Is Clearer Than One Elaborate Model.
- Give Surfaces A Translucent Fill And A Brighter Edge So They Read By Silhouette.

## Light And Color

- Choose Two Hues And White. Assign Their Meanings In [Directing](../DIRECTING.md). One Hue Can Be The System And The Other The Thing The Viewer Follows.
- Keep Saturated Color For Light And Dark, Muted Tones For Matter.
- Let Light Spill. A Soft Pool Beneath A Glowing Object, Or A Tint On A Neighbor, Does More For Belief Than More Bloom.
- Show Flow With Pulses Of Brightness Traveling Along Lines. A Pulse Has A Direction And A Speed, Which Makes It An Event.

## Type

- Set Text In A Clean Sans At Regular Or Medium Weight. Thin Type On A Dark Ground Disappears On A Phone.
- Keep Text Flat To The Screen And Place It On Calm, Dark Areas.
- Give Text A Faint Halo At Most. Text Is Read. It Does Not Compete With The Hero For Brightness.
- Attach Labels To Their Objects With A Thin Leader Line.

## Texture And Finish

- Add Fine Grain Over The Final Frame. Dark Gradients Band Badly After Video Compression, And Grain Breaks The Bands Up.
- A Slight Darkening Toward The Corners Holds The Eye In The Frame.
- Use Flares And Color Fringing Rarely, If At All.

## Camera And Motion

- Give Every Shot One Slow Move. Push In, Drift Sideways, Or Orbit Through A Few Degrees, Easing At Both Ends.
- Keep The Horizon Level. Do Not Spin.
- Travel To Change Subject. Follow A Link To The Next Node Instead Of Cutting, When The Route Itself Means Something.
- Render At 30 Or 60 FPS With Smooth Movement. Draw Fading Trails Behind Fast Points So Their Path Can Be Seen.
- Separate Ambient Motion From Events. Drift, Breathing, And Twinkle Are Ambient And Should Be Seeded And Slow. Each Beat Still Needs One Clear Event, Such As A Link Igniting, A Ring Closing, Or A Node Splitting. This Style Drifts Beautifully While Explaining Nothing, So Check Each Beat Against [Review](../REVIEW.md).

## The Quality Bar

- With Eyes Half Closed, The Brightest Thing In The Frame Is The Subject.
- Near And Far Are Distinct In A Single Still.
- No Banding Shows, And Nothing Clips To White By Accident.
- Text Reads On A Phone.
- Every Beat Has An Event Beyond Ambient Drift.
- A Paused Frame Looks Composed.

## Typical Failures

| Failure | Fix |
| --- | --- |
| Glow On Everything | Restore The Brightness Steps And Give Each Element A Core. |
| A Screensaver | Give Every Beat An Event Tied To A Word. |
| A Flat Picture | Add Haze, Scale Steps, Particles At Depth, And A Camera Move. |
| Thin Glowing Text | Use A Heavier Weight On A Calm Area With Little Halo. |
| Banding After Compression | Add Grain, And Avoid Large Smooth Dark Gradients. |
| A Rainbow | Return To Two Hues And White. |
| Random Flicker | Seed Every Twinkle And Derive It From The Frame Number. |
| Objects Floating In Pure Black | Build The Stage With A Lifted Background And A Ground Hint. |
| A Long, Disorienting Flight | Shorten The Move, Or Cut. |
