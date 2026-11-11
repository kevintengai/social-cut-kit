# Reflect Scenarios

Each Scenario Describes A Work Session, What The User Says Next, And The Behaviors A Correct Reflection Shows. Use Them To Check By Hand That An Agent Following [The Reflect Skill](../SKILL.md) Behaves As Intended.

These Are Scenarios. They Are Not An Automated Test Suite, And A Good Run Is Not A Guarantee Of How An Agent Will Behave In Your Own Sessions.

## What A Scenario Contains

[The Scenario File](scenarios.json) Is One Object With A `skill` Name And A `scenarios` List. Every Scenario Has Six Fields.

| Field | Meaning |
| --- | --- |
| `id` | A Whole Number That Is Unique In The File. |
| `name` | A Unique Label In `snake_case`. |
| `request` | What The User Types. |
| `session` | What Happened In The Session And What Guidance Existed. |
| `feedback` | What The User Says After Seeing The Preliminary Findings. |
| `checks` | Three To Six Behaviors A Correct Response Must Show. These Stay Hidden From The Agent Under Test. |

## Run One Scenario By Hand

1. Start An Independent Agent In A Scratch Workspace. Give It `SKILL.md` And The Files It Links To, But Not This `scenarios` Folder.
2. Give It The `session` Text As The Record Of The Session, Then Give It The `request` As The User's Message.
3. Let It Work Until It Shows Preliminary Findings And Asks For The User's View. Reply With The `feedback` Text.
4. Let It Finish, And Save The Whole Response.
5. Afterwards, Compare The Response With Each Entry In `checks`. Mark Each One Shown, Not Shown, Or Unclear, And Note The Passage That Decided It.

Keep `checks` Out Of The Agent's Context Until Step Five. If The Agent Asks For Something The `session` Text Does Not State, Answer That It Is Not Available. If The Agent Never Asks For The User's View, Give The `feedback` After Its First Report And Record That It Did Not Ask.

## Read The Result

- One Run Shows How One Agent Responded Once. Responses Vary, So Repeat A Scenario Before Drawing A Conclusion.
- Read The Whole Response. A Response Can Show Every Listed Behavior And Still Do Something The Skill Forbids.
- No Scenario Calls For Exporting, Publishing, Installing, Changing Memory, Or Resuming The Reviewed Work. A Response That Does Any Of These Has Failed The Scenario.
- Add Your Own Scenarios From Sessions That Went Wrong In Your Work. Give Each A New `id` And `name`.

## Check The File

Run These Commands From The Skill Folder With Python 3.9 Or Later.

```text
python scripts/check_scenarios.py
python -B -m unittest discover -s tests -v
```

The Validator Checks The Shape Of The File, Unique Ids And Names, And Filled Fields. It Does Not Run A Scenario Or Judge A Response. Pass A Path To Check Another File, `--skill NAME` To Expect Another Skill Name, Or `--minimum COUNT` To Require A Number Of Scenarios.
