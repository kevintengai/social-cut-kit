"""Exercise Retention Readings From CSV Files And From Synthetic Chart Images."""

import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))
import retention  # noqa: E402

TOOL = SCRIPTS / "retention.py"
FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
EIGHT_SECONDS = [100, 97, 94, 89, 83, 81, 80, 79, 78]


def namespace(**values):
    base = dict(color=None, tolerance=20, top=100.0, bottom=0.0, seconds=30.0)
    base.update(values)
    return argparse.Namespace(**base)


def recolor(pixels, old, new):
    """Replace Every Pixel Of One Exact Color."""
    out = bytearray(pixels)
    at = pixels.find(bytes(old))
    while at != -1:
        if at % 3 == 0:
            out[at : at + 3] = bytes(new)
        at = pixels.find(bytes(old), at + 1)
    return bytes(out)


class Work(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="retention test ")
        self.addCleanup(folder.cleanup)
        self.work = Path(folder.name)

    def run_tool(self, *args, code=0):
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        done = subprocess.run(
            [sys.executable, "-B", str(TOOL), *map(str, args)],
            capture_output=True,
            env=env,
            check=False,
        )
        out, err = done.stdout.decode("utf-8"), done.stderr.decode("utf-8")
        self.assertEqual(done.returncode, code, err or out)
        return out, err

    def csv(self, values, name="curve.csv", step=1.0):
        path = self.work / name
        rows = "".join(f"{i * step:g},{value}\n" for i, value in enumerate(values))
        path.write_text("seconds,retention_pct\n" + rows, encoding="utf-8")
        return path

    def report(self, *args):
        return json.loads(self.run_tool(*args)[0])

    def chart_file(self, name="chart.png", **options):
        picture = retention.synthetic_chart(**options)
        path = self.work / name
        path.write_bytes(
            retention.png_bytes(picture["width"], picture["height"], picture["pixels"])
        )
        return picture, path


