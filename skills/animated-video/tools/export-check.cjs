// Check A Finished, Owner-Approved Export Against Its Storyboard: Size, Frame Rate, Length, Sound, And Loudness.
// This Tool Only Reads The Exported File. It Writes Nothing Except An Optional JSON Report, And It Changes Nothing.
"use strict";
const fs = require("node:fs"), path = require("node:path");
const { parseArgs } = require("node:util");
const Film = require("./lib/film.cjs"), Meter = require("./lib/ffmpeg.cjs");
const P = require("../studio/project.js");

const usage = "Usage: node tools/export-check.cjs ExportedFile Storyboard.json [--target -14] [--peak -1.5] [--tolerance 0.15] [--report Check.json] [--strict] [--ffmpeg Path] [--ffprobe Path] [--overwrite]";
const stamp = value => value.toFixed(2) + "s";
const ratio = text => { const [a, b] = String(text || "").split("/").map(Number); return Number.isFinite(a) && Number.isFinite(b) && b ? a / b : Number.isFinite(a) && b === undefined ? a : null; };

// True When The Storyboard Should Make Sound: Any Sound Cue, Recorded Voice Cue, Or Film Voice With A Gain Above Zero.
function expectsSound(project) {
  const voice = project.voice;
  return project.scenes.some(scene => scene.cues.some(cue => cue.gain > 0 && (cue.type === "Sound" || cue.clip))) || Boolean(voice && (voice.clip || voice.file) && voice.gain > 0);
}
// Compare What FFprobe And The Loudness Measurement Found With What The Storyboard Asks For.
// Returns { lines, failures, checks }. A Failure Means The File Is Not The Film. A Check Is A Level Worth A Second Look.
function judge(project, found, options = {}) {
  const lines = [], failures = [], checks = [], target = options.target ?? -14, peak = options.peak ?? -1.5, tolerance = options.tolerance ?? 0.15;
  const [width, height] = P.size(project), fps = project.fps, wanted = Math.ceil(P.duration(project) * fps - 1e-7) / fps;
  const say = (ok, line, problem) => { lines.push((ok ? "Pass" : "Fail") + " | " + line); if (!ok) failures.push(problem || line); };
  say(found.bytes > 0, "File Size " + (found.bytes / 1048576).toFixed(2) + " MiB", "The Exported File Is Empty.");
  const streams = (found.probe && found.probe.streams) || [], picture = streams.find(stream => stream.codec_type === "video"), sound = streams.find(stream => stream.codec_type === "audio");
  if (!picture) say(false, "No Picture Stream Was Found", "The File Has No Picture Stream.");
  else {
    say(picture.width === width && picture.height === height, "Frame Size " + picture.width + " × " + picture.height + " | Storyboard " + width + " × " + height, "The Frame Size Is " + picture.width + " × " + picture.height + ", Not " + width + " × " + height + ".");
    const rate = ratio(picture.avg_frame_rate) || ratio(picture.r_frame_rate);
    if (rate === null) { lines.push("Note | The Frame Rate Could Not Be Read From The File."); checks.push("The Frame Rate Could Not Be Read. Confirm It In The Player."); }
    else say(Math.abs(rate - fps) <= 0.5, "Frame Rate " + rate.toFixed(2) + " | Storyboard " + fps, "The Frame Rate Is " + rate.toFixed(2) + ", Not " + fps + ".");
  }
  const stated = Number(found.probe && found.probe.format && found.probe.format.duration);
  const length = Number.isFinite(stated) && stated > 0 ? stated : Number.isFinite(found.lastFrame) ? found.lastFrame + 1 / fps : null;
  if (length === null) say(false, "The Length Could Not Be Read", "The Length Of The File Could Not Be Read.");
  else say(Math.abs(length - wanted) <= tolerance, "Length " + stamp(length) + (Number.isFinite(stated) && stated > 0 ? "" : " (Measured From The Last Frame)") + " | Storyboard " + stamp(wanted) + " | Tolerance " + stamp(tolerance),
    "The Length Is " + stamp(length) + ", Not " + stamp(wanted) + ".");
  const expected = expectsSound(project);
  if (!sound) say(!expected, expected ? "No Sound Stream Was Found" : "No Sound Stream, And The Storyboard Makes No Sound", "The File Has No Sound, But The Storyboard Has Sound Cues Or A Voice.");
  else {
    say(true, "Sound Stream Present | " + (sound.codec_name || "Unknown Codec") + " | " + (sound.channels || "?") + " Channel" + (sound.channels === 1 ? "" : "s") + " | " + (sound.sample_rate || "?") + " Hz");
    if (!expected) checks.push("The File Has A Sound Stream, But The Storyboard Makes No Sound.");
    const loud = found.loudness;
    if (!loud) checks.push("The Loudness Was Not Measured.");
    else if (loud.silent) { if (expected) say(false, "The Sound Stream Is Silent", "The Sound Stream Is Silent, But The Storyboard Has Sound Cues Or A Voice."); else lines.push("Note | The Sound Stream Is Silent."); }
    else {
      const off = loud.integrated - target;
      lines.push("Note | Integrated Loudness " + loud.integrated.toFixed(1) + " LUFS | Target " + target.toFixed(1) + " | Loudness Range " + (loud.range === null ? "Unmeasured" : loud.range.toFixed(1) + " LU") + " | True Peak " + (Number.isFinite(loud.truePeak) ? loud.truePeak.toFixed(1) : "Unmeasured") + " dBTP | Ceiling " + peak.toFixed(1));
      if (Math.abs(off) > 1) checks.push("Integrated Loudness Is " + Math.abs(off).toFixed(1) + " LU " + (off < 0 ? "Under" : "Over") + " The Target Of " + target.toFixed(1) + " LUFS.");
      if (Number.isFinite(loud.truePeak) && loud.truePeak > peak) checks.push("True Peak Is " + (loud.truePeak - peak).toFixed(1) + " dB Over The Ceiling Of " + peak.toFixed(1) + " dBTP.");
    }
  }
  if (P.standIn(project)) say(false, "The Storyboard Uses Stand-In Voice Timing", "The Storyboard Uses Stand-In Voice Timing, So An Export From It Is Not A Finished Film.");
  return { lines, failures, checks, length, wanted };
}

