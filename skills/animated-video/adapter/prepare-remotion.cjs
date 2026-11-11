"use strict";
const fs = require("node:fs"), path = require("node:path"), crypto = require("node:crypto");
const P = require("../studio/project.js"), Sound = require("../studio/sound.js");
const skillRoot = path.resolve(__dirname, "..");
const studioFiles = ["project.js", "marks.js", "space.js", "kit.js", "timing.js", "scenes.js", "captions.js", "frame.js"];
const read = file => fs.readFileSync(file, "utf8").replace(/^﻿/, "");
// The Painter As One Module: The Studio Sources, The Kit's Parts, Then The Film's Own Scene Modules.
// Each Part And Module Runs In Its Own Function And Sees MotionScenes And MotionKit By Name, As It Does In Motion Studio.
function painterSource(modules = []) {
  const sources = studioFiles.map(name => read(path.join(skillRoot, "studio", name)));
  const partsDir = path.join(skillRoot, "parts");
  const parts = fs.existsSync(partsDir) ? fs.readdirSync(partsDir).filter(name => name.endsWith(".js")).sort().map(name => read(path.join(partsDir, name))) : [];
  const wrap = source => "(function () {\n" + source + "\n})();";
  return "const sceneScope = {};\nfunction loadPainter(globalThis, module) {\n" + sources.join("\n") +
    "\nconst MotionScenes = globalThis.MotionScenes, MotionKit = globalThis.MotionKit;\n" + parts.map(wrap).join("\n") + "\nMotionScenes.seal();\n" + modules.map(item => wrap(item.source)).join("\n") +
    "\n}\nloadPainter(sceneScope, undefined);\nexport const MotionFrame = sceneScope.MotionFrame;\n";
}
function audioExtension(bytes, mime) {
  const header = bytes.subarray(0, 4).toString("ascii");
  if (header === "RIFF") return "wav";
  if (header === "OggS") return "ogg";
  if (header === "fLaC") return "flac";
  if (bytes.subarray(4, 8).toString() === "ftyp") return "m4a";
  if (bytes.subarray(0, 3).toString() === "ID3" || (bytes[0] === 255 && (bytes[1] & 224) === 224)) return "mp3";
  const types = {mpeg: "mp3", mp3: "mp3", mp4: "m4a", "x-m4a": "m4a", webm: "webm", aac: "aac", wav: "wav", "x-wav": "wav", ogg: "ogg", flac: "flac"};
  return types[mime.split("/").pop()] || "bin";
}
// A Stereo Copy Of A Bank Sound Placed Left Or Right With Equal Power.
function pannedWav(name, pan) {
  const mono = Sound.make(name), angle = (Math.max(-1, Math.min(1, pan)) + 1) * Math.PI / 4, sides = [Math.cos(angle), Math.sin(angle)];
  const out = Buffer.alloc(44 + mono.length * 4);
  out.write("RIFF", 0); out.writeUInt32LE(out.length - 8, 4); out.write("WAVEfmt ", 8); out.writeUInt32LE(16, 16); out.writeUInt16LE(1, 20); out.writeUInt16LE(2, 22);
  out.writeUInt32LE(48000, 24); out.writeUInt32LE(48000 * 4, 28); out.writeUInt16LE(4, 32); out.writeUInt16LE(16, 34); out.write("data", 36); out.writeUInt32LE(mono.length * 4, 40);
  for (let i = 0; i < mono.length; i++) for (let side = 0; side < 2; side++) {
    const v = Math.max(-1, Math.min(1, mono[i] * sides[side] * 1.33));
    out.writeInt16LE(Math.round(v * (v < 0 ? 32768 : 32767)), 44 + i * 4 + side * 2);
  }
  return out;
}
// options.base Is The Storyboard's Folder. It Is Needed When The Storyboard Lists Scene Modules Or A Voice File.
function build(raw, options = {}) {
  const project = P.cleanProject(raw), files = new Map();
  const [width, height] = P.size(project), fps = project.fps;
  const timeline = {width, height, fps, frames: Math.ceil(P.duration(project) * fps - 1e-7), audio: [], notes: []};
  const pretty = v => JSON.stringify(v, null, 2) + "\n";
  const beside = name => {
    if (!options.base) throw new Error("This Storyboard Lists Files Beside It. Prepare It From Its Saved File So They Can Be Found.");
    const at = path.join(options.base, ...name.split("/"));
    if (!fs.existsSync(at)) throw new Error("File Not Found Beside The Storyboard: " + name);
    return at;
  };
  const modules = (project.modules || []).map(name => ({name, source: read(beside(name))}));
  let offset = 0;
  for (let i = 0; i < project.scenes.length; i++) {
    const s = project.scenes[i], end = Math.ceil((offset + s.duration) * fps - 1e-7);
    s.cues.forEach((cue, j) => {
      const from = Math.round((offset + cue.at) * fps);
      const id = "s" + (i + 1) + "-c" + (j + 1);
      if (cue.type === "Voice") timeline.notes.push({id, from, line: cue.text, recorded: Boolean(cue.clip)});
      if ((cue.type === "Voice" && !cue.clip) || cue.gain === 0 || from >= end) return;
      let file, bytes, frames = end - from;
      if (cue.type === "Sound") {
        const slug = cue.sound.toLowerCase().replaceAll(" ", "-");
        if (cue.pan) { file = "audio/" + slug + "-pan-" + (cue.pan < 0 ? "left-" : "right-") + Math.round(Math.abs(cue.pan) * 100) + ".wav"; bytes = pannedWav(cue.sound, cue.pan); }
        else { file = "audio/" + slug + ".wav"; bytes = fs.readFileSync(path.join(skillRoot, "assets/sounds", slug + ".wav")); }
        frames = Math.min(frames, Math.ceil(Sound.lengths[cue.sound] * fps));
      } else {
        const comma = cue.clip.indexOf(",");
        bytes = Buffer.from(cue.clip.slice(comma + 1), "base64");
        const mime = cue.clip.slice(5, cue.clip.indexOf(";")), hash = crypto.createHash("sha256").update(bytes).digest("hex").slice(0, 20);
        file = "audio/voice-" + hash + "." + audioExtension(bytes, mime);
      }
      files.set("public/" + file, bytes); timeline.audio.push({id, file, from, frames, gain: cue.gain});
    });
    offset += s.duration;
  }
  // The Film Voice Runs Across Every Scene. A Negative Offset Starts Partway Into The Recording.
  const voice = project.voice;
  if (voice && (voice.clip || voice.file) && voice.gain > 0) {
    let bytes, mime;
    if (voice.clip) { bytes = Buffer.from(voice.clip.slice(voice.clip.indexOf(",") + 1), "base64"); mime = voice.clip.slice(5, voice.clip.indexOf(";")); }
    else { bytes = fs.readFileSync(beside(voice.file)); mime = "audio/" + path.extname(voice.file).slice(1).toLowerCase(); }
    const file = "audio/film-voice-" + crypto.createHash("sha256").update(bytes).digest("hex").slice(0, 20) + "." + audioExtension(bytes, mime);
    const from = Math.max(0, Math.round(voice.offset * fps)), entry = {id: "film-voice", file, from, frames: timeline.frames - from, gain: voice.gain};
    if (voice.offset < 0) entry.trimBefore = Math.round(-voice.offset * fps);
    if (entry.frames > 0) { files.set("public/" + file, bytes); timeline.audio.push(entry); }
  }
  const visuals = {...project, scenes: project.scenes.map(s => ({...s, cues: []}))};
  if (visuals.voice) { visuals.voice = {...visuals.voice}; delete visuals.voice.clip; }
  files.set("src/frame-project.json", pretty(visuals)); files.set("src/timeline.json", pretty(timeline));
  files.set("src/painter.mjs", painterSource(modules));
  files.set("src/index.jsx", fs.readFileSync(path.join(__dirname, "remotion-entry.jsx")));
  files.set("render-reviewed.cjs", fs.readFileSync(path.join(__dirname, "render-reviewed.cjs")));
  files.set("source-storyboard.json", pretty(project));
  // Scene Modules And A Voice File Travel Beside The Source Storyboard So Motion Studio Can Reopen It.
  for (const item of modules) files.set(item.name, item.source);
  if (voice && voice.file) files.set(voice.file, fs.readFileSync(beside(voice.file)));
  files.set("package.json", pretty({
    name: "motion-storyboard", private: true, version: "1.0.0",
    scripts: {studio: "remotion studio src/index.jsx", "render-reviewed": "node render-reviewed.cjs"},
    dependencies: {"@remotion/cli": "4.0.535", "@remotion/media": "4.0.535", remotion: "4.0.535", react: "19.2.8", "react-dom": "19.2.8"}
  }));
  return {files, timeline};
}
function prepare(source, target) {
  const dest = path.resolve(target);
  if (fs.existsSync(dest)) throw new Error("Choose A New Output Directory.");
  const {files, timeline} = build(JSON.parse(read(source)), {base: path.dirname(path.resolve(source))});
  fs.mkdirSync(path.dirname(dest), {recursive: true});
  const staging = fs.mkdtempSync(path.join(path.dirname(dest), ".motion-prepare-"));
  try {
    for (const [name, content] of files) {
      const full = path.join(staging, name);
      fs.mkdirSync(path.dirname(full), {recursive: true}); fs.writeFileSync(full, content, {flag: "wx"});
    }
    fs.renameSync(staging, dest);
  } finally {
    if (fs.existsSync(staging) && path.dirname(staging) === path.dirname(dest) && path.basename(staging).startsWith(".motion-prepare-"))
      fs.rmSync(staging, {recursive: true, force: true});
  }
  return timeline;
}
module.exports = {build, prepare, painterSource, pannedWav};
if (require.main === module) {
  const [source, target] = process.argv.slice(2);
  try {
    if (!source || !target) throw new Error("Usage: node adapter/prepare-remotion.cjs Storyboard.json NewProjectFolder");
    const t = prepare(source, target); console.log("Prepared " + t.frames + " Frames And " + t.audio.length + " Audio Cues. Open The Project In Remotion Studio For Review.");
  } catch (error) { console.error(error.message); process.exitCode = 1; }
}
