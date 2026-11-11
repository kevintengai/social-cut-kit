"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs"), path = require("node:path");
const P = require("../studio/project.js"), Audio = require("../studio/sound.js"), Space = require("../studio/space.js"), Marks = require("../studio/marks.js");
const root = path.resolve(__dirname, "..");
const p = P.cleanProject(P.demo());
assert(Math.abs(P.duration(p) - 13.6) < 0.00001);
assert.equal(P.locate(p, 3.8).index, 1);
assert.equal(P.locate(p, 9).index, 2);
assert.equal(P.locate(p, 99).local, 4.6);
assert.equal(P.locate(p, -1).local, 0);
assert.throws(() => P.cleanProject({ version: 2 }));
assert.throws(() => P.cleanProject({version: 1, scenes: [{ cues: [{type: "Voice", clip: "https://example.invalid/audio"}] }]}));
// Every Example Storyboard Is Already Clean: Top-Level Files, And The Storyboards Inside Example Folders.
const exampleFiles = [];
for (const entry of fs.readdirSync(path.join(root, "examples"), {withFileTypes: true})) {
  if (entry.isFile() && entry.name.endsWith(".json")) exampleFiles.push(path.join(root, "examples", entry.name));
  else if (entry.isDirectory()) for (const name of fs.readdirSync(path.join(root, "examples", entry.name))) if (/^storyboard.*\.json$/.test(name)) exampleFiles.push(path.join(root, "examples", entry.name, name));
}
assert(exampleFiles.length >= 9);
for (const file of exampleFiles) {
  const example = JSON.parse(fs.readFileSync(file)), clean = P.cleanProject(example);
  if (path.dirname(file) === path.join(root, "examples") || file.endsWith(".timed.json")) assert.deepEqual(example, clean, path.basename(file));
  assert.deepEqual(P.cleanProject(JSON.parse(JSON.stringify(clean))), clean);
}
for (const [name, length] of Object.entries(Audio.lengths)) {
  const samples = Audio.make(name), packed = Audio.wav(samples);
  assert.equal(samples.length, Math.round(length * 48000));
  let max = 0, energy = 0;
  for (const v of samples) { assert(Number.isFinite(v)); max = Math.max(max, Math.abs(v)); energy += v * v; }
  assert(max > 0.01 && max < 1); assert(energy / samples.length > 0.00001);
  assert.equal(Buffer.from(packed.subarray(0, 4)).toString(), "RIFF");
  assert.deepEqual(Buffer.from(packed), fs.readFileSync(path.join(root, "assets/sounds", name.toLowerCase().replaceAll(" ", "-") + ".wav")));
}
for (const shape of P.shapes) {
  const faces = Space.faces(shape); assert(faces.length >= 8);
  for (const f of faces) assert(Math.abs(Math.hypot(...f.normal) - 1) < 0.00001);
  const capture = camera => {
    const points = [], proxy = new Proxy({}, {get: (_, key) => (...args) => {
      if (key === "moveTo" || key === "lineTo") { assert(args.every(Number.isFinite)); points.push(args); }
    }});
    const scene = Object.assign(P.scene("3D Object"), {shape, azimuth: camera});
    Space.draw(proxy, scene, 0.47, 250, 250, 500);
    assert(points.length >= 6); return points;
  };
  assert.notDeepEqual(capture(-30), capture(20));
}
for (const name of Object.keys(Marks.paths)) assert(fs.existsSync(path.join(root, "assets/marks", name.toLowerCase() + ".svg")));
assert.equal(fs.readdirSync(path.join(root, "assets/overlays")).length, 2);
const adapter = require("../adapter/prepare-remotion.cjs");
const remotion = adapter.build(p);
assert.equal(remotion.timeline.frames, 408);
assert.equal(remotion.timeline.audio.length, 5);
assert.equal(remotion.timeline.notes.length, 1);
assert.equal(remotion.timeline.audio[1].from, Math.round((3.8 + 0.85) * 30));
for (const cue of remotion.timeline.audio) assert(remotion.files.has("public/" + cue.file));
const withVoice = P.demo();
withVoice.scenes[0].cues[1].clip = "data:audio/wav;base64," + Buffer.from(Audio.wav(Audio.make("Paper Tap"))).toString("base64");
const recorded = adapter.build(withVoice);
assert.equal(recorded.timeline.notes[0].recorded, true);
const voice = recorded.timeline.audio.find(cue => cue.file.startsWith("audio/voice-"));
assert(voice.file.endsWith(".wav"));
assert.equal(voice.from, 12); assert.equal(voice.gain, 1);
assert.deepEqual(recorded.files.get("public/" + voice.file), Buffer.from(Audio.wav(Audio.make("Paper Tap"))));
console.log("Passed Storyboard, Timeline, Mesh Projection, WAV, And Asset Checks.");

