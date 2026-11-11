# Publish Or Schedule A Short Video

Use This Workflow When The Owner Asks To Save A Platform Draft, Publish Now, Or Schedule A Release. An Agent With Access To The Selected Browser Or Connector Performs The Platform Steps. The Included Python Tool Keeps A Local Attempt History And Stores The Operator’s Evidence. Each Destination Has Its Own Outcome.

## Prepare The Release

1. Read The Owner’s Request For The Exact Edit, Platform, Account, Visibility, Action, And Timing. Match The Signed-In Identity And Selected Page, Channel, Or Profile To A Stable Account ID Or Unique Handle. Preserve Any Required Login Identity, Workspace, Or Scheduler Location. Resolve Ambiguous Destinations Before Uploading.
2. Use The Owner’s Reviewed Export. If A New Export Is Needed, Save The Editable Project, Give The Owner An In-Editor Review, And Wait For Their Approval Of That Edit Before Exporting. Reuse An Existing Approval That Covers The Exact Work. An Approval To Export Covers Only The Scope The Owner Granted.
3. Preview The Actual File. Check Duration, Orientation, Opening And Closing Audio, Legibility, Crop, And Baked-In Captions. Compare The Requested Cover Image Or Frame With The Platform Preview. Check Platform Limits And Account Features In The Current Composer. Resolve Any Required Transformation With The Owner’s Editing Instructions.
4. Prepare Separate Copy For Each Destination. Preserve Supplied Spelling, Links, Line Breaks, Audience Settings, And CTA Rules. For A Direct-Link X Campaign, Lead With The Hook And Include The Approved Resource Link. For A Short-Form Keyword Campaign, Quote The Requested Keyword, Describe The Actual Benefit, And Confirm The Promised Delivery Method. Use The Owner’s Requested Hashtag Spacing And Platform Exceptions. Put Exact Follow-Up Text And Any Pinning Requirement In The Packet.
5. For A Schedule, Resolve Relative Wording To A Calendar Date, Local Clock Time, And Named Time Zone. Check The UTC Instant And The Zone Shown In The Planner. A Spring Clock Change Can Remove A Time. An Autumn Change Can Give A Time Two Different Offsets. Ask Which Instant The Owner Means When Their Request Leaves That Choice Open.

## Stage One Packet Per Destination

Run The Commands From The Installed `video-edit` Skill Directory. Use One Local SQLite File For The Campaign And One Stable `id` For Each Intended Delivery. All Operators Working On The Same Release Need The Same Ledger. Use A Local Disk Supporting SQLite File Locks. Keep Actual Content And Private Receipts In The Campaign Workspace.

Create `packet.json` Next To The Approved Media. Replace The Example Values With The Actual Destination And Copy. The `caption` May Be An Empty String For A Captionless Post. YouTube Also Requires A `title` And An Owner-Supplied `audience` Setting. `visibility` Is The Intended Audience Or Privacy Setting. For A Native Draft That Only Exposes Its Draft State, Use The Observable Draft Visibility.

```json
{
  "id": "autumn-demo-shorts",
  "platform": "youtube",
  "account": "EXACT_CHANNEL_ID",
  "mode": "schedule",
  "media": "approved.mp4",
  "title": "How We Made The Demo",
  "caption": "Watch The Demo From Start To Finish.",
  "audience": "Not Made For Kids",
  "visibility": "Public",
  "local": "2030-10-08T09:30",
  "zone": "America/New_York",
  "cover_frame": "00:00:02",
  "notes": "Use The Frame Showing The Completed Demo."
}
```

- Use `instagram`, `facebook`, `tiktok`, `youtube`, `x`, Or `linkedin` For `platform`. Choose `draft`, `now`, Or `schedule` For `mode`. Include `local` And `zone` For Scheduled Posts Only.
- Choose An Optional `cover_file` Or `cover_frame`. Media And Cover File Paths Resolve Relative To The Packet. Add `follow_up` For A Requested Action After Publication. Record The Exact Text, Link, And Expected Result There. Use `notes` For Other Campaign Instructions.
- Use An IANA Zone Such As `America/New_York` Or `UTC`. For A Repeated Hour, Include The Chosen Offset, Such As `2030-11-03T01:30-04:00` Or `2030-11-03T01:30-05:00`. The Tool Checks The Offset Against The Named Zone. On Systems Missing The IANA Database, Install It For This Python With `python -m pip install tzdata`. UTC Works With Standard Python.

