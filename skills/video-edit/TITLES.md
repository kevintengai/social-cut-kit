# Transparent Title Overlays

Use [The Title Helper](scripts/titles.py) To Make A Frame-Sized Transparent PNG For A Headline Or Callout. It Runs With Python 3.9 Or Later And A Local Chrome, Chromium, Or Edge Installation. The Helper Uses Installed Fonts And A Temporary Browser Profile. Pass `--browser` When The Executable Is In A Custom Location.

Run From The Video Edit Skill Folder. Choose A Canvas Matching The Editable Project.

```text
python scripts/titles.py --text "Inside The Edit" --highlight "Edit" --width 1080 --height 1920 --position top --style box --out opening.png
python scripts/titles.py --text "Listen Here" --highlight "Listen" --width 1920 --height 1080 --align right --position bottom --style plain --size 84 --out callout.png
```

For Fixed Line Breaks, Save The Following Two Lines As A UTF-8 File Named `title.txt`.

```text
Watch The Timing
On This Cut
```

```text
python scripts/titles.py --text-file title.txt --highlight "Timing" --align left --margin 90 --padding 28 --size 76 --out timing.png
```

The Text Preserves Supplied Spelling And Case. The Highlight Matches Every Whole Occurrence Of The Word Or Phrase, Ignoring Case. Long Lines Wrap Inside The Margin. If The Title Overflows, Adjust The Font Size, Margin, Or Canvas And Run Again. The Helper Protects Existing Files Unless You Supply `--overwrite`.

- `--align` Positions The Block And Aligns Its Lines Horizontally. `--position` Places It At The Top, Center, Or Bottom Of The Canvas. Both Use The Margin Measured In Pixels.
- `--style box` Places A Rounded Plate Behind The Text. `--style plain` Draws A Dark Text Outline For Contrast. Set `--ink`, `--accent`, And `--plate-color` With Quoted Six-Digit Hex Colors.
- Select An Installed Face With `--font-family`. Emoji Use The Browser's Native Font Fallback. Appearance And Glyph Coverage Depend On The Machine. Inspect Any Emoji And Custom Colors In The Editor At Delivery Size.
- Place The PNG Above The Footage At Its Original Frame Size And Position. Set Its Start And End Times In The Editable Timeline. The Transparent Area Lets The Footage Show Through.
