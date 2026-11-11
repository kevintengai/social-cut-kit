# Animated Inserts

Hand A Shot To The [Animated Video Skill](../animated-video/SKILL.md) When A Beat Needs A Picture That Has To Be Drawn. The Edit Keeps The Timeline, The Mix, And The Cue Sheet. The Animation Side Makes One Clip That Fits The Slot.

## Decide Whether A Beat Needs One

Use What The Edit Already Has First. Hand A Beat Over Only When None Of These Carries It.

| The Beat Needs | Use |
| --- | --- |
| The Real Thing Being Named, Such As A Product, A Page, Or A Document | A Screenshot Or Screen Recording As An Overlay Or A Cutaway |
| A Few Words Or One Number On Screen | A [Transparent Title](TITLES.md) |
| A Closer Look At Part Of A Picture | The Shot's `zoom`, `pan_x`, And `pan_y` Fields |
| Movement That Explains Something, Such As A Process, A Count Rising, Or A Diagram Building | An Animated Insert |

Go Through The Script Or The Cut Beat By Beat And List Every Beat In The Last Row. When The Owner Asked For Animated Graphics, Make This List Without Being Asked Again And Show It To Them With Your Recommendation For Each Beat. An Insert Costs More Time Than An Overlay, So Say Which Ones You Would Skip.

## Write The Shot Brief

Write One Brief Per Insert And Keep It Beside The Timeline. Take Every Number From The Timeline, Never From Memory.

| The Brief States | Where It Comes From |
| --- | --- |
| Frames | The Slot's Length In Whole Frames At The Canvas Rate |
| Rate | `canvas.fps` |
| Size | `canvas.width` And `canvas.height`, And Whether The Clip Fills The Frame Or Sits Over Footage |
| Cue Frames | The Frames Inside The Slot Where An Event Must Land, Counted From The Slot's First Frame And Tied To A Spoken Word |
| Layer Order | What Sits Above The Clip, Such As Captions And The Headline, And Which Regions Must Stay Clear |
| Look | Colors, Type, And Whether The Clip Should Feel Part Of The Footage Or A Clear Graphic Break |
| Neighboring Frames | A Still Of The Frame Before The Slot And The Frame After It |

Make The Neighboring Stills With The Edit's Own Command.

```sh
python scripts/edit_video.py still "First Cut/timeline.json" "First Cut/Before Insert.png" --at 25.9
python scripts/edit_video.py still "First Cut/timeline.json" "First Cut/After Insert.png" --at 31.1
```

## Hand It Over And Hold The Slot

Ask The Animated Video Skill For The Insert And Give It The Brief And The Two Stills. Its Own Guide For This Case Is [Handoffs](../animated-video/HANDOFFS.md). If That Skill Is Not Installed, Tell The Owner, Name The Beats That Wanted An Insert, And Cover Them With A Title Or A Still.

While The Insert Is Being Built, Hold Its Place With A Still Of Its Key Frame As An Image Overlay. The Cut Can Then Be Reviewed For Timing Before The Clip Exists.

## Place What Comes Back

The Clip Is A Video File. The Animation Side Creates It Only After The Owner Has Reviewed The Editable Scene And Approved It. Never Ask For A Test Render Of It.

1. Add The Clip As A Video Asset And Replace The Placeholder Overlay With It, Using The Same `at` And `end`.
2. Add Each Returned Sound Event To `audio[]`. Convert Its Frame To Seconds From The Start Of The Edit.
3. Run `validate` And `check`, Take A Still On Each Cue Frame, And Level The New Cues With `loudness --cues`.
4. Record The Library Entries The Insert Used In The Cut's Declaration When The Asset Library Is In Use.

Approval Of An Insert Is Not Approval Of The Edit. The Owner Still Reviews The Whole Saved Edit In The Editor Before Any Video Export, Including Test And Preview Exports.
