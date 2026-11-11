---
name: teng-campaign-brief
description: Turn A Business Offer Into An Evidence-Based Campaign Decision And An Editable Brief For A Social Video.
---

# Social Cut Kit | Campaign Brief

Ask What Decision A Viewer Can Make After Watching. Document The Exact Action, The Destination That Accepts It, And The Event The Client Can Actually Observe. A Booking Confirmation And A Visit To A Calendar Page Measure Different Things.

For Each Claim, Obtain A Recording, An On-Screen State, A Document, Or A Client-Approved Quote. Pair It With What The Viewer Should See. A Result From One Project Can Support An Example About That Project. A General Promise Needs Broader Evidence. Keep Exact Product Names, URLs, And Quoted Speech Intact.

Use `scripts/campaign.py new` To Save An Editable Campaign File. Use `show` To Read Its Production Brief. Use `--proof "Claim" "Source And Location" "Visible Evidence"` Once Per Claim. If Evidence Is Missing, Make The Missing Capture An Open Item And Use The Offer Itself As A Starting Point.

```sh
python scripts/campaign.py new campaign.json --title "Repair Queue Reel" --viewer "Repair Shop Owners" --offer "A Live Repair Desk Demo" --action "Book A Walkthrough" --channel "Instagram Reels" --metric "Completed Bookings" --proof "The Queue Filters By Status" "Owned Demo Recording At 00:12" "Only Ready Jobs Remain In The List"
python scripts/campaign.py show campaign.json
```

Send The File And The Actual Evidence To The Writer. Treat Any Missing Customer Approval Or Media Rights As A Specific Open Decision For The Relevant Asset. A Draft Brief Does Not Change The Offer Or Publish A Post.
