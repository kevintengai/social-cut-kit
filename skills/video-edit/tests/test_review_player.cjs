const assert = require("node:assert/strict");
const {readFileSync} = require("node:fs");
const {join} = require("node:path");
const {test} = require("node:test");
const vm = require("node:vm");

const html = readFileSync(join(__dirname, "../scripts/review.html"), "utf8");
const playerCode = html.match(/<script>([\s\S]*?)<\/script>/)[1];

function player() {
  const nodes = new Map();
  function element() {
    return {style: {setProperty() {}}, dataset: {}, classList: {toggle() {}}, children: [], textContent: "", value: "",
      volume: 1, paused: true, readyState: 0,
      replaceChildren(...kids) { this.children = kids; }, append(...kids) { this.children.push(...kids); },
      insertBefore() {}, addEventListener() {}, setAttribute() {}, removeAttribute() {}, remove() {},
      pause() {}, load() {}, play() { return Promise.resolve(); }};
  }
  const document = {
    title: "", createElement: element,
    getElementById(id) {
      if (!nodes.has(id)) nodes.set(id, element());
      return nodes.get(id);
    },
  };
  const ctx = vm.createContext({document, window: {}, fetch: () => new Promise(() => {}),
    performance: {now: () => 0}, requestAnimationFrame() {}, cancelAnimationFrame() {}});
  vm.runInContext(playerCode, ctx);
  return {ctx, nodes, run: text => vm.runInContext(text, ctx)};
}

function model(extra) {
  return {project: {}, revision: "r", model: Object.assign({title: "Cut", duration: 8, width: 360, height: 640, fps: 24,
    caption_style: {size: 20, font: "Arial", color: "#FFFFFF", stroke: 1, outline: "#000000", margin: 7},
    assets: {}, shots: [], overlays: [], audio: [], captions: [], warnings: []}, extra)};
}

test("Fade Levels Follow Straight Ramps Inside A Shot Or Cue", () => {
  const app = player();
  app.ctx.shot = {type: "shot", row: {at: 2, duration: 4, gain: 0.8, fade_in: 1, fade_out: 2}};
  app.ctx.cue = {type: "audio", row: {at: 1, end: 3, fade_out: 0.5}};
  app.ctx.plain = {type: "audio", row: {at: 1, end: 3, gain: 0.36}};
  const levels = app.run("[2, 2.5, 3.5, 5, 6].map(t => level(shot, t))");
  assert.deepEqual(Array.from(levels).map(v => Math.round(v * 1000) / 1000), [0, 0.4, 0.8, 0.4, 0]);
  assert.deepEqual(Array.from(app.run("[1, 2.75, 3.2].map(t => level(cue, t))")), [1, 0.5, 0]);
  assert.deepEqual(Array.from(app.run("[1, 2, 2.99].map(t => level(plain, t))")), [0.36, 0.36, 0.36]);
});

test("Only Rows With Fades Have Their Volume Driven During Playback", () => {
  const app = player();
  app.ctx.state = model({
    assets: {Bed: {kind: "audio"}, Tap: {kind: "audio"}},
    audio: [{asset: "Bed", at: 0, end: 4, start: 0, gain: 0.5, fade_out: 2}, {asset: "Tap", at: 0, end: 4, start: 0, gain: 0.25}],
  });
  app.run("setState(state, 'Ready.')");
  app.run("layers.forEach(l => { l.media.readyState = 4; })");
  app.run("time = 3; draw(true)");
  const volumes = Array.from(app.run("layers.map(l => l.media.volume)"));
  assert.deepEqual(volumes, [0.25, 0.25]);
  app.run("time = 3.5; draw(true)");
  assert.deepEqual(Array.from(app.run("layers.map(l => l.media.volume)")), [0.125, 0.25]);
});

test("Splitting A Shot Keeps Each Fade On Its Outer Edge", () => {
  const app = player();
  const shot = {asset: "A", in: 1, out: 5, lead: 0.5, speed: 2, fade_in: 0.2, fade_out: 0.3, tone_map: false};
  app.ctx.state = model({
    duration: 2.25, assets: {A: {kind: "image"}},
    shots: [{asset: "A", at: 0, start: 0.5, end: 5, duration: 2.25, speed: 2, gain: 1, fit: "cover",
      geometry: {browser: [0, 0, 1, 1]}, brightness: 1, contrast: 1, saturation: 1, fade_in: 0.2, fade_out: 0.3}],
  });
  app.ctx.state.project = {version: 1, title: "Cut", assets: {}, shots: [shot]};
  app.run("setState(state, 'Ready.')");
  app.run("time = 1");
  app.nodes.get("split").onclick();
  const halves = JSON.parse(app.nodes.get("document").value).shots;
  assert.equal(halves.length, 2);
  assert.deepEqual(halves[0], {asset: "A", in: 0.5, out: 2.5, lead: 0, speed: 2, fade_in: 0.2, tone_map: false, tail: 0});
  assert.deepEqual(halves[1], {asset: "A", in: 2.5, out: 5, lead: 0, speed: 2, fade_out: 0.3, tone_map: false, tail: 0});
  assert.match(app.nodes.get("status").textContent, /Save Timeline To Apply/);
});

test("Source Notes From Validation Appear Under The Editor Status", () => {
  const app = player();
  app.ctx.state = model({warnings: ["Asset Phone Is HLG HDR.", "Asset Phone Is Stored 3840 By 2160."]});
  app.run("setState(state, 'Ready.')");
  assert.deepEqual(app.nodes.get("notes").children.map(node => node.textContent),
    ["Asset Phone Is HLG HDR.", "Asset Phone Is Stored 3840 By 2160."]);
  assert.equal(app.nodes.get("status").textContent, "Ready.");
  app.ctx.state = model({});
  app.run("setState(state, 'Timeline Saved.')");
  assert.equal(app.nodes.get("notes").children.length, 0);
});
