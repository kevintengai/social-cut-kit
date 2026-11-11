# Write A How It Works Script

A How It Works Video Loses Viewers When It Lists Parts. It Holds Them When Each Part Arrives As The Answer To A Problem The Viewer Has Just Felt. This Guide Turns An Explanation Into That Kind Of Story. The Rules In [The Skill Guide](SKILL.md) Still Apply: One Idea, An Opening Inside Three Seconds, A Picture Beside Every Line, And A Source For Every Claim.

## Build A Chain Of Problems

1. Start With The Job The Thing Does For The Viewer, In One Situation They Recognize.
2. Write The Explanation As A Chain. Each Part Answers The Problem The Previous Part Raised, And Raises The Next One.
3. Stop When A Part Raises No New Problem. That Part Is The Payoff.

Here Is A Chain For Noise-Cancelling Headphones.

| The Problem The Viewer Feels | The Part That Answers It | The Problem That Part Raises |
| --- | --- | --- |
| A Jet Engine Drones Through The Whole Flight. | A Microphone On The Outside Of The Ear Cup Hears The Drone. | Hearing It Does Not Remove It. |
| Hearing It Does Not Remove It. | A Chip Builds A Mirror Image Of The Drone. Where The Drone Pushes, The Mirror Image Pulls. | A Mirror Image Is Still Only A Signal. |
| A Mirror Image Is Still Only A Signal. | The Speaker Plays The Mirror Image Along With The Music. Push Meets Pull, And The Drone Mostly Cancels. | The Match Is Never Perfect. |
| The Match Is Never Perfect. | In Many Models, A Second Microphone Inside The Cup Hears What Is Left And Corrects The Mirror Image. | None. The Chain Is Closed. |

A Part That Answers No Problem In The Chain Does Not Belong In This Video. Save It For The Caption Or The Backlog.

## Follow One Example Through Every Stage

Choose One Concrete Case And Stay With It: One Passenger, One Flight, One Engine Drone. Every Stage Acts On That Same Drone. A New Example At Each Stage Makes The Viewer Start Again Each Time. Attach Every Number To The Example, Not To The General Case.

## Write Narration To Be Seen

Write The Picture First, Then The Sentence That Names What Is In It. Each Sentence Should Point At Something On Screen While It Is Spoken: The Outside Microphone, The Drone Drawn As A Wave, The Mirror Image, The Two Meeting. A Sentence With Nothing To Show Is Background. Turn It Into A Picture Or Cut It. Fill The `picture` And `capture` Fields For Every Line. A Diagram Or Animated Insert Is Planned Here And Built With The Animated Video Skill.

## Use One Name Per Thing

Give Each Part One Name And Use It Every Time. If The Outside Microphone Becomes The Sensor And Then The Pickup, The Viewer Counts Three Parts. Say The Plain Name First. Introduce A Technical Term Only When The Viewer Will Need It Again, And Then Keep To It.

## Simplify Without Saying Anything False

A Simplification Leaves Detail Out. It Must Not Put Something False In.

1. For Each Simplified Sentence And Each Analogy, Write The Sentence An Expert Would Say Instead.
2. If The Expert's Version Changes What The Viewer Would Believe Or Do, Reword The Line.
3. If It Only Adds Detail, Keep The Line And Consider Putting The Detail In The Caption.

| Draft Line | What An Expert Would Correct | Line That Stays True |
| --- | --- | --- |
| The Headphones Block The Noise. | The Cancelling Blocks Nothing. It Adds A Second Sound. | The Headphones Play A Mirror Image Of The Noise. |
| It Cancels Every Sound Around You. | Steady Low Sounds Cancel Best. Sudden Sharp Ones Are Hardly Cancelled. | It Cancels A Steady Drone Best. |
| It Reads The Sound And Deletes It. | Nothing Is Deleted. Two Waves Add Up To Less. | Push Meets Pull, And The Drone Mostly Cancels. |

Give An Analogy The Same Test, And Say Where It Stops. Two Evenly Matched Teams In A Tug Of War Explain Why The Drone Goes Quiet. They Do Not Explain Why A Sudden Clap Is Hardly Cancelled, So Do Not Stretch The Analogy That Far. Small Words Such As Mostly, Usually, And About Keep A Short Line True.

Simplified Lines Are Claims. List Each One In `evidence` With Its Source, And Have The Separate Claim Check Read Them As Worded.

## Recap Through Every Part

Before The Call To Action, Pass Once Through The Whole Chain In Order. Name Each Part Once, By The Name Used Before, On The Same Example: The Outside Microphone Hears The Drone, The Chip Builds Its Mirror Image, The Speaker Plays The Mirror Image, And The Inside Microphone Corrects It. Show Every Part In One Frame While It Is Said. If The Recap Reads Well Without A Part, That Part Can Leave The Script.

## When The Runtime Is Too Short, Cut Parts

Do Not Shrink Every Part To Fit. A Part Needs Time To Be Seen: About Six Seconds At Three Words Per Second, One Sentence For The Problem And One For The Answer. A 30-Second Script Holds An Opening, About Three Parts, A Recap, And One Call To Action.

1. Remove A Whole Link, Together With The Problem It Answers.
2. Rejoin The Chain. The Problem Before The Cut Must Lead Straight To The Part After It.
3. Move Limits And Edge Cases To The Caption.
4. Rewrite The Recap So It Passes Through The Parts That Remain.

In The Headphone Chain, The Inside Microphone Is The Link To Cut First. The Story Still Closes When The Drone Cancels.

## Lay It Out For Short Form

| Seconds | Content |
| --- | --- |
| 0 To 3 | The Result Or The Puzzle, In The Viewer's Terms. |
| 3 To 10 | The First Problem And The First Part. |
| The Middle | One Link Of The Chain At A Time, Each With Its Picture. |
| The End | The Recap In One Frame, Then One Short Call To Action. |

Then Run The Check Against The Target Runtime And Read The Script Aloud Against The Checklist.

```sh
python scripts/script_desk.py check assets/practice-script.json --target 30
```
