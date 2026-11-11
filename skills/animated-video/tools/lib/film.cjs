// Shared Film Loading For The Node Tools: Read A Storyboard And Its Scene Modules, Run The Painter Without A Browser,
// And Record Every Drawing Call So Frames Can Be Compared.
"use strict";
const fs = require("node:fs"), path = require("node:path");
const P = require("../../studio/project.js");
const skillRoot = path.resolve(__dirname, "../..");
const studioFiles = ["project.js", "marks.js", "space.js", "kit.js", "timing.js", "scenes.js", "captions.js", "frame.js"];

const read = file => fs.readFileSync(file, "utf8").replace(/^﻿/, "");
// The Painter Sources In Load Order, Then The Kit's Own Parts.
function studioSources() {
  return studioFiles.map(name => ({ name: "studio/" + name, source: read(path.join(skillRoot, "studio", name)) }));
}
function partSources() {
  const dir = path.join(skillRoot, "parts");
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter(name => name.endsWith(".js")).sort().map(name => ({ name: "parts/" + name, source: read(path.join(dir, name)) }));
}
// Read A Storyboard And The Scene Modules It Lists Beside It.
function loadFilm(file) {
  const full = path.resolve(file), dir = path.dirname(full);
  if (!fs.existsSync(full)) throw new Error("Storyboard Not Found: " + file);
  let raw;
  try { raw = JSON.parse(read(full)); } catch (error) { throw new Error("The Storyboard Is Not Valid JSON: " + error.message); }
  const project = P.cleanProject(raw);
  const modules = (project.modules || []).map(name => {
    const at = path.join(dir, ...name.split("/"));
    if (!fs.existsSync(at)) throw new Error("Scene Module Not Found Beside The Storyboard: " + name);
    return { name, file: at, source: read(at) };
  });
  return { file: full, dir, raw, project, modules };
}

class StubPath { constructor(d) { this.d = String(d ?? ""); } }
// Stand-Ins That Record And Refuse Any Use Of Randomness Or The Clock Inside A Scene Module.
function guards() {
  const touched = new Set(), math = Object.create(Math);
  const refuse = (name, advice) => function () { touched.add(name); throw new Error(name + " Is Not Allowed In A Scene Module. " + advice); };
  Object.defineProperty(math, "random", { value: refuse("Math.random", "Use The State's random Or rng.") });
  const date = refuse("Date", "Use The State's time.");
  date.now = refuse("Date.now", "Use The State's time.");
  const clock = { now: refuse("performance.now", "Use The State's time.") };
  return { touched, math, date, clock };
}
// Run One Scene Module The Way Motion Studio Does: In Its Own Function, Seeing Only MotionScenes And MotionKit.
function runModule(scope, name, source, guard) {
  const shell = { MotionScenes: scope.MotionScenes, MotionKit: scope.MotionKit };
  const names = ["MotionScenes", "MotionKit", "globalThis", "window", "self", "global", "Math", "Date", "performance", "setTimeout", "setInterval", "requestAnimationFrame", "document", "fetch"];
  const values = [scope.MotionScenes, scope.MotionKit, shell, shell, shell, shell, guard ? guard.math : Math, guard ? guard.date : Date, guard ? guard.clock : undefined];
  try { new Function(...names, source + "\n//# sourceURL=" + name.replace(/\s/g, "-")).apply(undefined, values); }
  catch (error) { error.message = "Scene Module " + name + " Could Not Be Loaded: " + error.message; throw error; }
}
// A Fresh Painter With The Kit's Parts Loaded And Sealed. Scene Modules Are Added With loadModules.
function createScope(options = {}) {
  const scope = {}, guard = options.guard === false ? null : guards();
  new Function("globalThis", "module", "Path2D", studioSources().map(item => item.source).join("\n"))(scope, undefined, StubPath);
  for (const part of partSources()) runModule(scope, part.name, part.source, guard);
  scope.MotionScenes.seal();
  scope.touched = guard ? guard.touched : new Set();
  scope.guard = guard;
  return scope;
}
function loadModules(scope, modules) {
  scope.MotionScenes.reset();
  for (const module of modules) runModule(scope, module.name, module.source, scope.guard);
}
// Open A Storyboard File Ready To Draw: { film, scope, project }.
function openFilm(file, options) {
  const film = loadFilm(file), scope = createScope(options);
  loadModules(scope, film.modules);
  return { film, scope, project: film.project };
}

