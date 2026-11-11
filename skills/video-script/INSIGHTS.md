# Read Analytics As Comparable Numbers

An Analytics Screen Shows One Video At One Moment. This Guide Turns That Screen Into Numbers That Can Sit Beside Every Other Video The Creator Has Posted. The Examples Continue With The Practice Library From [The Library Guide](LIBRARY.md).

## Capture The Screens

Ask The Creator For Screenshots Or Exports Of The Video's Analytics, Then Record Four Things And The Moment They Were Read.

1. Summary Counts: Views, Viewers, Average Watch Time, Follows, Likes, Comments, Shares, Saves, And Reposts. Open The Detail View For Exact Counts. When The App Shows Only A Rounded Figure Such As 12.8K, Enter It As Shown.
2. Rates, Each Under The Label The App Gives It, Word For Word. A Renamed Rate Cannot Be Matched To The App Later.
3. The Retention Curve With Its Duration: A CSV Export, Or A Screenshot That Includes The Whole Chart With No Point Selected, Plus The Video's Runtime In Seconds.
4. Views By Source, Such As Feed, Explore, Search, And Profile, As Counts Or Percents.
5. The Snapshot's Date And Time. The Numbers Keep Moving For Days, So A Number Without Its Capture Time Cannot Be Compared.

A Number That Is Not On The Screen Stays Out. It Is Stored As Not Captured. Do Not Work It Out From Another Number And Do Not Carry It Over From An Earlier Snapshot.

Labels And Definitions Change, So Confirm Them Inside The App. Before Recording, Open The App's Own Explanation Of What Counts As A View, Who Counts As A Viewer, Whether Average Watch Time Includes Replays, And What Each Rate Divides By. Write Any Change In The Platform Notes Of The Defaults File With The Date. Do Not Rely On What A Label Meant Last Year, Or On This Guide, For A Definition.

Compare The Creator's Videos With Each Other. A Platform's Relative Labels, Such As Higher Than Usual Or A Comparison With Similar Videos, Rest On A Baseline The Creator Cannot Inspect. Keep Such A Label In The Snapshot's Note If It Is Wanted, And Draw Findings Only From The Creator's Own Library, In The Same Format, At The Same Age.

## Record The Snapshot

```sh
python scripts/video_log.py --library "Practice Library" snapshot ready-repair --captured "2026-11-10 09:30" --views 18100 --viewers 15240 --average-watch 14.0 --follows 44 --shares 81 --saves 97 --rate "Skip Rate" 42.0% --source Feed 66% --source Explore 24% --non-follower-share 89 --note "Day Seven Reading"
```

Every Option Is Listed In [The Library Guide](LIBRARY.md). The Command Prints Which Counts Were Not Captured, So A Missed Number Is Noticed While The Screen Is Still Open.

## Derive The Comparable Numbers

| Number | How | Why It Compares |
| --- | --- | --- |
| Average Watch Share Of Runtime | Average Watch Time Divided By Runtime | A 20-Second Video And A 60-Second Video Can Be Set Side By Side. Replays Can Push It Past 100 Percent. |
| Share Still Watching At 10 Seconds | The Retention Curve Read At Ten Seconds | It Measures The Opening And The Second Sentence Together, Whatever The Runtime. |
| Non-Follower Share Of Views | Non-Follower Views Divided By Views | It Shows How Far The Video Travelled Beyond The Existing Audience. |
| Follows Per 1,000 Viewers | Follows Divided By Viewers, Times 1,000 | It Separates A Video That Earned Followers From One That Only Reached Many People. |

`python scripts/video_log.py --library "Practice Library" index` Computes All Four For Every Video. Derive A Number Only From Values In The Same Snapshot.

## Read The Curve

`scripts/retention.py` Reads A CSV With `seconds` And `retention_pct` Columns, Or A Chart Image. Both Print The Same JSON Report.

