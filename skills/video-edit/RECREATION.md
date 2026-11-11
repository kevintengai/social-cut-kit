# Recreate A Camera Move Or A Cut Pattern

To Apply A Reference’s Pan, Zoom, And Rotation To A Target Clip Automatically, Use [Camera Motion Transfer](CAMERA.md). To Inspect One Moving Detail Or Plan A Similar Shot Manually, Use The Measurement Below.

Choose A Source You Have Permission To Analyze. Record The Aspect Ratio, Beat Timing, Focal Point, And Camera Movement In A Shot Board. Use Your Own Footage, Copy, And Artwork For The New Piece.

Pick A High-Contrast Detail That Stays In The Frame Through A Single Shot. Read Its Initial X And Y As Fractions Of Picture Width And Height. Run `python scripts/reference_track.py reference.mp4 --point 0.48 0.32 --start 1 --seconds 3`. Inspect The Reported Positions Against The Source. Low Texture, Occlusion, A Scene Change, Or A Fast Zoom May End The Track. A Tracked Subject Can Move Even When The Camera Is Still. Use The Positions As Measurements, Then Set The Framing On Your Own Shot.

## Repeated Takes And Full Retakes

For Long Recordings With Repeated Attempts, Run `python scripts/takes.py words.json --words 3 --window 30`. It Lists Each Short Phrase That Is Said Again Within The Window. Audition Each Pair With Its Audio Handles. Choose The Take That Finishes The Thought And Carries The Intended Performance. A Repeated Phrase Can Be Intentional Emphasis. Check The Finish Of Each Word At Playback Speed Before Committing The Cut.

That Search Only Sees Repeats Close Together. Add `--retakes` To Also Group Whole Passages Performed Several Times Anywhere In The Recording, Such As A Sentence Recorded Again Minutes Later Or An Ending Performed Three Times. Add `--script` To Align Every Attempt Against The Lines Of A Plain Text Script. Without Either Option The Output Is The Same List As Before.

```sh
python scripts/takes.py words.json --retakes
python scripts/takes.py words.json --script script.txt --min-words 5 --gap 0.7 --handle 0.15
```

| Option | Effect |
| --- | --- |
| `--retakes` | Print A Report Object With `retakes`, The Groups Of Attempts At The Same Line, And `nearby_repeats`, The List The Tool Prints Without This Option. |
| `--script script.txt` | Also Print `script`, With The Attempts Found For Each Script Line. This Turns On `--retakes`. Stage Directions In Brackets, Labels Such As `HOOK:`, List Marks, And Timecodes Are Ignored. |
| `--min-words 5` | The Fewest Shared Words For Two Passages To Count As The Same Line. A Passage That Opens With The Same Words As Another Also Counts, So A Short False Start Is Still Found. |
| `--gap 0.7` | A Silence At Least This Long Ends A Passage. A Passage Also Ends At Sentence Punctuation, At A Word That Trails Off With A Dash Or An Ellipsis, And Where Its Opening Words Are Said Again. |
| `--words 3`, `--window 30`, `--handle 0.15` | The Phrase Length For A Repeat Or Restart, The Window For Nearby Repeats, And The Audio Handle In Seconds. |

Each Attempt Carries These Fields.

| Field | Meaning |
| --- | --- |
| `source_seconds`, `audition_range`, `handles` | The Attempt In Source Time, The Range To Listen To, And The `lead` And `tail` That Produce It. Each Handle Stops Short Of The Neighboring Word, So It Never Lets In The End Of The Previous Word Or The Start Of The Next. Copy Them Into The Shot. |
| `reaches_sentence_end` | Whether The Attempt Ends On Sentence Punctuation. Null When The Transcript Has No Punctuation. |
| `interrupted` | True When The Attempt Trails Off, Or The Speaker Starts The Same Words Again Right After It. |
| `hint` | `complete`, `interrupted`, Or `no_sentence_end`. Without Punctuation It Is `ends_at_a_pause` Or `runs_on`. |
| `share_of_longest_attempt` | The Attempt's Word Count Against The Longest Attempt In Its Group. A Low Share Marks A Fragment. |
| `split_at_repeat` | The Passage Was Divided Where Its Opening Words Were Said Again Inside One Sentence. This Can Be A Restart Or Deliberate Parallel Phrasing, So Listen First. |
| `script_coverage`, `reaches_line_end`, `wording_differs_from_script` | With `--script`: The Share Of The Script Line's Words Found In The Attempt, Whether It Reaches The Line's Last Words, And Whether A Complete Take Uses Different Wording. |

Each Group And Each Script Line Carries A `decision`.

| `decision` | What To Do |
| --- | --- |
| `one_complete_take` | Audition That Take, Then Use It. |
| `owner_choice` | Several Attempts Are Equally Complete. Offer The Owner The Choice. Recommend `latest_complete_take`, And Give The Source Times Of Each. |
| `no_complete_take` | Tell The Owner The Line Has No Clean Take, And Ask Whether To Drop It, Use The Best Partial Take, Or Record It Again. |
| `not_spoken` | The Script Line Was Not Found In The Recording. Do Not Build It From Fragments. |

`lines_without_a_complete_take` Collects The Last Two Cases, And `spoken_but_not_in_script` Lists Passages Of Four Or More Words That Match No Script Line.

- **The Agent Cannot Hear Performance.** Every Hint Comes From Words And Times. It Cannot Judge Energy, A Stumble Inside A Word, A Breath, Or A Smile. When Attempts Are Equally Complete, Offer The Owner The Choice And Never Pick Silently.
- The Script Is A Reference, Not A Word List To Enforce. [The Script Or Outline](BRIEF.md#the-script-or-outline) Says What To Do When The Spoken Words Depart From It.
- Completeness Depends On The Transcript. A Recognizer Can Add A Period To A Sentence That Was Cut Short, Or Miss One. Audition Every Range Before Committing A Cut.
- A Subtitle File Gives Cue Times, Not Word Times. The Report Counts Those Units As `estimated_word_timings`, And Its Ranges Are Then Approximate.