// A Canvas Stand-In Whose 2D Context Records Every Call And Property Change. Text Is Measured By A Fixed Estimate.
function recorder(width, height) {
  const calls = [], bad = [], stack = [], overrides = {};
  const state = { globalAlpha: 1, globalCompositeOperation: "source-over", fillStyle: "#000000", strokeStyle: "#000000", lineWidth: 1, lineCap: "butt", lineJoin: "miter",
    miterLimit: 10, lineDashOffset: 0, font: "10px sans-serif", textAlign: "start", textBaseline: "alphabetic", direction: "ltr", shadowBlur: 0, shadowColor: "rgba(0, 0, 0, 0)",
    shadowOffsetX: 0, shadowOffsetY: 0, filter: "none", imageSmoothingEnabled: true, imageSmoothingQuality: "low", letterSpacing: "0px", wordSpacing: "0px", fontKerning: "auto" };
  let dash = [], matrix = [1, 0, 0, 1, 0, 0], made = 0;
  const plain = value => {
    if (typeof value === "number") return Number.isFinite(value) ? value : String(value);
    if (value && typeof value === "object") return value.tag || (value instanceof StubPath ? "path:" + value.d : Array.isArray(value) ? value.map(plain) : "object");
    if (typeof value === "function") return "function";
    return value;
  };
  const log = (name, args) => {
    if (args.some(arg => typeof arg === "number" && !Number.isFinite(arg))) bad.push(name + "(" + args.map(String).join(", ") + ")");
    calls.push([name, ...args.map(plain)]);
  };
  const multiply = (a, b, c, d, e, f) => {
    const m = matrix;
    matrix = [m[0] * a + m[2] * b, m[1] * a + m[3] * b, m[0] * c + m[2] * d, m[1] * c + m[3] * d, m[0] * e + m[2] * f + m[4], m[1] * e + m[3] * f + m[5]];
  };
  const paint = kind => (...args) => {
    const tag = kind + "#" + (++made);
    log(kind, args);
    return { tag, addColorStop(offset, color) { log("addColorStop", [tag, offset, color]); } };
  };
  const glyph = ch => ch === " " ? 0.28 : /[iljtf.,;:'!|()\[\]]/.test(ch) ? 0.3 : /[mwMW@%]/.test(ch) ? 0.86 : /[A-Z]/.test(ch) ? 0.67 : /[0-9]/.test(ch) ? 0.56 : 0.52;
  const methods = {
    save() { stack.push({ state: Object.assign({}, state), dash: dash.slice(), matrix: matrix.slice() }); log("save", []); },
    restore() { const top = stack.pop(); if (top) { Object.assign(state, top.state); dash = top.dash; matrix = top.matrix; } log("restore", []); },
    reset() { stack.length = 0; matrix = [1, 0, 0, 1, 0, 0]; dash = []; log("reset", []); },
    translate(x, y) { multiply(1, 0, 0, 1, x, y); log("translate", [x, y]); },
    scale(x, y) { multiply(x, 0, 0, y, 0, 0); log("scale", [x, y]); },
    rotate(a) { multiply(Math.cos(a), Math.sin(a), -Math.sin(a), Math.cos(a), 0, 0); log("rotate", [a]); },
    transform(a, b, c, d, e, f) { multiply(a, b, c, d, e, f); log("transform", [a, b, c, d, e, f]); },
    setTransform(a, b, c, d, e, f) { matrix = typeof a === "object" && a ? [a.a, a.b, a.c, a.d, a.e, a.f] : [a ?? 1, b ?? 0, c ?? 0, d ?? 1, e ?? 0, f ?? 0]; log("setTransform", matrix.slice()); },
    resetTransform() { matrix = [1, 0, 0, 1, 0, 0]; log("resetTransform", []); },
    getTransform() { return { a: matrix[0], b: matrix[1], c: matrix[2], d: matrix[3], e: matrix[4], f: matrix[5] }; },
    setLineDash(list) { dash = Array.from(list || []); log("setLineDash", [dash]); },
    getLineDash() { return dash.slice(); },
    measureText(text) {
      const size = parseFloat(/(\d+(?:\.\d+)?)px/.exec(state.font)?.[1] ?? "10"), bold = /\b([6-9]00|bold)\b/.test(state.font) ? 1.06 : 1;
      let width = 0;
      for (const ch of String(text)) width += glyph(ch);
      return { width: width * size * bold, actualBoundingBoxAscent: size * 0.74, actualBoundingBoxDescent: size * 0.2, fontBoundingBoxAscent: size * 0.9, fontBoundingBoxDescent: size * 0.24 };
    },
    createLinearGradient: paint("createLinearGradient"), createRadialGradient: paint("createRadialGradient"), createConicGradient: paint("createConicGradient"), createPattern: paint("createPattern"),
    getImageData() { throw new Error("A Draw Function Must Not Read Pixels Back From The Canvas."); },
    isPointInPath() { return false; }, isPointInStroke() { return false; }
  };
  const canvas = { width, height };
  const context = new Proxy({}, {
    get(_, key) {
      if (typeof key === "symbol") return undefined;
      if (key in overrides) return overrides[key];
      if (key === "canvas") return canvas;
      if (key in methods) return methods[key];
      if (key in state) return state[key];
      return (...args) => log(key, args);
    },
    set(_, key, value) {
      if (typeof value === "function") { overrides[key] = value; return true; }
      state[key] = value; calls.push(["=", key, plain(value)]);
      return true;
    },
    deleteProperty(_, key) { delete overrides[key]; return true; },
    has(_, key) { return key in methods || key in state || key in overrides; }
  });
  canvas.getContext = () => context;
  return { canvas, context, calls, bad };
}
// Draw One Frame Into A Recorder. Returns { calls, bad, problems }.
function drawFrame(scope, project, time, options = {}) {
  const size = scope.MotionProject.size(project), record = recorder(size[0], size[1]);
  scope.MotionScenes.clearProblems();
  scope.MotionFrame.draw(record.canvas, project, time, options);
  return { calls: record.calls, bad: record.bad, problems: scope.MotionScenes.problems() };
}
// Strip Comments And String Contents So A Source Scan Does Not Trip On Prose.
function codeOnly(source) {
  return source.replace(/\/\*[\s\S]*?\*\//g, " ").replace(/(^|[^:\\])\/\/.*$/gm, "$1").replace(/(["'`])(?:\\.|(?!\1)[^\\\n])*\1/g, "\"\"");
}
// Names Of Clock Or Randomness Calls That Appear In A Module's Code.
function impureMentions(source) {
  const code = codeOnly(source), found = [];
  for (const [name, pattern] of [["Math.random", /\bMath\s*\.\s*random\b/], ["Date.now", /\bDate\s*\.\s*now\b/], ["new Date", /\bnew\s+Date\b/], ["performance.now", /\bperformance\s*\.\s*now\b/],
    ["setTimeout", /\bsetTimeout\b/], ["setInterval", /\bsetInterval\b/], ["requestAnimationFrame", /\brequestAnimationFrame\b/]]) if (pattern.test(code)) found.push(name);
  return found;
}
// Times Worth Checking In Every Scene: Its First Frame, Three Interior Moments, And Its Last Frame.
function sampleTimes(project) {
  const times = [], frame = 1 / project.fps;
  let start = 0;
  for (const scene of project.scenes) {
    for (const u of [0, 0.23, 0.5, 0.77]) times.push(Math.round((start + scene.duration * u) / frame) * frame);
    times.push(Math.max(start, start + scene.duration - frame));
    start += scene.duration;
  }
  return [...new Set(times.map(time => Math.round(time * 1e6) / 1e6))];
}
// Draw Chosen Frames Twice, In Two Different Orders, And Compare The Recorded Calls.
// Returns A List Of Plain-Language Failures. An Empty List Means The Film Draws The Same Frame The Same Way Every Time.
function determinism(scope, project, times) {
  const failures = [], list = times || sampleTimes(project), first = new Map();
  const label = time => time.toFixed(3) + "s (Scene " + (scope.MotionProject.locate(project, time).index + 1) + ")";
  scope.touched.clear();
  for (const time of list) {
    const result = drawFrame(scope, project, time);
    for (const problem of result.problems) failures.push("Frame At " + label(time) + ": " + problem.message);
    if (result.bad.length) failures.push("Frame At " + label(time) + " Passes A Non-Finite Number To " + result.bad[0] + ".");
    first.set(time, JSON.stringify(result.calls));
  }
  for (const time of list.slice().reverse()) {
    const again = JSON.stringify(drawFrame(scope, project, time).calls);
    if (again !== first.get(time)) failures.push("Frame At " + label(time) + " Draws Differently The Second Time. A Draw Function Is Keeping State Between Frames.");
  }
  for (const name of scope.touched) failures.push("A Scene Module Used " + name + ".");
  return [...new Set(failures)];
}

module.exports = { skillRoot, studioFiles, studioSources, partSources, loadFilm, createScope, loadModules, openFilm, runModule, guards, recorder, drawFrame, codeOnly, impureMentions, sampleTimes, determinism, StubPath, read };