```sh
python scripts/retention.py csv assets/practice-retention.csv --reported-average 14.2
python scripts/retention.py image assets/practice-chart.png --seconds 30 --top 100 --bottom 0 --reported-average 14.9
```

| Report Field | Meaning |
| --- | --- |
| `readings` | Percent Still Watching At 1, 2, 3, 5, 10, 15, 20, 30, 45, 60, 90, 120, And 180 Seconds, As Far As The Video Runs. `--at` Replaces The List. |
| `drop_3_to_10_points` | Points Lost Between Three And Ten Seconds. A Positive Number Means Viewers Left. |
| `average_watch_seconds`, `average_watch_share_pct` | Average Watch Time Worked Out From The Area Under The Curve, And Its Share Of Runtime. |
| `reported_average_seconds`, `average_gap_seconds` | The App's Figure From `--reported-average`, And The Area-Based Figure Minus It. |
| `steepest_drops` | Up To Three Stretches Where Viewers Left Fastest, Each With `from`, `to`, `delta_points`, And `points_per_second`. `--count` Changes How Many. |
| `flattest_stretches` | Up To Three Stretches Of At Least One Second Where Almost No One Left. |
| `calibration` | For An Image: The Plot Rectangle, Line Color, And Axis Bounds Used, Whether Each Was Supplied Or Detected, And How The Curve Was Traced. |
| `warnings` | Anything That Lowers Trust In The Reading. Read These First. |
| `samples`, `chart_coverage`, `first_pct`, `last_pct`, `largest_drop`, `largest_lift` | The Original Fields. `--interval` Sets The Window For The Last Two. |

A Drop Is Steep When Viewers Leave Faster Than One And A Half Times The Curve's Typical Rate. A Stretch Is Flat When They Leave At Under Half That Rate. An Empty List Means Nothing Stood Out, Which Is A Steady Slope. On Evenly Spaced Rows, Time Ranges Are Good To About Half A Second, And To About A Second On A Small Screenshot. Widely Or Unevenly Spaced CSV Rows Blur A Range By About One Row Gap.

Add `--output FILE` To Save The Report With Its Curve For `video_log.py attach`. For A CSV Whose Last Row Comes Before The End Of The Video, Pass `--runtime`.

### Pass The App's Average Watch Time

`--reported-average` Takes The Average Watch Time The App Shows, As `14.2` Or `0:14`. The Tool Compares It With The Area Under The Curve And Warns When They Differ By More Than Three Seconds. A Gap That Large Usually Means A Misread: The Wrong Rectangle, The Wrong Axis Bounds, The Wrong Line, Or The Wrong Duration. Replays Counted By The App Can Also Widen The Gap. Change The Limit With `--average-tolerance`.

### Let The Tool Calibrate An Image

Given Only `--seconds`, The Tool Finds The Plot From Its Evenly Spaced Horizontal Gridlines And The Curve From The Dominant Saturated Color Between Them, On Dark And Light Themes. It Prints What It Found:

```text
Detected Plot Rectangle 72 170 599 410 From 5 Gridlines On A Dark Theme And Detected Line Color 64 196 255. Check Each Against The Screenshot. The Top Gridline Is Read As 100 Percent And The Bottom Gridline As 0 Percent. Pass --top And --bottom When The Axis Labels Differ.
```

Check Three Things Against The Screenshot Before Using The Reading.

1. The Rectangle's Top And Bottom Sit On The Highest And Lowest Gridlines, And Its Left And Right Sit On The Ends Of The Curve.
2. The Color Is The Curve's Color.
3. The Top Gridline Is Labelled 100 Percent And The Bottom One 0 Percent. If Not, Pass The Labelled Values With `--top` And `--bottom`.

