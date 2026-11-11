// Resolve A Storyboard's Phrase Anchors Against Word Timings And Write A New Timed Storyboard.
// Run It Again With New Word Timings To Retime The Whole Film. It Writes JSON Only.
"use strict";
const fs = require("node:fs"), path = require("node:path");
const { parseArgs } = require("node:util");
const P = require("../studio/project.js"), Timing = require("../studio/timing.js");

const usage = "Usage: node tools/retime.cjs Storyboard.json Words.json|Words.srt Timed.json [--voice Recording.wav] [--embed-voice] [--lead 0.2] [--offset 0] [--tail 0.6] [--strict] [--report Report.json] [--overwrite]";
const read = file => fs.readFileSync(file, "utf8").replace(/^﻿/, "");
const mimes = { wav: "audio/wav", mp3: "audio/mpeg", m4a: "audio/mp4", aac: "audio/aac", ogg: "audio/ogg", flac: "audio/flac", webm: "audio/webm" };

// Read A Word Timing File: JSON In Any Supported Shape, Or SRT Or WebVTT Subtitles.
function readWordsFile(file) {
  if (!fs.existsSync(file)) throw new Error("Word Timings Not Found: " + file);
  const text = read(file);
  if (/\.(srt|vtt)$/i.test(file)) return Timing.readWords(text);
  let raw;
  try { raw = JSON.parse(text); } catch (error) { throw new Error("The Word Timings Are Not Valid JSON: " + error.message); }
  return Timing.readWords(raw);
}
// Decode An Uncompressed WAV Into Mono Samples For Level Measurement. Returns Null For Other Encodings.
function wavSamples(bytes) {
  if (bytes.length < 44 || bytes.toString("ascii", 0, 4) !== "RIFF" || bytes.toString("ascii", 8, 12) !== "WAVE") return null;
  let at = 12, format = null, data = null;
  while (at + 8 <= bytes.length) {
    const id = bytes.toString("ascii", at, at + 4), size = bytes.readUInt32LE(at + 4), body = at + 8;
    if (id === "fmt ") format = { tag: bytes.readUInt16LE(body), channels: bytes.readUInt16LE(body + 2), rate: bytes.readUInt32LE(body + 4), bits: bytes.readUInt16LE(body + 14),
      sub: size >= 26 ? bytes.readUInt16LE(body + 24) : 0 };
    if (id === "data") { data = bytes.subarray(body, Math.min(bytes.length, body + size)); break; }
    at = body + size + (size % 2);
  }
  if (!format || !data || !format.channels) return null;
  const tag = format.tag === 0xfffe ? format.sub : format.tag, width = format.bits / 8, frames = Math.floor(data.length / (width * format.channels));
  if (!(tag === 1 && [8, 16, 24, 32].includes(format.bits)) && !(tag === 3 && format.bits === 32)) return null;
  const samples = new Float32Array(frames);
  for (let i = 0; i < frames; i++) {
    let sum = 0;
    for (let ch = 0; ch < format.channels; ch++) {
      const p = (i * format.channels + ch) * width;
      sum += tag === 3 ? data.readFloatLE(p) : width === 1 ? (data[p] - 128) / 128 : width === 2 ? data.readInt16LE(p) / 32768 : width === 3 ? data.readIntLE(p, 3) / 8388608 : data.readInt32LE(p) / 2147483648;
    }
    samples[i] = sum / format.channels;
  }
  return { samples, rate: format.rate, seconds: frames / format.rate };
}