// ---------------------------------------------------------------- Storyboard Format Additions
const near = (a, b, e = 1e-9) => assert(Math.abs(a - b) <= e, a + " Is Not Near " + b);
assert.deepEqual(Object.keys(P.cleanProject(P.demo())), ["version", "title", "aspect", "fps", "scenes"]);
assert.deepEqual(P.size({aspect: "Custom", size: [1080, 1350]}), [1080, 1350]);
assert.throws(() => P.cleanProject({version: 1, aspect: "Custom", size: [1081, 1350], scenes: [{}]}));
assert.throws(() => P.cleanProject({version: 1, modules: ["../outside.js"], scenes: [{}]}));
assert.throws(() => P.cleanProject({version: 1, modules: ["scenes/a.txt"], scenes: [{}]}));
assert.throws(() => P.cleanProject({version: 1, scenes: [{start: {phrase: ""}}]}));
assert.throws(() => P.cleanProject({version: 1, safe: "Nowhere", scenes: [{}]}));
assert.throws(() => P.cleanProject({version: 1, captions: {lines: [{text: "A", at: 2, end: 1}]}, scenes: [{}]}));
const safe = P.safe({aspect: "Portrait", safe: "Vertical Feed"});
near(safe.top, 0.13 * 1920); near(safe.bottom, 1920 - 0.24 * 1920); near(safe.w, 1080 * 0.8);
near(P.safe({aspect: "Landscape"}).left, 96);
const shorthand = P.cleanProject({version: 1, scenes: [{mode: "Code Scene", draw: "X", start: "hello there", beats: {a: 1.5, b: "now"}, cues: [{type: "Sound", anchor: "now", pan: 2}]}]}).scenes[0];
assert.deepEqual(shorthand.start, {phrase: "hello there"}); assert.deepEqual(shorthand.beats, {a: {at: 1.5}, b: {phrase: "now"}});
assert.equal(shorthand.cues[0].pan, 1); assert(Object.isFrozen(shorthand.params));

