"""Measure The Composed Mix Through A Null Sink And Plan One Linear Gain Toward A Loudness Target."""

import re
import subprocess
import tempfile
from pathlib import Path

from media import decimal, process, run_graph, sound_graph
from timeline import EditError, binary

TARGET_LUFS = -14.0
CEILING_DBTP = -1.5
METER = "ebur128=peak=true:framelog=verbose,volumedetect"
CHANGE = ("One Constant Gain Multiplies The Whole Mix, Speech Included. No Compression, Limiting, Or "
          "Equalization Is Applied, So The Balance Between Speech And Cues Stays As Reviewed.")


def read_meter(log):
    """Read The EBU R 128 Summary And The Sample Statistics FFmpeg Prints When The Stream Ends."""
    summary = log[log.rfind("Summary:"):] if "Summary:" in log else ""

    def value(pattern, text):
        found = re.search(pattern, text)
        try:
            return float(found[1]) if found else None
        except ValueError:
            return None

    integrated = value(r"\bI:\s+(-?[\d.]+|-?inf|nan) LUFS", summary)
    spread = value(r"\bLRA:\s+(-?[\d.]+|-?inf|nan) LU", summary)
    peak = value(r"\bPeak:\s+(-?[\d.]+|-?inf|nan) dBFS", summary)
    mean = value(r"mean_volume:\s+(-?[\d.]+) dB", log)
    top = value(r"max_volume:\s+(-?[\d.]+) dB", log)
    if not summary or integrated is None:
        raise EditError("FFmpeg Did Not Report A Loudness Summary. Check That The Build Includes The ebur128 Filter.")
    # The Meter Reports Minus 70 LUFS Until One 400 Millisecond Block Passes Its Gate.
    measurable = integrated == integrated and integrated > -69.95
    finite = peak is not None and peak == peak and peak != float("-inf")
    quiet = mean is None or mean <= -90
    return {"integrated_lufs": integrated if measurable else None,
            "loudness_range_lu": spread if measurable and spread == spread else None,
            "true_peak_dbtp": peak if finite else None,
            "rms_dbfs": None if quiet else mean,
            "sample_peak_dbfs": None if quiet or top is None else top}


def measure(model, layer="mix", start=None, seconds=None, master_gain=None):
    """Decode Only The Sound Of The Edit And Meter It. No File Is Written."""
    inputs, expression = sound_graph(model, layer, start, seconds, master_gain)
    with tempfile.TemporaryDirectory(prefix="social-cut-") as tmp:
        result = run_graph(Path(tmp), inputs, expression + METER + "[measured]",
                           ["-map", "[measured]", "-f", "null", "-"], level="info")
    return read_meter(result.stderr)


def measure_file(path):
    """Meter The First Audio Stream Of A Finished File Through A Null Sink."""
    args = [binary("ffmpeg"), "-hide_banner", "-loglevel", "info", "-nostdin", "-nostats", "-i", str(path),
            "-map", "0:a:0", "-af", METER, "-f", "null", "-"]
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode:
        raise EditError(result.stderr.strip()[-4000:] or "Could Not Measure The File.")
    return read_meter(result.stderr)


def check_targets(target, ceiling):
    for value, name, low, high in ((target, "Loudness Target", -40, -5), (ceiling, "True Peak Ceiling", -60, 0)):
        if not isinstance(value, (int, float)) or value != value or not low <= value <= high:
            raise EditError(f"{name} Must Be A Number Between {low} And {high}.")


def gain_plan(measured, target=TARGET_LUFS, ceiling=CEILING_DBTP):
    """The Single Gain That Moves The Measured Mix To The Target, And Whether It Fits Under The Ceiling."""
    check_targets(target, ceiling)
    plan = {"target_lufs": target, "true_peak_ceiling_dbtp": ceiling, "gain_db": None, "linear_gain": None,
            "true_peak_after_gain_dbtp": None, "breaches_ceiling": None,
            "largest_gain_within_ceiling_db": None, "loudness_at_largest_gain_lufs": None}
    integrated, peak = measured["integrated_lufs"], measured["true_peak_dbtp"]
    if integrated is None or peak is None:
        plan["note"] = "The Mix Is Silent Or Shorter Than The Meter Needs, So No Gain Can Be Planned."
        return plan
    gain = round(target - integrated, 2)
    room = round(ceiling - peak, 2)
    plan.update(gain_db=gain, linear_gain=round(10 ** (gain / 20), 6),
                true_peak_after_gain_dbtp=round(peak + gain, 2), breaches_ceiling=gain > room + 1e-9,
                largest_gain_within_ceiling_db=room, loudness_at_largest_gain_lufs=round(integrated + room, 2))
    if plan["breaches_ceiling"]:
        plan["note"] = (f"Reaching {decimal(target)} LUFS Needs {signed(gain)} dB, Which Would Put The True Peak At "
                        f"{signed(peak + gain)} dBTP, Above The {decimal(ceiling)} dBTP Ceiling. The Largest Gain "
                        f"That Fits Is {signed(room)} dB, Which Gives {decimal(round(integrated + room, 2))} LUFS. "
                        "Lower The Loudest Peak In The Edit To Go Further.")
    else:
        plan["note"] = (f"A Gain Of {signed(gain)} dB Reaches {decimal(target)} LUFS With The True Peak At "
                        f"{signed(peak + gain)} dBTP, Inside The {decimal(ceiling)} dBTP Ceiling.")
    return plan


