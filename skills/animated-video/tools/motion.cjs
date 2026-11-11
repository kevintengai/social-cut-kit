// Measure How Much The Picture Changes From Frame To Frame, List The Stillest Stretches, And Check That Frames Redraw Identically.
// Frames Are Drawn Small In A Local Browser And Compared In Memory. Nothing Is Saved Except An Optional JSON Report. No Video Is Written.
"use strict";
const fs = require("node:fs"), path = require("node:path");
const { parseArgs } = require("node:util");
const Film = require("./lib/film.cjs"), Browser = require("./lib/browser.cjs");
const P = require("../studio/project.js");

const usage = "Usage: node tools/motion.cjs Storyboard.json --browser BrowserPath [--still 0.75] [--threshold 0.05] [--with-captions] [--determinism] [--report Motion.json] [--overwrite]";
const stamp = value => value.toFixed(2) + "s";

// ---------------------------------------------------------------- Functions That Run Inside The Page
// Draw A Run Of Frames Small And Return The Mean Pixel Change Between Neighbours, As A Percentage Of Full Scale.
function pageChanges(first, count, fps, scale, captions) {
  const size = MotionProject.size(window.film), canvas = window.motionCanvas || (window.motionCanvas = document.createElement("canvas"));
  canvas.width = Math.max(2, Math.round(size[0] * scale)); canvas.height = Math.max(2, Math.round(size[1] * scale));
  const context = canvas.getContext("2d", { alpha: false, willReadFrequently: true }), out = [];
  MotionScenes.clearProblems();
  for (let frame = first; frame < first + count; frame++) {
    MotionFrame.draw(canvas, window.film, frame / fps, { captions });
    const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data, before = window.motionBefore;
    if (before && window.motionBeforeFrame === frame - 1) {
      let sum = 0;
      for (let i = 0; i < pixels.length; i += 4) sum += Math.abs(pixels[i] - before[i]) + Math.abs(pixels[i + 1] - before[i + 1]) + Math.abs(pixels[i + 2] - before[i + 2]);
      out.push(sum / (pixels.length / 4 * 3) / 255 * 100);
    } else out.push(null);
    window.motionBefore = pixels; window.motionBeforeFrame = frame;
  }
  return { changes: out, problems: MotionScenes.problems() };
}
// Draw Frames And Return A Short Fingerprint Of Each, To Compare Two Passes.
function pagePrints(frames, fps, scale) {
  const size = MotionProject.size(window.film), canvas = document.createElement("canvas");
  canvas.width = Math.round(size[0] * scale); canvas.height = Math.round(size[1] * scale);
  const context = canvas.getContext("2d", { alpha: false, willReadFrequently: true });
  return frames.map(frame => {
    MotionFrame.draw(canvas, window.film, frame / fps);
    const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
    let a = 0x811c9dc5, b = 0;
    for (let i = 0; i < pixels.length; i++) { a = Math.imul(a ^ pixels[i], 0x01000193); b = (b + pixels[i] * (i % 251 + 1)) >>> 0; }
    return (a >>> 0).toString(16) + "-" + b.toString(16);
  });
}

