# Brief And Revisions

An Edit Goes Wrong More Often From A Lost Instruction Than From A Bad Cut. This Guide Covers What To Ask Before Cutting, How To Hold The Brief Across Sessions, And How To Apply Corrections Without Undoing Accepted Work.

## With No Brief, Ask Once

Inspect The Footage First With `probe`, `analyze`, And A Transcript. Read The User's Saved Defaults, Which `defaults` Prints. Then Ask Once, In One Message, Only For What The Footage Cannot Tell You. Give A Recommended Answer With Each Question So The Owner Can Reply With A Single Yes.

| Ask | Why The Footage Cannot Answer | A Recommendation To Offer |
| --- | --- | --- |
| Where Will It Be Posted? | The Destination Sets The Canvas, The Length Limit, And The Edges To Keep Clear. | The Canvas That Matches How The Footage Was Shot |
| Roughly How Long? | The Footage Shows What Exists, Not How Much To Keep. | The Shortest Length That Keeps The Whole Argument, Stated In Seconds |
| Music? | Taste And Rights Are The Owner's. | No Music, Unless They Name A Track They Have The Right To Use |
| Effects Or A Hook Headline? | Some Owners Want A Plain Cut. | A Hook Headline Drawn From Their Strongest Line And No Other Effects |
| An Editable Project In A Particular Editor? | The Editor Decides The Hand-Off Format. | The Kit's Browser Editor, With [Resolve](RESOLVE.md) Or An OTIO And SRT Hand-Off On Request |
| Recordings Of Your Own Product? | A Claim About A Result Needs The Result On Screen. | A Capture For Each Claim You Found In The Transcript, Listed By Its Line |

Anything The Saved Defaults Already Answer Is Not Asked Again. If Some Answers Do Not Arrive, Continue On The Recommendations You Stated And Mark Them As Assumptions In The Brief File. Do Not Return With The Same Questions Later.

## Staged Scope

When The Owner Sets Stages, Do Exactly The Stage Requested And Stop.

- **Restate The Brief.** Give It Back In Your Own Words, In A Few Lines. Include What This Stage Will Deliver And What It Will Leave Untouched. Then Wait For Confirmation.
- **Wait For Uploads.** Do Not Begin With Partial Footage Or Placeholders. List What Has Arrived, With Each File's Length From `probe`, And What Is Still Missing.
- **Cut Dialogue Only.** A Dialogue Pass Contains Shots With Handles And Nothing Else. No Captions, Music, Cues, Zooms, Color Changes, Or Titles. Extra Layers Make The Review Harder, Because The Owner Can No Longer Tell What They Are Being Asked To Judge.

Close Each Stage By Saying What Was Done And What Comes Next, Then Wait.

## The Active Brief File

Keep A Plain Text File Named `active-brief.md` Beside The Timeline. It Lists The Newest Version Asked For And All Corrections Still Open, And Keeps Each There Until It Is Verified. A Session Ends And Its Memory Goes With It. The File Stays. Read It At The Start Of Every Session And Again Before Every Hand-Off.

```text
Request
  Vertical 1080 By 1920, About 40 Seconds, Talking Head With One Screen Insert.
  No Music. Hook Headline Approved As "Stop Quoting By The Hour".
Sources
  A-Cam.mp4, 6 Minutes 12 Seconds, The Main Take.
  Invoice-Screen.mp4, The Owner's Own Capture.
Corrections
  C4  Open      "At 0:14 The Cut Feels Tight." Version 3 At 14.0 Is A-Cam At 221.6.
  C3  Verified  "Make The Logo Smaller." Width 420 To 300. Checked On A Still At 9.2.
Rejected
  The Whoosh Under The Logo. "Too Loud And Too Much."
Open Items
  No Real Image Yet For "The Signed Contract" At 22.4 To 24.0.
Versions
  Version 4  timeline.json     Current. Not Yet Reviewed.
  Version 3  timeline-v3.json  Reviewed By The Owner.
```

- Record Each Correction In The Owner's Own Words, With The Timestamp They Quoted And The Version They Watched.
- A Correction Moves From Open To Changed To Verified. Verified Means You Reopened The Saved Project And Saw The Fix In Place On A Still, In `check`, Or In `review`. Editing The JSON Is Not Verification.
- A Correction Leaves The List Only When It Is Verified. Before Every Hand-Off, Recheck The Verified Ones As Well. A Later Change Can Undo An Earlier Fix. A Retimed Shot Moves Every Overlay After It.

