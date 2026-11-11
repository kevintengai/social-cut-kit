# Talking Head

A Person Speaks To Camera And The Words Carry The Value. The Edit Makes Each Sentence Land Sooner And Stay Longer Than It Would Alone, Without Coming Between The Viewer And The Speaker. The Clock Is Speech. The [Style Index](../STYLES.md) Says When This Style Fits. Run Commands From The Video Edit Skill Folder.

## The Quality Bar

- Every Word Begins And Ends Whole, And The Breaths Between Sentences Sound Natural.
- The Speaker Stays A Person. The Face Is Visible For Most Of The Video And The Eyes Sit Near One Height Across Cuts.
- Each Supporting Visual Shows The Specific Thing Being Said, At The Moment It Is Said.
- With The Sound Off, The Hook Text And Captions Carry The Argument. With The Sound On, Nothing Competes With The Voice.
- The Closing Words Are Complete, Including Any Keyword The Viewer Is Asked To Use.

## Typical Failures

| Failure | Usual Cause |
| --- | --- |
| Visuals That Could Sit Under Any Video | Illustrating A Word Instead Of The Claim. An Arrow Rising Under The Word Growth Proves Nothing. |
| A Visual That Arrives After Its Word | Placing Overlays By Eye Instead Of From Word Timings |
| A Speaker Reduced To A Voiceover | Back-To-Back Full-Frame Visuals That Hide The Face |
| Emphasis On Every Line | Highlighting By Rhythm Instead Of By Meaning |
| A Hook That Is Only A Large Caption | Reusing The First Spoken Sentence As The Headline |
| Cues That Fight The Voice | A Sound On Every Cut, Set Too Loud, Landing On A Word |
| A Breathless Voice | Removing Every Pause And Breath To Save Time |
| A Chopped Ending | Trimming The Last Sentence To Reach A Target Length |

## Starting Values