// ---------------------------------------------------------------- Kit Maths
const K = require("../studio/kit.js");
for (const [name, curve] of Object.entries(K.ease)) { near(curve(0), 0, 1e-9); near(curve(1), 1, 1e-9); assert(Number.isFinite(curve(0.37)), name); }
for (const name of ["linear", "outQuad", "inOutCubic", "outExpo", "inOutSine", "outCirc"]) for (let i = 0; i < 50; i++) assert(K.ease[name]((i + 1) / 50) >= K.ease[name](i / 50) - 1e-12);
assert(K.ease.outBack(0.6) > 1); assert.throws(() => K.easing("nope"));
const css = K.bezier(0.25, 0.1, 0.25, 1); near(css(0), 0); near(css(1), 1); assert(css(0.5) > 0.75 && css(0.5) < 0.85);
near(K.bezier(0, 0, 1, 1)(0.3), 0.3, 1e-4);
assert.equal(K.clamp(5, 0, 1), 1); assert.equal(K.lerp(2, 4, 0.5), 3); assert.equal(K.remap(5, 0, 10, 100, 200), 150); assert.equal(K.remap(50, 0, 10, 0, 1), 1);
assert.equal(K.between(1, 2, 4), 0); assert.equal(K.between(3, 2, 4), 0.5); assert.equal(K.wrap(370, 0, 360), 10); assert.equal(K.wrap(-10, 0, 360), 350);
assert.equal(K.spring(0), 0); near(K.spring(6), 1, 1e-6); near(K.spring(8, {from: 5, to: -2, stiffness: 90, damping: 30, mass: 2}), -2, 1e-4);
assert(Math.max(...Array.from({length: 60}, (_, i) => K.spring(i / 30, "bouncy"))) > 1.05);
assert(Math.max(...Array.from({length: 90}, (_, i) => K.spring(i / 30, {stiffness: 100, damping: 40}))) <= 1 + 1e-9);
assert.equal(K.stagger(0.1, 3, {each: 0.1, duration: 0.5}), 0); assert.equal(K.stagger(2, 3, {each: 0.1, duration: 0.5}), 1);
assert.equal(K.tween(0.5, 0, 1, 10, 20), 15);
assert.equal(K.stepTime(0.999, 24, 2), 22 / 24); assert.equal(K.boilStep(1.01, 8), 8);
const a = K.rng(7), b = K.rng(7), other = K.rng(8), draws = Array.from({length: 2000}, () => a());
assert.deepEqual(draws.slice(0, 50), Array.from({length: 50}, () => b())); assert.notEqual(draws[0], other());
assert(draws.every(v => v >= 0 && v < 1)); near(draws.reduce((s, v) => s + v, 0) / draws.length, 0.5, 0.03);
assert.equal(K.rand("x", 3), K.rand("x", 3)); assert.notEqual(K.rand("x", 3), K.rand("x", 4));
assert.deepEqual(K.rng(1).shuffle([1, 2, 3, 4, 5]).sort(), [1, 2, 3, 4, 5]);
for (let i = 0; i < 200; i++) { const v = K.noise2(i * 0.37, i * 0.11, 5); assert(v >= -1 && v <= 1); assert(Math.abs(K.noise(i * 0.1 + 0.001, 2) - K.noise(i * 0.1, 2)) < 0.02); }
assert.equal(K.noise(3.25, 9), K.noise(3.25, 9)); assert(Math.abs(K.fbm(1.3, 2.7, {seed: 4})) <= 1);
assert.equal(K.track([[0, 0], [1, 10], [3, 30, "hold"]], 0.5), 5); assert.equal(K.track([[0, 0], [1, 10], [3, 30, "hold"]], 2), 10); assert.equal(K.track([[0, 0], [1, 10]], 9), 10);
assert.deepEqual(K.track([[0, {x: 0, y: [0, 2]}], [2, {x: 4, y: [2, 4]}]], 1), {x: 2, y: [1, 3]});
assert.equal(K.track([[0, "#000000"], [1, "#ffffff"]], 0.5), "rgb(128,128,128)");
assert.deepEqual(K.parseColor("#0f08"), [0, 255, 0, 136 / 255]); assert.deepEqual(K.parseColor("rgba(10, 20, 30, 0.5)"), [10, 20, 30, 0.5]);
assert.deepEqual(K.parseColor("hsl(120, 100%, 50%)").map(Math.round), [0, 255, 0, 1]); assert.throws(() => K.parseColor("nonsense"));
assert.equal(K.rgba("#336699", 0.5), "rgba(51,102,153,0.5)"); assert.equal(K.mixColor("#ff0000", "#0000ff", 0.5), "rgb(128,0,128)");
assert.equal(K.readable("#101010"), "#ffffff"); assert.equal(K.readable("#fafafa"), "#111111"); near(K.contrast("#000000", "#ffffff"), 21, 1e-6);
near(K.toHsl(K.hsl(210, 0.5, 0.4))[0], 210, 1.5); assert.equal(K.ramp(["#000000", "#ffffff"], 1), "rgb(255,255,255)");
const square = [[0, 0], [10, 0], [10, 10], [0, 10]];
assert.equal(K.pathLength(square), 30); assert.deepEqual(K.pointAt(square, 0.5), {x: 10, y: 5, angle: Math.PI / 2});
assert.deepEqual(K.slicePath(square, 0, 0.5), [[0, 0], [10, 0], [10, 5]]); near(K.pathLength(K.circlePoints(0, 0, 10, 360)), 2 * Math.PI * 10, 0.01);
near(K.pathLength(K.resample(square, 1)), 30, 0.2); assert.equal(K.boilPath(square, {seed: 1, step: 2})[2][0], K.boilPath(square, {seed: 1, step: 2})[2][0]);
assert.notEqual(K.boilPath(square, {seed: 1, step: 2})[2][0], K.boilPath(square, {seed: 1, step: 3})[2][0]);
const spline = K.splinePoints([[0, 0], [5, 5], [10, 0]]); assert.deepEqual(spline[0], [0, 0]); assert.deepEqual(spline[spline.length - 1], [10, 0]);
const knee = K.joint(0, 0, 0, 1.6, 1, 1); near(Math.hypot(knee.x, knee.y), 1, 1e-9); near(Math.hypot(knee.x - knee.endX, knee.y - knee.endY), 1, 1e-9);
const far = K.joint(0, 0, 0, 5, 1, 1); near(far.endY, 2, 1e-4);
assert.equal(K.formatNumber(1234567.891, {decimals: 1}), "1,234,567.9"); assert.equal(K.formatNumber(-0.004, {decimals: 2}), "0.00"); assert.equal(K.formatNumber(7, {pad: 3, prefix: "$", suffix: "K"}), "$007K");
assert.equal(K.count(0, 100, 1), 100); assert.equal(K.typeOn("Hello", 0.4), "He");
const Film = require("./lib/film.cjs");
const measure = Film.recorder(100, 100).context;
measure.font = K.font(40, 700);
const wrapped = K.wrapText(measure, "One Two Three Four Five Six", 260); assert(wrapped.length > 1 && wrapped.join(" ") === "One Two Three Four Five Six");
for (const line of wrapped) assert(measure.measureText(line).width <= 260);
assert.deepEqual(K.wrapText(measure, "A\nB", 999), ["A", "B"]);
const fitted = K.fitText(measure, "A Longer Headline That Must Shrink To Fit", {width: 300, height: 120, size: 90}); assert(fitted.size < 90 && fitted.height <= 120.01 && fitted.width <= 300.01);
assert.equal(K.fitText(measure, "Hi", {width: 300, height: 120, size: 60}).size, 60);
const placed = K.layoutWords(measure, "Each Word Gets A Place", {width: 220, size: 40}); assert.equal(placed.words.length, 5); assert(placed.words.every(w => w.x + w.width <= 220.01));
const cam = K.camera({width: 1000, height: 600}, {x: 300, y: 200, zoom: 2, rotate: 20});
const there = cam.toScreen(300, 200); near(there.x, 500); near(there.y, 300);
const back = cam.toWorld(cam.toScreen(123, 456).x, cam.toScreen(123, 456).y); near(back.x, 123, 1e-9); near(back.y, 456, 1e-9);
const pinned = cam.toScreen(77, 88, 0); near(pinned.x, 77); near(pinned.y, 88);
assert(Math.abs(cam.toScreen(400, 200, 0.5).x - cam.toScreen(300, 200, 0.5).x) < Math.abs(cam.toScreen(400, 200, 1).x - cam.toScreen(300, 200, 1).x));
assert.deepEqual(K.shake(5, {at: 1, duration: 0.5}), {x: 0, y: 0, rotate: 0, zoom: 0}); assert(Math.abs(K.shake(1.1, {at: 1, amount: 10}).x) <= 10); assert(Math.abs(K.drift(3.3, {amount: 8}).x) <= 8);
// 3D Additions.
const lens = Space.view({cx: 100, cy: 80, size: 500, yaw: 30, pitch: 20, distance: 6});
const centre = lens.project([0, 0, 0]); near(centre[0], 100, 1e-9); near(centre[1], 80, 1e-9); near(centre[2], 6, 1e-9);
assert(lens.project([0, 1, 0])[1] < 80); assert(lens.scaleAt([0, 0, 0]) > Space.view({distance: 12, size: 500}).scaleAt([0, 0, 0]));
for (const mesh of [Space.box(1, 2, 3), Space.sphere(1, 12, 8), Space.cylinder(1, 2, 12), Space.cylinder(1, 2, 12, 0), Space.torus(), Space.plane(2, 2), Space.extrude([[0, 0], [2, 0], [2, 1], [1, 1], [1, 2], [0, 2]], 0.5)])
  for (const face of mesh) { assert(face.points.length >= 3); near(Math.hypot(...face.normal), 1, 1e-6); }
