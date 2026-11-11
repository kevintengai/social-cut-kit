# Review A Posted Video

Use This Guide When The Creator Asks Why A Posted Video Held Or Lost Its Viewers. The Review Ends In A Library Record, An Index Row, Updated Findings, And One Test For The Next Video. It Does Not Change The Video. The Examples Continue With The Practice Library From [The Library Guide](LIBRARY.md).

A Review Of An Unposted Script Or Cut Has No Numbers. Add It With `add --review`, Give Notes Against The Checklist In [The Skill Guide](SKILL.md), And Keep It Out Of The Findings.

## 1. Record Every Number

Capture The Summary Counts, Every Rate Under Its Own Label, The Views By Source, And The Capture Time, As [Read Analytics](INSIGHTS.md) Describes. Record All Of Them, Including The Ones That Seem To Say Nothing Today. A Later Video May Need The Comparison. Leave Out What The Screen Does Not Show.

If The Video Has No Record Yet, Add One First With Its Posting Date, Format, Runtime, First Two Spoken Sentences, And Links To The Project, The Final File, And The Captions.

## 2. Read The Curve

Read The Retention Curve With `scripts/retention.py`, Pass The App's Average Watch Time, Check Any Warning, Save The Report, And Attach It.

```sh
python scripts/retention.py csv assets/practice-retention.csv --reported-average 14.2
python scripts/video_log.py --library "Practice Library" show ready-repair
```

For A Screenshot, Check The Printed Plot Rectangle And Line Color Against The Image Before Trusting A Single Reading. Do Not Describe A Curve By Eye.

## 3. Line Up Every Cliff And Plateau With The Video

For Each Steep Drop And Each Flat Stretch, Find The Words And Pictures Of The Three Seconds Before It Starts And While It Lasts. `lineup` Prints The Spoken Half Of That Table Straight From The Captions File Linked In The Record.

```sh
python scripts/video_log.py --library "Practice Library" lineup ready-repair
```

- Quote Lines And Times From The Captions File. Do Not Quote From Memory, And Do Not Quote The Script As If It Were The Posted Cut.
- Fill The Shown Column From The Posted Video, Its Project, Or Its Timeline.
- When The Record Has No Captions Link, Pass `--captions` With An SRT Or WebVTT File, Or Ask The Creator For One.
- Failing That, Print The Planned Timing With `python scripts/script_desk.py read assets/practice-script.json` And Label Every Quote As Planned, Not As Posted.

This Is The Practice Video With The Last Two Columns Filled In:

| Stretch | Change | Said Just Before And During | Shown | Reading |
| --- | --- | --- | --- | --- |
| Drop, 0 To 2.25 Seconds | -25.5 Points | 0: "Your Repair Was Ready Two Days Ago." | A Finished Phone On A Shelf | The Opening Loss. Compare It With Other Openings In This Format. |
| Drop, 9.75 To 11.5 Seconds | -8 Points | 6: "Forty Jobs Share One List," 8.3: "So A Finished One Hides Between Two Broken Ones." 11: "Here Is The Fix." | One Ready Row Circled | Hypothesis: The Problem Is Stated A Second Time Before Any Fix Appears. |
| Flat, 12.5 To 19.5 Seconds | -4 Points | 8.3: "So A Finished One Hides Between Two Broken Ones." 11: "Here Is The Fix." 12: "Filter The Queue By One Status." 15: "Select Ready Only," 17.3: "And The List Drops To The Jobs That Can Leave Today." | The Menu Opens And The List Shrinks | The Fix And The Demonstration Held The Viewers Who Stayed. |
| Drop, 24.5 To 28 Seconds | -11 Points | 20: "Call Those Three First," 22.3: "And Nobody Waits On A Repair That Is Already Done." 25: "Open The Demo And Try It." | The Call, Then The Filter Control | Viewers Leave Around The Call To Action. Compare The Size With Other Endings. |

A Drop Marks Where To Look. The Reading Column Holds A Hypothesis Until Another Video Agrees.

## 4. Compare With The Same Format

Pick Two To Four Same-Format Videos From The Library And Compare Them At The Same Seconds. Note Where This Video Sits At Three Seconds, At Ten Seconds, And In The Drop Between Them. A Different Format Or A Very Different Runtime Is A Weak Comparison, And The Tool Says When Formats Differ.

```sh
python scripts/video_log.py --library "Practice Library" compare ready-repair three-calls
```

## 5. Write The Library Entry And The Index Row

Record The Snapshot, Attach The Retention Report, And Rebuild The Index. The Commands Are In [The Library Guide](LIBRARY.md). Add A Dated Note With The Single Most Useful Observation.

```sh
python scripts/video_log.py --library "Practice Library" update ready-repair --note "The Second Statement Of The Problem At 6 Seconds Preceded An 8 Point Drop."
python scripts/video_log.py --library "Practice Library" index
```

Check The New Row: Average Watch Share, Watching At 10 Seconds, Non-Follower Share, Follows Per 1,000 Viewers, Plus The Status.

## 6. Update The Findings

Run `finding list` And Go Through Each Hypothesis This Video Bears On.

- Cite The Video As Evidence With `supports` Or `weakens`, And Put The Number In `--note`.
- Change A Status Only When At Least Two Videos Agree. The Tool Refuses Otherwise. One Video Is A Lead.
- Add A New Open Hypothesis For Each Reading In Step 3 That Is Worth Testing.

```sh
python scripts/video_log.py --library "Practice Library" finding add "Stating The Problem Once Before The Fix Loses Fewer Viewers Before Twelve Seconds Than Stating It Twice."
python scripts/video_log.py --library "Practice Library" finding list
```

## 7. Label Opinion

Sort Every Statement In The Review Into One Of Three Kinds And Label It.

| Kind | Rests On | Example |
| --- | --- | --- |
| Measured | A Recorded Number, With Its Capture Time | 57.0 Percent Were Still Watching At 10 Seconds On Day 2. |
| Hypothesis | A Number And A Guess About Its Cause | The Repeated Problem At 6 Seconds May Have Caused The Drop At 9.75. |
| Opinion | Taste Or Experience, Without A Number | Opinion: The Shelf Shot Feels Slow. |

Anything The Numbers Do Not Support Is Opinion And Carries That Word.

## Hand Over

Give The Creator, In This Order:

1. The Numbers, With The Capture Time And Anything Not Captured.
2. The Curve: The Readings, The Drop From Three To Ten Seconds, And The Table From Step 3.
3. Where The Video Sits Against The Same Format.
4. The Findings It Touched And Their Status.
5. Opinion, Labelled.
6. One Change To Test In The Next Video, Saved With `backlog add` And Tied To Its Hypothesis With `--tests`.
