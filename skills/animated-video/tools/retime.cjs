// Resolve A Storyboard's Phrase Anchors Against Word Timings, Place Sounds On Its Picture Events, And Write The Timed Storyboard.
// The Timed Storyboard Is The One File To Review, Prepare For Remotion, And Export. Run This Again After Any Change To The Voice Or The Scenes.
// It Writes JSON Only.
"use strict";
const fs = require("node:fs"), path = require("node:path");
const { parseArgs } = require("node:util");
const P = require("../studio/project.js"), Timing = require("../studio/timing.js");
const Film = require("./lib/film.cjs"), Events = require("./events.cjs");

const usage = "Usage: node tools/retime.cjs Storyboard.json Words.json|Words.srt Timed.json [--voice Recording.wav] [--embed-voice] [--lead 0.2] [--offset 0] [--tail 0.6] [--strict] [--no-sounds] [--report Report.json] [--overwrite]\n" +
  "   Or: node tools/retime.cjs Storyboard.json --no-words Timed.json [--no-sounds] [--report Report.json] [--overwrite]   For A Film That Declares \"narration\": \"None\" And Uses No Spoken Phrases.";
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
// Place A Bank Sound On Every Picture Event The Film's Scenes Declare, Using The Scene Modules Beside The Authored Storyboard.
// Returns { project, placed, notes, skipped }. When The Modules Cannot Be Read Or Run Yet, The Storyboard Comes Back Unchanged With The Reason In skipped.
function placeEventSounds(project, dir) {
  let scope;
  try { scope = Film.createScope(); Film.loadModules(scope, Film.readModules(project, dir)); }
  catch (error) { return { project, placed: 0, notes: [], skipped: error.message }; }
  try {
    const result = Events.placeEvents(scope, project);
    return { project: result.project, placed: result.placed, notes: result.notes, skipped: "" };
  } catch (error) {
    if (error.tooMany) throw error;
    return { project, placed: 0, notes: [], skipped: error.message };
  }
}
// A Film With No Narration And No Spoken Phrases Keeps The Times Its Author Wrote. List Anything That Still Needs Word Timings.
function untimed(project) {
  const problems = [], lines = (project.captions && project.captions.lines) || [];
  if (project.narration !== "None") problems.push("--no-words Is For A Film With No Narration. Add \"narration\": \"None\" To The Storyboard, Or Supply Word Timings.");
  project.scenes.forEach((scene, i) => {
    const label = "Scene " + (i + 1);
    for (const edge of ["start", "end"]) if (scene[edge]) problems.push(label + " Has A Spoken Phrase On Its " + (edge === "start" ? "Start" : "End") + ". Without Word Timings, Set The Scene's Duration In Seconds.");
    for (const [name, beat] of Object.entries(scene.beats || {})) if (beat.at === undefined) problems.push(label + " Beat " + name + " Is Tied To A Spoken Phrase. Without Word Timings, Give It A Time In Seconds.");
    scene.cues.forEach((cue, j) => { if (cue.anchor) problems.push(label + " Cue " + (j + 1) + " Is Anchored To A Spoken Phrase. Without Word Timings, Give It A Start Time In Seconds."); });
  });
  lines.forEach((line, i) => {
    if (line.at === undefined || line.phrase != null) problems.push("Caption Line " + (i + 1) + " Is Timed From Spoken Words. Without Word Timings, Give It at And end In Seconds And No phrase.");
  });
  const round = value => Math.round(value * 1000) / 1000;
  const scenes = project.scenes.map((scene, i) => ({ scene: i + 1, title: scene.title, start: round(P.start(project, i)), duration: scene.duration, was: scene.duration, anchored: false }));
  return { project: JSON.parse(JSON.stringify(project)), problems, notes: [],
    report: { scenes, beats: 0, cues: 0, captions: 0, manualCaptions: lines.length, mismatches: [], uncaptioned: [], words: 0, standIn: false, approximate: false, narration: "None", duration: round(P.duration(project)) } };
}

