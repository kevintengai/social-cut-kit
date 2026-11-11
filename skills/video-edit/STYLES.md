# Editing Styles

A Style Is A Set Of Choices On Six Layers. Pick It By Looking At The Footage, The Goal, And A Reference If One Exists, Then Read Only The Guides This Video Uses. A Style Guide Gives A Starting Point. The Brief And The User's Saved Defaults Win Over It.

## The Six Layers

Answer One Question Per Layer Before Cutting. Write The Answers In The [Active Brief File](BRIEF.md) So A Later Session Continues The Video You Planned.

| Layer | The Question | Common Answers | Where It Lives In This Kit |
| --- | --- | --- | --- |
| Clock | What Decides When A Cut Or Change Happens? | Speech, A Music Track, A Visible Action, Or The Reading Time Of An On-Screen Line | Word Timings From The [Speech Tools](SPEECH.md), Silences From `analyze`, Or Beat Times The Owner Supplies |
| Payoff | How Does Each Beat Reward The Viewer? | A Visual On Its Word, A Result After An Action, A Reaction After A Set-Up, A Reveal After A Question | Shot Order, Overlay Start Times, And Holds |
| Picture | What Does The Viewer See, And What Is The Camera Doing? | A Speaker At Full Height, A Screen Capture, One Held Shot, Cutaways, Locked Off Or Handheld | `shots[]` With `fit`, `zoom`, `pan_x`, And `pan_y`, Plus [Camera Transfer](CAMERA.md) |
| Words | What Words Are On Screen? | A Hook Headline, Running Captions, Labels, One Line That Carries A Joke, Or None | `captions[]` And [Title Overlays](TITLES.md) |
| Sound | What Carries The Energy In Sound? | The Voice Alone, A Music Bed, One Song Phrase, Sparse Cues, Or Silence Before A Cut | Shot `gain`, `audio[]`, And The [Cue Bank](assets/cue-bank/README.md) |
| Effects | Which Effects Land On Picture Beats? | A Punch-In, A Speed Change, A Color Shift, An Overlay Arriving | Split Shots With `zoom`, `speed`, Or The Color Fields |

The Clock Matters Most Because It Defines A Good Cut. On A Speech Clock A Cut Is Right When The Phrase Is Complete. On A Music Clock It Is Right On The Beat. On An Action Clock It Is Right When The Action Finishes. A Section That Tries To Obey Two Clocks Lands Its Cuts On Neither.

## Choose A Style

Read The Footage Before The Adjectives In The Request. Run `probe` And `analyze`, Read Any Transcript, And Look At Stills. What Was Filmed Narrows The Choice More Than Taste Does.

1. **Footage.** A Person Speaking To The Lens For Most Of The Recording Is A Talking Head. Takes Played To Camera Without Dialogue Are A Skit. A Screen Recording, Or A Product Shown On A Screen, Is A Screen Demo. Mixed Footage Becomes Sections, Each With Its Own Style.
2. **Goal.** Ask What The Viewer Should Believe Or Do At The End. Teaching And Arguing Favor A Speech Clock. Proof Favors The Screen And Its Result. Recognition And Sharing Favor The Skit.
3. **Reference.** When The Owner Supplies A Reference They Have Permission To Have Analyzed, Study Its Timing And Structure One Layer At A Time. Note Shot Lengths, When Text Appears, And What The Sound Does. The [Reference Tools](RECREATION.md) Measure A Move Or A Cut Pattern. Build The New Video From The Owner's Footage, Words, And Artwork. Nothing Taken From The Reference Itself Goes Into The Edit.

| Style | It Fits When | Clock | Guide |
| --- | --- | --- | --- |
| Talking Head | A Person Speaks To Camera And The Words Carry The Value | Speech | [Talking Head](styles/talking-head.md) |
| Skit Or Meme Reel | Silent Acting Or A Reaction Clip, Where A Single Line Of Text Holds The Joke And The Audio Supplies The Energy | The Sound, And The Reading Time Of The Line | [Skit](styles/skit.md) |
| Screen Demo | The Product Or Its Result On A Screen Is The Proof | The Action On Screen | [Screen Demo](styles/screen-demo.md) |