assert.equal(Space.box().length, 6); assert.equal(Space.extrude([[0, 0], [1, 0], [1, 1], [0, 1]], 1).length, 6);
const moved = Space.place({position: [1, 2, 3], rotate: [0, 90, 0], scale: 2}); const q = moved.point([1, 0, 0]); near(q[0], 1, 1e-9); near(q[1], 2, 1e-9); near(q[2], 1, 1e-9);
const solid = Film.recorder(400, 400); assert.equal(Space.render(solid.context, lens, [{mesh: Space.box(), color: "#8090a0"}, {mesh: Space.sphere(0.5, 8, 6), color: "rgb(200,100,50)", place: {position: [2, 0, 0]}}]) > 3, true);
assert.equal(solid.bad.length, 0);

// ---------------------------------------------------------------- Voice Timing
const T = require("../studio/timing.js");
assert.deepEqual(T.tokens("Don’t Stop, it's R&D—twenty-one!"), ["dont", "stop", "its", "r", "and", "d", "twenty", "one"]);
const said = "Start small then grow. Then grow again, and then stop.".split(" ").map((text, i) => ({start: 1 + i * 0.5, end: 1.4 + i * 0.5, text}));
const index = T.makeIndex(said, 0);
assert.equal(T.find(index, "then grow").length, 2); assert.equal(T.resolve(index, {phrase: "Start small"}).time, 1);
assert.equal(T.resolve(index, {phrase: "then grow", occurrence: 2}).time, 3); near(T.resolve(index, {phrase: "then grow", occurrence: 2, edge: "end", offset: 0.25}).time, 4.15);
assert.equal(T.resolve(T.makeIndex(said, 2), {phrase: "small"}).time, 3.5);
const code = (action) => { try { action(); } catch (error) { assert(error.timing, error.message); return error; } assert.fail("Expected A Timing Problem"); };
const unknown = code(() => T.resolve(index, {phrase: "start tall"}, {label: "Scene 2 Start"}));
assert.equal(unknown.code, "unknown"); assert(unknown.message.includes("start tall") && unknown.message.includes("Scene 2 Start") && unknown.message.includes("start small"));
const twice = code(() => T.resolve(index, {phrase: "then"}));
assert.equal(twice.code, "ambiguous"); assert(twice.message.includes("3 Times") && twice.message.includes("then"));
assert.equal(code(() => T.resolve(index, {phrase: "then grow", occurrence: 3})).code, "range");
assert.equal(T.resolve(index, {phrase: "then"}, {span: [4.4, 9]}).time, 5);
assert.equal(code(() => T.resolve(index, {phrase: "then"}, {span: [0, 3.2]})).code, "ambiguous");
assert.equal(T.resolve(index, {phrase: "then"}, {fromToken: 3}).time, 3); assert.equal(code(() => T.resolve(index, {phrase: "start"}, {fromToken: 2})).code, "order");
// Word Timing Shapes: The Speech Tool's Output, A Plain List, Recognizer Segments, And Subtitles.
assert.deepEqual(T.readWords({words: [{start: 0.5, end: 0.9, text: "Hi"}]}).words, [{start: 0.5, end: 0.9, text: "Hi"}]);
assert.deepEqual(T.readWords([{word: " There", start: 1, end: 1.2}]).words, [{start: 1, end: 1.2, text: "There"}]);
assert.equal(T.readWords({segments: [{words: [{word: "A", start: 0, end: 0.2}, {word: "B", start: 0.3, end: 0.5}]}]}).words.length, 2);
const subtitles = T.readWords("1\n00:00:01,000 --> 00:00:03,000\nHello there friend\n\n2\n00:00:03,500 --> 00:00:04,000\nBye\n");
assert.equal(subtitles.words.length, 4); assert.equal(subtitles.approximate, true); assert.equal(subtitles.words[0].start, 1); assert.equal(subtitles.words[3].text, "Bye");
assert.equal(T.readWords({standIn: true, words: [{start: 0, end: 1, text: "X"}]}).standIn, true);
assert.throws(() => T.readWords({words: [{start: 2, end: 1, text: "X"}]})); assert.throws(() => T.readWords({nothing: 1})); assert.throws(() => T.readWords([]));
const stand = T.standIn("# Note\nOne two three. [Pause] Four five,\nsix seven eight nine ten.\n\nEleven twelve.", {wpm: 120, start: 0.5});
assert.equal(stand.length, 12); assert.equal(stand[0].start, 0.5); assert(stand.every((w, i) => w.end > w.start && (!i || w.start >= stand[i - 1].end)));
assert(stand[3].start - stand[2].end > stand[1].start - stand[0].end); near(stand[11].end - 0.5, 12 / 120 * 60, 0.2);
assert.throws(() => T.standIn("# Only A Note")); assert.throws(() => T.standIn("Words", {wpm: 5}));
const levels = T.levelsFromWords(stand, 30); assert(levels.every(v => v >= 0 && v <= 1) && Math.max(...levels) > 0.5 && levels[0] === 0);
const tone = new Float32Array(48000).map((_, i) => i > 24000 ? Math.sin(i * 0.2) * 0.5 : 0), measured = T.levelsFromSamples(tone, 48000, 30);
assert.equal(measured.length, 30); assert(measured[5] < 0.05 && measured[25] > 0.9);
near(T.levelAt({offset: 1, levels: {rate: 10, values: [0, 1, 0]}}, 1.05), 0.5, 1e-9); assert.equal(T.levelAt(null, 1), 0);
// Retiming A Storyboard.
const board = P.cleanProject({version: 1, title: "Timed", scenes: [
  {mode: "Code Scene", draw: "A", duration: 2, beats: {grow: {phrase: "grow", occurrence: 1}, fixed: 0.5}, cues: [{type: "Sound", sound: "Paper Tap", anchor: "start"}, {type: "Sound", at: 1.9}]},
  {mode: "Code Scene", draw: "B", duration: 1}, {mode: "Code Scene", draw: "C", duration: 3},
  {mode: "Code Scene", draw: "D", duration: 2, start: {phrase: "then grow", occurrence: 2}, end: {phrase: "stop", offset: 0.5}, beats: {again: "again"}}],
  captions: {lines: ["Start Small Then Grow.", {text: "Then Grow Again,", phrase: "then grow"}, {text: "And Then Halt.", phrase: "and then", until: "stop"}, {text: "A Sign", at: 0.1, end: 0.6}]}});
