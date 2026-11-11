// Build The Film's Sound Mix In Memory From The Storyboard And Measure It. Nothing Here Is Applied To The Film.
// The Mix Follows The Remotion Route: The Film Voice, Voice Cues With Recordings, And Every Sound Cue With Its Gain And Pan, Starting On Whole Frames.
// It Reports Integrated Loudness, Loudness Range, And True Peak, Each Cue's Level Against The Voice Under It, And Cues That Sit On Key Spoken Words.
// It Can Write A WAV Check Mix When Asked. It Never Writes A Picture.
"use strict";
const fs = require("node:fs"), path = require("node:path"), os = require("node:os");
const { parseArgs } = require("node:util");
const Film = require("./lib/film.cjs"), Meter = require("./lib/ffmpeg.cjs"), Events = require("./events.cjs");
const P = require("../studio/project.js"), Sound = require("../studio/sound.js"), Timing = require("../studio/timing.js");
const { panSides } = require("../adapter/prepare-remotion.cjs");

const usage = "Usage: node tools/audio.cjs Storyboard.json [--target -14] [--peak -1.5] [--window 0.4] [--margin 6] [--all-words] [--wav CheckMix.wav] [--report Audio.json] [--strict] [--ffmpeg Path] [--overwrite]";
const RATE = Meter.RATE;
const stamp = value => value.toFixed(2) + "s";
const level = value => value === null ? "Unmeasured" : Number.isFinite(value) ? value.toFixed(1) : "Silent";
const round = (value, places = 2) => value === null || !Number.isFinite(value) ? value : Math.round(value * 10 ** places) / 10 ** places;

