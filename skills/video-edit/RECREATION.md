# Recreate A Camera Move Or A Cut Pattern

To Apply A Reference’s Pan, Zoom, And Rotation To A Target Clip Automatically, Use [Camera Motion Transfer](CAMERA.md). To Inspect One Moving Detail Or Plan A Similar Shot Manually, Use The Measurement Below.

Choose A Source You Have Permission To Analyze. Record The Aspect Ratio, Beat Timing, Focal Point, And Camera Movement In A Shot Board. Use Your Own Footage, Copy, And Artwork For The New Piece.

Pick A High-Contrast Detail That Stays In The Frame Through A Single Shot. Read Its Initial X And Y As Fractions Of Picture Width And Height. Run `python scripts/reference_track.py reference.mp4 --point 0.48 0.32 --start 1 --seconds 3`. Inspect The Reported Positions Against The Source. Low Texture, Occlusion, A Scene Change, Or A Fast Zoom May End The Track. A Tracked Subject Can Move Even When The Camera Is Still. Use The Positions As Measurements, Then Set The Framing On Your Own Shot.

For Long Recordings With Repeated Attempts, Run `python scripts/takes.py words.json --words 3 --window 30`. Audition Each Pair With Its Audio Handles. Choose The Take That Finishes The Thought And Carries The Intended Performance. A Repeated Phrase Can Be Intentional Emphasis. Check The Finish Of Each Word At Playback Speed Before Committing The Cut.
