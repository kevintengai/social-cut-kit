# Experiment Record

Copy This File Into The Project's Working Notes And Fill In Every Section. Write “Unknown” Where A Fact Is Not Available. Keep The Record To One Or Two Pages. Keep Private Traces Local And Point To Them Here Instead Of Pasting Them.

## Target And Versions

| Item | Entry |
| --- | --- |
| Target (Skill, Instruction File, Tool, Or Process Step) | |
| Current Version (Path And Revision Or Hash) | |
| Candidate Version (Path And Revision Or Hash) | |
| Model And Version | |
| Date Opened And Date Closed | |

## Authorization And Bounds

| Bound | Entry |
| --- | --- |
| Who Authorized The Experiment, And For What | |
| Budget (Time, Cost, Or Run Cap) | |
| Stopping Rule | |
| Editable Scope | |
| Who May Adopt The Result, And Where | |

## Evidence And Diagnosis

- Source Of The Finding (A Reflect Finding Or Rebuilt Evidence):
- Failed Runs Compared With Successful Runs:
- Why This Is A Defect In The Target, Not A Model Limit, Missing Access, An Outage, Or A Changed Requirement:
- Earlier Failed Ideas For This Target, And The New Reason To Try Again:

## Prediction

Write This Section Before The First Run.

- Smallest Candidate Change:
- Outcome Expected To Improve, And By How Much:
- Nearby Situation It Could Harm:
- Date Written:

## Candidate Diff

```text
Paste The Compact Diff, Or Name The Revision That Holds It.
```

## Case Split

| Split | Case Ids | Chosen When, And By Whom | Seen By The Optimizing Agent |
| --- | --- | --- | --- |
| `develop` | | | |
| `select` | | | |
| `final` | | | |

- Date The Candidate Was Frozen:
- Final Cases That Informed An Edit, And Their Replacements:

## Settings And Scoring

- Starting State And Reset Method:
- Tools, Settings, And Limits, Identical For Both Arms:
- How Each Arm Was Confirmed To Load Its Own Version:
- Success Criteria (Metric, Direction, Threshold, Number Of Cases):
- Behavior That Must Not Regress, And Its Limit:
- Scoring Method (Deterministic Check, Or Fixed Rubric With Blind, Order-Balanced Comparison):
- Where Scoring Code And Expected Answers Live, And How Their Isolation Was Verified:

## Commands

```text
List Each Command As It Was Run, In Order.
```

## Outcomes

Log Each Attempt You Planned, Failed And Timed-Out Ones Too.

| Attempt | Split | Case | Arm | Order | Result | Guardrail | Evidence Pointer | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | | | | | | | | |
| 2 | | | | | | | | |

- Saved Helper Report (Path To The Output Of `scripts/compare.py`):
- Warnings In That Report:

## Cost

- Runs Used Against The Cap:
- Time Used (Measured, Or Not Measured):
- Money Spent (Measured, Or Not Measured):

## Decision

- Decision (Adopt The Candidate, Keep The Current Version, Revise The Candidate, Or Collect More Pairs):
- Criteria Met Or Missed:
- Scope In Which The Result Applies:
- Important Counterexample:
- Failed Ideas To Keep On File, With Their Evidence:

## Adoption And Rollback

- Adopted By, On What Date, And Where:
- Target Checked For Changes Since The Trial:
- How The Change Was Confirmed To Load:
- Rollback Pointer (Path To The Saved Copy Or Revision):
- Location Of Private Traces, Kept Local:
