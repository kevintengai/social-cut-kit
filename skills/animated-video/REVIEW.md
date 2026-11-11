# Review

Judge The Film Without Watching Playback. An Agent Sees Frames, Not Motion, And Hears Nothing. This Guide Covers What An Agent Can Check From Frames And Numbers, How To Use Independent Judges, And What Happens At The Export Gate. The Owner's Own Viewing In Remotion Studio Is A Separate Review That None Of This Replaces. [Review Tools](REVIEW-TOOLS.md) Has The Exact Usage Of `tools/stills.cjs` For Stills, Boards, And Frame Strips, `tools/motion.cjs` For Measuring Motion, `tools/events.cjs` For Checking Events, `tools/audio.cjs` For Measuring The Sound Mix, And `tools/export-check.cjs` For Checking A Finished Export. All Of Them Read `storyboard.timed.json`, The One Storyboard That Is Reviewed And Exported.

## Judge Motion From Strips

A Single Still Cannot Show Whether A Move Is Smooth Or Broken. Check Motion From Strips Of Consecutive Frames.

- **Dense Strips Around Events.** Take Every Frame Across An Event, From Just Before It Starts To Just After It Settles. Read The Spacing Between Positions. Even Spacing Is Linear And Mechanical. Spacing That Tightens Is A Deceleration. One Gap Larger Than Its Neighbors Is A Pop.
- **Sparse Strips Across The Film.** Take A Frame Every Half Second Or So. Read The Rhythm Of Change. Long Runs Of Near-Identical Frames Show Where The Film Stalls.
- **Measurement.** Use The Motion Measurement To Find Stretches Of Very Low Change And Sudden Spikes, Then Look At Those Frames.
- **Sound.** Check Sound From Its Numbers. Compare The Frame Of Each Cue With The Frame Of The Event It Marks. Measure The Mix With `tools/audio.cjs`, And Read Which Cues Sit On Key Spoken Words And How Far Under The Voice Each One Is.

## What To Look For

- **The Voice Explains While The Picture Only Drifts.** Map Each Spoken Line To Its Frame Range. Compare The First And Last Frame Of The Range. If They Differ Only By A Slow Push, A Float, Or Ambient Motion, The Picture Is Not Explaining. Give The Line An Event, Or Cut The Line.
- **Every Beat Needs An Event.** For Each Line Of The Beat Sheet, Find The Frame Where Its Event Starts And The Frame Where It Completes. An Event Too Subtle To See In A Strip At Phone Size Does Not Count.
- **Events Land On Their Words.** An Event Arrives On, Or A Few Frames Before, The Word That Names It. Late Reads As A Mistake.
- **Effects Are Punctuation.** A Flash, A Shake, A Burst, Or A Whip Belongs On A Beat That Needs Emphasis. For Each Effect, Name The Beat It Punctuates. If It Has None, Remove It. An Effect In Every Shot Stops Meaning Anything.
- **Results Hold.** After An Event Completes, Its Result Stays Long Enough To Register Before The Next One Begins.
- **Text Can Be Read.** Text Stands Still While It Is Read, Is Large Enough At Phone Size, Has Contrast, And Stays Clear Of The Platform's Own Buttons And Text.
- **Cuts Are Continuous.** Positions, Scale, Colors, And Direction Of Travel Agree Across Each Cut. Each Color Keeps Its Meaning.
- **First And Last Frames.** The First Frame Gives A Reason To Watch. The Last Frame Holds The Conclusion.

## Screening Checks

- **Flicker.** In A Hold, Where Nothing Should Change, Compare Consecutive Frames. Any Difference Is Flicker. Common Causes Are Texture That Swims, Thin Lines That Shimmer, Draw Order That Flips, And Random Values Without A Seed. In The Motion Measurement, Flicker Shows As Spikes Inside A Hold Or As Change That Alternates High And Low. A Deliberate Boil Is Stepped And Regular.
- **Two Renders Of The Same Moment.** Render The Same Frame Twice, And Once More As Part Of A Strip. The Results Must Be Identical. A Difference Means A Frame Depends On Something Other Than Its Frame Number, Such As Unseeded Randomness, The Clock, State Carried Over From Earlier Frames, Or A Font Or Image That Had Not Finished Loading. Fix The Cause. Until Renders Repeat Exactly, The Stills You Reviewed Are Not The Frames That Will Be Exported.

## Independent Judges

The Builder Knows What Was Intended And Sees It Whether Or Not It Is There. Use Fresh Agents As Judges. Give Each One Only The Brief, The Approved Beat Sheet, The Style Sheet, And The Frames. Withhold The Build History And Your Own Opinion.

| Judge | Looks At | Asks |
| --- | --- | --- |
| Motion | Dense Strips And The Motion Measurement | Is Each Move Readable, Eased, And Weighted? Are There Pops, Flicker, Or Missing Holds? |
| Story | Ordered Stills With The Script | Does Each Picture Carry Its Claim? Do The Order, The Pace, The Opening, And The Ending Work? |
| Design | Stills At Delivery Size And At Phone Size | Do Hierarchy, Color Meaning, Type, And Legibility Hold, And Do They Match The Chosen Style Frame? |

