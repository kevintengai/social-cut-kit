# Find Ideas Worth Scripting

Use This Guide When The Creator Asks What To Make Next, Wants Hooks, Or Brings A Topic Without An Angle. The Result Is A Few Developed Ideas For The Creator To Choose Between And A Backlog Line For Each Of The Rest. The Examples Continue With The Practice Library From [The Library Guide](LIBRARY.md).

## Start From What Is Saved

Read These Before Suggesting Anything.

```sh
python scripts/video_log.py --library "Practice Library" backlog list
python scripts/video_log.py --library "Practice Library" finding list
python scripts/video_log.py --library "Practice Library" index
```

- The Backlog Holds Ideas Already Judged Worth Keeping.
- The Findings Say What Has Been Measured For This Audience, And Which Hypotheses Still Need A Video.
- The Index Shows The Best And Worst Performers. Within One Format, Take The Two Strongest And The Two Weakest By Watching At 10 Seconds And By Average Watch Share. Note How Each One Opened.

## Gather Fresh Material

| Source | What To Collect |
| --- | --- |
| What The Creator Recently Built, Learned, Or Lived Through | Ask For Specifics: A Number, A Mistake, A Before And An After, Something That Can Be Filmed. |
| Dated News In Their Field | Go To The Primary Source: The Announcement, Release Note, Filing, Paper, Or The Person's Own Post. Keep Its Date And Its Link. |
| Viewer Questions | Comments, Messages, And Replies, Quoted Exactly. A Question Asked Three Times Outranks A Clever One Asked Once. |
| The Library's Best And Worst Performers | What To Repeat, What To Stop, And Which Open Hypothesis A New Video Could Settle. |

Mark Any Premise You Could Not Confirm At Its Source As Unverified. That Includes A Summary Of News Whose Original Could Not Be Opened, A Statistic Without A Traceable Origin, And Anything Recalled From Memory. The Mark Stays With The Idea Through The List, The Backlog, And The Script. An Unverified Premise Is Never Presented As Fact.

## Go Wide Before Judging

Judging While Listing Narrows The List To What Already Feels Safe. Separate The Two Steps.

1. Hand The Raw Material To A Separate Agent And Ask It To Brainstorm From That Material Alone. Give It The Material, The Audience, And The Platform. Withhold The Favorites, The Findings, And The Tests Below.
2. Ask For Twenty To Thirty Distinct Premises, One Sentence Each, Each Naming The Item It Came From.
3. Merge Duplicates And Keep The Source Of Each.

With No Separate Agent Available, Write The Whole List In One Pass Before Scoring Any Line, And Say That The Wide Pass Was Not Independent.

## Judge Against The Goal

Name The Video's Goal: Reach, Follows, Saves, Or Shares. When The Creator Gives None, Assume Reach And Say So.

| Goal | The Idea Must | Starting Assumption, Until A Finding Says Otherwise |
| --- | --- | --- |
| Reach | Make Sense To A Stranger In The First Sentence | Reach Comes From Viewers Who Do Not Follow The Creator. |
| Follows | Promise More Of The Same | A Viewer Follows When The Video Is Clearly One Of A Kind They Want Again. |
| Saves | Be Worth Returning To | Steps, Settings, And Checklists Are Kept. |
| Shares | Say Something The Viewer Wants To Say To One Person | The Sender Has Someone In Mind. |

Put Every Candidate Through Three Tests.

1. Who Outside The Niche Has A Reason To Care? Name The Person And The Reason In One Line. Everyone Is Not An Answer.
2. What Proof Does The Creator Have, Or Can Capture? A Recording, A Screen State, A Number With Its Source, An Object On Camera. If It Cannot Be Captured Soon, The Idea Waits In The Backlog.
3. Does The Opening Surprise? State The Expectation It Breaks. If The First Sentence Is What The Viewer Would Have Guessed, It Is Not An Opening Yet.

Mark Each Test As Pass, Weak, Or Fail. Drop Any Idea With A Fail. Rank The Rest By The Goal.

## Develop The Strongest Few

Develop About Three. For Each One Give The Creator:

- A Working Title And The One Idea In A Sentence.
- The First Two Sentences. The First One Finishes Within Three Seconds At The Creator's Pace, Which Is About Nine Words At Three Words Per Second. The Second Answers The First Or Raises Its Stakes.
- The Proof That Will Appear On Screen, And Whether It Exists Or Must Be Captured.
- The Finding It Relies On, Or The Open Hypothesis It Tests, By ID. Say None Yet When There Is None.
- The Past Videos It Resembles, With Title, Date, And The Number That Matters.
- Any Premise Still Marked Unverified.

Two Versions Whose Main Difference Is The Opening Count As A Single Test Pair, Not Two Ideas. Present Them As A Pair, Name The One Thing That Differs, And Plan Them With The Opening Test Rules In [Read Analytics](INSIGHTS.md).

## Save The Rest

Save Every Remaining Idea That Passed As One Line. Add `--tests` When The Idea Would Test A Hypothesis. Mark A Line Done Once It Becomes A Script.

```sh
python scripts/video_log.py --library "Practice Library" backlog add "What One Unanswered Call Costs A Repair Shop" --tests F01
python scripts/video_log.py --library "Practice Library" backlog add "Unverified: A Parts Supplier Is Said To Be Changing Its Returns Window"
python scripts/video_log.py --library "Practice Library" backlog list
```

## Hand Over

Give The Creator The Goal, Stated Or Assumed. Then The Developed Ideas, Strongest First, Each In The Shape Above. Then The Count Of Lines Saved To The Backlog. Once The Creator Chooses, Write The Script With [The Skill Guide](SKILL.md).