// Everything That Sounds, In Film Seconds, With The Same Whole-Frame Starts And Lengths The Remotion Project Uses.
function plan(project) {
  const fps = project.fps, frames = Math.ceil(P.duration(project) * fps - 1e-7), items = [], silent = [];
  let offset = 0;
  project.scenes.forEach((scene, i) => {
    const end = Math.ceil((offset + scene.duration) * fps - 1e-7);
    scene.cues.forEach((cue, j) => {
      const from = Math.round((offset + cue.at) * fps), label = "Scene " + (i + 1) + " Cue " + (j + 1);
      if (cue.type === "Voice" && !cue.clip) { silent.push(label + " Is A Script-Only Voice Line And Makes No Sound."); return; }
      if (cue.gain === 0 || from >= end) { silent.push(label + (cue.gain === 0 ? " Has A Gain Of Zero." : " Starts On Or After Its Scene's Last Frame.") + " It Makes No Sound."); return; }
      const item = { kind: cue.type === "Sound" ? "sound" : "voice", scene: i + 1, cue: j + 1, start: from / fps, gain: cue.gain, pan: cue.pan || 0 };
      if (cue.type === "Sound") { item.name = cue.sound; item.seconds = Math.min(end - from, Math.ceil(Sound.lengths[cue.sound] * fps)) / fps; if (cue.event) item.event = cue.event; }
      else { item.name = "Voice Cue"; item.seconds = (end - from) / fps; item.clip = cue.clip; }
      items.push(item);
    });
    offset += scene.duration;
  });
  const voice = project.voice;
  if (voice && (voice.clip || voice.file) && voice.gain > 0) {
    const from = Math.max(0, Math.round(voice.offset * fps));
    if (frames - from > 0) items.push({ kind: "film-voice", name: "Film Voice", scene: 0, cue: 0, start: from / fps, seconds: (frames - from) / fps, gain: voice.gain, pan: 0,
      skip: voice.offset < 0 ? Math.round(-voice.offset * fps) / fps : 0, clip: voice.clip || "", file: voice.file || "" });
  }
  return { fps, frames, seconds: frames / fps, items: items.sort((a, b) => a.start - b.start), silent };
}
// Mix The Plan Into Two Stereo Tracks Of Interleaved Floats: Everything Spoken, And Every Sound Cue. `decoded` Maps An Item To Its Stereo Samples.
function render(planned, decoded) {
  const count = Math.round(planned.seconds * RATE), voice = new Float32Array(count * 2), cues = new Float32Array(count * 2), bank = new Map();
  for (const item of planned.items) {
    const first = Math.round(item.start * RATE), most = Math.round(item.seconds * RATE);
    if (item.kind === "sound") {
      if (!bank.has(item.name)) bank.set(item.name, Sound.make(item.name, RATE));
      const mono = bank.get(item.name), sides = item.pan ? panSides(item.pan) : [1, 1];
      for (let n = 0; n < Math.min(mono.length, most) && first + n < count; n++) for (let side = 0; side < 2; side++)
        cues[(first + n) * 2 + side] += Math.max(-1, Math.min(1, mono[n] * sides[side])) * item.gain;
    } else {
      const samples = decoded.get(item);
      if (!samples) continue;
      const skip = Math.round((item.skip || 0) * RATE), available = Math.floor(samples.length / 2) - skip;
      for (let n = 0; n < Math.min(available, most) && first + n < count; n++) {
        voice[(first + n) * 2] += samples[(skip + n) * 2] * item.gain;
        voice[(first + n) * 2 + 1] += samples[(skip + n) * 2 + 1] * item.gain;
      }
    }
  }
  const mix = new Float32Array(count * 2);
  for (let i = 0; i < mix.length; i++) mix[i] = voice[i] + cues[i];
  return { voice, cues, mix, count };
}
// The RMS Level Of A Stereo Track Between Two Film Times, In dB Relative To Full Scale. Silence Is Minus Infinity.
function rmsDb(track, from, to) {
  const a = Math.max(0, Math.round(from * RATE)) * 2, b = Math.min(track.length, Math.round(to * RATE) * 2);
  if (b <= a) return -Infinity;
  let sum = 0;
  for (let i = a; i < b; i++) sum += track[i] * track[i];
  return sum ? 10 * Math.log10(sum / (b - a)) : -Infinity;
}
// One Cue Alone As A Stereo Track, For Measuring It Apart From Everything Else.
function soloDb(item, window) {
  const solo = render({ seconds: item.seconds, items: [Object.assign({}, item, { start: 0 })] }, new Map());
  return rmsDb(solo.cues, 0, Math.min(window, item.seconds));
}
// The Spoken Words That Phrase Anchors Point At, In Film Time: Scene Cuts, Beats, And Anchored Cues. With `all`, Every Spoken Word.
function keyWords(project, all) {
  const voice = project.voice;
  if (!voice || !Array.isArray(voice.words) || !voice.words.length) return [];
  const offset = voice.offset || 0, words = voice.words.map(word => ({ start: word[0], end: word[1], text: word[2] }));
  const film = at => ({ text: words[at].text, start: round(words[at].start + offset, 3), end: round(words[at].end + offset, 3) });
  if (all) return words.map((_, at) => film(at));
  const index = Timing.makeIndex(words, offset), chosen = new Set();
  // Take The Occurrence The Anchor Names, Or The One Nearest The Time The Timing Tool Resolved.
  const mark = (anchor, near, edge) => {
    if (!anchor || !anchor.phrase) return;
    const found = Timing.find(index, anchor.phrase);
    if (!found.length) return;
    const wanted = near - (anchor.offset || 0), side = anchor.edge || edge;
    const match = anchor.occurrence && found[anchor.occurrence - 1] ? found[anchor.occurrence - 1]
      : found.reduce((best, item) => Math.abs((side === "end" ? item.end : item.start) - wanted) < Math.abs((side === "end" ? best.end : best.start) - wanted) ? item : best);
    for (let k = match.first; k <= match.last; k++) chosen.add(index.tokens[k].word);
  };
  let start = 0;
  project.scenes.forEach(scene => {
    mark(scene.start, start, "start"); mark(scene.end, start + scene.duration, "end");
    for (const beat of Object.values(scene.beats || {})) if (beat.phrase && beat.at !== undefined) mark(beat, start + beat.at, "start");
    for (const cue of scene.cues) if (cue.anchor) mark(cue.anchor, start + cue.at, "start");
    start += scene.duration;
  });
  return [...chosen].sort((a, b) => a - b).map(film);
}
// Each Sound Cue's Level Against The Voice Under It, And Each Place A Cue Sits On A Key Word.
function analyse(project, planned, tracks, options = {}) {
  const window = options.window ?? 0.4, margin = options.margin ?? 6, hasVoice = planned.items.some(item => item.kind !== "sound"), keys = keyWords(project, options.allWords);
  const cues = planned.items.filter(item => item.kind === "sound").map(item => {
    const span = Math.min(window, item.seconds), cue = soloDb(item, window), voice = hasVoice ? rmsDb(tracks.voice, item.start, item.start + span) : null;
    const spoken = voice !== null && voice > -60, under = spoken && Number.isFinite(cue) ? voice - cue : null;
    const out = { scene: item.scene, cue: item.cue, sound: item.name, time: round(item.start, 3), seconds: round(item.seconds, 3), gain: item.gain, pan: item.pan, cueDb: round(cue), voiceDb: voice === null ? null : round(voice), under: round(under) };
    if (item.event) out.event = item.event;
    out.words = keys.filter(word => word.end > item.start && word.start < item.start + item.seconds);
    out.check = out.words.length > 0 && under !== null && under < margin;
    return out;
  });
  const overlaps = cues.filter(cue => cue.words.length).map(cue => ({ time: cue.time, scene: cue.scene, cue: cue.cue, sound: cue.sound, words: cue.words, under: cue.under, check: cue.check }));
  return { window, margin, hasVoice, keyWords: keys.length, cues, overlaps };
}
// Sixteen-Bit Stereo WAV Bytes Of A Mix. Samples Past Full Scale Are Held At Full Scale, And Counted.
function wavBytes(mix) {
  const out = Buffer.alloc(44 + mix.length * 2);
  let clipped = 0;
  out.write("RIFF", 0); out.writeUInt32LE(out.length - 8, 4); out.write("WAVEfmt ", 8); out.writeUInt32LE(16, 16); out.writeUInt16LE(1, 20); out.writeUInt16LE(2, 22);
  out.writeUInt32LE(RATE, 24); out.writeUInt32LE(RATE * 4, 28); out.writeUInt16LE(4, 32); out.writeUInt16LE(16, 34); out.write("data", 36); out.writeUInt32LE(mix.length * 2, 40);
  for (let i = 0; i < mix.length; i++) {
    const v = Math.max(-1, Math.min(1, mix[i]));
    if (v !== mix[i]) clipped++;
    out.writeInt16LE(Math.round(v * (v < 0 ? 32768 : 32767)), 44 + i * 2);
  }
  return { bytes: out, clipped };
}
// Decode The Recordings The Plan Names. A File Sits Beside The Storyboard. An Embedded Recording Passes Through The System Temporary Folder.
function decodeAll(ffmpeg, planned, dir) {
  const decoded = new Map(), cache = new Map();
  let scratch = null;
  try {
    for (const item of planned.items) {
      if (item.kind === "sound") continue;
      const key = item.clip || "file:" + item.file;
      if (!cache.has(key)) {
        let file;
        if (item.clip) {
          scratch = scratch || fs.mkdtempSync(path.join(os.tmpdir(), "motion-studio-audio-"));
          file = path.join(scratch, "clip-" + cache.size + ".bin");
          fs.writeFileSync(file, Buffer.from(item.clip.slice(item.clip.indexOf(",") + 1), "base64"));
        } else {
          file = path.join(dir, ...item.file.split("/"));
          if (!fs.existsSync(file)) throw new Error("Voice Recording Not Found Beside The Storyboard: " + item.file);
        }
        cache.set(key, Meter.decode(ffmpeg, file));
      }
      decoded.set(item, cache.get(key));
    }
  } finally {
    if (scratch && path.dirname(fs.realpathSync(scratch)) === fs.realpathSync(os.tmpdir())) fs.rmSync(scratch, { recursive: true, force: true });
  }
  return decoded;
}
// The Lines Of The Printed Report, And The Things Worth A Second Look.
function describe(project, planned, measured, found, targets, eventSounds) {
  const lines = [], checks = [], sounds = planned.items.filter(item => item.kind === "sound").length;
  // Until The Voice Recording Is Attached, The Mix Is Only The Sound Cues, So Its Loudness Says Nothing About The Target.
  const whole = found.hasVoice || project.narration === "None";
  lines.push(project.title + " | Sound Mix Check");
  lines.push(stamp(planned.seconds) + " · " + sounds + " Sound Cue" + (sounds === 1 ? "" : "s") + " · " + (found.hasVoice ? "Voice Recording Included" : "No Voice Recording"));
  if (measured.silent) lines.push("The Mix Is Silent, Or Too Quiet To Measure.");
  else {
    const off = measured.integrated - targets.target;
    lines.push("Integrated Loudness " + measured.integrated.toFixed(1) + " LUFS | Target " + targets.target.toFixed(1) + " | " +
      (!whole ? "Not Compared Until The Voice Recording Is Attached" : Math.abs(off) < 0.05 ? "On Target" : Math.abs(off).toFixed(1) + " LU " + (off < 0 ? "Under" : "Over")));
    lines.push("Loudness Range " + (measured.range === null ? "Unmeasured" : measured.range.toFixed(1) + " LU"));
    lines.push("True Peak " + level(measured.truePeak) + " dBTP | Ceiling " + targets.peak.toFixed(1) + " | " + (measured.truePeak > targets.peak ? (measured.truePeak - targets.peak).toFixed(1) + " dB Over" : "Within"));
    if (whole && Math.abs(off) > 1) checks.push("Integrated Loudness Is " + Math.abs(off).toFixed(1) + " LU " + (off < 0 ? "Under" : "Over") + " The Target Of " + targets.target.toFixed(1) + " LUFS.");
    if (measured.truePeak > targets.peak) checks.push("True Peak Is " + (measured.truePeak - targets.peak).toFixed(1) + " dB Over The Ceiling Of " + targets.peak.toFixed(1) + " dBTP.");
  }
  if (found.cues.length) {
    lines.push("", "Each Cue Against The Voice Under It (RMS Over The First " + stamp(found.window) + " Of The Cue):");
    for (const cue of found.cues) lines.push("  " + stamp(cue.time) + " | Scene " + cue.scene + " | " + cue.sound + " | Gain " + cue.gain.toFixed(2) + (cue.pan ? " | Pan " + cue.pan.toFixed(2) : "") + " | Cue " + level(cue.cueDb) + " dBFS | " +
      (cue.voiceDb === null ? "No Voice Recording" : cue.under === null ? "No Voice Under It" : "Voice " + level(cue.voiceDb) + " dBFS | Cue Is " + Math.abs(cue.under).toFixed(1) + " dB " + (cue.under >= 0 ? "Under" : "Over") + " The Voice"));
  }
  lines.push("", found.keyWords ? "Cues On Key Spoken Words (" + found.keyWords + " Key Word" + (found.keyWords === 1 ? "" : "s") + ", Margin " + found.margin + " dB):" : "No Key Spoken Words Were Found, So No Overlaps Are Listed.");
  if (found.keyWords && !found.overlaps.length) lines.push("  No Cue Sits On A Key Spoken Word.");
  for (const item of found.overlaps) {
    const words = item.words.map(word => "“" + word.text + "” " + stamp(word.start) + " To " + stamp(word.end)).join(", ");
    lines.push("  " + stamp(item.time) + " | Scene " + item.scene + " | " + item.sound + " | Over " + words + " | " +
      (item.under === null ? (found.hasVoice ? "No Voice Under It" : "Unmeasured Without A Recording") : Math.abs(item.under).toFixed(1) + " dB " + (item.under >= 0 ? "Under" : "Over") + " The Voice" + (item.check ? " | Check" : " | Clear")));
    if (item.check) checks.push(item.sound + " At " + stamp(item.time) + " Is " + (item.under >= 0 ? "Only " + item.under.toFixed(1) + " dB Under" : Math.abs(item.under).toFixed(1) + " dB Over") + " The Voice On " + item.words.map(word => "“" + word.text + "”").join(", ") + ".");
  }
  lines.push("");
  if (eventSounds) { lines.push(Events.describe(eventSounds)); if (eventSounds.state === "missing" || eventSounds.state === "stale") checks.push("The Placed Event Sounds Do Not Match The Scenes. This Mix Is Not The Mix The Film Should Have."); }
  if (P.standIn(project)) lines.push("The Storyboard Uses Stand-In Voice Timing. Word Times Are Estimates, So Overlaps Will Move When The Recording Arrives.");
  if (!found.hasVoice && project.narration !== "None") lines.push("No Voice Recording Is Attached. The Loudness Is Of The Sound Cues Alone, And Cue Levels Against The Voice Could Not Be Measured.");
  for (const note of planned.silent) lines.push("Note: " + note);
  return { lines, checks };
}