```text
python scripts/posting.py --ledger campaign.sqlite3 prepare packet.json
python scripts/posting.py --ledger campaign.sqlite3 show autumn-demo-shorts
```

Check The Saved Account, Copy, File Fingerprints, Mode, And Schedule. Preparing Again With The Same Packet Is Safe. Before Any Attempt, A Corrected Packet Can Replace The Prepared Version Under The Same ID.

## Make The Authorized Platform Change

1. Open The Specified Platform Or Connected Scheduler. If Using A Connector, Inspect Its Available Actions And Connected Account IDs. Select The Exact Destination And Only That Destination. Turn Off Unrequested Cross-Posting. If Access Is Missing, Keep This Destination Prepared And Continue With Other Authorized Destinations.
2. Check The Ledger And The Account’s Drafts, Scheduled Queue, And Recent Posts For An Existing Match. Compare The Account, Title Or Caption, Video, And Intended Slot. When A Matching Item Already Exists, Reopen It And Record Its Observed State. Reuse Its Native Identifier. For An Existing Draft Being Promoted, Open That Draft Directly.
3. Immediately Before The First Remote Change, Claim This Delivery In The Ledger. An Upload Can Create A Platform Item. Start The Claim Before Uploading Or Calling A Connector Create Action. Cite The Owner’s Existing Instruction In `--authorization`. A Successful `begin` Grants One Operator The Attempt. If It Fails, Inspect `show` And Reconcile The Existing Attempt Before Acting.

   ```text
   python scripts/posting.py --ledger campaign.sqlite3 begin autumn-demo-shorts --authorization "Owner Approved The Reviewed Short And The October 8 Slot"
   ```

4. Attach The Approved Export Or Open The Identified Draft. Wait For Upload And Processing To Reach The State Required By The Composer. Set The Destination’s Copy, Cover, Audience, Visibility, And Any Supplied Per-Post Options. Check The Final Preview, Including Line Breaks, Truncation, Link Previews, And Whether Automatic Captions Duplicate Burned-In Text. If A Required Option Is Unavailable, Preserve The Current Item And Report What Is Missing.
5. Choose The Requested Action. For `draft`, Save Using The Platform’s Draft Control. For `now`, Select The Requested Visibility And Use The Final Publish, Share, Or Post Control. For `schedule`, Select The Future Date And Time In The Planner’s Display Zone, Compare The Converted Instant, And Confirm The Final Schedule Control. A Reminder For Manual Posting Requires A Separate User Action. Record That Limitation If The Account Offers Only A Reminder.
6. With A Connector, Use The Observed Destination ID, Native Draft Or Upload ID, And Approved Fields In Its Matching Draft, Publish, Or Schedule Action. If An Idempotency Key Is Supported, Reuse The Same Campaign Delivery ID For That Operation. Retain Returned Job And Item IDs. Poll Processing Jobs Using Read-Only Status Calls, Then Retrieve The Item Or Queue Entry Again.
7. With A Browser, Leave The Composer And Reopen The Account’s Content List, Scheduler, Or Drafts. Open The Actual Item And Compare It To The Packet. With Either Route, Record A Receipt For Each Destination. A Submit Toast, Returned Link, Or Processing Job Alone Leaves The Outcome Unconfirmed.

### Destination Controls And Readback