const result = T.retime(board, {words: said, standIn: true}, {});
assert.deepEqual(result.problems, []);
assert.deepEqual(result.project.scenes.map(s => s.duration), [1, 0.5, 1.5, 3.4]);
assert.equal(result.project.scenes[0].beats.grow.at, 2.5); assert.equal(result.project.scenes[0].beats.fixed.at, 0.5); assert.equal(result.project.scenes[3].beats.again.at, 1);
assert.equal(result.project.scenes[0].cues[0].at, 0.99); assert.equal(result.project.scenes[0].cues[1].at, 0.99);
const timedLines = result.project.captions.lines;
assert.equal(timedLines[0].at, 1); assert.equal(timedLines[0].end, 3); assert.deepEqual(timedLines[0].words, [1, 1.5, 2, 2.5]); assert.equal(timedLines[0].phrase, "Start Small Then Grow.");
assert.equal(timedLines[1].at, 3); assert.deepEqual(timedLines[1].words, [3, 3.5, 4]); assert.equal(timedLines[2].at, 4.5); assert.equal(timedLines[2].words, undefined);
assert.deepEqual(timedLines[3], {text: "A Sign", at: 0.1, end: 0.6});
assert.equal(result.report.mismatches.length, 1); assert.equal(result.report.mismatches[0].line, 3); assert.equal(result.report.mismatches[0].spoken, "and then stop");
assert.equal(result.report.manualCaptions, 1); assert.equal(result.report.uncaptioned.length, 0);
assert.equal(result.project.voice.standIn, true); assert.equal(result.project.voice.words.length, 10); assert.equal(result.project.voice.levels.estimated, true);
assert.deepEqual(P.cleanProject(result.project), P.cleanProject(JSON.parse(JSON.stringify(P.cleanProject(result.project)))));
// Retiming Again With A Slower Recording Moves Everything.
const slower = T.retime(P.cleanProject(result.project), {words: said.map(w => ({start: w.start * 2, end: w.end * 2, text: w.text}))}, {});
assert.deepEqual(slower.problems, []); assert.deepEqual(slower.project.scenes.map(s => s.duration), [2, 1, 3, 6.3]); assert.equal(slower.project.captions.lines[1].at, 6); assert.equal(slower.project.voice.standIn, undefined);
assert.equal(T.retime(board, {words: said}, {lead: 0.2}).project.voice.offset, -0.8);
// Problems Stop The Run And Name The Phrase.
const broken = JSON.parse(JSON.stringify(board));
broken.scenes[1].start = {phrase: "then"}; broken.scenes[2].beats = {gone: {phrase: "never said"}}; broken.captions.lines[0].text = "Begin Small";
const failed = T.retime(P.cleanProject(broken), {words: said}, {});
assert(failed.problems.some(m => m.includes("Scene 2 Start") && m.includes("“then”") && m.includes("3 Times")));
assert(failed.problems.some(m => m.includes("Scene 3 Beat gone") && m.includes("never said")));
assert(failed.problems.some(m => m.includes("Caption Line 1") && m.includes("Begin Small")));
const firstAnchored = JSON.parse(JSON.stringify(board)); firstAnchored.scenes[0].start = {phrase: "start"};
assert(T.retime(P.cleanProject(firstAnchored), {words: said}, {}).problems.some(m => m.includes("Scene 1")));
const backwards = JSON.parse(JSON.stringify(board)); backwards.scenes[2].start = {phrase: "stop"};
assert(T.retime(P.cleanProject(backwards), {words: said}, {}).problems.some(m => m.includes("Would")));
const outside = JSON.parse(JSON.stringify(board)); outside.scenes[0].cues[0].anchor = {phrase: "stop"};
assert(T.retime(P.cleanProject(outside), {words: said}, {}).problems.some(m => m.includes("Scene 1 Cue 1") && m.includes("Outside")));
const gap = T.retime(P.cleanProject({version: 1, scenes: [{duration: 3}], captions: {lines: ["Start Small"]}}), {words: said}, {});
assert.equal(gap.report.uncaptioned.length, 1); assert(gap.report.uncaptioned[0].text.startsWith("then grow")); assert(gap.notes.some(n => n.includes("The Voice Runs To")));