## Newer Instructions And Accepted Edits

- A Newer Instruction Replaces An Older One Of The Same Kind. The Same Kind Means The Same Target And The Same Property, Such As The Hook Wording, The Caption Color, The Music Track, The Length, Or The Take Used For One Line. Keep The Older One In The File, Marked As Replaced.
- Unrelated Accepted Edits Stay. A New Note About Captions Does Not Reopen Cuts The Owner Already Accepted. Make The Smallest Change That Satisfies The Instruction, And Leave Everything It Did Not Mention As It Was.
- When A New Instruction Cannot Be Met Without Changing Accepted Work, Say What Would Have To Give And Ask, With A Recommendation. A Request For A Shorter Video That Can Only Be Met By Removing An Approved Section Is The Usual Case.
- When It Is Unclear Whether A Note Applies To One Spot Or To The Whole Video, Apply It At The Spot And Ask About The Rest.
- A Preference The Owner Wants Kept For Future Videos Also Goes Into Their Saved Defaults.
- Current Instructions And Verified Corrections Rank Above The Style Guides And Above Older Notes.

## Map A Quoted Timestamp Back To The Source

A Timestamp From The Owner Belongs To The Version They Watched, Which May No Longer Be The Current Timeline.

1. Identify The Version They Watched. Ask When It Is Not Certain.
2. Open That Version's Timeline. Walk Its Shots In Order, Adding Each Shot's Length, Until You Reach The Shot That Contains The Quoted Time. A Shot's Length Is Its Source Range With Handles, Divided By Its `speed`.
3. Convert To Source Time. Take The Shot's `in` Minus Its `lead`, And Add The Time Elapsed Inside The Shot Multiplied By Its `speed`.
4. Find That Source Moment In The Current Timeline And Make The Change There.
5. Record Both Positions In The Brief File, And Quote Both When You Report The Fix.

Quoted Times Are Approximate. A Player Shows Whole Seconds And People Round. Look About A Second Either Side And Identify The Moment By Its Content, Such As The Word Being Spoken. When Two Candidates Fit, Name The One You Chose.

## Rejected Stays Rejected

- Record Every Rejected Take, Visual, Sound, Font, Color, Effect, Or Wording In The Brief File With The Owner's Reason.
- A Rejected Item Does Not Return In A Later Version Or A Later Section Unless The Owner Asks For It.
- Scope The Rejection To What Was Rejected. A Whoosh That Was Too Loud Is A Note About That Sound And Its Level. It Is Not A Ban On Sound.
- Check The Rejected List Before Adding Any Asset. Take Extra Care When Rebuilding From An Older Version, Because Older Timelines Still Contain The Rejected Items.

## Originals And Earlier Deliverables

- Source Files Are Never Modified, Overwritten, Renamed, Or Moved. Every Change Lives In The Timeline.
- Before Changing A Version The Owner Has Seen, Copy It To A Numbered Snapshot In The Same Folder, Such As `timeline-v3.json`. The Same Folder Keeps Its Relative Asset Paths Working, And The Snapshot Is What A Later Quoted Timestamp Will Refer To.
- Earlier Exports And Earlier Project Files Stay Where They Are. Do Not Delete Or Overwrite Them To Tidy A Folder. The Kit's Export And Sidecar Commands Refuse To Overwrite An Existing File. Treat The Timeline With The Same Care.

## Hand-Off

- Leave One Clearly Named Current File. `timeline.json` Is Always The Current Project And Numbered Snapshots Are History. When The Owner Has Their Own Naming Scheme, Use It. They Should Never Have To Guess Which File To Open.
- Give A Short Change Summary. State The Path Of The Current File, What Changed Since The Version They Last Saw, What Was Not Done And Why, The Open Items, And Which Checks Ran.
- The Hand-Off Is The Saved, Editable Project. The Owner Personally Reviews It In The Editor Before Any Video File Is Created, Including A Test Or Preview Export. Agent Checks Do Not Replace That Review.
- Approval Covers The Version That Was Reviewed. After Approval, Export To A New, Clearly Versioned Filename. A Later Change Needs A New Review.