async function main() {
  const { values: options, positionals } = parseArgs({ allowPositionals: true, options: { browser: { type: "string" }, still: { type: "string" }, threshold: { type: "string" },
    "with-captions": { type: "boolean" }, determinism: { type: "boolean" }, report: { type: "string" }, overwrite: { type: "boolean" }, help: { type: "boolean" } } });
  if (options.help) { console.log(usage); return; }
  if (positionals.length !== 1) throw new Error(usage);
  const film = Film.loadFilm(positionals[0]), project = film.project, executable = Browser.browserPath(options.browser);
  const least = options.still == null ? 0.75 : Number(options.still), threshold = options.threshold == null ? 0.05 : Number(options.threshold);
  if (!(least > 0) || !(threshold >= 0)) throw new Error("--still Needs Positive Seconds And --threshold A Percentage Of Zero Or More.");
  if (options.report) Film.guardOutput(options.report, "The Report");
  if (options.report && fs.existsSync(path.resolve(options.report)) && !options.overwrite) throw new Error("Choose A New Report File, Or Add --overwrite.");
  const fps = project.fps, total = P.duration(project), frames = Math.ceil(total * fps - 1e-7), size = P.size(project), scale = Math.min(1, 320 / Math.max(size[0], size[1]));
  const page = await Browser.openFilmPage(executable, film), changes = [], problems = new Map();
  let mismatched = [];
  try {
    for (let first = 0; first < frames; first += fps) {
      const result = await page.call(pageChanges, first, Math.min(fps, frames - first), fps, scale, Boolean(options["with-captions"]));
      changes.push(...result.changes);
      for (const problem of result.problems) problems.set(problem.scene + "|" + problem.message, problem);
    }
    if (options.determinism) {
      const picks = [...new Set(Film.sampleTimes(project).map(time => Math.min(frames - 1, Math.round(time * fps))))];
      const once = await page.call(pagePrints, picks, fps, 0.5), twice = await page.call(pagePrints, picks.slice().reverse(), fps, 0.5);
      twice.reverse();
      mismatched = picks.filter((frame, i) => once[i] !== twice[i]);
    }
  } finally { await page.close(); }
  // Per-Second Averages.
  const seconds = [];
  for (let s = 0; s * fps < frames; s++) {
    const part = changes.slice(s * fps, (s + 1) * fps).filter(value => value != null);
    seconds.push({ second: s, scene: P.locate(project, Math.min(total, s + 0.5)).index + 1, mean: part.length ? part.reduce((sum, v) => sum + v, 0) / part.length : 0, peak: part.length ? Math.max(...part) : 0 });
  }
  // Still Stretches: Runs Of Frames Whose Change Stays Under The Threshold.
  const stretches = [];
  let run = null;
  for (let frame = 1; frame <= frames; frame++) {
    const quiet = frame < frames && changes[frame] != null && changes[frame] <= threshold;
    if (quiet) { if (!run) run = { from: frame - 1 }; }
    else if (run) { run.to = frame - 1; run.seconds = (run.to - run.from) / fps; if (run.seconds >= least) stretches.push(run); run = null; }
  }
  stretches.sort((a, b) => b.seconds - a.seconds);
  const top = Math.max(...seconds.map(item => item.mean), 1e-9);
  console.log(project.title + " | Picture Change Per Second (Mean Percent Of Full Scale" + (options["with-captions"] ? ", Captions Included" : ", Captions Hidden") + ")");
  for (const item of seconds) console.log(String(item.second).padStart(4) + "s | Scene " + String(item.scene).padEnd(3) + "| " + item.mean.toFixed(3).padStart(7) + " | " + "#".repeat(Math.round(item.mean / top * 40)));
  if (stretches.length) {
    console.log("Stillest Stretches (Change At Or Below " + threshold + " Percent For " + least + " Seconds Or Longer):");
    for (const item of stretches.slice(0, 12)) console.log("  " + stamp(item.from / fps) + " To " + stamp(item.to / fps) + " | " + item.seconds.toFixed(2) + " Seconds | Scene " + (P.locate(project, item.from / fps).index + 1));
  } else console.log("No Still Stretch Of " + least + " Seconds Or Longer Was Found.");
  if (options.determinism) console.log(mismatched.length ? "Determinism Failed: Frames " + mismatched.join(", ") + " Drew Differently The Second Time." : "Determinism Passed: The Sampled Frames Drew Identically Twice.");
  if (options.report) fs.writeFileSync(path.resolve(options.report), JSON.stringify({ title: project.title, fps, frames, threshold, captions: Boolean(options["with-captions"]), seconds, stretches,
    determinism: options.determinism ? { passed: !mismatched.length, mismatched } : null, problems: [...problems.values()] }, null, 2) + "\n");
  console.log("Measured " + frames + " Frames In Memory. No Video Or Image Was Written.");
  for (const problem of problems.values()) console.error("Scene " + problem.scene + ": " + problem.message);
  if (problems.size || mismatched.length) throw new Error("The Motion Check Found Problems.");
}
if (require.main === module) main().catch(error => { console.error(error.message); process.exitCode = 1; });