// ---------------------------------------------------------------- Code Scenes In Node
const scope = Film.createScope();
assert.deepEqual(scope.MotionScenes.names().sort(), ["Chart", "Doodle Character", "Globe", "Phone"]);
for (const part of Film.partSources()) assert.deepEqual(Film.impureMentions(part.source), [], part.name);
// The Registry And The State.
Film.loadModules(scope, [{name: "probe.js", source: `
  MotionScenes.register("Probe", function (c, s) {
    c.fillRect(s.safe.left, s.safe.top, s.safe.w * s.progress, s.params.size + s.random() + s.rng("k")());
    c.fillText(s.words.map(w => w.text).join(" ") + "|" + s.beat("hit") + "|" + s.since("hit") + "|" + s.when("hit") + "|" + s.when(2) + "|" + s.voice + "|" + s.phrase("grow again") + "|" + s.frame + "|" + s.fps + "|" + s.globalTime, 0, 0);
    s.use(c, "Inner", { label: "x" }, { x: 100, y: 200, w: 300, h: 400, start: 0.25 });
  }, { defaults: { size: 40, extra: [1, 2] }, events: s => [{ id: "hit", at: s.beat("hit"), what: "It Lands", pan: 0.5, sound: "Paper Tap" }].concat(s.events("Inner", {}, { x: 540, y: 0, w: 540, h: 400, start: 0.25, key: "in" })) });
  MotionScenes.register("Inner", (c, s) => { c.fillText(s.params.label + "|" + s.time + "|" + s.width + "|" + s.beat("hit") + "|" + s.safe.left, 0, 0); }, { events: s => [{ id: "pop", at: 0.5, what: "Inner Pop", pan: 0 }] });
  MotionScenes.register("Thrower", (c, s) => { c.save(); c.save(); throw new Error("Deliberate Failure"); });
  MotionScenes.register("Gambler", (c, s) => { c.fillRect(0, 0, Math.random(), 1); });
  MotionScenes.register("Clock", (c, s) => { c.fillRect(0, 0, Date.now(), 1); });
  let kept = 0;
  MotionScenes.register("Hoarder", (c, s) => { c.fillRect(0, 0, kept++, 1); });
`}]);
const probe = P.cleanProject({version: 1, fps: 30, scenes: [{duration: 1}, {mode: "Code Scene", draw: "Probe", duration: 4, beats: {hit: 1.5}, params: {size: 50}}],
  voice: {offset: 0, words: said.map(w => [w.start, w.end, w.text]), levels: {rate: 30, values: T.levelsFromWords(said, 30)}}});
const frame = Film.drawFrame(scope, probe, 2);
assert.deepEqual(frame.problems, []);
const text = frame.calls.filter(call => call[0] === "fillText").map(call => call[1]);
assert.equal(text[0], "Start small then grow. Then grow again, and|1.5|-0.5|1.5|2|" + T.levelAt(probe.voice, 2) + "|2.5|60|30|2");
assert.equal(text[1], "x|0.75|300|1.25|0");
const rect = frame.calls.find(call => call[0] === "fillRect" && call[1] === 54); assert.equal(rect[3], 972 * 0.25); assert(rect[4] > 50 && rect[4] < 52);
assert.deepEqual(frame.calls.filter(call => call[0] === "translate")[0], ["translate", 100, 200]);
assert.deepEqual(scope.MotionScenes.events(probe), [
  {scene: 2, id: "in.pop", at: 0.75, time: 1.75, what: "Inner Pop", pan: 0.5},
  {scene: 2, id: "hit", at: 1.5, time: 2.5, what: "It Lands", pan: 0.5, sound: "Paper Tap", gain: 0.6}]);
assert.deepEqual(Film.determinism(scope, probe), []);
// A Scene That Fails Shows A Card, Reports The Problem, And Leaves The Context Balanced. Captions Still Draw.
const failing = P.cleanProject({version: 1, scenes: [{mode: "Code Scene", draw: "Thrower", duration: 2}, {mode: "Code Scene", draw: "Absent", duration: 2}], captions: {lines: [{text: "Still Here", at: 0, end: 4}]}});
const thrown = Film.drawFrame(scope, failing, 1);
assert.equal(thrown.problems[0].message, "Deliberate Failure"); assert.equal(thrown.problems[0].scene, 1);
assert.equal(thrown.calls.filter(call => call[0] === "save").length, thrown.calls.filter(call => call[0] === "restore").length);
assert(thrown.calls.some(call => call[0] === "fillText" && call[1] === "Still")); assert.throws(() => Film.drawFrame(scope, failing, 1, {strict: true}), /Deliberate/);
assert.equal(Film.drawFrame(scope, failing, 3).problems[0].kind, "missing");
// Randomness, The Clock, And Kept State Are Caught.
const impure = name => Film.determinism(scope, P.cleanProject({version: 1, scenes: [{mode: "Code Scene", draw: name, duration: 2}]}));
assert(impure("Gambler").some(m => m.includes("Math.random"))); assert(impure("Clock").some(m => m.includes("Date.now"))); assert(impure("Hoarder").some(m => m.includes("Keeping State")));
assert.deepEqual(Film.impureMentions("// Math.random Is Banned\nconst a = \"Date.now\"; draw();"), []); assert.deepEqual(Film.impureMentions("x = Math.random() + performance.now();"), ["Math.random", "performance.now"]);
// Captions Draw Over Every Scene Kind And Can Be Hidden.
const kinds = P.cleanProject({version: 1, scenes: [{mode: "Kinetic Type", duration: 1}, {mode: "Process Diagram", duration: 1}, {mode: "3D Object", duration: 1}, {mode: "Code Scene", draw: "Inner", duration: 1, beats: {hit: 0}, params: {label: "z"}}],
  captions: {style: {mode: "Word Build", case: "Upper", plate: "#000000"}, lines: [{text: "One Line For All", at: 0, end: 4, words: [0, 1, 2, 3]}]}});
