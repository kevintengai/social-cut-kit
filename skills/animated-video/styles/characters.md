# Character Cartoon And Doodle

Characters The Viewer Reads At A Glance. A Clear Silhouette, A Face That Shows Thought, And Poses That Carry The Story Without Words. Cartoon Uses Solid Shapes, Outlines, And Squash And Stretch. Doodle Uses A Loose Pen Line And Very Few Features. Choose This Look In [Style Frames](../STYLE-FRAMES.md). The Drawing Helpers Are In [Code Scenes](../CODE-SCENES.md) And The Reusable Character Is In [Parts](../PARTS.md).

## Design A Simple, Consistent Cast

- **Build From A Few Shapes.** A Bean For The Body, A Round Head, Tubes For Limbs. Define Each Character Once, As A Drawing That Takes A Pose. Every Shot Calls That One Definition. This Is What Keeps A Character On Model.
- **Keep The Constants In One Place.** Head Size, Limb Lengths, Line Width, And Colors Are Named Values. No Shot Overrides Them.
- **Make A Model Sheet Before Any Scene.** Render Stills Of Each Character From The Front, At Three Quarters, And From The Side. Add The Expressions The Story Needs And A Line-Up Of The Whole Cast Standing Together.
- **Test Every Scale The Story Needs.** Render The Character Filling The Frame, At Mid Size, And As Small As The Widest Shot Requires. Features That Vanish When Small Need A Simpler Small Version With The Same Silhouette And Colors. Judge It At Phone Size.
- **Pass The Silhouette Test.** Filled Solid Black, Each Character Is Still Recognizable And Each Pose Still Reads. Tell The Cast Apart By Shape, Height, And One Color Each.
- **Favor The Face.** A Large Head Keeps The Face Legible On A Phone. Eyes Need Pupils That Can Look Somewhere. Brows Are Separate Strokes, And They Carry Most Of The Emotion.
- **Leave Out Costly Detail.** Stripes, Patterns, And Small Logos Have To Be Tracked Through Every Pose, And They Shimmer When Small.

## Line, Color, Light, And Camera

- Choose The Line Rule Once. Either The Line Scales With The Character, Or It Keeps A Constant Width On Screen. Constant Width Suits Doodle. Set A Minimum Width So A Small Character Does Not Dissolve.
- For Doodle, Use The Line And Boil From [Hand-Made 2D](handmade-2d.md). For Cartoon, Use Even Outlines And Flat Fills.
- Give Each Character Two Or Three Colors Plus The Line. Follow The Color Meanings From [Directing](../DIRECTING.md).
- Draw Light Simply. One Shadow Tone On One Side, Kept On That Side Throughout, And A Soft Shape On The Ground Under The Feet.
- Animate Character Action With Each Drawing Held For Two Frames At 24 FPS. Poses Read More Clearly And The Result Looks Drawn.
- Keep Backgrounds Simpler And Paler Than The Characters So Poses Stand Clear.
- Stage Like A Play. Give Wide Shots For Geography, Mid Shots For Action, And Close Shots For Thought. Leave Space In The Direction A Character Looks Or Moves.
- Set Any Type In The Voice Of The Line. Hand-Lettered For Doodle, A Rounded Face For Cartoon.

## Posing And Acting

- **A Pose Carries One Thought.** Run A Single Curve, The Line Of Action, Through The Body. Put The Weight On One Leg. Tilt The Head. Avoid Twinning, Where Both Arms Mirror Each Other.
- **Thinking Comes Before Moving.** The Eyes Move First, Then The Head, Then The Body. Anticipate, Act, And Settle. A Character Who Moves Without First Noticing Looks Operated.
- **Hold Poses.** A Held Pose With A Breath, A Blink, Or A Slight Drift Reads Better Than Constant Motion. Give The Viewer Time To See It.
- **Stage For Silhouette.** Gesture With The Hands Away From The Body. Show The Important Action In Profile Or At Three Quarters.
- **Squash And Stretch Keep Volume.** A Shape That Gets Shorter Gets Wider. Use More In Cartoon And Very Little In A Sober Doodle.
- **Move On Arcs.** Heads And Hands Travel Along Curves. Let Hair, Ears, And Clothing Trail And Settle After The Body Stops.
- **Change The Whole Face.** An Expression Is Brows, Eyes, Mouth, And Head Tilt Together. A Blink Just Before It Helps The Change Read.
- **Act To The Voice.** Place One Gesture Per Phrase, On The Stressed Word, Using The Word Timings From [Voice Timing](../VOICE-TIMING.md). A Gesture On Every Word Is Noise.
- **Use Reactions.** A Character's Reaction Tells The Viewer How To Feel About What Was Just Shown.

## Walk Cycles

| Pose | What Happens |
| --- | --- |
| Contact | The Front Heel Strikes With The Legs At Their Widest. The Arms Are Opposite To The Legs. |
| Down | The Front Leg Takes The Weight And Bends. The Body Is At Its Lowest. |
| Passing | The Supporting Leg Is Straight Beneath The Body And The Other Leg Swings Past. The Body Rises. |
| Up | The Back Foot Pushes Off. The Body Is At Its Highest. |

