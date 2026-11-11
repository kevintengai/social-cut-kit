---
name: video-script
description: Develop Short-Form Scripts, Openings And Evidence Shots From A Business Brief, And Inspect Audience Retention From CSV Or A Chart Capture.
---

# Social Cut Kit | Script Desk

Write For One Viewer Making One Decision. Use The Platform, Running Time, Offer, Proof, And Next Action From The Brief. Invite A Real Question In The Opening And Pay It Off With A Visible Change. Work A Second Opening From A Different Motive, Such As An Avoidable Mistake Or A Visible Result. Read Both Aloud Against The First Shot.

Write A Two-Column Draft. Put The Spoken Line In One Column And The Image Or Change That Carries It In The Other. Mark The Source Of Each Commercial Claim. Keep The First Proof Shot On Screen Long Enough To Inspect. Say The CTA At The Moment The Viewer Can Do What It Asks. A Product Demo Can Show A Filter Being Applied And Its Result Before Asking For A Booking.

`scripts/script_desk.py outline campaign.json beats.json` Creates A Timed Draft And A Pair Of Opening Treatments From A Campaign Brief. Edit The Lines And Durations In `beats.json`. Use `read beats.json` For A Table Read. The Director Can Accept That File Directly.

For A Performance Review, Supply Time In Seconds And Retention In Percent. Compare Drops To The Published Cut's Exact Moments, Then Offer One Different Opening Or Proof Placement To Test. Preserve The Platform's Measurement Definition. Percentages Above 100 Can Represent Replays. An Observed Drop Alone Cannot Establish Its Cause.

```sh
python scripts/retention.py csv performance.csv
python scripts/retention.py image chart.png --plot 120 40 980 410 --color 66 141 242 --seconds 40 --top 100 --bottom 0
```

For A Chart Capture, Read The Actual Axis Bounds And Line Color. The Plot Rectangle Is Left, Top, Right, Bottom In Image Pixels. Review The Reported Coverage Before Describing A Curve. When A Measured Chart Is Unavailable, Use The Platform's Visible Labels Or Ask For A CSV.