for (let i = 0; i < 4; i++) {
  const shown = Film.drawFrame(scope, kinds, i + 0.5).calls.filter(call => call[0] === "fillText").map(call => call[1]);
  assert.deepEqual(shown.slice(-(i + 1)), ["ONE", "LINE", "FOR", "ALL"].slice(0, i + 1), "Scene Kind " + (i + 1));
  assert(!Film.drawFrame(scope, kinds, i + 0.5, {captions: false}).calls.some(call => call[1] === "ONE"));
}
kinds.captions.show = false; assert(!Film.drawFrame(scope, kinds, 0.5).calls.some(call => call[1] === "ONE"));
const style = scope.MotionCaptions.styleFor(P.cleanProject({version: 1, aspect: "Landscape", scenes: [{}], captions: {lines: []}})); assert.equal(style.size, Math.round(1080 * 0.052)); assert.equal(style.position, "Bottom");

// ---------------------------------------------------------------- Every Example Code Scene And Part Draws The Same Frame The Same Way
const Events = require("./events.cjs");
let codeScenes = 0, eventCount = 0;
for (const file of exampleFiles) {
  const film = Film.loadFilm(file);
  if (!film.project.scenes.some(scene => scene.mode === "Code Scene")) continue;
  for (const module of film.modules) assert.deepEqual(Film.impureMentions(module.source), [], module.name);
  Film.loadModules(scope, film.modules);
  const untimed = film.project.scenes.some(scene => Object.values(scene.beats || {}).some(beat => beat.at === undefined));
  for (const scene of film.project.scenes) if (scene.mode === "Code Scene") { assert(scope.MotionScenes.has(scene.draw), scene.draw); codeScenes++; }
  if (untimed) continue;
  assert.deepEqual(Film.determinism(scope, film.project), [], path.relative(root, file));
  const gathered = Events.gather(scope, film.project);
  for (const event of gathered.events) { assert(event.time >= 0 && event.time <= P.duration(film.project)); assert(event.what && event.id); assert(!event.sound || P.sounds.includes(event.sound)); }
  assert.deepEqual(Events.gather(scope, film.project), gathered);
  eventCount += gathered.events.length;
  const withSounds = Events.place(film.project, gathered.events), again = Events.place(withSounds.project, Events.gather(scope, withSounds.project).events);
  assert.deepEqual(again.project, withSounds.project); assert.equal(withSounds.placed, gathered.events.filter(event => event.sound).length);
}
assert(codeScenes >= 14 && eventCount >= 30);
// The Voiced Example: Its Timed Storyboard Is Exactly What The Timing Tool Makes From Its Authored Storyboard And Stand-In Words.
const travels = path.join(root, "examples/an-idea-travels"), { readWordsFile } = require("./retime.cjs");
const made = T.retime(Film.loadFilm(path.join(travels, "storyboard.json")).project, readWordsFile(path.join(travels, "words.json")), {});
assert.deepEqual(made.problems, []); assert.equal(made.report.mismatches.length, 0); assert.equal(made.report.captions, 6); assert.equal(made.report.beats, 5);
assert.deepEqual(P.cleanProject(made.project), JSON.parse(fs.readFileSync(path.join(travels, "storyboard.timed.json"))));
// Moving A Beat Moves Its Event And Its Placed Sound.
const moving = Film.openFilm(path.join(travels, "storyboard.timed.json")), shifted = JSON.parse(JSON.stringify(moving.project));
shifted.scenes[0].beats.small.at += 0.4;
const before = Events.gather(moving.scope, moving.project).events.find(event => event.id === "idea-appears"), after = Events.gather(moving.scope, P.cleanProject(shifted)).events.find(event => event.id === "idea-appears");
near(after.time - before.time, 0.4, 1e-9);
near(Events.place(P.cleanProject(shifted), [after]).project.scenes[0].cues[0].at - Events.place(moving.project, [before]).project.scenes[0].cues[0].at, 0.4, 1e-9);
assert(Events.gather(moving.scope, moving.project).events.find(event => event.id === "count.count-start").sound === undefined);
// The Stills Tool Chooses Real Frames.
const Stills = require("./stills.cjs");
assert.deepEqual(Stills.chooseTimes(p, {times: "0,1.01,13.6"}).map(pick => pick.frame), [0, 30, 407]); assert.equal(Stills.chooseTimes(p, {}).length, 3);
assert.deepEqual(Stills.chooseTimes(p, {strip: "5", "strip-frames": "5"}).map(pick => pick.frame), [148, 149, 150, 151, 152]); assert.throws(() => Stills.chooseTimes(p, {times: "99"}));
assert.equal(Stills.lineAt(moving.project, 1).caption, "Every Idea Starts Small."); assert(Stills.lineAt(moving.project, 1).spoken.includes("Idea"));
// The Voice File Reader Measures Levels From Uncompressed WAV.
const { wavSamples } = require("./retime.cjs"), tap = wavSamples(Buffer.from(Audio.wav(Audio.make("Paper Tap"))));
assert.equal(tap.rate, 48000); assert.equal(tap.samples.length, Math.round(0.19 * 48000)); assert.equal(wavSamples(Buffer.from("not audio at all, just some text bytes here")), null);