function main() {
  const { values: options, positionals } = parseArgs({ allowPositionals: true, options: { target: { type: "string" }, peak: { type: "string" }, window: { type: "string" }, margin: { type: "string" },
    "all-words": { type: "boolean" }, wav: { type: "string" }, report: { type: "string" }, strict: { type: "boolean" }, ffmpeg: { type: "string" }, overwrite: { type: "boolean" }, help: { type: "boolean" } } });
  if (options.help) { console.log(usage); return; }
  if (positionals.length !== 1) throw new Error(usage);
  const number = (name, fallback, min, max) => {
    if (options[name] == null) return fallback;
    const value = Number(options[name]);
    if (!Number.isFinite(value) || value < min || value > max) throw new Error("--" + name + " Needs A Number From " + min + " To " + max + ".");
    return value;
  };
  const targets = { target: number("target", -14, -40, -5), peak: number("peak", -1.5, -20, 0) }, window = number("window", 0.4, 0.05, 5), margin = number("margin", 6, 0, 40);
  for (const name of ["wav", "report"]) if (options[name]) {
    const target = path.resolve(options[name]);
    Film.guardOutput(target, name === "wav" ? "The Check Mix" : "The Report");
    if (name === "wav" && !/\.wav$/i.test(target)) throw new Error("Name The Check Mix As A .wav File. This Tool Writes Sound Only.");
    if (fs.existsSync(target) && !options.overwrite) throw new Error("Choose A New Output File, Or Add --overwrite: " + target);
  }
  const { film, scope, project } = Film.openFilm(positionals[0]), ffmpeg = Meter.locate("ffmpeg", options.ffmpeg);
  const planned = plan(project), tracks = render(planned, decodeAll(ffmpeg, planned, film.dir));
  if (!tracks.count) throw new Error("The Film Has No Length To Measure.");
  const measured = Meter.loudness(ffmpeg, tracks.mix), found = analyse(project, planned, tracks, { window, margin, allWords: options["all-words"] });
  let eventSounds = null;
  try { eventSounds = Events.status(scope, project); } catch (error) { planned.silent.push("The Event Sounds Could Not Be Checked: " + error.message); }
  const { lines, checks } = describe(project, planned, measured, found, targets, eventSounds);
  console.log(lines.join("\n"));
  console.log(checks.length ? "To Check (" + checks.length + "):" : "Nothing Stands Out Against The Targets.");
  for (const check of checks) console.log("  " + check);
  if (options.wav) {
    const packed = wavBytes(tracks.mix);
    fs.writeFileSync(path.resolve(options.wav), packed.bytes);
    console.log("Wrote The Check Mix As Sound Only: " + path.resolve(options.wav) + (packed.clipped ? " (" + packed.clipped + " Samples Passed Full Scale And Were Held There.)" : ""));
  }
  if (options.report) fs.writeFileSync(path.resolve(options.report), JSON.stringify({ title: project.title, storyboard: path.basename(film.file), seconds: planned.seconds, targets, loudness: measured,
    standInVoice: P.standIn(project), narration: project.narration || "Voice", voiceRecording: found.hasVoice, eventSounds: eventSounds && { state: eventSounds.state, placed: eventSounds.placed, expected: eventSounds.expected },
    window, margin, cues: found.cues, overlaps: found.overlaps, notes: planned.silent, checks }, null, 2) + "\n");
  console.log("Nothing Was Changed. These Levels Are Reported, Never Applied. Change A Gain In The Authored Storyboard And Run The Timing Tool Again. No Video Was Written.");
  if (options.strict && checks.length) throw new Error(checks.length + " Item" + (checks.length === 1 ? "" : "s") + " To Check, And --strict Is Set.");
}
module.exports = { plan, render, rmsDb, soloDb, keyWords, analyse, wavBytes, describe };
if (require.main === module) { try { main(); } catch (error) { console.error(error.message); process.exitCode = 1; } }
