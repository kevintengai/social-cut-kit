# Repair Desk Example

Open `demo.html` And Switch Between All Jobs And Ready Only. The Two PNGs Are Stills From This Fictional Interactive Demo. The Supplied Script Uses The First State For The Opening And The Second For The Proof. The Retention CSV Is Invented Practice Data.

From The Product Root, Run The Following Commands. Use New Filenames For Your Own Versions.

```sh
python skills/teng-campaign-brief/scripts/campaign.py show examples/repair-desk/campaign.json
python skills/video-script/scripts/script_desk.py read examples/repair-desk/beats.json
python skills/director/scripts/board.py board examples/repair-desk/beats.json shots.html
python skills/director/scripts/board.py timeline examples/repair-desk/beats.json edit.json --width 720 --height 1280
python skills/video-script/scripts/retention.py csv examples/repair-desk/retention.csv
```

Open `shots.html` To Review The Plan. Use The Video Edit Skill With `edit.json` To Review The Cut. The Spoken Lines In The Plan Are A Recording Script. Record A Narrator Or Use A Caption Track If You Want Those Lines In The Finished Piece.

To Inspect How The Supplied Eight-Second Cut Maps To Native Resolve Tracks, Run This From The Product Root. The Dry Run Works With Resolve Closed.

```sh
python skills/video-edit/scripts/edit_video.py resolve examples/repair-desk/timeline.json --project "Repair Desk" --name "Repair Desk 01" --dry-run
```

To Build The Editable Timeline In An Open Project, Follow The [Native Resolve Guide](../../skills/video-edit/RESOLVE.md).
