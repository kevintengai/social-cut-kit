---
name: rsi
description: Run Limited Before-And-After Experiments That Improve How An Agent Works, Through Its Skills, Instructions, Tools, Or Process, While The Model Stays The Same. Use To Test One Proposed Change Against The Current Version On Paired Cases And Finish With Either A Change That Passed Its Test Or A Reasoned Choice To Leave Things As They Are.
---

# RSI

Improve How An Agent Works By Changing Its Skills, Instructions, Tools, Or Working Process While The Underlying Model Stays Fixed. Each Improvement Is A Bounded Before-And-After Experiment. It Ends In One Of Two Results: A Change That Passed Its Test, Or A Reasoned Choice To Leave Things As They Are.

This Skill Supplies A Procedure, A Paired-Trial Helper, And A Record Template. It Does Not Run Tasks For You, Isolate Them, Schedule Them, Or Limit What They Spend. Use The Project's Own Tools For Those And Stay Inside Their Limits. Writing New Instructions, Passing File Validation, Or Producing A Persuasive Write-Up Does Not Show Better Task Performance. Only A Fair Comparison On Real Tasks Does.

## Set The Bounds Before Anything Runs

Write Down Each Bound And Confirm It With The User Before The First Run.

| Bound | What To Record |
| --- | --- |
| Target | The Skill, Instruction File, Tool, Or Process Step Under Test, And Its Current Version. |
| Authorization | What The User Approved: A Diagnosis, A Comparison, Or Adoption. |
| Budget | A Limit On Time, Cost, Or The Number Of Runs. |
| Stopping Rule | The Condition That Ends The Experiment, Whether Or Not The Candidate Is Ahead. |
| Editable Scope | The Files The Candidate May Change. Everything Else Is Read-Only. |
| Comparison Task | The Task And The Cases That Both Versions Attempt. |
| Model And Settings | The Model, Its Version, And Its Settings, Identical For Both Versions. |
| Success Criteria | The Measured Outcome, The Threshold, And The Number Of Cases. |
| Must Not Regress | Behavior That Has To Stay At Least As Good As It Is Now. |
| Adoption | Who May Adopt The Result, And Where. |

- When The User Asked Only For A Review, Do Only A Review. Report The Diagnosis And A Proposed Plan, Then Stop.
- Scope Nobody Stated Never Allows Unattended Runs, Paid Services, Publishing, Changes To Production, Or Edits To Global Instructions. Ask First.
- When A Bound Is Missing, Ask For It, Or Propose A Small Default For The User To Confirm. Do Not Fill It In Silently.
- Prefer One Candidate That Changes One Mechanism, So A Result Can Be Traced To Its Cause.

## Diagnose And Predict

Start From A Repeated Problem Whose Cost You Can Observe.

1. Reuse A Current Finding From [The `reflect` Skill](../reflect/SKILL.md) When Its Evidence Still Applies To The Version Under Test. Otherwise Rebuild The Evidence From Session Records.
2. Compare Failed And Successful Runs Of The Same Procedure. Note What Differed, Including Whether The Skill Was Discovered And Loaded At All. A Skill That Never Loaded Needs A Change To How It Is Found, Not To Its Body.
3. Tell A Skill Or Tool Defect Apart From A Model Limit, Missing Access, An Outage, Or A Changed Requirement. Only A Defect In The Skill, Instruction, Tool, Or Process Is A Target Here.
4. Name The Smallest Change Worth Testing, What Should Get Better, And A Neighboring Case It Might Make Worse. Write This Prediction Down Before Any Run.
5. Keep Failed Ideas And Their Evidence, So They Are Not Retried Without A New Reason.

## Build A Fair Comparison

A Comparison Has Two Arms: The Current Version As The Baseline, And The Candidate.

### Keep The Versions Apart

- Keep The Current Version Intact. Record It And How To Restore It Before Starting. Put The Candidate In A Separate Copy Or Worktree.
- Confirm That Each Arm Really Loads Its Own Version. A Marker Line Or A Reported File Path In Each Run's Log Is Enough.
- Give Both Arms The Same Starting State, Model, Tools, Settings, And Limits.
- Reset The Working Copy After Every Attempt, So Neither Arm Gains From The Other's Work. Start Each Attempt In A Fresh Session That Cannot See The Other Arm's Transcript, Notes, Caches, Or Output Files.