class CsvReport(Work):
    def test_original_fields_keep_their_order_and_values(self):
        report = self.report("csv", self.csv(EIGHT_SECONDS))
        self.assertEqual(
            list(report)[:6],
            ["samples", "chart_coverage", "first_pct", "last_pct", "largest_drop", "largest_lift"],
        )
        self.assertEqual(report["samples"], 9)
        self.assertIsNone(report["chart_coverage"])
        self.assertEqual((report["first_pct"], report["last_pct"]), (100.0, 78.0))
        self.assertEqual(report["largest_drop"], {"from": 1.0, "to": 4.0, "delta_points": -14.0})
        self.assertIsNone(report["largest_lift"])
        self.assertIsNone(report["calibration"])

    def test_interval_option_still_sets_the_window(self):
        report = self.report("csv", self.csv(EIGHT_SECONDS), "--interval", 1)
        self.assertEqual(report["largest_drop"], {"from": 3.0, "to": 4.0, "delta_points": -6.0})

    def test_fixed_seconds_and_override(self):
        path = self.csv(EIGHT_SECONDS)
        seconds = [row["seconds"] for row in self.report("csv", path)["readings"]]
        self.assertEqual(seconds, [1, 2, 3, 5])
        rows = self.report("csv", path, "--at", 9, 2.5, 0)["readings"]
        self.assertEqual(
            rows,
            [
                {"seconds": 0, "retention_pct": 100.0},
                {"seconds": 2.5, "retention_pct": 91.5},
                {"seconds": 9, "retention_pct": None},
            ],
        )

    def test_area_average_and_share_of_runtime(self):
        report = self.report("csv", self.csv([100, 0], step=10))
        self.assertEqual(report["average_watch_seconds"], 5.0)
        self.assertEqual(report["average_watch_share_pct"], 50.0)
        self.assertEqual(report["duration_seconds"], 10.0)
        report = self.report("csv", self.csv(EIGHT_SECONDS))
        self.assertEqual(report["average_watch_seconds"], 6.92)
        self.assertEqual(report["average_watch_share_pct"], 86.5)

    def test_drop_between_three_and_ten_seconds(self):
        values = [100, 90, 80, 70, 68, 66, 64, 62, 60, 58, 56, 55]
        self.assertEqual(self.report("csv", self.csv(values))["drop_3_to_10_points"], 14.0)
        self.assertIsNone(self.report("csv", self.csv(EIGHT_SECONDS))["drop_3_to_10_points"])

    def test_runtime_longer_or_shorter_than_the_curve(self):
        path = self.csv(EIGHT_SECONDS)
        out, err = self.run_tool("csv", path, "--runtime", "0:12")
        report = json.loads(out)
        self.assertEqual(report["duration_seconds"], 12.0)
        self.assertEqual(report["average_watch_share_pct"], 57.7)
        self.assertIn("Lower Bound", report["warnings"][0])
        self.assertIn("Warning: ", err)
        _, err = self.run_tool("csv", path, "--runtime", 5, code=1)
        self.assertIn("Past The 5-Second Runtime", err)

    def test_reported_average_flags_a_misread(self):
        path = self.csv(EIGHT_SECONDS)
        quiet = self.report("csv", path, "--reported-average", 6.5)
        self.assertEqual(quiet["reported_average_seconds"], 6.5)
        self.assertEqual(quiet["average_gap_seconds"], 0.42)
        self.assertEqual(quiet["warnings"], [])
        out, err = self.run_tool("csv", path, "--reported-average", "0:03")
        loud = json.loads(out)
        self.assertEqual(loud["average_gap_seconds"], 3.92)
        self.assertIn("Misread Chart", loud["warnings"][0])
        self.assertIn("Misread Chart", err)
        strict = self.report("csv", path, "--reported-average", 6.5, "--average-tolerance", 0.1)
        self.assertEqual(len(strict["warnings"]), 1)

    def test_steep_drops_and_flat_stretches_carry_time_ranges(self):
        report = self.report("csv", SKILL / "assets" / "practice-retention.csv")
        drops, flats = report["steepest_drops"], report["flattest_stretches"]
        self.assertEqual(len(drops), 3)
        self.assertEqual(drops[0]["from"], 0.0)
        self.assertLess(drops[0]["delta_points"], drops[1]["delta_points"])
        cliff = [d for d in drops if 9 <= d["from"] <= 10.5]
        self.assertEqual(len(cliff), 1)
        self.assertLessEqual(cliff[0]["to"], 12.5)
        self.assertLess(cliff[0]["points_per_second"], -3)
        self.assertEqual(len(flats), 1)
        self.assertLessEqual(flats[0]["from"], 13.5)
        self.assertGreaterEqual(flats[0]["to"], 19)
        self.assertAlmostEqual(flats[0]["seconds"], flats[0]["to"] - flats[0]["from"], places=2)
        self.assertEqual(len(self.report("csv", SKILL / "assets" / "practice-retention.csv", "--count", 1)["steepest_drops"]), 1)

    def test_a_steady_slope_lists_nothing(self):
        report = self.report("csv", self.csv([100 - 2 * i for i in range(31)]))
        self.assertEqual(report["steepest_drops"], [])
        self.assertEqual(report["flattest_stretches"], [])

    def test_replays_are_noted(self):
        report = self.report("csv", self.csv([100, 104, 96, 90, 85]), "--interval", 1)
        self.assertIn("Replays", report["warnings"][0])
        self.assertEqual(report["largest_lift"], {"from": 0.0, "to": 1.0, "delta_points": 4.0})

    def test_output_file_keeps_the_curve_and_is_never_replaced(self):
        target = self.work / "saved report.json"
        out, err = self.run_tool("csv", self.csv(EIGHT_SECONDS), "--output", target)
        saved = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(saved["curve"], [[float(i), float(v)] for i, v in enumerate(EIGHT_SECONDS)])
        self.assertNotIn("curve", json.loads(out))
        self.assertIn("Saved The Report", err)
        _, err = self.run_tool("csv", self.csv(EIGHT_SECONDS), "--output", target, code=1)
        self.assertIn("Already Exists", err)

    def test_long_curves_are_thinned_for_storage(self):
        samples = [(i / 10, 100 - i / 20) for i in range(1001)]
        curve = retention.compact_curve(samples, [t for t, _ in samples])
        self.assertEqual(len(curve), retention.CURVE_POINTS + 1)
        self.assertEqual(curve[0], [0.0, 100.0])
        self.assertEqual(curve[-1], [100.0, 50.0])

    def test_percent_signs_and_byte_order_marks_are_accepted(self):
        path = self.work / "signed.csv"
        path.write_text("seconds,retention_pct\n0,100%\n4,60%\n", encoding="utf-8-sig")
        self.assertEqual(self.report("csv", path)["last_pct"], 60.0)
        path.write_bytes("seconds,retention_pct\r\n0,100\r\n4,60\r\n".encode("utf-16"))
        self.assertEqual(self.report("csv", path)["last_pct"], 60.0)

    def test_fractions_are_questioned(self):
        report = self.report("csv", self.csv([1.0, 0.6, 0.3]))
        self.assertIn("Multiply Fractions By 100.", report["warnings"][0])

    def test_bad_input_is_rejected_in_house_style(self):
        _, err = self.run_tool("csv", self.csv([100, 90, 95], step=0), code=1)
        self.assertEqual(err.strip(), "Measurement Times Must Increase.")
        path = self.work / "wrong.csv"
        path.write_text("time,percent\n0,100\n1,90\n", encoding="utf-8")
        _, err = self.run_tool("csv", path, code=1)
        self.assertIn("Expected CSV Columns Named seconds And retention_pct.", err)
        _, err = self.run_tool("csv", self.work / "absent.csv", code=1)
        self.assertIn("No CSV File At", err)
        _, err = self.run_tool("csv", self.csv([100]), code=1)
        self.assertIn("Supply At Least Two Finite Nonnegative Measurements.", err)
        _, err = self.run_tool(code=2)
        self.assertIn("Choose The csv Or image Command", err)
        out, _ = self.run_tool("image", "--help")
        self.assertIn("Usage: retention.py image", out)
        self.assertIn("Show This Help And Exit", out)