The Time Axis Runs From The Curve's First Column To Its Last, Since Labels Can Shorten The Gridlines. A Warning Appears When The Axis Was Assumed To Run From 0 To 100, When The Curve Is Clearly Narrower Than The Gridlines, When The Gridline Count Does Not Divide 0 To 100 Evenly, Or When The Curve Does Not Start Near 100 Percent. Passing `--top` And `--bottom` Confirms The Axis And Clears The First Of These. A Thin Marker In The Curve's Color Is Left Out Of The Reading, And A Wide One Stops It.

The Tool Stops With A Message, And Asks For Values By Hand, When It Finds Fewer Than Three Evenly Spaced Gridlines, No Saturated Curve, A Curve That Does Not Span The Plot, A Curve That Leaves The Gridlines, Or More Than One Chart. Cropping The Screenshot To The Chart Often Settles It. A Heavily Compressed Image Can Also Fail.

### Calibrate By Hand

```sh
python scripts/retention.py image assets/practice-chart.png --seconds 30 --plot 72 170 599 410 --color 64 196 255 --top 100 --bottom 0
```

- `--plot` Is Left, Top, Right, Bottom In Image Pixels. Left And Right Are The Columns Where The Curve Starts And Ends. Top And Bottom Are The Rows Of The Axis Values Given To `--top` And `--bottom`. An Image Editor Shows Pixel Positions Under The Pointer.
- `--color` Is The Line's Red, Green, And Blue From A Color Picker. `--tolerance` Widens The Match For A Compressed Image.
- Supply Just One Of The Two And The Tool Finds The Other.
- Review `chart_coverage`. A Value Well Under 1 Means Part Of The Curve Was Not Found.

### Prove The Reader Works Here

```sh
python scripts/retention.py --selftest
```

The Self Test Draws A Dark Chart And A Light Chart In Pure Python, Reads Them Back, And Passes When Every Fixed Second Is Within 1.5 Retention Points And The Area-Based Average Within Half A Second. With FFmpeg Present It Also Saves Each Chart As A PNG And Decodes It.

## Curve Shapes

| Shape | What It Shows | What To Look At |
| --- | --- | --- |
| A Steep Drop | Many Viewers Left In A Short Stretch. | The Words And Pictures Of The Two Or Three Seconds Before It. Viewers Decide Before They Leave. |
| A Flat Stretch | The Viewers Who Remained Kept Watching. | What Was On Screen. It Worked For The People Still There. |
| A Steady Slope | No Single Moment Lost The Audience. | Overall Pace And Interest, Against Other Videos In The Same Format. |
| A Rise | Replays Or Skips Back. Readings Can Pass 100 Percent. | The Moment Viewers Returned To. |

The Drop Between Three And Ten Seconds Reflects The Second Sentence. The Opening Earned The First Three Seconds. What Follows Either Answers It Or Loses The Viewer. Compare `drop_3_to_10_points` Across Videos To Judge Second Sentences.

Every Curve Falls Fastest At The Start, So Judge An Opening Against The Creator's Other Openings, Not Against Zero. A Drop Marks Where To Look. It Does Not Name Its Cause. Treat Each Reading As A Hypothesis Until A Second Video Agrees.

## Run Opening Tests Fairly

1. Change One Thing: The First Sentence, Or The First Frame, Not Both. Keep The Body, The Runtime, And The Ending The Same.
2. Use The Same Caption And The Same Posting Window: The Same Kind Of Day And The Same Part Of The Day.
3. Record Both Videos At Fixed Ages. Choose The Ages Once, Such As One Day, Three Days, And Seven Days, And Keep Them For Every Test.
4. Compare The Numbers An Opening Can Move: The Readings At Three And Ten Seconds And The Drop Between Them. Total Views Depend On Much More Than The Opening.
5. Treat One Win As A Lead Until It Is Repeated. Add The Hypothesis With `finding add`, Cite The Winning Video With `finding evidence`, And Leave The Status Open Until A Second Video Agrees.

```sh
python scripts/video_log.py --library "Practice Library" compare ready-repair three-calls --at 3 10
```