// ---------------------------------------------------------------- The Adapter Carries Code Scenes, Parts, Captions, And The Film Voice
const carried = adapter.build(JSON.parse(fs.readFileSync(path.join(travels, "storyboard.timed.json"))), {base: travels});
assert(carried.files.has("scenes/idea.js")); assert.equal(carried.timeline.frames, Math.ceil(P.duration(moving.project) * 30 - 1e-7));
assert.throws(() => adapter.build(JSON.parse(fs.readFileSync(path.join(travels, "storyboard.timed.json")))), /Beside/);
const painter = carried.files.get("src/painter.mjs"); assert(painter.includes("Idea Spread") && painter.includes("Doodle Character") && painter.includes("MotionScenes.seal()"));
assert(!/\brequire\s*\(/.test(painter));
const visuals = JSON.parse(carried.files.get("src/frame-project.json")); assert.equal(visuals.captions.lines.length, 6); assert.equal(visuals.voice.words.length, 26);
// Run The Generated Painter Module Itself And Compare A Frame With The Studio Painter.
const generated = {}; new Function("sceneScope", "Path2D", painter.replace("const sceneScope = {};", "").replace(/export const MotionFrame = .*/, ""))(generated, Film.StubPath);
for (const time of [1.2, 6.5, 10.4]) {
  const mine = Film.drawFrame(moving.scope, moving.project, time), theirs = Film.recorder(1080, 1920);
  generated.MotionFrame.draw(theirs.canvas, visuals, time);
  assert.deepEqual(theirs.calls, mine.calls); assert.deepEqual(generated.MotionScenes.problems(), []);
}
const placedFilm = Events.place(moving.project, Events.gather(moving.scope, moving.project).events).project;
const sounded = adapter.build(placedFilm, {base: travels});
assert(sounded.timeline.audio.some(cue => /-pan-(left|right)-\d+\.wav$/.test(cue.file))); assert.equal(sounded.timeline.audio.length, 17);
const panned = adapter.pannedWav("Paper Tap", -1); assert.equal(panned.readUInt16LE(22), 2); assert.equal(panned.readInt16LE(44 + 4 * 500 + 2), 0); assert.notEqual(panned.readInt16LE(44 + 4 * 500), 0);
const spoken = JSON.parse(JSON.stringify(moving.project)); spoken.voice.clip = "data:audio/wav;base64," + Buffer.from(Audio.wav(Audio.make("Room Air"))).toString("base64"); spoken.voice.offset = -0.5;
const voiced = adapter.build(spoken, {base: travels}), track = voiced.timeline.audio.find(cue => cue.id === "film-voice");
assert.equal(track.from, 0); assert.equal(track.trimBefore, 15); assert.equal(track.frames, voiced.timeline.frames); assert(voiced.files.has("public/" + track.file));
assert.equal(JSON.parse(voiced.files.get("src/frame-project.json")).voice.clip, undefined);
// The Export Paths Stay Behind Owner Approval.
const renderer = fs.readFileSync(path.join(root, "adapter/render-reviewed.cjs"), "utf8"), editor = fs.readFileSync(path.join(root, "studio/editor.js"), "utf8");
assert(renderer.includes("APPROVE") && renderer.includes("isTTY")); assert(editor.includes("if (kind === \"export\" && (!reviewed || !$(\"approve\").checked || !canRecord())) return;"));
for (const name of fs.readdirSync(__dirname).filter(name => name.endsWith(".cjs") && name !== "check.cjs").concat(fs.readdirSync(path.join(__dirname, "lib")).map(name => "lib/" + name)))
  assert(!/MediaRecorder|captureStream|startScreencast|\bffmpeg\b|\.webm"|\.mp4"/i.test(fs.readFileSync(path.join(__dirname, name), "utf8").replace(/assert\(!\/.*$/m, "")), name + " Must Not Write Video");

// ---------------------------------------------------------------- Scenarios
const scenarioFile = path.join(root, "scenarios/scenarios.json");
let scenarioCount = 0;
if (fs.existsSync(scenarioFile)) {
  const listed = JSON.parse(fs.readFileSync(scenarioFile, "utf8"));
  assert(listed && !Array.isArray(listed) && Array.isArray(listed.scenarios) && listed.scenarios.length, "scenarios.json Needs A scenarios List");
  const ids = new Set();
  for (const item of listed.scenarios) {
    for (const key of ["id", "name", "request", "session", "feedback"]) assert(item[key] !== undefined && item[key] !== null && String(item[key]).trim(), "A Scenario Is Missing " + key);
    assert(Array.isArray(item.checks) && item.checks.length && item.checks.every(check => typeof check === "string" && check.trim()), "Scenario " + item.id + " Needs A Non-Empty checks List");
    assert(!ids.has(item.id), "Scenario id " + item.id + " Repeats"); ids.add(item.id);
  }
  scenarioCount = listed.scenarios.length;
}
console.log("Passed Kit Maths, Phrase Resolution, Caption, Event, Adapter, And Determinism Checks For " + codeScenes + " Example Code Scenes" + (scenarioCount ? " And " + scenarioCount + " Scenarios." : "."));
