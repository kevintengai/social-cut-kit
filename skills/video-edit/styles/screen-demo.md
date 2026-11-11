# Screen Demo

The Product, Or Its Result, On A Screen Is The Proof. The Clock Is The Action On Screen. A Cut Or Reframe Is Right When An Action Completes Or A Result Appears. The [Style Index](../STYLES.md) Says When This Style Fits. Run Commands From The Video Edit Skill Folder.

## Real Capture

Use A Real Recording Of The Owner's Own Product, Account, And Data. A Mock-Up Presented As The Product, Or A Capture Of Someone Else's Screen, Is Not Proof. When A Claim Depends On A Result, The Capture Has To Show That Result.

- Ask For The Whole Action In One Continuous Recording, Waiting Included. Dead Time Can Be Sped Up Later. A Missing Step Cannot Be Recreated.
- Ask For A Readable Capture At The Source. A Browser Zoomed In, A Clean Window, A Visible Cursor, And Notifications Switched Off Do More Than Any Enlargement Afterward.
- Ask For The Result To Stay On Screen For A Few Seconds At The End.
- Look For Private Details Before Building. Customer Names, Addresses, Keys, And Figures The Owner May Not Want Public Should Be Hidden At The Source Or Recorded In A Demo Account. List Anything You Spot For The Owner.
- Show Interface States And Numbers Exactly As Captured. Editing A Capture To Show A Better Number Turns Proof Into A False Claim.

## Legible At Phone Size

The Viewer Must Read Three Things. Where The Cursor Acts, What Was Entered, And What Came Back. A Whole Desktop Shown Small Fails All Three.

- Frame Each Of The Three With `shots[].zoom`, `pan_x`, And `pan_y`. Each Shot Holds One Framing, So Split The Shot Where Attention Moves And Set The Fields On Each Part. Split On An Action, Such As A Click Or The Enter Key, So The Jump Has A Reason.
- Order The Framings As Context, Action, Result. Show The Whole Window Briefly So The Viewer Knows Where They Are. Move To The Field Or Control Being Used. Then Give The Result The Largest Framing And Hold It.
- With `cover`, A Horizontal Capture Fills A Vertical Canvas And `pan_x` Chooses The Region. With `contain`, The Capture Sits In A Band Against Black, `zoom` Enlarges It Within The Canvas, And `pan_y` Moves The Band. A Band Anchored High With `pan_y` At −1 Leaves The Lower Frame Free For A Reaction Inset Or A Label.
- To Aim A Pan, Work On One Axis At A Time. The Drawn Size Is The Source Size Times The Fit Scale Times `zoom`. The Fit Scale Is The Larger Of The Two Canvas-To-Source Ratios For `cover` And The Smaller For `contain`. Let `v` Be The Canvas Size Divided By The Drawn Size, Capped At 1. That Is The Share Of The Source Still Visible. To Center A Point At Fraction `c` Along The Source, Set The Pan To `2 * (c - v / 2) / (1 - v) - 1` And Keep It Within −1 And 1. Confirm The Framing On A Still.
- Keep The Cursor Inside The Framed Region Through Every Action. When The Cursor Travels Far, Split At The Click And Reframe There.
- Hold Typed Input After The Last Character. Typing Can Be Sped Up. The Finished Text Is Read At Normal Speed.
- Enlargement Has A Limit. Past About 2× On A 1080-Line Capture The Text Softens. Ask For A Larger Capture Before Reaching For The Maximum `zoom` Of 4.
- A Tap From The [Cue Bank](../assets/cue-bank/README.md) On A Click Or Key Press, Such As `button-down` Or `soft-key`, Marks The Action. Use It On Actions The Viewer Can See.
- Name A Step With A Small Title From The [Title Helper](../TITLES.md) When The Screen Alone Does Not Say What Is Happening. Keep It Outside The Framed Region.

## Shorten By Speeding Dead Time

Viewers Trust A Demo When They See The Action Lead To The Result In One Unbroken Piece. A Cut Between The Click And The Result Invites The Thought That Something Was Swapped. So Shorten The Wait And Leave The Result Alone.

