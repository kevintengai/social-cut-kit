# Realistic 3D

Use This Style When The Viewer Must Believe A Physical Object Exists. Choose It In [Style Frames](../STYLE-FRAMES.md).

## The Honest Limit

Code-Drawn 3D Reads As CGI. A Renderer Written In Drawing Code Projects Polygons And Shades Their Faces With A Key Light, A Highlight, And A Rim. The Result Is Clean, Graphic, And Plainly Computer-Made. It Cannot Give The Soft Bounced Light, True Reflections, Real Shadows, Material Depth, And Lens Behavior That A Product Shot Depends On. That Is Fine When A Stylized Object Is What The Film Wants. It Is Not Fine When The Object Is Meant To Pass As Photographed.

Route Photoreal Product Shots To The Kit's Blender Scene Builder. Its [Guide](../blender/README.md) Covers The Commands, The Direction File, And The Verifier. The Builder Writes An Editable Blender Scene. For A Product It Does Not Cover, Extend Its Geometry Or Model The Product In Blender, And Apply The Principles Below.

| The Shot Needs | Route |
| --- | --- |
| A Stylized Object, A Diagram In Space, A Turntable That Reads As Designed | Draw It In Code With [Code Scenes](../CODE-SCENES.md), And Make The Graphic Look Deliberate |
| A Product The Viewer Should Take For Real, Or A Close View Of Metal, Glass, Rubber, Or Liquid | The Blender Scene Builder |
| A Product That Exists And Can Be Filmed | Film It. Footage The Owner Has The Right To Use Beats Any Render. |

## Scale

- Model In Real Units. A Dial Is Forty Millimeters Across, Not Four Meters. Light Falloff, Focus, And Bevel Size All Follow From True Size.
- Use A Lens A Product Photographer Would Choose. A Longer Lens From Farther Back Keeps Proportions Calm. A Wide Lens Up Close Bends A Small Object.
- Place The Camera Where A Real Camera Could Stand.
- Bevel Every Edge. No Manufactured Edge Is Perfectly Sharp, And The Bevel Catches The Highlight That Draws The Form.
- Keep Small Features In Proportion. Screws, Seams, Printed Text, And Surface Grain Each Have A Real Size.
- Mind The Focus. A Very Shallow Focus Makes A Product Look Like A Miniature.
- Give An Unfamiliar Product A Cue For Its Size, Such As A Tabletop With A Known Texture.

## Materials

- Describe Each Surface Physically, By Its Base Color, Its Roughness, And Whether It Is Metal.
- Variation Is What Reads As Real. Break Up Roughness With Faint Smudges And Fine Scratches. Let Color Shift Slightly Across A Surface. Add Wear Sparingly And Only Where Hands Would Cause It.
- Avoid Pure Black, Pure White, And Fully Saturated Base Colors. Real Surfaces Do Not Reach Them.
- Give Metal Something To Reflect. Without Surroundings It Renders As Gray Plastic.
- Give Glass Thickness And Something Behind It.
- Make Rubber Rough, And A Little Lighter Than Instinct Suggests.
- Let Lit Elements Cast Their Light On Nearby Surfaces. Keep Their Bloom Small.
- Match The Finishes Of The Real Product From The Owner's Photos Or Samples.

## Light

- Light It As A Studio Would. A Large Soft Key Draws Gradient Highlights That Describe Curvature. A Rim From Behind Separates The Edge From The Background. A Low Fill Keeps The Shadow Side Readable Without Flattening It.
- On Glossy Surfaces The Reflections Are The Lighting. Shape Them. Long Strip Lights Along An Edge Give The Clean Line Seen In Product Photography.
- Stand The Object On A Surface With A Soft Contact Shadow. That Shadow Is What Stops It Floating.
- Avoid Even Light From Everywhere, And Avoid A Single Small Hard Light. Both Look Computed.
- Keep Highlights On The Product Below Clipping.
- Keep One Lighting Scheme Across Every Shot Of The Same Object.

## Air

Air Is Everything Between The Lens And The Object. Renders Without It Look Too Clean To Be Real.

- Focus On The Feature And Let The Rest Fall Off Gently.
- Add A Little Haze For Depth In A Larger Scene.
- Let Only The Brightest Highlights Bloom.
- Add A Slight Darkening Toward The Corners And A Fine Grain.
- Blur Whatever Moves, As A Camera Shutter Would.
- Use A View Transform That Rolls Highlights Off Softly Instead Of Clipping Them.

## Weighted Motion

- Mass Shows In Timing. Heavy Parts Start Slowly And Stop Slowly. Nothing Begins Or Ends In A Single Frame.
- Mechanisms Have Character. A Key Bottoms Out And Rebounds. A Dial Has Friction And Settles At Its Mark. A Lid Slows Into Its Hinge. Ask The Owner How The Real Part Behaves, And How Far It Travels.
- Add The Secondary Response. A Light Warms Up Instead Of Switching On. A Cable Sways After The Body Stops.
- Give The Camera Mass Too. Move It As If On A Slider Or A Turntable, With Slow Easing And A Small Settle, And No Sudden Reversal.
- Cut Between Views In Place Of Impossible Flights.

## Truth And Review

- A Render Of The Owner's Real Product Matches It In Shape, Color, Finish, And Features.
- A Render Of Something That Does Not Exist Yet Is Reported To The Owner As Synthetic. See [Review](../REVIEW.md).
- Render Other Companies' Products And Marks Only With The Right To Do So.
- Check With Stills At The Story Moments. The Owner Reviews The Saved Scene In Blender Before Any Video File Is Created, Including A Test Or Preview Render.
- An Approved Render Returns To The Film As A Clip. Match Its Frame Rate, Size, Grain, And Color To The Scenes Around It, As Described In [Handoffs](../HANDOFFS.md).

## When Code-Drawn 3D Is The Choice

Make It Plainly Stylized. Use Flat Or Two-Tone Shading, Visible Facets, A Rim Light, One Consistent Light Direction, And A Simple Shadow Shape For Contact. Do Not Half-Imitate Realism. The Uncomfortable Middle, Almost Real, Is The Worst Result. Say In The Style Frame That The Look Is Graphic By Intent.

## The Quality Bar

- A Still Passes As A Photograph At Phone Size, Or Is Clearly Stylized On Purpose. Nothing Sits In Between.
- Everything That Touches A Surface Has A Contact Shadow.
- Highlights Describe The Form, And Every Edge Has A Bevel.
- With Color Removed, The Materials Can Still Be Told Apart By Their Roughness And Reflection.
- Motion Has Weight, With Eased Starts And Stops And A Settle.
- The Scale Is Believable.

## Typical Failures

| Failure | Fix |
| --- | --- |
| A Plastic Look | Vary Roughness, Add Bevels, And Give The Surface Something To Reflect. |
| A Floating Object | Add A Ground And A Soft Contact Shadow. |
| A Toy Scale | Use A Longer Lens, Deepen The Focus, And Correct The Size Of Bevels And Grain. |
| Weightless Motion | Ease Starts And Stops, Add A Settle, And Slow The Camera. |
| Flat Or Harsh Light | Use A Large Soft Key, A Rim, And A Low Fill. |
| Heavy Processing | Reduce Bloom, Fringing, And Flares Until They Go Unnoticed. |
| Perfect Sharpness, Pure Black, Pure White | Add Grain, Soften The Roll-Off, And Lift The Blacks Slightly. |
| A Code-Drawn Object Offered As A Photograph | Change The Route, Or Change The Promise. |
| A Render That Differs From The Real Product | Correct It Against The Owner's Reference. |