- Ask For Issues, Not Scores. Each Issue States Where It Is, What Is Observed, Why It Hurts The Brief, And A Suggested Fix. Scores Drift Between Judges And Invite Argument About Numbers.
- Track Issues In One List. Record Where, What, How Serious, And A Status Of Open, Fixed, Verified, Or Declined With A Reason. Rank By Consequence. An Issue That Blocks Understanding Comes Before One That Hurts Polish.
- Verify Each Fix With New Frames And A Judge Who Has Not Seen The Earlier Round.
- Stop When A Round Gains Little. When A Round Raises Only Polish, Or Reverses What An Earlier Judge Preferred, Further Rounds Are Trading Taste. Take The Film To The Owner And Report What Remains Open.
- Judges Advise. They Do Not Approve. Only The Owner Approves.

## Real Footage Against Its Words

For Every Use Of Real Footage Or A Photo, State The Claim Made By The Words Over It, Then Check That The Image Shows Exactly That. It Must Be The Right Person, Place, Product, Version, And Date. A Similar Thing Presented As The Thing Is A False Statement, However Good It Looks. Label Illustrative Footage As Illustrative, Or Replace It. Confirm The Source And The Rights For Each Item And Keep The List For The Report.

## The Silent Viewing Test

1. Render Ordered Stills With Captions And Sound Removed. Take One Still For Each Completed Event And One From The Middle Of Any Long Move. Leave Designed Labels In Place. They Are Part Of The Picture.
2. Give The Stills To A Fresh Judge Who Has Never Seen The Script, The Brief, Or The Beat Sheet.
3. Ask The Judge To Describe What Happens, In Order, And What It Explains Or What Story It Tells.
4. Compare That Account With The Script, Claim By Claim.
5. Send Every Claim The Judge Could Not Recover Back To Its Shot. That Picture Is Not Carrying Its Claim. Redesign The Picture Through The Search In [Directing](DIRECTING.md). Adding A Label Or A Caption Hides The Problem Without Fixing It.
6. Treat A Claim Recovered Wrongly As More Serious Than A Missing One. The Picture Is Saying Something Else.

Use A New Judge For Every Run. A Judge Who Has Read The Script Cannot Read The Pictures Without It.

## When The Owner Rejects A Whole Cut

A Whole-Cut Rejection Means The Pictures Are Wrong. Easing, Color, And Transitions Are Not The Fault, And Adjusting Them On The Same Pictures Returns The Same Film.

- Record What Was Wrong In The Owner's Words, And Ask Which Parts, If Any, Should Stay.
- Keep The Script And The Voice If They Were Approved.
- Return To Finding Pictures In [Directing](DIRECTING.md). Show New Rendered Directions For The Key Beats And Wait For A Choice Before Rebuilding.
- Archive The Rejected Cut. Do Not Delete It.

## Final Checks And The Export Gate

Before Handing Over, Confirm The Following On `storyboard.timed.json`.

- Every Scene Renders At The First Frame, The Last Frame, And Each Scene Boundary.
- The Frame Rate, Size, And Length Match The Brief.
- The Timing Follows The Final Voice Recording. A Storyboard Still On Stand-In Timing Is Not Ready, And Both Export Routes Refuse It. A Film With No Narration Declares That In Its Storyboard, With The Owner's Agreement.
- Caption Text Matches The Voice. Names And Figures Are Spelled And Stated Correctly.
- `tools/events.cjs` Reports That The Storyboard Carries All Its Event Sounds.
- `tools/audio.cjs` Has Measured The Mix With The Real Recording Attached. Report Its Integrated Loudness, Loudness Range, And True Peak Against The Defaults Of About -14 LUFS And -1.5 dBTP, And Every Cue It Lists To Check. These Are Reported, Never Applied Automatically.
- Every Blocking Issue Is Closed, And The Repeat-Render Check Passes.
- Every Outside Asset Has A Recorded Source And Rights.

Then Prepare A Remotion Project From The Timed Storyboard, Read Its Warnings, And Hand The Editable Project To The Owner. The Owner Personally Reviews It In Remotion Studio Before Any Video File Is Created. That Includes Test And Preview Exports. Motion Studio Is The Owner's Review Route Only When Node.js Packages Cannot Be Installed. Agent Checks And Judges Do Not Replace That Review. Before Approval, Use Stills, Boards, Strips, Measurements, And Playback Inside The Editable Project. Wait For Explicit Approval Of The Current Cut. Any Edit After Approval Needs A New Review.

After Approval, Follow The Export Steps In The [Skill Guide](SKILL.md) And Write To A New File. Then Run `tools/export-check.cjs` On That File With The Timed Storyboard. It Checks The File's Size, Frame Size, Frame Rate, Length, And Sound, And Measures Its Loudness. Report What It Prints. When It Fails, Do Not Present The File As Finished.

## What To Report

- **Path.** The Current Editable Project And, After An Approved Export, The Video File.
- **Open Issues.** Each Issue Left Unfixed, With The Reason.
- **Skipped Checks.** Each Check Not Run, With The Reason. Include A Silent Viewing Test Or A Judge Round That Could Not Be Run, And A Sound Or Export Check Skipped Because FFmpeg Is Not Installed.
- **Sound Levels.** The Measured Loudness And True Peak Of The Mix And Of The Export, And Any Cue Listed To Check. The Owner Decides Whether To Change A Level.
- **Sourced Images.** Every Image, Clip, Font, And Sound That Was Not Made In The Project, With Its Source And Rights.
- **Anything Synthetic Or Invented.** Generated Images Or Voices, Stand-In Timings, Placeholder Data, Figures Or Quotes Without A Source From The Owner, A Render Of A Product That Does Not Exist, And Any Interface State That Was Redrawn Instead Of Captured. The Owner Decides What To Disclose. Your Part Is Making Sure They Know.
