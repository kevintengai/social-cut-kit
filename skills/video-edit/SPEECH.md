# Speech And Take Preparation

If A Source Has A Word-Timed Transcript, Use It Directly. Otherwise Run A Locally Installed Speech Recognizer. The Toolkit Can Call An Installed Whisper CLI Or Use The Optional `faster-whisper` Python Package. Models Are Supplied Separately. A Local Model Folder Can Be Passed To `--model` To Work Offline. The Setup Check Reports Which Recognizer Is Present. If The Package Cannot Open A File Itself, The Toolkit Decodes The Sound With FFmpeg And Hands It The Samples.

```sh
python scripts/speech.py transcribe interview.wav words.json --backend faster-whisper --model /path/to/model --language en
python scripts/speech.py captions words.json edit.json --asset interview --with-timeline --output captioned.json
python scripts/speech.py sync camera.mp4 recorder.wav --seconds 30 --lag 5
python scripts/speech.py levels interview.wav
```

The Caption Mapper Also Accepts SRT And WebVTT. It Distributes Fully Contained Words Or Subtitle Cues Across Repeated Shots, Handles, And Playback Speed Changes. Inspect The Count Of Speech Units Crossing Cut Boundaries. Move The Cut Outward Or Refine The Transcript Timing To Keep A Word Intact. Spot Check The Actual Audio When A Speaker Pauses Or Repeats A Line.

For External Audio, A Positive `secondary_event_later_by_seconds` Means The Matching Event Occurs Later In The Secondary File. Trim That Much At The Start Of The Secondary Track To Align The Two. Validate Two Distinct Transients Far Apart In The Take To Check For Drift. For Weak Or Repetitive Signals, Compare The Strongest Correlation To The Next Distinct Peak And Listen In The Editor.

Measure Available Gain Before Boosting A Quiet Track. When Gain Would Overload A Peak, Use Source Selection Or The Editor’s Dynamics Controls. Preserve Original Stereo Channels And Leave Natural Speech Handles.

## Phrase Captions

Without The Options Below, The Mapper Writes Sentence-Length Cues Exactly As Before. Add `--phrases`, Or Any Single Phrase Option, To Group Word Timings Into Short On-Screen Phrases.

```sh
python scripts/speech.py captions words.json edit.json --asset interview --phrases --output phrases.json
python scripts/speech.py captions words.json edit.json --asset interview --max-words 3 --max-chars 22 --pause 0.35 --min-seconds 0.4 --fix "tang=Teng" --fix "chat gpt=ChatGPT" --position center --with-timeline --replace-existing --output phrased.json --srt Phrases.srt
```

| Option | Effect |
| --- | --- |
| `--phrases` | Turn On Phrase Grouping With The Defaults In This Table. |
| `--max-words 4` | The Most Words In One Phrase. A Rejoined Number Counts As One Word. |
| `--max-chars 28` | The Most Characters In One Phrase. A Single Longer Word Still Gets Its Own Phrase. |
| `--pause 0.4` | A Silence At Least This Long Between Two Words Starts A New Phrase. Shorter Gaps Between Phrases Are Closed So The Text Does Not Flicker. |
| `--sentence-breaks on` | Start A New Phrase After A Period, A Question Mark, Or An Exclamation Mark. Titles Such As Dr. And Lone Initials Do Not Count. Use `off` To Let A Phrase Run Across A Sentence End. |
| `--join-numbers on` | Rejoin One Spoken Number That The Recognizer Split, Such As `$2` With `,000`, `3` With `.5`, Or `50` With `%`. Use `off` To Keep The Fragments. |
| `--fix "heard=shown"` | Change Spelling In The Captions Only. Matching Ignores Case And Surrounding Punctuation. Repeat The Option For More Fixes, Use Several Words On Either Side, Or Leave The Shown Side Empty To Drop A Filler Word. The Transcript File Is Never Changed. |
| `--fixes fixes.json` | Read The Same Fixes From A JSON Object Of Heard Text To Shown Text. |
| `--min-seconds 0.3` | The Shortest Time A Phrase Stays On Screen. A Short Phrase Is Extended Into Free Time Only, Up To The Next Phrase, The Cut, Or The End Of The Edit. |
| `--position bottom` | Caption Position For The New Cues: `top`, `center`, Or `bottom`. |
| `--srt Phrases.srt` | Also Write The New Cues To A New SubRip File. |
| `--replace-existing` | With `--with-timeline`, Remove Existing Captions At The Same Position Before Adding The New Ones. Use It When Regenerating Captions After A Recut. |

Every Phrase Starts And Ends On An Output Frame. A Phrase Never Crosses A Cut, Never Overlaps Another Phrase, Never Starts Before Its Shot, And Never Ends After The Edit.

### Read The Report

The Command Prints A JSON Report. Act On Three Lists Before Showing The Captions To The Owner.

- `clamped_words` Lists Each Word A Cut Trimmed That Still Appears In A Caption, Because Most Of The Word Plays Inside The Shot. Each Entry Gives The Shot, The Source Seconds, The Part That Was Kept, And The Edit Seconds. When `sound_continues_across_cut` Is `true`, The Cut Only Splits One Continuous Take, As A Punch-In Does, And The Word Is Heard In Full. When It Is `false`, Listen At The Listed Edit Time. Move The Cut Outward With A Handle If The Word Is Clipped.
- `dropped_words` Lists Each Word That Touches A Shot Without Appearing In Its Captions, Because Most Of The Word Was Cut Away. Listen There For A Stray Syllable.
- `below_minimum_time` Lists Phrases That Could Not Reach The Minimum Time Because The Next Phrase Or The Cut Came First. Raise `--max-words`, Or Accept The Short Phrase.

`estimated_word_timings` Counts Transcript Units That Carried Several Words, Such As Subtitle Cues. Their Word Times Are Spread Evenly Inside Each Unit, So Check Phrase Timing Near Cuts More Carefully Or Transcribe With Word Timestamps.

### Carry Phrases Into The Hand-Off

Write The Phrases Into A New Timeline With `--with-timeline`. From That Timeline, `captions` Writes The SubRip File, `handoff` Carries Each Phrase As A Marker In The OpenTimelineIO File, The [Native Resolve Build](RESOLVE.md) Creates An Editable Text+ Title Per Phrase, And `check` Renders Them Into The Null Sink.

```sh
python scripts/edit_video.py captions phrased.json Dialogue.srt
python scripts/edit_video.py handoff phrased.json Assembly.otio
python scripts/edit_video.py check phrased.json
```

After Any Change To A Shot's In Point, Out Point, Handles, Or Speed, Run The Mapper Again From The Uncaptioned Timeline Or With `--replace-existing`. Caption Times Are Edit Times And Do Not Follow A Recut By Themselves. To Confirm The Captions Against What Is Actually Heard, Transcribe A Check Mix As [The Technical Reference](TECHNICAL.md#checking-a-correction-without-exporting) Describes.
