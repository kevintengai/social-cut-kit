# Editorial Cue Bank

These 56 Original Synthesized Sounds Were Designed For Social Cut Kit. The First 33 Are Short Interface Sounds, Sweeps, Low Bumps, And Three Quiet Beds. The 23 Added Sounds Cover Whooshes In Four Weights, A Riser, A Drum Roll, A Stinger, A Deep Impact, Clock Ticks, A Typing Burst, A Register Chime, A Coin, A Second Camera Shutter, A Glitch, An Error Buzz, A Notification, A Pop, And Six Longer Ambience Beds.

Every File Is Mono 16-Bit PCM At 24 kHz. The Timeline Mixer Places A Mono Cue In Both Channels At 48 kHz.

## Choose A Cue

Read `sounds/index.json`. Each Entry Describes One File.

| Field | Meaning |
| --- | --- |
| `file`, `family`, `seconds` | The WAV Name, Its Sound Family, And Its Duration. |
| `tags` | Lowercase Search Words, Such As `whoosh`, `transition`, `money`, Or `loop`. |
| `use` | One Suggested Use. |
| `peak_dbfs`, `rms_dbfs` | Measured Sample Peak And Average Level Of The File At A Gain Of 1. A Full-Scale Sine Reads −3 Average. |
| `overlap_seconds` | On The Six Added Beds, The Length Of The Built-In Fade At Each End. |
| `sha256` | The Digest Of The Shipped File. |

| You Need | Reach For |
| --- | --- |
| A Tap On An Interface Action | `button-down`, `button-up`, `small-switch`, `soft-key`, `counter-step`, `pop-bubble` |
| Movement Across A Cut | `whoosh-light`, `whoosh-medium`, `whoosh-heavy`, `quick-pass`, `soft-swipe`, `long-sweep`, `page-flick`, `focus-shift` |
| A Build Toward A Reveal | `riser-tension`, `drum-roll-build`, `whoosh-reverse` |
| The Reveal Itself | `impact-deep`, `stinger-bright`, `low-drop`, `transition-hit` |
| A Result Or A Message | `success-pair`, `enter-confirm`, `notify-triad`, `notification-bloom`, `glass-point`, `gentle-alert` |
| Money | `register-chime`, `coin-ping`, `receipt-feed` |
| A Mistake Or A Fault | `error-buzz`, `glitch-stutter`, `rubber-stop` |
| Time Passing | `clock-ticks`, `countdown-tick`, `countdown-finish` |
| Typing Or A Device | `typing-burst`, `three-keys`, `dial-turn`, `shutter-mechanical`, `shutter-snap` |
| Presence Under A Gap | `room-tone-warm`, `room-tone-bright`, `soft-room`, `desk-air` |
| A Place | `machine-hum`, `machine-idle`, `night-air`, `water-stream`, `radio-static` |

One Cue Per Event Is Usually Enough. A Playful Sound Over A Sincere Passage Tells The Viewer The Speaker Does Not Mean It. Check The Rejected List In The [Active Brief File](../../BRIEF.md) Before Adding A Sound The Owner Has Already Turned Down.

## Place A Cue

Copy The WAV Into The Project Folder So The Project Stays Portable, Add It As An Audio Asset In The Timeline, And Set Its `at`, `end`, And `gain`. Source Audio Stays On Its Own Track.

```json
{
  "assets": {"whoosh": {"path": "Sounds/whoosh-medium.wav", "kind": "audio"}},
  "audio": [{"asset": "whoosh", "at": 3.7, "end": 4.25, "gain": 0.35}]
}
```

- **Whooshes.** Place The Loudest Point On The Cut. It Sits A Little Past The Middle Of Each File, So Start The Cue About 0.2 Seconds Before The Cut For The Light One, 0.35 For The Medium, And 0.6 For The Heavy.
- **Builds.** End `riser-tension` And `whoosh-reverse` Exactly On The Reveal. Both Stop Dead. In `drum-roll-build`, The Final Hit Lands 1.8 Seconds After The Start.
- **Impacts.** Start `impact-deep` And `stinger-bright` On The Reveal Frame, In A Gap Between Words.
- **Ticks.** `clock-ticks` Holds Six Ticks Half A Second Apart. Repeat It Every 3 Seconds To Continue The Rhythm.
- **Beds.** Each Added Bed Fades In And Out Over 0.25 Seconds. To Extend One, Start The Next Entry 0.25 Seconds Before The Previous One Ends, And The Two Fades Cross Without A Dip. To End A Bed Early, Set `end` Where You Need It And Add A `fade_out`. The Three Original Beds Have Short Edges, So Give Them A `fade_in` And A `fade_out`.

## Level A Cue Against Speech

A Cue's Level In The Index Is Its Level Alone. What Matters Is Its Level Against The Speech Playing At The Same Moment. Start From The Gains Below, Then Measure.

| Kind Of Cue | Starting `gain` | Aim Against Speech |
| --- | --- | --- |
| Taps, Keys, Ticks, And Pops | 0.2 To 0.4 | 12 To 18 dB Under |
| Whooshes And Brushes | 0.25 To 0.5 | 9 To 15 dB Under The Speech On Either Side |
| Bells, Chimes, And Notifications | 0.25 To 0.45 | 10 To 16 dB Under |
| Impacts, Stingers, And Bumps | 0.4 To 0.8 | 3 To 9 dB Under, In A Gap |
| Risers And Rolls | 0.3 To 0.5 | 6 dB Or More Under At Their Loudest |
| Beds | 0.1 To 0.3 | 20 To 30 dB Under |

```sh
python scripts/edit_video.py loudness "First Cut/timeline.json" --cues --cue-aim -12
```

- Run The Command From The Skill Folder. For Each Cue It Reports The Cue Alone, The Speech Under It, And The Difference, Measured In A Short Window At The Cue. A Whole-File Average Cannot Show Whether A Half-Second Sound Is Heard.
- `gain` Is Linear. Halving It Lowers The Cue By 6 dB. `gain_for_aim` In The Report Is The Gain That Reaches The Aim.
- Phone Speakers Reproduce Little Below About 300 Hz. `low-drop`, `low-pulse`, `machine-idle`, And Most Of `machine-hum` Sit There. `impact-deep` And `whoosh-heavy` Carry A Mid Layer So They Still Read On A Phone, At A Lower Level Than Their Numbers Suggest.
- Watch `mix_true_peak_dbtp`. When A Cue Pushes The Mix Toward Full Scale, Lower The Cue.
- Numbers Guide The Level And Ears Decide It. Ask The Owner To Listen On Headphones And On A Phone Speaker During Review. The [Technical Reference](../../TECHNICAL.md#mixing-cues-under-speech) Explains Each Reading.

## Rebuild The Bank

The `sounds/` Folder Contains The PCM WAVs And The Index. To Rebuild The Collection In A New Directory, Run `python build.py fresh-cues` From This Folder. The Generator Uses Only Python's Standard Library And Seeds Each Sound From Its Name Or Position, So Adding A Sound Never Changes Another. The 33 Original Files Are Byte-Identical To Earlier Editions, And The Tests Compare Each Shipped File With Its Digest.
