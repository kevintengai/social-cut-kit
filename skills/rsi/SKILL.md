---
name: rsi
description: Test One Proposed Editing Workflow Improvement Against Its Baseline With Paired Inputs, Predeclared Thresholds, And Measured Quality Checks. Use To Decide Whether To Adopt, Revise, Or Retire A Repeatable Change.
---

# Compare Workflow Revisions

Start With A Repeated Editing Problem Whose Cost You Can Observe. Choose One Change To A Cueing Procedure, Asset Search, Caption Pass, Or Other Repeatable Step. Record The Current Workflow Revision And How To Restore It Before Starting.

## Define The Trial

- Copy [The Example Plan](assets/example-plan.json). Specify A Primary Metric, Its Unit, Its Preferred Direction, A Minimum Useful Median Gain In That Unit, And The Required Number Of Distinct Matched Inputs. A Gain Of Two Minutes Means Two Minutes Saved Per Paired Input.
- Choose One Numeric Quality Guardrail Where Larger Values Mean Worse Quality, Such As The Count Of Caption Errors At Editor Review. Set The Largest Acceptable Increase On Any One Pair. Use Absolute Counts When Paired Inputs Have Identical Lengths, Or A Defined Rate When The Rate Better Measures The Actual Cost.
- Identify The Actual Source Revisions, Editor Version, Operator, And Timing Or Scoring Rules. Hold Them Constant Within A Pair. Begin Each Run From The Same Saved Starting State In Separate Working Copies. Alternate Which Workflow Runs First When Feasible And Document Residual Practice Effects.

## Collect And Compare

Use [The Example Trials](assets/example-trials.csv) As The Column Schema. Each Row Represents One Distinct Matched Input. Both Runs Use That Same Input. `AB` Means Baseline First. `BA` Means Candidate First. Each Evidence Pointer Identifies A Specific Observation, Editor Marker, Or Timing Log Entry. Preserve The Original Raw Measurements.

Run From This Skill Folder With Python 3.9 Or Later.

```text
python scripts/compare.py assets/example-plan.json assets/example-trials.csv
```

The Bundled Numbers Are Synthetic. Their Paired Time Savings Are Three, Two, And One Minute. The Median Gain Is Two Minutes And No Quality Guardrail Is Breached. The Helper Reports `Candidate Meets Trial Criteria`. For A Real Trial, Pass The Paths To Your Own Plan And CSV. The Helper Reads The Supplied Values And Evidence Labels. Check Each Evidence Pointer Against The Original Record.

Any Pair Above The Guardrail Limit Produces `Revise Candidate`. An Undersized Set Without A Breach Produces `Collect More Pairs`. A Complete Set Needs A Positive Median Gain At Or Above The Declared Threshold To Meet The Trial Criteria. Read The Individual Losses And Run Orders Before Drawing A Conclusion. The Result Describes Those Inputs And Supplies No Estimate Of Population-Wide Performance.

## Apply The Decision

Keep A Decision Note With The Tested Workflow Revisions, The Saved Plan, The Trial Table, An Important Counterexample, And The Scope In Which The Result Applies. If Adoption Is Authorized, Change Only The Tested Step And Preserve A Way To Restore The Baseline. If The Change Fails, Keep The Baseline And Use An Observed Failure To Choose A Single Revision For The Next Trial. Run A Fresh Trial When You Change The Procedure Or Threshold. Use Saved In-Editor Projects For Video Review Under Kevin's Review-Before-Export Rule.
