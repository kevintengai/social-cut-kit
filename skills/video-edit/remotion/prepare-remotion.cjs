"use strict";
// Turn A Social Cut Kit Timeline Into A Standalone Remotion Project. This Writes Project Files And Media Copies. It Never Writes A Video.
const fs = require("node:fs"), path = require("node:path");
const {spawnSync} = require("node:child_process");
const Cut = require("./cut-plan.cjs");

const USAGE = "Usage: node remotion/prepare-remotion.cjs Timeline.json NewProjectFolder [--allow-hdr] [--link-media] [--json]";
const PACKAGES = {"@remotion/cli": "4.0.535", "@remotion/media": "4.0.535", remotion: "4.0.535", react: "19.2.8", "react-dom": "19.2.8"};
const COMPOSITION = "VideoEdit";
const read = file => fs.readFileSync(file, "utf8").replace(/^﻿/, "");
const pretty = value => JSON.stringify(value, null, 2) + "\n";

function ffprobe(file) {
  const done = spawnSync("ffprobe", ["-v", "error", "-show_format", "-show_streams", "-of", "json", file], {encoding: "utf8", maxBuffer: 1 << 26});
  if (done.error && done.error.code === "ENOENT") throw new Cut.CutError("Install ffprobe And Add It To PATH.");
  if (done.error) throw done.error;
  if (done.status) throw new Cut.CutError((done.stderr || "").trim().slice(-2000) || `FFprobe Could Not Read ${file}.`);
  return Cut.probeSummary(JSON.parse(done.stdout));
}

// One Readable, Unique File Name Under public/media For Each Distinct Source File.
function mediaNames(doc, root) {
  const byPath = new Map(), names = {}, sources = {};
  if (!doc || typeof doc !== "object" || !doc.assets || typeof doc.assets !== "object" || Array.isArray(doc.assets)) return {names, sources};
  for (const [key, obj] of Object.entries(doc.assets)) {
    if (!obj || typeof obj.path !== "string" || !obj.path.trim()) continue;
    const full = path.resolve(root, obj.path);
    if (!fs.existsSync(full) || !fs.statSync(full).isFile()) continue;
    if (!byPath.has(full)) {
      const safe = path.basename(full).replace(/[^A-Za-z0-9._-]+/g, "-").replace(/^-+/, "") || "media";
      byPath.set(full, "media/" + String(byPath.size + 1).padStart(2, "0") + "-" + safe);
    }
    names[key] = byPath.get(full); sources[key] = full;
  }
  return {names, sources};
}

// The Plan And Every File Of The Project Except The Media. options.probe Replaces FFprobe In Tests.
function build(doc, root, options = {}) {
  const {names, sources} = mediaNames(doc, root), probes = {};
  for (const [key, full] of Object.entries(sources)) probes[key] = (options.probe || ffprobe)(full);
  const plan = Cut.plan(doc, probes, names, {allowHdr: Boolean(options.allowHdr)});
  // The Copy Of The Timeline Points At The Project's Own Media, So The Kit's Editor And Checks Open It From The Project Folder.
  const copy = JSON.parse(JSON.stringify(doc));
  for (const key of Object.keys(copy.assets)) copy.assets[key].path = "public/" + names[key];
  const files = new Map();
  files.set("src/cut.json", pretty(plan));
  files.set("src/cut-plan.cjs", fs.readFileSync(path.join(__dirname, "cut-plan.cjs")));
  files.set("src/index.jsx", fs.readFileSync(path.join(__dirname, "remotion-entry.jsx")));
  files.set("render-reviewed.cjs", fs.readFileSync(path.join(__dirname, "render-reviewed.cjs")));
  files.set("source-timeline.json", pretty(copy));
  files.set("package.json", pretty({
    name: "video-edit-review", private: true, version: "1.0.0",
    scripts: {studio: "remotion studio src/index.jsx", "render-reviewed": "node render-reviewed.cjs"},
    dependencies: PACKAGES
  }));
  const media = new Map();
  for (const [key, full] of Object.entries(sources)) media.set("public/" + names[key], full);
  return {plan, files, media};
}

function place(source, target, link) {
  if (link) {
    try { fs.linkSync(source, target); return; } catch (error) { if (error.code === "EEXIST") throw error; }
  }
  fs.copyFileSync(source, target, fs.constants.COPYFILE_EXCL);
}

function prepare(source, target, options = {}) {
  const dest = path.resolve(target), from = path.resolve(source);
  if (fs.existsSync(dest)) throw new Cut.CutError("Choose A New Output Directory.");
  let doc;
  try { doc = JSON.parse(read(from)); } catch (error) { throw new Cut.CutError(`Cannot Read Project ${from}. ${error.message}`); }
  const {plan, files, media} = build(doc, path.dirname(from), options);
  fs.mkdirSync(path.dirname(dest), {recursive: true});
  const staging = fs.mkdtempSync(path.join(path.dirname(dest), ".cut-prepare-"));
  try {
    for (const [name, content] of files) {
      const full = path.join(staging, name);
      fs.mkdirSync(path.dirname(full), {recursive: true}); fs.writeFileSync(full, content, {flag: "wx"});
    }
    for (const [name, original] of media) {
      const full = path.join(staging, name);
      fs.mkdirSync(path.dirname(full), {recursive: true}); place(original, full, Boolean(options.linkMedia));
    }
    fs.renameSync(staging, dest);
  } finally {
    if (fs.existsSync(staging) && path.dirname(staging) === path.dirname(dest) && path.basename(staging).startsWith(".cut-prepare-"))
      fs.rmSync(staging, {recursive: true, force: true});
  }
  return {project: dest, composition: COMPOSITION, title: plan.title, width: plan.width, height: plan.height, fps: plan.fps, frames: plan.frames,
    shots: plan.shots.length, overlays: plan.overlays.length, audio_cues: plan.audio.length, captions: plan.captions.length,
    media_files: media.size, warnings: plan.warnings};
}

module.exports = {build, prepare, mediaNames, PACKAGES, COMPOSITION};
if (require.main === module) {
  const args = process.argv.slice(2), flags = new Set(args.filter(arg => arg.startsWith("--"))), rest = args.filter(arg => !arg.startsWith("--"));
  try {
    const unknown = [...flags].find(flag => !["--allow-hdr", "--link-media", "--json"].includes(flag));
    if (unknown || rest.length !== 2) throw new Cut.CutError(USAGE);
    const summary = prepare(rest[0], rest[1], {allowHdr: flags.has("--allow-hdr"), linkMedia: flags.has("--link-media")});
    if (flags.has("--json")) console.log(JSON.stringify(summary, null, 2));
    else {
      for (const warning of summary.warnings) console.log("Warning: " + warning);
      console.log(`Prepared ${summary.frames} Frames At ${summary.fps} FPS With ${summary.shots} Shots, ${summary.overlays} Overlays, ` +
        `${summary.audio_cues} Audio Cues, And ${summary.captions} Captions. No Video Was Written. Run npm install And npm run studio ` +
        "In The Project For Owner Review.");
    }
  } catch (error) { console.error(error.message); process.exitCode = 1; }
}