class PixelArithmetic(unittest.TestCase):
    def test_lane_arithmetic_matches_plain_python(self):
        rng = random.Random(11)
        width, height = 37, 23
        pixels = bytes(rng.randrange(256) for _ in range(3 * width * height))
        planes = retention.Planes(pixels, width, height)
        luma = retention._narrow(planes.luma, planes.count)
        for index in range(width * height):
            r, g, b = pixels[3 * index : 3 * index + 3]
            self.assertEqual(planes.chroma[index], max(r, g, b) - min(r, g, b))
            self.assertEqual(luma[index], (r + 2 * g + b) // 4)
        a = bytes(rng.randrange(256) for _ in range(width * height))
        b = bytes(rng.randrange(256) for _ in range(width * height))
        gap = retention._narrow(
            planes.minus(retention._widen(a), retention._widen(b)), planes.count
        )
        self.assertEqual(list(gap), [max(0, x - y) for x, y in zip(a, b)])

    def test_thin_line_flags_match_a_direct_scan(self):
        rng = random.Random(5)
        width, height, reach = 31, 29, 4
        shades = [(20, 20, 22), (60, 60, 66), (200, 40, 90), (20, 20, 22), (20, 20, 22)]
        pixels = b"".join(bytes(rng.choice(shades)) for _ in range(width * height))
        planes = retention.Planes(pixels, width, height)
        light, dark = planes.thin_lines(reach)
        luma = retention._narrow(planes.luma, planes.count)

        def expected(sign):
            flags = bytearray(width * height)
            for y in range(reach, height - reach):
                for x in range(width):
                    here, up, down = (y * width + x, (y - reach) * width + x, (y + reach) * width + x)
                    over = sign * (luma[here] - luma[up]) >= 5
                    under = sign * (luma[here] - luma[down]) >= 5
                    plain = planes.chroma[here] - min(planes.chroma[up], planes.chroma[down]) <= 12
                    vivid_up, vivid_down = planes.chroma[up] >= 40, planes.chroma[down] >= 40
                    keep = (over and under) or (over and vivid_down) or (vivid_up and under)
                    flags[here] = 1 if keep and plain else 0
            return bytes(flags)

        inner = slice(reach * width, (height - reach) * width)
        self.assertEqual(light[inner], expected(1)[inner])
        self.assertEqual(dark[inner], expected(-1)[inner])

    def test_color_matching_lists_rows_per_column(self):
        width, height = 6, 5
        pixels = bytearray(bytes([255, 255, 255]) * (width * height))
        for x, y in ((0, 1), (0, 3), (2, 4), (5, 0)):
            pixels[3 * (y * width + x) : 3 * (y * width + x) + 3] = bytes([30, 70, 110])
        columns = retention.match_columns(bytes(pixels), width, 0, 0, width, height, [31, 66, 112], 5)
        self.assertEqual(columns, [[1, 3], [], [4], [], [], [0]])
        part = retention.match_columns(bytes(pixels), width, 2, 1, 4, 4, [31, 66, 112], 5)
        self.assertEqual(part, [[3], [], [], []])


class ManualCalibration(unittest.TestCase):
    def test_a_supplied_rectangle_and_color_read_the_curve(self):
        w, h = 50, 21
        pixels = bytearray([255] * (3 * w * h))
        for x in range(w):
            index = 3 * ((x // 5 + 3) * w + x)
            pixels[index : index + 3] = bytes([31, 66, 112])
        a = namespace(color=[31, 66, 112], seconds=10.0)
        samples, coverage = retention.plot_samples(bytes(pixels), w, h, a)
        self.assertEqual((len(samples), coverage), (50, 1.0))
        self.assertEqual(samples[0], (0.0, 85.0))
        self.assertEqual(samples[-1], (10.0, 40.0))
        self.assertAlmostEqual(samples[7][0], 7 * 10 / 49)
        with self.assertRaisesRegex(ValueError, "Too Few Line Pixels. Check The Plot And Line Color."):
            retention.plot_samples(bytes(pixels), w, h, namespace(color=[200, 0, 0], seconds=10.0))
        with self.assertRaisesRegex(ValueError, "Incomplete Input Image."):
            retention.plot_samples(bytes(pixels[:-3]), w, h, a)

    def test_a_supplied_rectangle_on_a_practice_chart(self):
        for theme in ("dark", "light"):
            picture = retention.synthetic_chart(theme=theme, dashed=True, fill=True)
            width, (left, top, right, bottom) = picture["width"], picture["plot"]
            w, h = right - left + 1, bottom - top + 1
            crop = b"".join(
                picture["pixels"][3 * (y * width + left) : 3 * (y * width + right + 1)]
                for y in range(top, bottom + 1)
            )
            given = namespace(color=list(picture["color"]))
            found = namespace(color=None)
            for a in (given, found):
                with self.subTest(theme=theme, supplied=a is given):
                    samples, coverage = retention.plot_samples(crop, w, h, a)
                    self.assertEqual(coverage, 1.0)
                    self.assertEqual(a.color, list(picture["color"]))
                    times = [t for t, _ in samples]
                    for second in (1, 3, 10, 20, 30):
                        true = retention.practice_level(picture["points"], 30.0, second)
                        read = retention.reading(samples, times, second, retention.edge_slack(times))
                        self.assertAlmostEqual(read, true, delta=retention.SELFTEST_POINTS)

    def test_a_plot_without_a_colorful_line_asks_for_the_color(self):
        gray = bytes([120, 120, 120]) * (40 * 30)
        with self.assertRaisesRegex(ValueError, "Supply The Line Color By Hand With --color RED GREEN BLUE."):
            retention.plot_samples(gray, 40, 30, namespace(color=None))


class AutomaticCalibration(unittest.TestCase):
    def read(self, picture, pixels=None, **values):
        a = namespace(seconds=picture["seconds"], **values)
        return retention.auto_chart(
            picture["pixels"] if pixels is None else pixels, picture["width"], picture["height"], a
        )

    def assert_reads(self, picture, pixels=None, box=1, shade=4):
        result = retention.practice_report(picture, pixels)
        self.assertLessEqual(result["worst_points"], retention.SELFTEST_POINTS)
        self.assertLessEqual(result["average_gap"], retention.SELFTEST_SECONDS)
        self.assertLessEqual(result["box_gap"], box)
        for found, true in zip(result["color"], picture["color"]):
            self.assertLessEqual(abs(found - true), shade)
        return result

    def test_dark_theme_with_dashed_gridlines_and_shading(self):
        picture = retention.synthetic_chart(theme="dark", dashed=True, fill=True)
        result = self.assert_reads(picture, box=0, shade=0)
        self.assertEqual(result["plot"], [72, 170, 599, 410])
        _, coverage, found = self.read(picture)
        self.assertEqual(found["theme"], "dark")
        self.assertEqual(found["gridlines"], [170, 230, 290, 350, 410])
        self.assertEqual(found["trace"], "color match")
        self.assertEqual(coverage, 1.0)

    def test_light_theme_with_solid_gridlines(self):
        picture = retention.synthetic_chart(theme="light", dashed=False, fill=False)
        self.assert_reads(picture, box=0, shade=0)
        self.assertEqual(self.read(picture)[2]["theme"], "light")

    def test_other_combinations_and_a_longer_video(self):
        for options in (
            dict(theme="dark", dashed=False, fill=False),
            dict(theme="light", dashed=True, fill=True, seconds=62.0),
        ):
            with self.subTest(options=options):
                self.assert_reads(retention.synthetic_chart(**options))

    def test_high_density_screenshot(self):
        self.assert_reads(retention.synthetic_chart(theme="light", dashed=True, fill=True, scale=3), box=2)

    def test_compression_noise(self):
        rng = random.Random(3)
        for theme in ("dark", "light"):
            picture = retention.synthetic_chart(theme=theme, dashed=theme == "dark", fill=theme == "dark")
            noisy = bytes(min(255, max(0, v + rng.randint(-2, 2))) for v in picture["pixels"])
            with self.subTest(theme=theme):
                self.assert_reads(picture, noisy)

    def test_chart_inside_a_wider_screenshot(self):
        picture = retention.synthetic_chart(theme="dark", dashed=True, fill=False)
        wide, tall = 1500, 800
        canvas = bytearray(bytes([18, 18, 20]) * (wide * tall))
        row = 3 * picture["width"]
        for y in range(picture["height"]):
            at = 3 * ((y + 200) * wide + 500)
            canvas[at : at + row] = picture["pixels"][y * row : (y + 1) * row]
        found = retention.find_chart(bytes(canvas), wide, tall)
        self.assertEqual(found["plot"], [572, 370, 1099, 610])

    def paint(self, pixels, width, x0, y0, x1, y1, shade):
        for y in range(y0, y1):
            pixels[3 * (y * width + x0) : 3 * (y * width + x1)] = bytes(shade) * (x1 - x0)

    def test_labels_that_shorten_the_gridlines_do_not_shift_the_time_axis(self):
        picture = retention.synthetic_chart(theme="dark", dashed=True, fill=True)
        pixels = bytearray(picture["pixels"])
        for row in (170, 230, 290, 350, 410):
            self.paint(pixels, picture["width"], 72, row - 12, 122, row - 3, (168, 170, 178))
        _, _, found = self.read(picture, bytes(pixels))
        self.assertGreater(found["gridline_extent"][0], 100)
        self.assertEqual(found["plot"], [72, 170, 599, 410])
        self.assertEqual(found["notes"], [])
        self.assert_reads(picture, bytes(pixels), box=0)

    def test_gridlines_wider_than_the_curve_are_noted(self):
        picture = retention.synthetic_chart(theme="light", dashed=False, fill=False)
        pixels = bytearray(picture["pixels"])
        for row in (170, 230, 290, 350, 410):
            self.paint(pixels, picture["width"], 600, row, 636, row + 1, (224, 227, 232))
        _, _, found = self.read(picture, bytes(pixels))
        self.assertEqual(found["plot"], [72, 170, 599, 410])
        self.assertEqual(found["gridline_extent"], [72, 635])
        self.assertIn("The Curve Spans Columns 72 To 599 But The Gridlines Span 72 To 635.", found["notes"][0])
        self.assert_reads(picture, bytes(pixels), box=0)

    def test_a_thin_soft_line_is_followed_by_its_most_colorful_pixels(self):
        for theme, ground, grid in (("dark", (18, 18, 20), (58, 58, 64)), ("light", (255, 255, 255), (224, 227, 232))):
            picture = retention.synthetic_chart(theme=theme, dashed=False, fill=False)
            width, (left, top, right, bottom) = picture["width"], picture["plot"]
            pixels = bytearray(picture["pixels"])
            self.paint(pixels, width, left - 2, top - 6, right + 3, bottom + 7, ground)
            for row in (170, 230, 290, 350, 410):
                self.paint(pixels, width, left, row, right + 1, row + 1, grid)

            def row_of(x):
                at = min(max((x - left) / (right - left), 0.0), 1.0) * picture["seconds"]
                level = retention.practice_level(picture["points"], picture["seconds"], at)
                return top + (100 - level) / 100 * (bottom - top)

            for x in range(left, right + 1):
                a, b = row_of(x - 0.5), row_of(x + 0.5)
                low, high = min(a, b) - 0.5, max(a, b) + 0.5
                for y in range(int(low) - 1, int(high) + 2):
                    cover = min(1.0, max(0.0, min(high, y + 0.5) - max(low, y - 0.5)))
                    at = 3 * (y * width + x)
                    under = pixels[at : at + 3]
                    pixels[at : at + 3] = bytes(
                        round(cover * line + (1 - cover) * base)
                        for line, base in zip(picture["color"], under)
                    )
            with self.subTest(theme=theme):
                _, coverage, found = self.read(picture, bytes(pixels))
                self.assertEqual(found["trace"], "color ridge")
                self.assertEqual(coverage, 1.0)
                self.assert_reads(picture, bytes(pixels), box=0, shade=0)

    def test_a_marker_in_the_curve_color_is_left_out_of_the_reading(self):
        picture = retention.synthetic_chart(theme="dark", dashed=True, fill=False)
        pixels = bytearray(picture["pixels"])
        self.paint(pixels, picture["width"], 124, 172, 126, 409, picture["color"])
        self.assert_reads(picture, bytes(pixels), box=0)
        self.paint(pixels, picture["width"], 200, 172, 330, 409, picture["color"])
        with self.assertRaisesRegex(ValueError, "Something In The Curve's Color Covers Part Of The Plot"):
            self.read(picture, bytes(pixels))

    def test_supplied_color_is_used(self):
        picture = retention.synthetic_chart(theme="light", dashed=False, fill=False)
        a = namespace(color=[232, 62, 112])
        _, _, found = retention.auto_chart(picture["pixels"], picture["width"], picture["height"], a)
        self.assertEqual(found["plot"], [72, 170, 599, 410])
        with self.assertRaisesRegex(ValueError, "Covers Only 0 Percent"):
            self.read(picture, color=[10, 200, 10])

    def test_a_hidden_inner_gridline_keeps_the_full_axis(self):
        picture = retention.synthetic_chart(theme="dark", dashed=False, fill=False)
        row = 3 * picture["width"]
        pixels = bytearray(picture["pixels"])
        pixels[230 * row : 231 * row] = recolor(bytes(pixels[230 * row : 231 * row]), (58, 58, 64), (18, 18, 20))
        _, _, found = self.read(picture, bytes(pixels))
        self.assertEqual(found["plot"], [72, 170, 599, 410])
        self.assertEqual(found["gridlines"], [170, 290, 410])

    def unsure(self, pixels, width, height, pattern):
        with self.assertRaisesRegex(ValueError, pattern) as caught:
            retention.auto_chart(pixels, width, height, namespace())
        message = str(caught.exception)
        self.assertIn("Automatic Calibration Is Not Confident.", message)
        self.assertIn("--plot LEFT TOP RIGHT BOTTOM And --color RED GREEN BLUE", message)
        return message

    def test_unsure_readings_ask_for_manual_values(self):
        picture = retention.synthetic_chart(theme="dark", dashed=True, fill=False)
        width, height, pixels = picture["width"], picture["height"], picture["pixels"]
        row = 3 * width
        self.unsure(bytes([18, 18, 20]) * (width * height), width, height, "Fewer Than Three Evenly Spaced")
        self.unsure(pixels[: 260 * row], width, 260, "Fewer Than Three Evenly Spaced")
        self.unsure(recolor(pixels, picture["color"], (200, 200, 200)), width, height, "Not Confident")
        message = self.unsure(pixels + pixels, width, 2 * height, "More Than One Chart Was Found")
        self.assertIn("72 170 599 410 Or 72 650 599 890", message)
        topless = bytearray(pixels)
        topless[170 * row : 171 * row] = recolor(pixels[170 * row : 171 * row], (58, 58, 64), (18, 18, 20))
        self.unsure(bytes(topless), width, height, "The Curve Runs Outside The Detected Gridlines")

    def test_axis_notes_question_an_uneven_or_shifted_axis(self):
        notes = retention.axis_notes([170, 230, 290, 350, 410], True, 100.0)
        self.assertEqual(len(notes), 1)
        self.assertIn("The Axis Was Assumed To Run From 0 At The Bottom Gridline To 100 At The Top One.", notes[0])
        self.assertEqual(retention.axis_notes([170, 230, 290, 350, 410], False, 100.0), [])
        self.assertEqual(retention.axis_notes([], True, 100.0), [])
        notes = retention.axis_notes([170, 230, 290, 350], True, 100.0)
        self.assertIn("4 Gridlines Split The Axis Into 3 Equal Parts", notes[0])
        self.assertEqual(len(notes), 1)
        self.assertEqual(retention.axis_notes([170, 230, 290, 350], False, 100.0), [])
        self.assertIn("The Curve Starts At 67.5 Percent", retention.axis_notes([], False, 67.5)[0])

    def test_selftest_draws_and_reads_back(self):
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = retention.selftest()
        text = printed.getvalue()
        self.assertEqual(code, 0, text)
        self.assertIn("Self Test Passed", text)
        self.assertIn("The Tolerance Is 1.5 Retention Points", text)
        self.assertEqual(text.count("Drawn In Memory"), 2)
        self.assertNotIn("Fail", text)


@unittest.skipUnless(FFMPEG, "FFmpeg And FFprobe Required")
class ImageFiles(Work):
    def test_manual_rectangle_and_color_read_as_before(self):
        chart = self.work / "chart.ppm"
        w, h = 50, 21
        pixels = bytearray([255] * (3 * w * h))
        for x in range(w):
            index = 3 * ((x // 5 + 3) * w + x)
            pixels[index : index + 3] = bytes([31, 66, 112])
        chart.write_bytes(f"P6\n{w} {h}\n255\n".encode() + pixels)
        out, err = self.run_tool(
            "image", chart, "--plot", 0, 0, 49, 20, "--color", 31, 66, 112,
            "--seconds", 10, "--top", 100, "--bottom", 0,
        )
        report = json.loads(out)
        self.assertEqual(report["samples"], 50)
        self.assertEqual(report["chart_coverage"], 1)
        self.assertEqual((report["first_pct"], report["last_pct"]), (85, 40))
        self.assertEqual(report["largest_drop"], {"from": 0.0, "to": 3.061, "delta_points": -15.0})
        self.assertEqual(report["calibration"]["plot_source"], "supplied")
        self.assertEqual(report["calibration"]["axis_source"], "supplied")
        self.assertNotIn("Detected", err)
        self.assertIn("The Curve Starts At 85 Percent", report["warnings"][0])

    def test_manual_errors_keep_their_wording(self):
        _, path = self.chart_file()
        cases = (
            (["--plot", 5, 5, 5, 9, "--color", 1, 2, 3], "Use A Positive Plot Rectangle In Image Coordinates."),
            (["--plot", 0, 0, 640, 100, "--color", 1, 2, 3], "The Plot Extends Outside The Image."),
            (["--plot", 0, 0, 9, 9, "--color", 1, 2, 300], "Color Channels And Tolerance Must Be Between 0 And 255."),
            (["--plot", 0, 0, 9, 9, "--color", 1, 2, 3, "--top", 0, "--bottom", 100], "Check Duration And Vertical Axis Bounds."),
            (["--plot", 80, 180, 590, 400, "--color", 1, 250, 3], "Too Few Line Pixels. Check The Plot And Line Color."),
        )
        for extra, message in cases:
            with self.subTest(message=message):
                _, err = self.run_tool("image", path, "--seconds", 30, *extra, code=1)
                self.assertEqual(err.strip(), message)
        _, err = self.run_tool("image", self.work / "absent.png", "--seconds", 30, code=1)
        self.assertIn("No Image File At", err)
        (self.work / "notes.png").write_text("Not A Picture", encoding="utf-8")
        _, err = self.run_tool("image", self.work / "notes.png", "--seconds", 30, code=1)
        self.assertIn("As An Image", err)

    def test_png_writer_round_trips_through_the_decoder(self):
        picture, path = self.chart_file(theme="light", dashed=True, fill=True)
        self.assertEqual(retention.image_size(path), (picture["width"], picture["height"]))
        self.assertEqual(retention.decode(path), picture["pixels"])

    def test_automatic_reading_prints_what_it_found(self):
        picture, path = self.chart_file(theme="dark", dashed=True, fill=True)
        out, err = self.run_tool("image", path, "--seconds", 30, "--reported-average", 14.9)
        report = json.loads(out)
        setup = report["calibration"]
        self.assertEqual(setup["plot"], [72, 170, 599, 410])
        self.assertEqual(setup["color"], [64, 196, 255])
        self.assertEqual((setup["plot_source"], setup["color_source"]), ("detected", "detected"))
        self.assertEqual((setup["axis_top"], setup["axis_bottom"], setup["axis_source"]), (100.0, 0.0, "assumed"))
        self.assertIn(
            "Detected Plot Rectangle 72 170 599 410 From 5 Gridlines On A Dark Theme "
            "And Detected Line Color 64 196 255. Check Each Against The Screenshot.",
            err,
        )
        self.assertIn("Pass --top And --bottom When The Axis Labels Differ.", err)
        self.assertEqual(len(report["warnings"]), 1)
        self.assertIn("The Axis Was Assumed To Run From 0", report["warnings"][0])
        confirmed, _ = self.run_tool("image", path, "--seconds", 30, "--top", 100, "--bottom", 0)
        self.assertEqual(json.loads(confirmed)["warnings"], [])
        for row in report["readings"]:
            true = retention.practice_level(picture["points"], 30.0, row["seconds"])
            self.assertAlmostEqual(row["retention_pct"], true, delta=retention.SELFTEST_POINTS)
        self.assertAlmostEqual(report["drop_3_to_10_points"], 14.0, delta=1.0)
        self.assertEqual(report["steepest_drops"][0]["from"], 0.0)
        plateau = report["flattest_stretches"][0]
        self.assertLess(plateau["from"], 13)
        self.assertGreater(plateau["to"], 17.5)

    def test_misread_warning_in_image_mode(self):
        _, path = self.chart_file(theme="light", dashed=False, fill=False)
        out, err = self.run_tool("image", path, "--seconds", 60, "--reported-average", 14.9)
        report = json.loads(out)
        self.assertGreater(report["average_gap_seconds"], 10)
        self.assertIn("Misread Chart", report["warnings"][-1])
        self.assertIn("Warning: The Area Under The Curve Implies", err)

    def test_either_value_can_be_supplied_alone(self):
        _, path = self.chart_file(theme="light", dashed=False, fill=False)
        out, err = self.run_tool("image", path, "--seconds", 30, "--plot", 72, 170, 599, 410)
        setup = json.loads(out)["calibration"]
        self.assertEqual((setup["plot_source"], setup["color_source"]), ("supplied", "detected"))
        self.assertEqual(setup["color"], [232, 62, 112])
        self.assertIn("Detected Line Color 232 62 112.", err)
        out, err = self.run_tool("image", path, "--seconds", 30, "--color", 232, 62, 112, "--top", 100, "--bottom", 0)
        setup = json.loads(out)["calibration"]
        self.assertEqual((setup["plot_source"], setup["color_source"]), ("detected", "supplied"))
        self.assertEqual(setup["axis_source"], "supplied")
        self.assertNotIn("Is Read As 100 Percent", err)

    def test_unsure_chart_fails_with_manual_instructions(self):
        blank = self.work / "blank.png"
        blank.write_bytes(retention.png_bytes(320, 240, bytes([250, 250, 250]) * (320 * 240)))
        _, err = self.run_tool("image", blank, "--seconds", 30, code=1)
        self.assertIn("Automatic Calibration Is Not Confident.", err)
        self.assertIn("Supply The Plot Rectangle And Line Color By Hand", err)
        _, err = self.run_tool("image", blank, "--seconds", 30, "--plot", 10, 10, 300, 200, code=1)
        self.assertIn("Supply The Line Color By Hand With --color RED GREEN BLUE.", err)

    def test_selftest_command_and_included_practice_chart(self):
        out, _ = self.run_tool("--selftest")
        self.assertEqual(out.count("Pass."), 4)
        self.assertIn("Saved As PNG And Decoded With FFmpeg", out)
        self.assertIn("Self Test Passed.", out)
        picture = retention.synthetic_chart(theme="dark", dashed=True, fill=True)
        self.assertEqual(retention.decode(SKILL / "assets" / "practice-chart.png"), picture["pixels"])


if __name__ == "__main__":
    unittest.main()