function main() {
  const { values: options, positionals } = parseArgs({ allowPositionals: true, options: {
    voice: { type: "string" }, "embed-voice": { type: "boolean" }, lead: { type: "string" }, offset: { type: "string" }, tail: { type: "string" },
    strict: { type: "boolean" }, "no-words": { type: "boolean" }, "no-sounds": { type: "boolean" }, report: { type: "string" }, overwrite: { type: "boolean" }, help: { type: "boolean" } } });
  if (options.help) { console.log(usage); return; }
  const wordless = Boolean(options["no-words"]);
  if (positionals.length !== (wordless ? 2 : 3)) throw new Error(usage);
  if (wordless && ["voice", "embed-voice", "lead", "offset", "tail", "strict"].some(name => options[name] != null)) throw new Error("--no-words Takes Only --no-sounds, --report, And --overwrite. Name A Sound Bed In The Storyboard's voice Entry.");
  const source = path.resolve(positionals[0]), wordsFile = wordless ? null : path.resolve(positionals[1]), target = path.resolve(positionals[wordless ? 1 : 2]);
  if (target === source) throw new Error("Write The Timed Storyboard To A New File So The Authored Storyboard Keeps Its Own Durations.");
  Film.guardOutput(target, "The Timed Storyboard");
  if (options.report) Film.guardOutput(options.report, "The Report");
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
  const project = P.cleanProject(raw), words = wordless ? null : readWordsFile(wordsFile), settings = { offset: seconds("offset", -600, 600), lead: seconds("lead", 0, 600), tail: seconds("tail", 0, 60) };
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
  const result = wordless ? untimed(project) : Timing.retime(project, words, settings), report = result.report;
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
  let timed = P.cleanProject(result.project);
  // Event Sounds Go Into The Timed Storyboard Itself, So The File That Is Reviewed And Exported Is The File That Carries Them.
  const sounds = options["no-sounds"] ? null : placeEventSounds(timed, path.dirname(source));
  if (sounds) { timed = sounds.project; result.notes.push(...sounds.notes); }
  report.eventSounds = sounds ? { placed: sounds.placed, skipped: sounds.skipped } : { placed: 0, skipped: "--no-sounds Was Set." };
  Film.writeSafely(target, JSON.stringify(timed, null, 2) + "\n");
  if (options.report) fs.writeFileSync(path.resolve(options.report), JSON.stringify(Object.assign({}, report, { notes: result.notes }), null, 2) + "\n");
  for (const scene of report.scenes) console.log("Scene " + scene.scene + " | Starts " + Timing.clock(scene.start) + " | Lasts " + Timing.clock(scene.duration) + (Math.abs(scene.was - scene.duration) > 0.0005 ? " (Was " + Timing.clock(scene.was) + ")" : "") + (scene.anchored ? " | Anchored" : ""));
  for (const item of report.uncaptioned) console.log("Spoken Without A Caption At " + Timing.clock(item.at) + ": “" + item.text + "”.");
  for (const note of result.notes) console.log("Note: " + note);
  if (!wordless) console.log("Resolved " + report.beats + " Beat" + (report.beats === 1 ? "" : "s") + ", " + report.cues + " Anchored Cue" + (report.cues === 1 ? "" : "s") + ", And " + report.captions + " Caption Line" + (report.captions === 1 ? "" : "s") +
    " From " + report.words + " Words. " + report.mismatches.length + " Caption Mismatch" + (report.mismatches.length === 1 ? "" : "es") + ". The Film Lasts " + Timing.clock(report.duration) + ".");
  if (!sounds) console.log("Event Sounds Were Not Placed Because --no-sounds Was Set. Run This Tool Again Without It Before Review.");
  else if (sounds.skipped) console.error("Warning: Event Sounds Were Not Placed. " + sounds.skipped + " Fix That And Run This Tool Again Before Review, Or The Film Will Reach The Owner Without Its Event Sounds.");
  else console.log(sounds.placed ? "Placed " + sounds.placed + " Event Sound" + (sounds.placed === 1 ? "" : "s") + " In The Timed Storyboard." : "No Scene Declares An Event With A Sound, So None Were Placed.");
  if (report.standIn) console.log("These Are Stand-In Word Timings. The Timed Storyboard Is Marked As Not Ready For Export. Run This Tool Again With Timings From The Real Recording.");
  if (timed.narration === "None") console.log("This Film Declares No Narration. Its Timings Are The Author's Own" + (wordless ? "." : ", And The Word Timings Are Treated As A Reading Pace, Not As Stand-Ins For A Recording."));
  if (voice && !voice.measured) console.log("The Voice Level Track Was Estimated From Word Timings. Supply An Uncompressed WAV To Measure It.");
  console.log("Wrote " + target);
}
module.exports = { readWordsFile, wavSamples, placeEventSounds, untimed };
if (require.main === module) { try { main(); } catch (error) { console.error(error.message); process.exitCode = 1; } }