- Dead Time Is Loading, Waiting For A Response, Long Typing, Scrolling To Reach Something, And Cursor Travel. Split Those Stretches Out And Raise `speed`, Up To 4.
- Keep The Moment The Result Arrives, And The Result Itself, At A `speed` Of 1.
- When A Wait Is Too Long Even At The Maximum Speed, Cut Inside The Wait And Label The Real Elapsed Time. An Honest Jump Is Better Than A Hidden One.
- Speed Changes Affect The Sound Of The Shot As Well. Speed Up Only Stretches Without Speech, Or Set The Sped Shot's `gain` To 0 And Carry The Narration As Its Own `audio[]` Entry. Dialogue Stays At Its Recorded Speed.
- When Speed Itself Is The Claim, Leave That Stretch At 1 And Label It As Real Time.

## Label Sped-Up Footage With Its True Rate

Every Shot With A `speed` Other Than 1 Carries A Visible Label That States Its Actual Rate. A Sped-Up Demo Without A Label Claims The Product Is Faster Than It Is.

- Make The Label A Small Title Overlay In A Corner, With Text Such As `4x Speed`. The Number Is The Shot's `speed` Value, Not A Rounded Or Flattering One.
- The Label Starts And Ends With The Sped Shot. A Shot's Length On The Timeline Is Its Source Range, Handles Included, Divided By Its `speed` And Snapped To A Frame. Its Start Is The Sum Of The Shots Before It.
- Keep The Label Right After Every Speed Change. Changing `speed` Changes That Shot's Length And Moves Everything After It. Overlays, Captions, And Audio Entries Use Timeline Time And Do Not Follow. After Any Change, Recompute The Label's `at` And `end`, Update Its Text If The Rate Changed, And Recheck Every Later Cue.
- Two Neighboring Stretches At Different Speeds Each Need Their Own Label. One Shared Speed Is Simpler To Keep Honest.

## Supplied Tables And Captures

When The Owner Supplies A Table Or A Capture As Evidence, Show It Whole And Long Enough To Read.

- Show The Whole Image First With `contain`, Uncropped. Headers, Totals, Dates, And Units Are What Make It Evidence. Cropping Them Away Leaves A Number With No Context.
- Then Enlarge The Row That Matters If It Is Too Small To Read. Split The Shot And Set `zoom` And The Pan Fields On The Second Part.
- Time The Hold By Reading. Read The Lines That Matter At A Normal Pace, Then Add A Beat. A Dense Table Needs Seconds. If The Video Cannot Afford Them, Show Fewer Rows Clearly After The Whole Image Has Been Seen.
- Leave The Image As Supplied. A Retyped Table Is An Illustration And The Capture Is The Evidence. Rebuild It As A Graphic Only When The Owner Asks.
- If The Supplied File Is Too Small To Read When Shown Whole, Ask For The Original.
- Keep Captions Plain And Set `position` Away From The Rows That Matter.

## Reaction Cut-Ins

A Short Look At The Owner's Face Gives The Result A Human Verdict.

- Place It After The Viewer Has Had Time To Read The Result. Do Not Cover The Result With It.
- Keep It Brief, About A Second Or Two, Then Return To The Result Or Move On.
- As A Full-Frame Cut, Add The Face Camera As Its Own Shot. When Screen And Face Were Recorded Together, Find The Offset With `python scripts/speech.py sync`.
- As An Inset, Add The Face Camera As An Overlay With `x`, `y`, And `width`, In A Corner The Interface Does Not Use Or In The Empty Part Of A `contain` Layout. Overlay Sound Is Muted, So Give The Voice Its Own `audio[]` Entry.
- Use The Real Reaction With Its Real Sound. A Large Reaction To A Modest Result Reads As Acting.

## The Quality Bar

- A Viewer On A Phone Reads The Input And The Result Without Pausing.
- The Path From Action To Result Is Continuous, And Every Gap In It Is Labeled.
- Every Sped Stretch Carries A Correct Label That Starts And Ends With It.
- The Result Holds Long Enough To Read Twice.
- The Cursor Stays In Frame Through Every Action.
- No Private Detail Is Visible And No State Is Invented.
- The Opening Seconds Show The Result, Or A Clear Promise Of It, Before The Steps Begin.

Run `validate` And `check`, Open `review`, And Inspect A Frame From `still` For Every Framing. The Owner Then Reviews The Saved Project In The Editor. No Video File Is Created Before They Approve, Including A Test Or Preview Export.