### Split The Cases

Use Separate Cases For Three Jobs.

| Split | Job | Rule |
| --- | --- | --- |
| `develop` | Shape A Change. | Results May Be Read Freely And May Inform Edits. |
| `select` | Choose Between Candidates. | Results Rank Candidates. They Are Not The Reported Result. |
| `final` | Report The Result. | Chosen Before Candidate Results Are Seen, And Run On A Frozen Candidate. |

- Pick The Final Cases Before Seeing Candidate Results. Keep Them And Their Answers Out Of The Optimizing Agent's Context.
- Stop Editing The Candidate Once The Final Comparison Is About To Run.
- Once A Final Case Has Informed An Edit, It Is No Longer A Final Case. Move It To `develop` And Choose An Untouched Replacement.

### Fix The Scoring In Advance

- Define Scoring From The Requested Outcomes Before Any Run.
- Use Deterministic Checks For Mechanical Facts, Such As Counts, Timings, And Test Results.
- Use A Fixed Rubric With Blind, Order-Balanced Comparison For Judgment.
- An Agent Judge's Preference Is Not The User's Taste. For A Creative Outcome, The User Or The Project Owner Decides.
- Keep Scoring Code, Expected Answers, And Permissions Outside What The Candidate Can Write. Verify That This Isolation Exists Rather Than Assuming It.
- Fix A Broken Grader Separately, Then Rerun Both Arms.

## Run And Decide

1. Begin With The Cheapest Check That Actually Triggers The Suspected Mechanism.
2. Log Each Attempt You Planned, Failed And Timed-Out Ones Too.
3. Repeat Runs When Ordinary Variation Could Explain The Gain, And Repeat Both Arms Equally. Do Not Rerun Only The Candidate Until It Wins.
4. Add Tasks That Already Worked And Close Counterexamples.
5. Accept Only Under The Criteria Set Beforehand. A Tie Or An Unclear Result Keeps The Current Version, Unless Simplification Was The Declared Goal.
6. Reject Shortcuts That Raise The Score Without The Intended Behavior.
7. With Several Candidates, Choose On Selection Cases. Then Test The Locked Winner Against The Baseline Using Final Cases Nobody Has Touched.
8. Test Combined Changes Together. Two Changes That Each Passed Alone Are Unproven As A Pair.
9. Stop At The Budget Or The Stopping Rule, Even When The Result Is Unclear. Report What Ran And Keep The Current Version.

## Score Paired Trials With The Helper

[The Paired-Trial Helper](scripts/compare.py) Scores A Comparison Whose Outcome Is One Number Per Run. It Reads The Values You Supply. It Runs No Task And Checks No Evidence.

- **Plan.** Copy [The Example Plan](assets/example-plan.json). Label Both Versions. Specify A Primary Metric, Its Unit, Its Preferred Direction, A Minimum Useful Median Gain In That Unit, And The Required Number Of Distinct Matched Inputs. A Gain Of Two Minutes Means Two Minutes Saved Per Paired Input. Choose One Numeric Guardrail Where Larger Values Mean Worse Quality, Such As Caption Errors Remaining At Review, And Set The Largest Acceptable Increase On Any One Pair. Use Absolute Counts When Paired Inputs Have The Same Length, Or A Defined Rate When A Rate Measures The Cost Better.
- **Trials.** Use [The Example Trials](assets/example-trials.csv) As The Column Schema. Each Row Is One Distinct Matched Input That Both Versions Attempted From The Same Saved Starting State. Hold The Operator, Tool Versions, And Timing Or Scoring Rules Constant Within A Pair. `AB` Means Baseline First. `BA` Means Candidate First. Alternate The Order When Feasible And Note Any Remaining Practice Effect. Each Evidence Pointer Identifies A Specific Observation, Marker, Or Log Entry. Preserve The Original Raw Measurements.
- **Splits.** To Separate The Three Sets Of Cases, Add A `split` Column Holding `develop`, `select`, Or `final` On Every Row, As In [The Split Example](assets/example-split-trials.csv). The Decision Then Counts The `final` Rows Only, And `minimum_pairs` Applies To Them. The Report Names That Basis In `decision_split`, Summarizes The Other Rows Under `other_splits`, And Lists `warnings` When No `final` Rows Exist Or When One Input Appears In More Than One Split. Warnings Also Print To Standard Error.

