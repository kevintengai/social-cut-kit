---
name: director
description: Design A Shot Plan For A Social Video, Review Its Proof And Pacing, And Hand Sourced Shots To An Editable Video Timeline.
---

# Social Cut Kit | Director’s Desk

Start With The Decision The Story Asks A Viewer To Make. Write Down What The Audience Already Knows, What Changes During The Piece, And Which Shot Proves That Change. A Demo Usually Benefits From Showing The Screen State Before And After The Same Action. An Interview May Work Better With The Speaker On Camera Until They Name The Object You Can Cut To.

Turn Each Beat Into A Shot The Crew Can Capture. Name The Subject, Frame Size, Action, Sound Cue, And Reason For The Cut. Plan Space For Captions And Interface Controls At The Actual Delivery Aspect Ratio. For A Vertical Closeup, Keep The Product Control And Its Result Within The Same Readable Region Or Motivate The Reframe With The Action.

A Cut On A Hand Movement Can Hide A Change In Angle. A Sound That Arrives Before The Next Picture Can Introduce A Location. A Silent Hold After A Demonstration Gives The Viewer Time To Read Its Result. Choose A Technique Because It Helps That Particular Shot. For A Different Genre, Try Planning A Screen Demo, A Two-Person Skit, A Recreation From An Authorized Reference, Or An Animated Insert Using The Same Beat Records.

Use `board.py board` To Build An Offline HTML Shot Board From A Script Desk File. It Shows The Time, The Intended Picture, The Spoken Line, Evidence, And Missing Media. Edit The Script File To Make Changes. Keep `media` Paths Relative To That File. Set `source_in` In Seconds. `board.py timeline` Converts Fully Sourced Beats Into A Video Edit Timeline. It Rebases Paths For The Destination Folder.

```sh
python scripts/board.py board beats.json shots.html
python scripts/board.py timeline beats.json edit.json --width 1080 --height 1920 --fps 30
```

For A Review, First Watch The Editable Cut Muted And Record The First Frame That Makes The Offer Clear. Next Listen Without Picture For Clipped Word Edges, Room-Tone Jumps, Or An Unexplained Claim. Finally Read Every Caption And CTA At Phone Size. Give The Project Owner The Editable Project And Exact Timecodes. For TENG AI SCHOOL Productions The Owner Personally Reviews This Version In The Editor And Approves Before Any Video Export, Including Test Or Preview Files.