function main() {
  const { values: options, positionals } = parseArgs({ allowPositionals: true, options: {
    voice: { type: "string" }, "embed-voice": { type: "boolean" }, lead: { type: "string" }, offset: { type: "string" }, tail: { type: "string" },
    strict: { type: "boolean" }, report: { type: "string" }, overwrite: { type: "boolean" }, help: { type: "boolean" } } });
  if (options.help) { console.log(usage); return; }
  if (positionals.length !== 3) throw new Error(usage);
  const [source, wordsFile, target] = positionals.map(item => path.resolve(item));
  if (target === source) throw new Error("Write The Timed Storyboard To A New File So The Authored Storyboard Keeps Its Own Durations.");
  if (fs.existsSync(target) && !options.overwrite) throw new Error("Choose A New Output File, Or Add --overwrite To Replace The Timed Storyboard.");
  const seconds = (name, min, max) => {
    if (options[name] == null) return undefined;
    const value = Number(options[name]);
    if (!Number.isFinite(value) || value < min || value > max) throw new Error("--" + name + " Needs A Number Of Seconds From " + min + " To " + max + ".");
    return value;
  };
  if (!fs.existsSync(source)) throw new Error("Storyboard Not Found: " + positionals[0]);
  let raw;
  try { raw = JSON.parse(read(source)); } catch (error) { throw new Error("The Storyboard Is Not Valid JSON: " + error.message); }
  const project = P.cleanProject(raw), words = readWordsFile(wordsFile), settings = { offset: seconds("offset", -600, 600), lead: seconds("lead", 0, 600), tail: seconds("tail", 0, 60) };
  if (settings.offset != null && settings.lead != null) throw new Error("Use --offset Or --lead, Not Both.");
  let voice = null;
  if (options.voice) {
    const file = path.resolve(options.voice), extension = path.extname(file).slice(1).toLowerCase();
    if (!fs.existsSync(file)) throw new Error("Voice Recording Not Found: " + options.voice);
    if (!mimes[extension]) throw new Error("The Voice Recording Must Be A WAV, MP3, M4A, AAC, OGG, FLAC, Or WebM File.");
    const bytes = fs.readFileSync(file), decoded = wavSamples(bytes);
    voice = { bytes, extension, measured: Boolean(decoded) };
    if (decoded) settings.levels = { rate: 30, values: Timing.levelsFromSamples(decoded.samples, decoded.rate, 30) };
    if (options["embed-voice"]) {
      if (bytes.length > 20 * 1024 * 1024) throw new Error("Embed A Voice Recording Under 20 MiB, Or Leave It Beside The Storyboard.");
      voice.clip = "data:" + mimes[extension] + ";base64," + bytes.toString("base64");
    } else {
      voice.file = path.relative(path.dirname(target), file).split(path.sep).join("/");
      if (voice.file.startsWith("..") || path.isAbsolute(voice.file)) throw new Error("Keep The Voice Recording In The Timed Storyboard's Folder Or Below It, Or Add --embed-voice.");
    }
  }
  const result = Timing.retime(project, words, settings), report = result.report;
  if (options.strict && report.mismatches.length) result.problems.push(report.mismatches.length + " Caption Line" + (report.mismatches.length === 1 ? " Differs" : "s Differ") + " From The Spoken Words, And --strict Is Set.");
  for (const item of report.mismatches) console.log("Caption Line " + item.line + " Differs From Speech At " + Timing.clock(item.at) + ". Shown: “" + item.text + "”. Spoken: “" + item.spoken + "”.");
  if (result.problems.length) {
    for (const problem of result.problems) console.error(problem);
    throw new Error(result.problems.length + " Timing Problem" + (result.problems.length === 1 ? "" : "s") + " Found. Nothing Was Written.");
  }
  if (voice) {
    delete result.project.voice.file; delete result.project.voice.clip;
    if (voice.clip) result.project.voice.clip = voice.clip; else result.project.voice.file = voice.file;
  }
  const timed = P.cleanProject(result.project);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, JSON.stringify(timed, null, 2) + "\n");
  if (options.report) fs.writeFileSync(path.resolve(options.report), JSON.stringify(Object.assign({}, report, { notes: result.notes }), null, 2) + "\n");
  for (const scene of report.scenes) console.log("Scene " + scene.scene + " | Starts " + Timing.clock(scene.start) + " | Lasts " + Timing.clock(scene.duration) + (Math.abs(scene.was - scene.duration) > 0.0005 ? " (Was " + Timing.clock(scene.was) + ")" : "") + (scene.anchored ? " | Anchored" : ""));
  for (const item of report.uncaptioned) console.log("Spoken Without A Caption At " + Timing.clock(item.at) + ": “" + item.text + "”.");
  for (const note of result.notes) console.log("Note: " + note);
  console.log("Resolved " + report.beats + " Beat" + (report.beats === 1 ? "" : "s") + ", " + report.cues + " Anchored Cue" + (report.cues === 1 ? "" : "s") + ", And " + report.captions + " Caption Line" + (report.captions === 1 ? "" : "s") +
    " From " + report.words + " Words. " + report.mismatches.length + " Caption Mismatch" + (report.mismatches.length === 1 ? "" : "es") + ". The Film Lasts " + Timing.clock(report.duration) + ".");
  if (report.standIn) console.log("These Are Stand-In Word Timings. Run This Tool Again With Timings From The Real Recording.");
  if (voice && !voice.measured) console.log("The Voice Level Track Was Estimated From Word Timings. Supply An Uncompressed WAV To Measure It.");
  console.log("Wrote " + target);
}
module.exports = { readWordsFile, wavSamples };
if (require.main === module) { try { main(); } catch (error) { console.error(error.message); process.exitCode = 1; } }
