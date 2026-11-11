"""Locate Repeated Phrase Attempts And Suggest Speech-Safe Take Handles."""

import argparse
import json
from pathlib import Path
import re
from speech import load_words


def candidates(words, phrase, window, handle):
    normalize = lambda t: re.findall(
        r"[^\W_]+(?:['’][^\W_]+)*", t.casefold(), flags=re.UNICODE
    )
    tokens = []
    for s, e, w in words:
        # Subtitle cues can contain multiple words but supply only cue-level boundaries.
        tokens.extend((t, s, e) for t in normalize(w))
    occurrences = {}
    for i in range(len(tokens) - phrase + 1):
        span = tokens[i : i + phrase]
        if span[-1][2] - span[0][1] > phrase * 2:
            continue
        key = tuple(t[0] for t in span)
        occurrences.setdefault(key, []).append((i, span[0][1], span[-1][2]))
    choices = []
    for key, runs in occurrences.items():
        for first, second in zip(runs, runs[1:]):
            i, s, e = first
            j, t, u = second
            if not (i + phrase <= j and e <= t <= e + window):
                continue
            if i > 0 and j > 0 and tokens[i - 1][0] == tokens[j - 1][0]:
                continue
            choices.append(
                {
                    "phrase": " ".join(key),
                    "first_attempt": [s, e],
                    "next_attempt": [t, u],
                    "audition_ranges": [
                        [round(max(0, s - handle), 3), round(e + handle, 3)],
                        [round(max(0, t - handle), 3), round(u + handle, 3)],
                    ],
                }
            )
    return sorted(choices, key=lambda c: c["first_attempt"][0])


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("transcript", type=Path)
    p.add_argument("--words", type=int, default=3)
    p.add_argument("--window", type=float, default=30)
    p.add_argument("--handle", type=float, default=0.15)
    a = p.parse_args()
    if not 2 <= a.words <= 12 or not 0 < a.window <= 3600 or not 0 <= a.handle <= 5:
        p.error("Check Phrase Length, Window, And Audio Handle.")
    try:
        print(
            json.dumps(
                candidates(load_words(a.transcript), a.words, a.window, a.handle),
                indent=2,
                ensure_ascii=False,
            )
        )
    except (ValueError, KeyError, OSError, TypeError) as exc:
        p.exit(1, f"{exc}\n")