## A Style Without A Guide

Build It From The Same Six Layers. Write One Line Per Layer, Borrow The Matching Section Of The Nearest Guide, And Say What Is New. Three Worked Examples Follow.

| Video | Clock | Payoff | Picture | Words | Sound | Effects |
| --- | --- | --- | --- | --- | --- | --- |
| Montage Cut To Music | The Beats Of The Track | The Strongest Image On Each Strong Beat | Short Shots At Varied Scale, With Movement Continuing Across Cuts | One Title Or None | The Track Alone, With Source Sound Muted | Speed Changes That Resolve On A Beat |
| Before And After | The Action, Then A Hold | The After State, Framed Like The Before | Matched Framing, So Only The Subject Changes | Two Labels | Quiet Until The Reveal, Then One Cue | One Cut Or One Punch-In At The Reveal |
| Two-Person Interview Clip | Speech | An Answer That Completes Its Question | Each Speaker At Full Height, Cutting As The Speaker Changes | Captions And A Name Label | Both Voices As Recorded | Few Or None |

A Layer With No Good Answer Is The Weak Point Of The Plan. Resolve It With The Owner Before Cutting.

## Mixing Styles In One Video

- **One Clock Per Section.** Name Each Section And Its Clock In The Brief. A Change Of Clock Starts A New Section. A Talking Head That Becomes A Five-Second Music Montage And Then Returns Has Three Sections, And Each Is Cut By Its Own Rule.
- **A Borrowed Layer Must Fix A Real Weakness.** Borrow The Skit's Single On-Screen Line When A Spoken Opening Takes Too Long To State Its Promise. Borrow The Screen Demo's Zoom On The Result When A Speaker Quotes A Figure The Viewer Should See. If You Cannot Name The Weakness, Leave The Layer Out.
- **Make Each Seam A Deliberate Change.** Change Style Where The Outgoing Clock Completes Something, Such As The End Of A Sentence, A Bar Line, Or A Finished Action. Change Picture And Sound Together So The Seam Reads As A Decision. Carry One Constant Across It, Such As The Caption Style, The Voice, Or The Color, So The Video Still Reads As One Piece.
- **Check Each Seam.** Inspect The Last Word Before It And The First Word After It, Compare Loudness On Both Sides, And Recheck Every Overlay, Caption, And Cue That Sits Near It.

## What Overrides A Style Guide

1. The Owner's Current Instructions And The Verified Corrections In The Brief File.
2. The User's Saved Defaults, Such As Their Caption Look, Hook Format, And Cover Rules.
3. The Starting Values In The Style Guide.
4. This Index.

Numbers In A Guide Are Starting Values. When You Depart From One, Note The Reason In The Brief File So The Next Session Does Not Put It Back.

## Rules That Hold In Every Style

- **Owner Review.** The Project Owner Personally Reviews The Saved, Editable Project In The Editor Before Any Video File Is Created. That Includes Test And Preview Exports. Agent Checks Do Not Replace That Review. Before Approval, Check With Single Frames From `still`, The Null-Sink Decodes From `check` And `loudness`, And Playback In `review`.
- **Source Audio.** The Owner's Original Dialogue Stays As Recorded By Default. Gain Changes, Noise Reduction, And Any Other Processing Are Opt-In.
- **Rights.** Use Only Footage, Clips, Music, And Sounds The Owner Has The Right To Use, And Record Each Source In The [Asset Library](../asset-library/SKILL.md). A Reference Video Is Studied With Permission And Never Lifted.

Read Only The Guides A Video Uses. A Talking Head With One Screen Insert Needs The Talking Head Guide And The Legibility Section Of The Screen Demo Guide. It Does Not Need The Skit Guide.