| Setting | Start With | Reason |
| --- | --- | --- |
| Canvas | 1080 By 1920 At The Rate The [Canvas Frame Rate](../SKILL.md#canvas-frame-rate) Rule Gives, Which Is 30 For A 29.97 Or 59.94 Phone Clip | Vertical Delivery. Set The Rate Before Timing Captions. |
| Captions | Phrases Of Up To 3 Words And 20 Characters, A `size` Of 65, And A Bottom `margin` Of 25 On A 1080 By 1920 Canvas | These Are The Tool Defaults For A Vertical Canvas. Each Phrase Stays On One Line, Clear Of The Platform's Buttons And Description. |
| Framing | Footage Filling The Full Height Of The Frame, `zoom` At 1, Eyes In The Upper Third | The Viewer Meets A Person At Conversational Distance And The Lower Frame Stays Free For Captions. For A Horizontal Source Use `cover` And Set `pan_x` To Keep The Speaker Centered. |
| Color | `brightness`, `contrast`, And `saturation` At 1 | The Camera's Own Color Is The Owner's Look Until They Ask For A Grade. |
| Speed | `speed` At 1 For All Dialogue | Natural Delivery |
| Sound | Shot `gain` At 1 With The Original Audio Unprocessed | The Source Audio Rule. Run `python scripts/speech.py levels` To Measure Before Proposing Any Change. |
| Handles | `lead` And `tail` Long Enough To Keep Each First Consonant, Last Syllable, And Breath | A Cut Is Judged By The Words On Either Side Of It. |
| Ending | The Final Shot Runs Through The Last Word And Its Natural Tail | Shorten Elsewhere. The Close Carries The Ask. |

Cut From The Words. Transcribe First, Use `python scripts/takes.py words.json --retakes` To Find Restarts And Full Retakes, Add `--script script.txt` When The Project Has A Script, And Use `analyze` To Find Long Silences. The Tool Cannot Hear Performance. When Several Attempts At A Line Or At The Ending Are Equally Complete, Offer The Owner The Choice And Recommend The Latest. Remove False Starts, Abandoned Sentences, And Dead Air. Keep The Pause Before A Sentence That Needs Weight. After Mapping Captions, Read `speech_units_cut_at_boundaries`. Any Count Above Zero Means A Cut Runs Through A Word, So Move That Cut Outward.

## Supporting Visuals

A Supporting Visual Earns Its Place By Showing The Specific Thing Being Said. Sort Each Sentence That Might Take A Visual Into One Of Three Cases.

| The Sentence | Show | Example |
| --- | --- | --- |
| Names Something | The Real Thing On Its Word. The Real Logo, Product, Document, Person, Or Screen. | The Speaker Names A Booking Tool And Its Actual Logo Appears As The Name Is Spoken. |
| Makes A Claim That Needs Proof | Evidence The Viewer Can Inspect. The Dashboard, Receipt, Message, Or Page Where The Figure Can Be Read. | The Speaker Says Bookings Doubled And The Owner's Report Fills The Frame With Both Months Visible. |
| Describes Something With No Real Image | An Illustration, Such As A Simple Diagram Or An Icon Sequence | The Speaker Describes A Hand-Off Between Two Teams And A Two-Step Diagram Shows It. |

- Illustration Is The Last Choice. Viewers Discount A Drawing Of A Result And Trust A Capture Of It.
- Apply Two Tests. Remove The Visual, And If The Sentence Loses Nothing, The Visual Was Decoration. Imagine The Visual In A Different Video, And If It Fits There Too, It Is Generic.
- Start The Overlay At The Start Time Of The Word That Names It, Taken From The Transcript. A Frame Or Two Early Reads As On Time. Late Reads As A Mistake. End It When The Speaker Moves To The Next Idea.
- Hold Evidence Long Enough To Read The Line That Matters, And Enlarge That Line Instead Of Showing A Whole Page At Unreadable Size. The [Screen Demo Guide](screen-demo.md) Covers Legibility.
- Ask The Owner For The Logo File, The Capture, Or The Photo. Use Only Images They Have The Right To Use And Record Each Source In The [Asset Library](../../asset-library/SKILL.md).

## Placement And Layout

| Placement | Use It For | How |
| --- | --- | --- |
| A Card Above The Head Or Beside A Shoulder | Logos, Small Objects, One Number | An Overlay With `x`, `y`, And `width` In Space The Face Does Not Use |
| A Band Across The Lower Middle | A Wide Capture Strip Or A Short Quote | An Overlay Above The Caption Band, With Captions Moved Or Paused Where They Would Collide |
| Full Frame Over The Speaker | Evidence That Needs The Whole Screen To Be Read | An Overlay At Canvas Width. The Speaker's Shot And Voice Keep Running Underneath. |
| No Visual, Only A Punch-In | Emphasis That Belongs To The Speaker | Split The Shot And Set A Larger `zoom` On The Second Part |

- Keep The Eyes And Mouth Clear During The Lines That Matter Most. The Face Is Where Trust Comes From.
- Vary The Layout By The Job A Visual Does. Small And High For Things That Are Named, Full Frame For Proof. The Viewer Learns What Each Position Means. One Placement For Everything Makes Every Arrival Look Alike, And The Eye Stops Checking.
- Return To The Plain Speaker Between Visuals. The Face Is What Makes The Next Visual Feel Like News.
- Keep Three Bands Apart. A Hook Or Card Sits High, The Face Sits In The Middle, And Captions Sit Below. Leave The Outer Edges Clear For The Platform's Own Buttons And Text. Confirm On A Still At The Delivery Aspect Ratio.

## The Opening Hook Text

Design The Hook As Its Own Composition. It Is A Headline, Separate From The Running Captions.

- Build It With The [Title Helper](../TITLES.md) As A Transparent PNG On The Overlay Track. Give It Its Own Size, Position, And Plate So It Cannot Be Mistaken For A Caption.
- Write The Promise Or The Tension In A Few Words. If It Repeats The First Spoken Sentence Word For Word, Rewrite It, Or Hold The Captions Back Until It Clears.
- Highlight One Word With `--highlight`. Choose The Word That Carries The Stake.
- Show It From The First Frame, Hold It Long Enough To Read Twice, And Remove It Before The First Supporting Visual Needs The Space.
- Place It Where The Face Is Not. The Top Of The Frame Usually Works, With A `--margin` That Clears The Platform's Upper Edge.
- The Owner's Saved Hook Format Overrides These Choices.

## Captions

- Map Captions From Word Timings With `python scripts/speech.py captions` And `--phrases`. The Text Matches The Words As Spoken. Keep The Owner's Spelling Of Names And Of Any Keyword, Taken From The Script When There Is One.
- Start From The Tool Defaults For A Vertical Canvas: Up To 3 Words And 20 Characters In A Phrase, A `size` Of 6 Percent Of The Canvas Width, And A Bottom `margin` Of 25. Change Them Only For The Owner's Saved Caption Style Or A Stated Reason.
- A Caption Stays Fixed While A Word Is Being Spoken And Leaves With Its Sentence.
- Spread Emphasis By Meaning. Emphasize The Number, The Name, The Word That Turns The Argument, And The Keyword In The Ask. Most Sentences Get None. When Every Line Carries A Highlight, The Highlight Carries No Information.
- The Timeline Gives All Captions One Style. To Emphasize A Line, Replace Its Caption Cue With A Title Overlay That Highlights The Key Word, Placed Where The Caption Sat. A JSON Newline Escape Can Also Break A Line So The Key Word Ends It.
- Keep Captions Quiet Over Dense Evidence. While A Document, Table, Or Dashboard Fills The Frame, The Viewer Is Reading It. Use Plain Captions, Set `position` Away From The Line That Matters, Or Pause Captions For That Stretch When The Evidence Shows The Same Words.

## Sound Cues

- A Cue Marks Something The Viewer Sees. Where Nothing Visible Happens, Add No Cue.
- A Plain Talking Head Still Has Visible Events. The List Below Is Complete For A Cut With No Other Effects.

| Visible Event | A Cue That Fits |
| --- | --- |
| The Hook Text Arriving Or Leaving | `soft-swipe`, `whoosh-light`, Or `page-flick` |
| An On-Screen Keyword Or Number Appearing | `pop-bubble`, `counter-step`, Or `glass-point` |
| A Punch-In | `focus-shift` Or `quick-pass` |
| An Inserted Visual Arriving Or Leaving | `button-up`, `soft-swipe`, Or `success-pair` For A Result |

- A Plain Cut Between Two Takes Is Not A Visible Event. It Is Meant To Pass Unnoticed, So It Takes No Cue. A Caption Phrase Changing Is Not One Either.
- When The Brief Asks For Light Sound Effects, List The Visible Events The Edit Already Has And Give Each At Most One Cue. Light Means Two To Four Cues In A 30 To 45 Second Video.
- When The Edit Has No Visible Event, Do Not Scatter Cues Across The Cuts, And Do Not Leave The Request Unmet In Silence. Propose One Or Two Events To The Owner, Each With The Cue It Would Carry. Good First Proposals Are The Hook Text Arriving, A Punch-In On The Line That Turns The Argument, And The Key Number Appearing As Text On Its Word. Add Them After The Owner Agrees, And Record The Answer In The [Brief File](../BRIEF.md).
- Use Few. A Handful In A Minute Keeps Each One Meaningful. The Same Tap On Every Cut Turns Into A Metronome.
- Level Each Cue Against The Speech Around It. Start Well Below The Voice. The Included Example Sets A Short Tap To A `gain` Of 0.36. The `loudness` Command Measures The Mix Without Writing A File And Can Compare Each Cue With The Speech Under It. Numbers Guide The Level And Ears Decide It, So Ask The Owner To Judge On A Phone Speaker During Review.
- Land The Cue In The Gap After The Cue Word. A Transient On Top Of A Consonant Hides The Word. Take The End Time Of The Word From The Transcript And Start The Cue There. If The Sound Then Trails The Picture Noticeably, Move The Start Of The Visual To The Same Moment So Both Land Together.
- Taps Suit Small Arrivals And Interface Actions. Brushes Suit A Sliding Card Or A Change Of Section. Bells And Pairs Suit A Result. Save Bumps For One Or Two Reveals. The [Cue Bank](../assets/cue-bank/README.md) Holds The Sounds.
- Music Is Opt-In. Add A Bed Only When The Brief Asks For One, Only From Tracks The Owner Has The Right To Use, And Keep It Under The Voice.

## Playful Sounds

Playful Sounds Fit A Joke, A Self-Deprecating Aside, A Quick List Of Tips, Or A Light Reveal. They Tell The Viewer That The Moment Is Not Serious. That Same Signal Cheapens A Sincere Story. Over A Personal Setback, A Client's Hard Situation, Worries About Money Or Health, An Apology, Or A Testimonial, A Comic Sound Says The Speaker Does Not Mean It. In Those Passages Let The Voice And Its Pauses Carry The Moment. When A Video Holds Both Registers, Stop The Playful Cues Before The Sincere Turn And Bring Them Back Only After The Tone Has Clearly Lifted. A Useful Test Is Whether The Speaker Would Make That Sound Aloud, In The Room, At That Moment.

## When No Fitting Visual Exists

Leave The Speaker On Screen And List The Gap For The Owner. A Plain Face Is Better Than A Wrong Picture. In The Open Items Of The [Brief File](../BRIEF.md), Record The Time Range, The Spoken Line, The Real Image That Would Fit, And Who Could Supply It. Report The List At Hand-Off. A Generic Clip, An Invented Capture, Or A Made-Up Figure Trades A Small Gap For A False Statement.

## Before Review

Run `validate` And `check`, Then Open `review`. Use `still` To Inspect A Frame At Delivery Size For The Hook, For Each Visual, And For The Busiest Caption. When A Source Cannot Play In A Browser, Ask The Owner Once For A Working Copy First, As [The Skill Guide](../SKILL.md#when-a-browser-cannot-play-the-source) Describes. The Owner Then Reviews The Saved Project In The Editor. No Video Of The Edit Is Created Before They Approve, Including A Test Or Preview Export.