def signed(value):
    value = round(value, 2)
    return ("+" if value > 0 else "") + decimal(value)


def reading(difference):
    """A Rule Of Thumb For How A Cue Sits Against Speech In The Same Window. Listen Before Deciding."""
    if difference >= 3:
        return "Louder Than Speech. Expect It To Cover Words."
    if difference >= -6:
        return "Close To Speech Level. Prominent."
    if difference >= -18:
        return "Under Speech. Audible As Support."
    if difference >= -26:
        return "Well Under Speech. Subtle, And It May Vanish On A Phone Speaker."
    return "Likely Masked By Speech."


def cue_levels(model, window=3.0, aim=None):
    """Compare Each Added Cue With The Speech Under It Across A Short Window At The Cue."""
    if not isinstance(window, (int, float)) or not 0.05 <= window <= 60:
        raise EditError("Cue Window Must Be A Number Between 0.05 And 60.")
    if aim is not None and (not isinstance(aim, (int, float)) or not -60 <= aim <= 12):
        raise EditError("Cue Aim Must Be A Number Between -60 And 12.")
    rows = []
    for number, cue in enumerate(model["audio"], 1):
        start = cue["at"]
        seconds = min(window, cue["end"] - cue["at"])
        alone = measure(dict(model, audio=[cue]), "cues", start, seconds)
        speech = measure(model, "voice", start, seconds)
        together = measure(model, "mix", start, seconds)
        cue_level, speech_level = alone["rms_dbfs"], speech["rms_dbfs"]
        row = {"cue": number, "asset": cue["asset"], "at": cue["at"], "end": cue["end"], "gain": cue["gain"],
               "window_seconds": [start, round(start + seconds, 6)],
               "cue_rms_dbfs": cue_level, "speech_rms_dbfs": speech_level, "cue_minus_speech_db": None,
               "mix_true_peak_dbtp": together["true_peak_dbtp"]}
        if cue_level is None:
            row["reading"] = "The Cue Is Silent In This Window."
        elif speech_level is None:
            row["reading"] = "No Speech In This Window. The Cue Plays In The Clear."
        else:
            difference = round(cue_level - speech_level, 1)
            row.update(cue_minus_speech_db=difference, reading=reading(difference))
            if aim is not None:
                # The Timeline Accepts Gains From 0 To 4.
                row["gain_for_aim"] = round(min(4.0, cue["gain"] * 10 ** ((aim - difference) / 20)), 4)
        rows.append(row)
    return rows


def report(model, target=TARGET_LUFS, ceiling=CEILING_DBTP, layer="mix", start=None, seconds=None,
           cues=False, window=3.0, aim=None):
    check_targets(target, ceiling)
    result = {"layer": layer}
    if start is not None:
        result["window_seconds"] = [start, round(start + seconds, 6)]
    result.update(measure(model, layer, start, seconds))
    if layer == "mix" and start is None:
        result.update(gain_plan(result, target, ceiling))
    if cues:
        result["cues"] = cue_levels(model, window, aim)
    return result


def render(model, output, burn=True, target=TARGET_LUFS, ceiling=CEILING_DBTP, over="refuse"):
    """Encode The Approved Edit With One Linear Gain Toward The Target, Then Meter The Finished File."""
    if over not in ("refuse", "cap"):
        raise EditError(f"Unsupported Ceiling Choice {over}.")
    # Refuse A Bad Destination Before Spending Time On The Measurement.
    if output.suffix.lower() != ".mp4":
        raise EditError("Choose An MP4 Output Filename.")
    if output.resolve().exists():
        raise EditError(f"Output Already Exists {output.resolve()}.")
    before = measure(model)
    plan = gain_plan(before, target, ceiling)
    if plan["gain_db"] is None:
        raise EditError(plan["note"] + " Render Without --loudness-target.")
    gain, capped = plan["gain_db"], False
    if plan["breaches_ceiling"]:
        if over == "refuse":
            raise EditError(plan["note"] + " Nothing Was Rendered. Add --if-over-ceiling cap To Apply The Largest "
                            "Gain That Fits, Or Render Without --loudness-target.")
        gain, capped = plan["largest_gain_within_ceiling_db"], True
    linear = round(10 ** (gain / 20), 6)
    process(model, output, burn, master_gain=linear)
    after = measure_file(output.resolve())
    peak = after["true_peak_dbtp"]
    result = {"target_lufs": target, "true_peak_ceiling_dbtp": ceiling,
              "measured_mix": {key: before[key] for key in ("integrated_lufs", "loudness_range_lu", "true_peak_dbtp")},
              "applied_gain_db": gain, "applied_linear_gain": linear, "capped_at_ceiling": capped,
              "finished_file": {key: after[key] for key in ("integrated_lufs", "loudness_range_lu", "true_peak_dbtp")},
              "finished_within_ceiling": peak is None or peak <= ceiling + 1e-9, "what_changed": CHANGE}
    if capped:
        result["note"] = (f"The Target Needed {signed(plan['gain_db'])} dB. The Gain Was Capped At {signed(gain)} dB "
                          "To Keep The True Peak Under The Ceiling, So The File Is Quieter Than The Target.")
    if not result["finished_within_ceiling"]:
        result["note"] = (result.get("note", "") + " The Encoded True Peak Is "
                          f"{signed(peak)} dBTP, Above The Ceiling. Lossy Encoding Can Raise Peaks Slightly. "
                          "Choose A Lower Ceiling For The Next Approved Render If The Platform Requires It.").strip()
    return result
