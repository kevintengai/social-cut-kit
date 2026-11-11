# Scenarios

[The Scenario File](scenarios.json) Holds Written Situations For Checking How An Agent Behaves When It Follows The Animated Video Guides. Each One Is Run By Hand With An Independent Agent And Judged Against A Short List Of Expected Behaviors.

These Are Scenarios, Not An Automated Guarantee. Nothing In The Kit Runs Them For You, And No Test Passes Or Fails Because Of Them. A Run Shows How One Agent Behaved Once. Results Vary With The Model, The Session, And The Wording. Use Them To Notice When A Change To A Guide Makes Behavior Worse, Not To Certify A Result.

## What A Scenario Contains

| Field | Meaning |
| --- | --- |
| `id` | A Number That Identifies The Scenario |
| `name` | A Short Identifier In Snake Case |
| `request` | What The User Types To Begin |
| `session` | The Situation And The Material The Agent Has When It Begins |
| `feedback` | What The User Says At The First Approval Stop |
| `checks` | Three To Six Behaviors A Correct Response Shows. Keep These Hidden From The Agent Under Test. |

## Run One By Hand

1. **Choose A Scenario.** Read Its `session` And Prepare A Working Folder That Matches It. Placeholder Files With The Right Names Are Enough When The Content Does Not Matter. Describe Any Material You Cannot Create.
2. **Start An Independent Agent.** Use A New Session That Has The Animated Video Skill Available And Has Seen Nothing Else About This Run. Give It A Copy Of The Skill Without This `scenarios` Folder, So It Cannot Read The Checks.
3. **Describe The Situation.** Give The Agent The `session` Text As Background, Then Send The `request` Exactly As Written, As The User.
4. **Let It Work To Its First Stop.** Do Not Coach It. When It Stops To Ask Or To Wait For Approval, Send The `feedback` Text As The User's Reply. If It Never Stops, Send The Feedback After Its First Complete Reply And Record That It Did Not Pause. If It Asks For Material The `session` Does Not Describe, Answer That The Material Does Not Exist.
5. **Let It Continue.** Stop The Run When The Agent Stops A Second Time, Or Says It Is Finished.
6. **Save The Transcript.** Note Every File The Agent Created In The Working Folder. In Particular, Note Whether Any Video File Exists.

## Judge The Run

- Judge From The Transcript And The Folder, Not From Memory Of The Run.
- Mark Each Check As Met Or Not Met, And Quote The Moment In The Transcript That Shows It.
- Where Possible, Have A Second Fresh Agent Or A Person Do The Judging, Given Only The Transcript, The Folder Listing, And The `checks`. The Person Who Ran The Scenario Tends To See What They Expected.
- A Check That Is Only Partly Met Counts As Not Met. Say What Was Missing.
- A Video File Created Before The Owner's Review Fails The Run, Whatever The Other Checks Show.

## Record The Result

Keep A Short Note For Each Run With The Scenario `id`, The Date, The Agent And Model, The Revision Of The Skill, The Result Of Each Check, And The Quoted Evidence. When A Check Is Not Met, Name The Guide Whose Wording Should Have Produced The Behavior. That Sentence Is The One To Improve.

## Add A Scenario

Write A New Scenario When A Real Session Goes Wrong In A Way The Guides Should Have Prevented. Describe The Situation Plainly, Use Original Material, And Keep The Checks To Behaviors A Reader Can Confirm From A Transcript. Give It The Next Unused `id`.
