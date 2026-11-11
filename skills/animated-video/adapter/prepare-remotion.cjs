"use strict";
const fs = require("node:fs"), path = require("node:path"), crypto = require("node:crypto");
const P = require("../studio/project.js"), Sound = require("../studio/sound.js");
const skillRoot = path.resolve(__dirname, "..");
function painterSource() {
  const sources = ["project.js", "marks.js", "space.js", "frame.js"].map(name => fs.readFileSync(path.join(skillRoot, "studio", name), "utf8"));
  return "const sceneScope = {};\nfunction loadPainter(globalThis, module) {\n" + sources.join("\n") + "\n}\nloadPainter(sceneScope, undefined);\nexport const MotionFrame = sceneScope.MotionFrame;\n";
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
function build(raw) {
  const project = P.cleanProject(raw), files = new Map();
  const [width, height] = P.aspects[project.aspect], fps = project.fps;
  const timeline = {width, height, fps, frames: Math.ceil(P.duration(project) * fps - 1e-7), audio: [], notes: []};
  const pretty = v => JSON.stringify(v, null, 2) + "\n";
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
        const name = cue.sound.toLowerCase().replaceAll(" ", "-") + ".wav";
        bytes = fs.readFileSync(path.join(skillRoot, "assets/sounds", name)); file = "audio/" + name;
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
  const visuals = {...project, scenes: project.scenes.map(s => ({...s, cues: []}))};
  files.set("src/frame-project.json", pretty(visuals)); files.set("src/timeline.json", pretty(timeline));
  files.set("src/painter.mjs", painterSource());
  files.set("src/index.jsx", fs.readFileSync(path.join(__dirname, "remotion-entry.jsx")));
  files.set("render-reviewed.cjs", fs.readFileSync(path.join(__dirname, "render-reviewed.cjs")));
  files.set("source-storyboard.json", pretty(project));
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
  const {files, timeline} = build(JSON.parse(fs.readFileSync(source, "utf8")));
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
module.exports = {build, prepare, painterSource};
if (require.main === module) {
  const [source, target] = process.argv.slice(2);
  try {
    if (!source || !target) throw new Error("Usage: node adapter/prepare-remotion.cjs Storyboard.json NewProjectFolder");
    const t = prepare(source, target); console.log("Prepared " + t.frames + " Frames And " + t.audio.length + " Audio Cues. Open The Project In Remotion Studio For Review.");
  } catch (error) { console.error(error.message); process.exitCode = 1; }
}
