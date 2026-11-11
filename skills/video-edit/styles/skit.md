# Skit And Meme Reel

Silent Acting Or A Reaction Clip, With One On-Screen Line Carrying The Joke And A Sound Carrying The Energy. The Clock Is The Sound And The Reading Time Of The Line. The [Style Index](../STYLES.md) Says When This Style Fits. Run Commands From The Video Edit Skill Folder.

## Why They Work

- **Specific Recognition.** The Line Names A Situation That Only The Audience's Own Group Knows From The Inside. The Detail Is The Joke. A Line That Could Apply To Anyone Is Shared By No One.
- **Self-Deprecation.** The Performer Is The Target. Laughing At Yourself Reads As Warm. Laughing At The Audience Or At Customers Reads As Contempt.
- **Instant Read.** The Line And The Face Give The Whole Premise In The First Second. Nothing Has To Be Explained First.
- **An Ending That Loops.** The Clip Stops At Its Peak, On A Frame That Cuts Back To The First Without A Visible Reset. The Second Pass Is When Many Viewers Finish Reading The Line.

## Common Structures

| Structure | What Happens | Edit Decisions |
| --- | --- | --- |
| One Caption Over One Held Shot | One Take, One Line, One Sound | Which Take. A Start Already Inside The Expression. An End Before The Performer Breaks. A Length That Fits The Phrase Of The Sound And Lets The Line Be Read Twice. |
| Set-Up, Then A Cut To A Reaction | The Line Poses The Situation Over The First Shot, Then A Hard Cut Shows The Reaction | The Silent Beat Before The Cut. The Cut Frame Against The Sound. Whether The Line Stays, Changes, Or Leaves. Matched Loudness And Matched Framing Across The Two Clips. |
| A Two-Line Contrast | Two States Set Against Each Other, Such As What Was Said And What Was Meant | The Same Text Position For Both Lines So Only The Words Change. How Long The Second Line Holds. A Change In The Sound At The Switch. |
| A Numbered List Across Locations | Each Item Is A New Place, Pose, Or Outfit Under A Numbered Line | One Text Position And Style Throughout. The Performer At The Same Scale And Screen Position In Every Shot So Each Cut Pops. Cuts On The Beat. The Strongest Item Or The Twist Placed Last. |

## On-Screen Text

The Line Should Look Typed In A Platform's Own Text Tool. That Look Says A Person Made This On A Phone. A Designed Lower Third On A Meme Reel Reads As An Advertisement And The Joke Dies.

Build The Line With The [Title Helper](../TITLES.md). `--style box` Gives The Familiar Rounded Plate Behind Bold Text. A White Plate With Dark Ink Or A Dark Plate With White Ink Both Read As Native. `--style plain` Gives Outlined Text With No Plate.

```text
python scripts/titles.py --text-file line.txt --style box --ink "#111111" --plate-color "#FFFFFF" --position center --size 64 --out line.png
```

- Render The Line Centered On A Canvas-Sized PNG, Then Raise Or Lower It With The Overlay's `y`. The Upper Middle Of The Frame Is The Usual Home. Keep It Off The Face, Out Of The Lowest Part Of The Frame, And Away From The Platform's Own Buttons And Text.
- Size It To Be Read At Phone Size In One Glance. Judge A Still Scaled Down To The Width Of A Phone. Two Or Three Short Lines Read Faster Than One Long Line. Fix The Line Breaks In The Text File So The Punch Word Ends A Line.
- Start The Overlay At Zero. The Line Is On Screen In The First Frame Because The First Second, And The Cover Frame, Decide Whether Anyone Stays. A Static Line Is Correct Here. Native Text Does Not Animate In.
- Keep The Owner's Wording And Capitalization Exactly As Supplied. The Capitalization Used In These Guides Is Not A Rule For On-Screen Lines. Inspect Any Emoji At Delivery Size, Since They Depend On The Fonts Of The Machine.
- One Line Carries The Joke. If It Needs A Second Line To Explain It, The Premise Is Not Yet Specific Enough. Take That Back To The Owner Instead Of Adding Text.

## Sound Is Half The Joke

The Sound Sets The Feeling That The Picture Plays Against. The Same Deadpan Face Is Tragic Under One Track And Smug Under Another.