function main() {
  const { values: options, positionals } = parseArgs({ allowPositionals: true, options: { target: { type: "string" }, peak: { type: "string" }, tolerance: { type: "string" }, report: { type: "string" }, strict: { type: "boolean" },
    ffmpeg: { type: "string" }, ffprobe: { type: "string" }, overwrite: { type: "boolean" }, help: { type: "boolean" } } });
  if (options.help) { console.log(usage); return; }
  if (positionals.length !== 2) throw new Error(usage);
  const number = (name, fallback, min, max) => {
    if (options[name] == null) return fallback;
    const value = Number(options[name]);
    if (!Number.isFinite(value) || value < min || value > max) throw new Error("--" + name + " Needs A Number From " + min + " To " + max + ".");
    return value;
  };
  const settings = { target: number("target", -14, -40, -5), peak: number("peak", -1.5, -20, 0), tolerance: number("tolerance", 0.15, 0, 10) };
  const file = path.resolve(positionals[0]);
  if (!fs.existsSync(file) || !fs.statSync(file).isFile()) throw new Error("Exported File Not Found: " + positionals[0]);
  if (options.report) {
    Film.guardOutput(options.report, "The Report");
    if (path.resolve(options.report) === file) throw new Error("Write The Report To A New File, Not Over The Export.");
    if (fs.existsSync(path.resolve(options.report)) && !options.overwrite) throw new Error("Choose A New Report File, Or Add --overwrite.");
  }
  if (!fs.existsSync(positionals[1])) throw new Error("Storyboard Not Found: " + positionals[1]);
  let project;
  try { project = P.cleanProject(JSON.parse(Film.read(positionals[1]))); } catch (error) { throw new Error("The Storyboard Could Not Be Read: " + error.message); }
  const ffmpeg = Meter.locate("ffmpeg", options.ffmpeg), ffprobe = Meter.locateProbe(options.ffprobe, options.ffmpeg);
  const found = { bytes: fs.statSync(file).size, probe: Meter.probe(ffprobe, file) };
  const streams = found.probe.streams || [], stated = Number(found.probe.format && found.probe.format.duration);
  if (!(stated > 0) && streams.some(stream => stream.codec_type === "video")) found.lastFrame = Meter.lastFrameTime(ffprobe, file);
  if (streams.some(stream => stream.codec_type === "audio")) found.loudness = Meter.loudness(ffmpeg, file);
  const result = judge(project, found, settings);
  console.log(project.title + " | Export Check | " + path.basename(file));
  for (const line of result.lines) console.log(line);
  console.log(result.checks.length ? "To Check (" + result.checks.length + "):" : "No Level Stands Out Against The Targets.");
  for (const check of result.checks) console.log("  " + check);
  if (options.report) fs.writeFileSync(path.resolve(options.report), JSON.stringify({ title: project.title, file: path.basename(file), bytes: found.bytes, settings, length: result.length, storyboardLength: result.wanted,
    loudness: found.loudness || null, lines: result.lines, failures: result.failures, checks: result.checks }, null, 2) + "\n");
  console.log("The Exported File Was Read And Not Changed. Levels Are Reported, Never Applied.");
  if (result.failures.length) { for (const failure of result.failures) console.error(failure); throw new Error(result.failures.length + " Thing" + (result.failures.length === 1 ? " Does" : "s Do") + " Not Match The Storyboard."); }
  if (options.strict && result.checks.length) throw new Error(result.checks.length + " Item" + (result.checks.length === 1 ? "" : "s") + " To Check, And --strict Is Set.");
  console.log("The Export Matches The Storyboard.");
}
module.exports = { judge, expectsSound };
if (require.main === module) { try { main(); } catch (error) { console.error(error.message); process.exitCode = 1; } }
