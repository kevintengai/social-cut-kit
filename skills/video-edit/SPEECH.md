# Speech And Take Preparation

If A Source Has A Word-Timed Transcript, Use It Directly. Otherwise Run A Locally Installed Speech Recognizer. The Toolkit Can Call An Installed Whisper CLI Or Use The Optional `faster-whisper` Python Package. Models Are Supplied Separately. A Local Model Folder Can Be Passed To `--model` To Work Offline.

```sh
python scripts/speech.py transcribe interview.wav words.json --backend faster-whisper --model /path/to/model --language en
python scripts/speech.py captions words.json edit.json --asset interview --with-timeline --output captioned.json
python scripts/speech.py sync camera.mp4 recorder.wav --seconds 30 --lag 5
python scripts/speech.py levels interview.wav
```

The Caption Mapper Also Accepts SRT And WebVTT. It Distributes Fully Contained Words Or Subtitle Cues Across Repeated Shots, Handles, And Playback Speed Changes. Inspect The Count Of Speech Units Crossing Cut Boundaries. Move The Cut Outward Or Refine The Transcript Timing To Keep A Word Intact. Spot Check The Actual Audio When A Speaker Pauses Or Repeats A Line.

For External Audio, A Positive `secondary_event_later_by_seconds` Means The Matching Event Occurs Later In The Secondary File. Trim That Much At The Start Of The Secondary Track To Align The Two. Validate Two Distinct Transients Far Apart In The Take To Check For Drift. For Weak Or Repetitive Signals, Compare The Strongest Correlation To The Next Distinct Peak And Listen In The Editor.

Measure Available Gain Before Boosting A Quiet Track. When Gain Would Overload A Peak, Use Source Selection Or The Editor’s Dynamics Controls. Preserve Original Stereo Channels And Leave Natural Speech Handles.