- **Rights First.** Bake A Track Into The Project Only When The Owner Has The Right To Use It In An Exported File. When The Owner Plans To Add A Platform Sound In The App At Posting, Cut To The Timings They Give You And Leave That Track Out Of The Project.
- **Cut To The Sound.** Place The Cut, The Line Change, Or The Reveal On The Beat Or The Word Of The Track That The Joke Depends On. A Cut That Lands A Frame Or Two Late Feels Late.
- **The Silent Beat Before A Cut.** A Short Held Stillness Before The Reaction Is What Makes The Cut Land. Split The Set-Up Shot And Set `gain` To 0 On The Held Part, Or End The Music Entry Before The Cut And Start A Second Entry At The Cut With Its `in` Advanced To Match. Start With A Few Frames And Lengthen It While The Pause Still Feels Like Timing.
- **Match Loudness.** A Reaction Clip Is Often Far Louder Or Quieter Than The Set-Up. Measure Both With `python scripts/speech.py levels` And Set `gain` So The Cut Changes The Content, Not The Volume. Gain Is Linear, So Halving It Lowers The Level By About Six Decibels. Leave A Jump In Only When The Jump Is The Joke.
- **Source Sound.** Muting The Room Under A Track Is A Style Choice To State In The Brief. Any Spoken Line Stays As Recorded.
- **Accents.** A Cue From The [Cue Bank](../assets/cue-bank/README.md), Such As `rubber-stop` Or `low-drop`, Can Mark A Visible Event. One Is Usually Enough.

## Handheld Feel Versus A Locked-Off Shot

A Centered Subject In A Frame That Never Moves Reads As Staged. A Slight Handheld Drift Reads As A Friend Filming. The Text Stays Fixed While The Picture Moves, Which Is Also How Native Text Behaves.

Prefer Motion That Was Really Filmed, And Ask For Handheld Takes When A Reshoot Is Possible. To Add Gentle Motion To A Locked-Off Take, Use [Camera Transfer](../CAMERA.md). Measure The Sway Of A Handheld Clip The Owner Shot And Apply It At Reduced Strength.

```text
python scripts/camera_transfer.py analyze handheld.mp4 locked.mp4 motion.json --strength 0.4 --timing hold --edge-mode cover
python scripts/camera_transfer.py review motion.json
```

- Use `--timing hold` With A Reference At Least As Long As The Take, So The Sway Keeps Its Natural Speed. `--edge-mode cover` Enlarges The Picture Just Enough To Hide The Edges, So Confirm The Face Is Still Framed Well.
- The Moved Clip Is A New Video File. It Is Rendered Only After The Owner Has Reviewed The Motion On The Review Page And Approved It. Until Then The Timeline Keeps The Locked-Off Take.
- For A Change Without Drift, Split The Shot At The Reaction And Set `zoom` A Little Above 1 On The Second Part. A Small Punch-In At The Right Moment Breaks A Dead Frame.
- Gentle Means The Viewer Never Notices The Camera. If The Motion Can Be Seen As An Effect, Lower The Strength.

## Choosing The Committed Take

The Joke Lives In The Performance. Choose The Take Where The Performer Commits Completely.

- Look At The Frame Under The Punchline First. The Expression Holds, There Is No Smirk, And The Eyes Do Not Flick To The Phone To Check The Recording.
- Then Check The Edges. The Take Starts Already In Character And Ends Before The Performer Breaks.
- A Small Reaction Played With Full Commitment Is Usually Funnier Than A Big One Played For The Camera.
- For Silent Takes, Compare Stills From The Peak Moment Of Each Take. `python scripts/takes.py` Helps Only Where Speech Repeats.
- When Two Takes Are Close, Name The Runner-Up For The Owner. It Is Their Face.

## Reaction And Meme Clips

Use Only Clips The Owner Filmed, Licensed, Or Has Permission To Use. A Famous Film Or Television Reaction Belongs To Someone, And Popularity Is Not Permission. Work From Files The Owner Supplies. The Kit Does Not Fetch Other People's Posts.

- A Reaction The Owner Films Is Often Funnier, Fits The Account, And Raises No Question.
- A Friend Or Colleague Can React On Camera With Their Agreement.
- A Licensed Clip Works When Its Terms Cover This Use. Record The Source And Terms In The [Asset Library](../../asset-library/SKILL.md).
- A Remix Or Template Feature Inside A Platform Is Something The Owner Applies There, In Their Own Account.
- When The Idea Depends On A Clip The Owner Cannot Clear, List It As An Open Item In The [Brief File](../BRIEF.md) And Propose A Self-Filmed Substitute.

## The Quality Bar

- A Stranger From The Intended Group Gets The Joke On The First Watch With Sound, And Still Gets The Premise Without It.
- The Whole Line Is Readable At Phone Size From The First Frame, With No Word Under A Platform Control.
- The Cut Lands On The Sound To The Frame.
- There Are No Idle Frames At The Head Or Tail, And The Loop Shows No Reset.
- Loudness Is Even Across The Cut Unless The Jump Is The Joke.
- Every Second Is Set-Up, Beat, Or Payoff.
- Nothing In It Lacks Rights Or Permission.

The Owner Reviews The Saved Project In The Editor Before Any Video File Is Created, Including A Test Or Preview Export. Check Before That With Frames From `still`, The Decode From `check`, And Playback In `review`.