Run From This Skill Folder With Python 3.9 Or Later.

```text
python scripts/compare.py assets/example-plan.json assets/example-trials.csv
python scripts/compare.py assets/example-plan.json assets/example-split-trials.csv
```

The Bundled Numbers Are Synthetic. In The First Example The Paired Time Savings Are Three, Two, And One Minute. The Median Gain Is Two Minutes, No Guardrail Is Breached, And The Helper Reports `Candidate Meets Trial Criteria`. In The Split Example The Median Gain Shrinks From Four Minutes On `develop` To Three On `select` And Two On `final`. Only The `final` Figure Supports The Decision.

| Decision | When It Appears |
| --- | --- |
| `Revise Candidate` | Any Counted Pair Exceeds The Guardrail Limit. |
| `Collect More Pairs` | No Breach, And Fewer Counted Pairs Than `minimum_pairs`. |
| `Candidate Meets Trial Criteria` | A Complete Set With A Positive Median Gain At Or Above The Declared Threshold. |
| `Keep Baseline` | A Complete Set That Falls Short Of The Threshold. |

Counted Pairs Are All Rows In A Table Without A `split` Column, And The `final` Rows In A Table With One. Read The Individual Losses And Run Orders Before Drawing A Conclusion. Check Each Evidence Pointer Against The Original Record. The Result Describes Those Inputs And Supplies No Estimate Of Population-Wide Performance.

## Adopt And Keep The Evidence

A Winning Candidate Is Not Yet Installed, Published, Or Deployed. Adoption Is A Separate Step.

1. Stay Inside What The User Allowed You To Adopt And Inside What The Test Covered.
2. Check That The Maintained Target Has Not Changed Since The Trial.
3. Apply The Change, Then Check How It Loads In A Fresh Session.
4. Keep A Rollback Copy And Record Where It Is.

Keep One Concise Experiment Record From [The Record Template](assets/experiment-record.md). It Holds The Versions, Evidence, Prediction, Diff, Case Split, Settings, Commands, Every Outcome, Cost, The Decision, And Where The Rollback Copy Lives. Private Session Traces Stay On The Local Machine. The Record Points To Session Logs And Client Material Without Copying Them Into Shared Places.

When The Candidate Fails, Keep The Current Version And File The Failed Idea With Its Evidence. Use An Observed Failure To Choose A Single Revision For The Next Trial. A Changed Procedure Or Threshold Needs A Fresh Trial.

When A Comparison Involves Video, Compare Saved Editable Projects In The Editor. The Project Owner Personally Reviews The Editable Project And Approves Before Any Video Export, Including Test Or Preview Files. A Trial Never Changes That Rule.

## Improve The Improver

Three Extra Conditions Apply When The Thing Being Improved Is `reflect`, `rsi`, Or The Way Proposals Are Made.

- Lock Scoring And Adoption Rules Where The Candidate Cannot Change Them.
- Compare The Old And New Procedure On The Same Fresh Batch Of Problems With Equal Budgets.
- Judge Each Procedure By Externally Checked Results Of The Changes It Produces. Report Length, Proposal Count, And Self-Rating Are Not Results.

## Check This Skill

This Section Is For Maintaining The Skill. It Is Not A Step In An Experiment. [The Included Scenarios](scenarios/README.md) Describe Improvement Requests, The User's Reply, And The Behaviors A Correct Response Shows. Use Them To Check This Skill By Hand With An Independent Agent. They Are Hand-Run Examples And Promise Nothing About Future Results. Run These Commands From This Skill Folder With Python 3.9 Or Later.

```text
python scripts/check_scenarios.py
python -B -m unittest discover -s tests -v
```

The First Command Validates The Shape Of The Scenario File. The Second Runs The Offline Tests For The Helper And The Validator With Temporary Files.