- Repeat The Four Poses, Mirrored, For The Other Step.
- An Ordinary Walk Takes About Half A Second Per Step, Which Is Twelve Frames At 24 FPS. Faster Reads As Brisk Or Anxious. Slower Reads As Heavy Or Sad.
- Give The Walk A Personality Through Bounce, Stride Length, Lean, Arm Swing, And Speed.
- **Plant The Feet.** A Foot On The Ground Does Not Move Across It. On Each Step The Body Advances By Exactly The Distance From One Foot Contact To The Next. When The Cycle Runs In Place, The Ground Moves Under It At That Same Speed. Check A Strip Of Consecutive Frames Against A Mark On The Ground.
- **Keep Limbs The Same Length.** Find The Knee And Elbow From The Positions Of The Two Ends And The Fixed Bone Lengths. Do Not Stretch A Leg To Reach A Foot.
- Swing The Arms Opposite To The Legs, With The Hands Trailing Slightly. Let The Head Follow A Little Late.
- Loop So The Last Frame Leads Into The First. Begin A Walk With A Lean And A First Step, And End It With A Settle.
- When A Character Is Very Small, Two Leg Positions And A Bob Of The Body Are Enough.

## Mouth And Blink

- Keep A Small Set Of Mouth Shapes. Closed, Slightly Open, Wide Open, And Rounded Cover Most Speech. Add A Wide Shape With Teeth And A Lip-On-Teeth Shape When Close Shots Need Them.
- Drive The Mouth From The Word Timings. Open On Each Vowel Sound Within A Word And Close At Its End, At Pauses, And On The Lip Sounds Of M, B, And P. The Closed Shapes Are What Sell The Sync.
- Show A Shape A Frame Or Two Before Its Sound. Early Looks Right. Late Looks Dubbed.
- Hold Each Shape For At Least Two Frames. A New Shape On Every Frame Chatters.
- Scale The Effort To The Size. A Small Character Needs Only Open And Closed On The Syllables.
- Let The Jaw Move The Chin A Little On Wide Shapes. When Silent, The Mouth Rests In An Expression.
- Blink At Uneven, Seeded Intervals Of A Few Seconds. A Blink Lasts About Four To Six Frames At 24 FPS, With Two To Close, One Or Two Shut, And Two To Open.
- Blink On A Head Turn, A Change Of Gaze, And Just Before A Change Of Thought. Do Not Blink Across A Key Word Or A Key Expression.
- A Character Who Never Blinks Looks Lifeless. One Who Blinks On A Steady Beat Looks Mechanical.
- Add Small Quick Shifts Of The Eyes While A Character Thinks.

## Consistency Across Shots

- **Scale.** Record Each Character's Height In The Units Of The Scene, On The Line-Up. In Every Shot, Derive The Drawn Size From That Height And The Camera, Never By Eye. The Height Of A Character Against A Recurring Prop, Such As A Desk, Stays Constant.
- **Limbs.** Lengths Are Constants. When A Pose Needs A Longer Reach, Lean The Body.
- **Sides.** Mirroring A Character Flips Any One-Sided Detail. Either Avoid One-Sided Details Or Avoid Mirroring.
- **Direction.** A Character Traveling Left To Right Keeps That Direction Across Cuts Until A Turn Is Shown. When Two Characters Talk, Their Eyelines Meet.
- **State.** A Prop Stays In The Same Hand, And Clothing Stays As It Was, From One Shot To The Next.
- **Compare.** Put Stills Of The Character From Every Shot On One Board At A Common Scale, Using `tools/stills.cjs` As Described In [Review Tools](../REVIEW-TOOLS.md). Compare Head Size, Limb Length, Line, And Color.

## The Quality Bar

- Each Character Reads In Silhouette And At The Smallest Scale Used.
- The Character Is On Model In Every Shot.
- The Viewer Can Tell What A Character Thinks Before The Character Moves.
- Feet Stay Planted And Limbs Keep Their Length.
- Mouths Close On The Closed Sounds And Blinks Come Unevenly.
- Poses Are Asymmetric And Held Long Enough To See.

## Typical Failures

| Failure | Fix |
| --- | --- |
| Drift Off Model | Draw Every Shot From The One Definition And Its Constants. |
| A Sliding Walk | Tie Body Travel To The Distance Between Foot Contacts And Plant The Feet. |
| Lifeless Eyes | Add Blinks, Gaze Changes, And Eyes That Lead The Head. |
| A Flapping Mouth With No Acting | Add A Gesture On The Stressed Word And A Change Of Expression. |
| Twinning And Constant Motion | Break The Symmetry And Hold The Pose. |
| A Design That Breaks When Small | Simplify It, Or Add A Small Version. |
| Limbs Like Rubber | Fix The Bone Lengths And Solve For The Joint. |
| Everything At One Speed | Contrast Fast And Slow, And Pause Before The Important Action. |