| Destination | Prepare In The Composer | Where To Verify |
| --- | --- | --- |
| Instagram Reels | Select The Intended Instagram Profile And Reel Format. Inspect The Cover, Caption, And Profile Crop. Check Any Facebook Sharing Selector. | Open The Exact Reel From That Profile, Its Scheduled Content, Or Its Drafts. [Meta’s Reel Sharing Guide](https://about.fb.com/news/2020/08/introducing-instagram-reels/) |
| Facebook Reels | Switch To The Requested Page Or Profile And Check The Audience Selector. Select The Facebook Destination Explicitly In A Shared Meta Composer. | Reopen That Page Or Profile’s Reel. For A Future Release, Reopen Its Planner Entry And Check The Page And Slot. [Meta’s Facebook Video Guide](https://about.fb.com/news/2025/06/making-it-easier-create-videos-facebook/) |
| TikTok | Open The Requested Account’s Upload Flow. Check Description, Cover Frame, Audience, And Interaction Permissions. Use Its Available Scheduler For A Timed Release. | Reopen The Account’s Video, Scheduled Entry, Or Native Draft In The App Or Device Where It Was Saved. [TikTok’s Cover And Draft Guide](https://support.tiktok.com/en/using-tiktok/creating-videos/editing-posting-and-deleting) |
| YouTube Shorts | Select The Exact Channel, Upload The Approved Short, Set Title, Description, Audience, And Visibility, And Check Its Shorts Classification. Use Schedule For An Authorized Future Public Release. Confirm Any Required Cover Control In The Available Client. | Reopen The Video In Channel Content. Check Its Audience, Visibility, And Scheduled Instant As Applicable. After Publication, Open The Short And Complete Any Requested Comment Or Pin. [YouTube Shorts](https://support.google.com/youtube/answer/10059070) · [YouTube Scheduling](https://support.google.com/youtube/answer/1270709) |
| X | Confirm The Posting Handle, Attach The Video, And Inspect The Text And Any Direct Link. For A Schedule, Check The Available Scheduler And The Selected Posting Account. | Reopen The Status Under That Handle Or Locate The Entry In The Scheduler Used To Submit It. [X Video Posting](https://help.x.com/en/using-x/x-videos) · [X Media Studio Scheduling](https://help.x.com/en/using-x/media-studio-faqs) |
| LinkedIn | Select The Requested Member Profile Or Organization Page As The Author. Upload The Video, Add The Approved Text, And Inspect The Audience And Preview. | Reopen The Member Activity, Page Post, Or Scheduled Posts List Under The Selected Author. [LinkedIn Member Scheduling](https://www.linkedin.com/help/linkedin/answer/a1347212) · [LinkedIn Page Scheduling](https://www.linkedin.com/help/linkedin/answer/a1429854) |

If A Platform Lacks A Native Draft Or Scheduling Control, Check An Already Authorized Connector For That Same Destination. If Both Routes Lack The Requested Action, Keep The Local Packet And Report The Specific Blocker. A Native Draft Can Be Promoted Later Under New Authorization. Reuse The Same Packet ID, Change The Mode, Set `from_draft` To The Verified Draft’s `item`, And Use Its Existing Platform Object.

## Record What The Account Shows

Write The Actual Readback In `proof.json`. This Example Shows A Scheduled Item Observed In A Planner. `copy_sample` Is An Exact Excerpt From The Visible Caption Or Title. `media_detail` Names A Distinguishing Frame, Duration, Or Visual Feature You Checked. `item` Holds The Native ID Or Permalink. For A Private Draft Without An ID, Use A Reproducible Locator With Its Account, Title, Device Or Drafts View, And Creation Time.

```json
{
  "state": "scheduled",
  "account": "EXACT_CHANNEL_ID",
  "source": "planner",
  "item": "NATIVE_ITEM_OR_QUEUE_ID",
  "visibility": "Public",
  "copy_sample": "How We Made The Demo",
  "media_detail": "The Preview Opens On The Completed Demo And Runs For 28 Seconds.",
  "scheduled_for": "2030-10-08T09:30:00-04:00",
  "observation": "Reopened The Channel Planner And Matched Its Scheduled Row, Audience, Preview, And Time."
}
```

```text
python scripts/posting.py --ledger campaign.sqlite3 record autumn-demo-shorts proof.json
python scripts/posting.py --ledger campaign.sqlite3 show
```

- For `published`, Use `account-content` Or `connector-readback` As The Source. For `scheduled`, Use `planner` Or `connector-readback` And Include The Observed `scheduled_for` With Its Offset. Verify The Intended Release Audience In The Schedule Details. For `draft`, Use `drafts` Or `connector-readback`. Use The Displayed Audience Or Draft Visibility From The Packet. The Ledger Stores The Operator’s Observation And Its Record Time.
- A Scheduled Receipt Confirms A Queue Entry. If The Owner Asks To Monitor Delivery, Check The Exact Item Again When Due. Record `published` When Its Published State And Intended Audience Are Visible. Retain The Scheduler ID In The History When The Published Post Gets A Different ID.
- For A Timeout, Crash, Processing Delay, Or Unclear Response, Keep The Attempt Open. Record `state` As `unknown` With `account`, `source`, And An `observation` Describing The Last Known Step And Any Job ID. Check The Exact Account’s Drafts, Queue, Recent Content, And Connector Job Or History. Allow Time For Processing And Refresh Again. A Missing Entry On One Check Leaves The Attempt Unresolved.
- A Positive Readback Can Resolve An Earlier Error. Record The Matching Item Directly. Continue Read-Only Checks While Delivery Is Uncertain. A Retry Requires Authoritative Evidence That The Attempt Was Rejected Before Acceptance Or Failed Terminally Without A Published, Scheduled, Or Reusable Draft Item. Record `rejected` With `source` Set To `terminal-response`, The Specific Error In `observation`, And The Account And Job Checks In `reconciliation`. Then Correct The Packet As Needed And Claim One New Attempt Using The Same ID. For A Separately Requested Intentional Repeat Of An Already Published Identical Post, Use A New ID And Set `repeat_of` To The Earlier Delivery ID.

## Complete Requested Follow-Ups

After Publication, Read `follow_up` In The Packet. For An Authorized YouTube Comment And Pin, Reopen The Exact Short As Its Owner. Inspect Existing Comments For The Exact Supplied Text And Link. Reuse A Matching Owner Comment. Claim The Follow-Up Before Its First Remote Change With `begin DELIVERY_ID --follow-up --authorization "Existing Campaign Instruction"`. Post The Supplied Comment Once If Missing. Open The Matching Comment’s Menu, Choose Pin If Available, And Confirm. Reload The Comments And Verify The Comment Text, Link, Author, And Visible Owner Pin. [YouTube Comment Controls](https://support.google.com/youtube/answer/6000964)

Record `follow-up-verified` With The Exact `account`, `source` As `account-content` Or `connector-readback`, `parent_item` Matching The Published Receipt, `item` Identifying The Comment, And An `observation` Describing The Requested Outcome. If A Pin Fails After The Comment Appears, Record `follow-up-unknown` And Its Details. Reopen The Existing Comment And Complete Only The Outstanding Pin When Possible. Reconcile Ambiguous Comment Submission Before Adding Another. Report The Published Video And Pending Follow-Up Separately.

## Rehearse Locally

Use `--dry-run` On Every Rehearsal Command, Before The Subcommand. The Ledger Isolates Simulated Records And Labels Their Output `simulation`. Use A Local Fixture, A Synthetic Account, And Mock Readbacks. Run The Python Commands Only During A Rehearsal.

```text
python scripts/posting.py --ledger rehearsal.sqlite3 --dry-run prepare packet.json
python scripts/posting.py --ledger rehearsal.sqlite3 --dry-run begin autumn-demo-shorts --authorization "Synthetic Rehearsal"
python scripts/posting.py --ledger rehearsal.sqlite3 --dry-run record autumn-demo-shorts proof.json
python scripts/posting.py --ledger rehearsal.sqlite3 --dry-run show autumn-demo-shorts
```

For The Owner’s Handoff, Give Each Destination’s Exact Account, Recorded State, Scheduled Local Time And Zone If Applicable, Verified Item Or Queue ID, And Any Remaining Action. Report Local Preparation, Native Drafts, Scheduled Items, And Confirmed Publications By Their Recorded States.
