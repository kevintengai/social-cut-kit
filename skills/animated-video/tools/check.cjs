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
const Retime = require("./retime.cjs"), timedExample = JSON.parse(fs.readFileSync(path.join(travels, "storyboard.timed.json")));
assert.deepEqual(Retime.placeEventSounds(P.cleanProject(made.project), travels).project, timedExample);
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
assert.deepEqual(placedFilm, moving.project);
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
// The Sound Tools May Name FFmpeg, And Reach It Only Through The One Module Whose Every Run Measures Into The Null Sink Or Decodes Sound Into Memory.
const soundTools = ["audio.cjs", "export-check.cjs", "lib/ffmpeg.cjs"];
for (const name of fs.readdirSync(__dirname).filter(name => name.endsWith(".cjs") && name !== "check.cjs").concat(fs.readdirSync(path.join(__dirname, "lib")).map(name => "lib/" + name))) {
  const source = fs.readFileSync(path.join(__dirname, name), "utf8").replace(/assert\(!\/.*$/m, "");
  assert(!(soundTools.includes(name) ? /MediaRecorder|captureStream|startScreencast|\.webm"|\.mp4"|libx264|libvpx|\bmuxer\b/i : /MediaRecorder|captureStream|startScreencast|\bffmpeg\b|\.webm"|\.mp4"/i).test(source), name + " Must Not Write Video");
  if (!["lib/ffmpeg.cjs", "lib/browser.cjs", "check-browser.cjs"].includes(name)) assert(!/child_process/.test(source), name + " Must Not Start Another Program Itself");
}

// ---------------------------------------------------------------- One Storyboard, The Export Gate, Films Without Narration, The Film Folder, And Sound Measurement
const os = require("node:os"), { spawnSync } = require("node:child_process");
const Meter = require("./lib/ffmpeg.cjs"), Mix = require("./audio.cjs"), ExportCheck = require("./export-check.cjs"), Reviewed = require("../adapter/render-reviewed.cjs");
const eventCues = board => board.scenes.flatMap(scene => scene.cues.filter(cue => cue.event));
let ffmpegFound = true;
try { Meter.locate("ffmpeg"); } catch (error) { assert.equal(error.missingTool, "ffmpeg"); ffmpegFound = false; }
// The Timed Example Is The One File: It Carries Its Event Sounds, And A Remotion Project Prepared From It Plays Them.
assert.equal(eventCues(timedExample).length, 17);
const exampleStatus = Events.status(moving.scope, moving.project);
assert.deepEqual([exampleStatus.state, exampleStatus.placed, exampleStatus.expected], ["current", 17, 17]);
assert(!eventCues(timedExample).some(cue => cue.event === "count.count-start"), "A sounds Entry Of None Must Stay Silent");
assert(eventCues(timedExample).filter(cue => cue.sound === "Paper Tap" && cue.gain === 0.25).length >= 1, "A Per-Scene Sound Override Must Survive");
assert.deepEqual([carried.timeline.audio.length, carried.timeline.eventSounds.state, carried.timeline.eventSounds.placed], [17, "current", 17]);
for (const cue of carried.timeline.audio) assert(carried.files.has("public/" + cue.file));
assert.equal(carried.timeline.standIn, true); assert(carried.warnings.some(m => m.includes("Stand-In")) && !carried.warnings.some(m => m.includes("Event Sound")));
// A Storyboard Without Its Event Sounds Is Named As Such By Every Tool That Reads It.
const bare = JSON.parse(JSON.stringify(timedExample)); bare.scenes.forEach(scene => { scene.cues = scene.cues.filter(cue => !cue.event); });
assert.equal(Events.status(moving.scope, P.cleanProject(bare)).state, "missing");
const silentBuild = adapter.build(bare, {base: travels});
assert.equal(silentBuild.timeline.audio.length, 0); assert(silentBuild.warnings.some(m => m.includes("None Are Placed")));
const drifted = JSON.parse(JSON.stringify(timedExample)); eventCues(drifted)[0].at += 0.2;
assert.equal(Events.status(moving.scope, P.cleanProject(drifted)).state, "stale"); assert(adapter.build(drifted, {base: travels}).warnings.some(m => m.includes("Out Of Date")));
assert.deepEqual(Events.updateRaw(bare, timedExample), timedExample);
// Narration: A Film Declares That It Has No Spoken Voice. Stand-In Words Then Leave No Stand-In Mark. Nothing Else Changes.
assert.throws(() => P.cleanProject({version: 1, narration: "Later", scenes: [{}]}), /Narration/);
assert.equal(P.cleanProject({version: 1, narration: "Voice", scenes: [{}]}).narration, undefined); assert.equal(P.cleanProject({version: 1, narration: "None", scenes: [{}]}).narration, "None");
assert.equal(P.standIn(result.project), true); assert.equal(P.standIn(slower.project), false); assert.equal(P.standIn(p), false);
const textLed = T.retime(P.cleanProject(Object.assign(JSON.parse(JSON.stringify(board)), {narration: "None"})), {words: said, standIn: true}, {});
assert.deepEqual(textLed.problems, []); assert.equal(textLed.project.voice.standIn, undefined); assert.equal(textLed.report.standIn, false); assert.equal(textLed.project.narration, "None");
assert.deepEqual(textLed.project.scenes.map(s => s.duration), result.project.scenes.map(s => s.duration));
assert(Retime.untimed(P.cleanProject({version: 1, scenes: [{duration: 2}]})).problems.some(m => m.includes("narration")));
const anchoredNoWords = Retime.untimed(P.cleanProject({version: 1, narration: "None", scenes: [{duration: 2, end: "stop", beats: {a: "grow", b: 1}, cues: [{type: "Sound", anchor: "start"}]}], captions: {lines: ["Start Small", {text: "Held", at: 0, end: 1}]}}));
assert.equal(anchoredNoWords.problems.length, 4);
assert.deepEqual(Retime.untimed(P.cleanProject({version: 1, narration: "None", scenes: [{duration: 2, beats: {b: 1}}], captions: {lines: [{text: "Held", at: 0, end: 1}]}})).problems, []);
// The Export Gate: Both Export Paths Refuse Stand-In Timing, And The Preparation Warns.
assert(renderer.includes("standInReason(root)") && renderer.indexOf("standInReason(root)") < renderer.indexOf("isTTY"));
assert(editor.includes("if (kind === \"export\" && standIn()) {") && editor.includes("|| !canRecord() || standIn();") && editor.includes("const standIn = () => P.standIn(project);"));
// The Film Folder Lives Outside The Skill.
assert.equal(Film.insideSkill(root), true); assert.equal(Film.insideSkill(path.join(root, "examples", "new-film", "storyboard.timed.json")), true);
assert.equal(Film.insideSkill(path.dirname(root)), false); assert.equal(Film.insideSkill(path.join(os.tmpdir(), "a-film")), false); assert.equal(Film.insideSkill(root + "-copy"), false);
assert.throws(() => Film.guardOutput(path.join(root, "my-film", "board")), /Outside The Skill Folder/);
// Sound Measurement Without FFmpeg: The Plan Matches The Remotion Timeline, Levels Are Right, And Key Words Are Found.
const mixPlan = Mix.plan(moving.project), cueItems = mixPlan.items.filter(item => item.kind === "sound");
assert.equal(mixPlan.frames, carried.timeline.frames); assert.equal(cueItems.length, carried.timeline.audio.length);
assert.deepEqual(cueItems.map(item => [Math.round(item.start * 30), Math.round(item.seconds * 30), item.gain]).sort((a, b) => a[0] - b[0] || a[1] - b[1]),
  carried.timeline.audio.map(cue => [cue.from, cue.frames, cue.gain]).sort((a, b) => a[0] - b[0] || a[1] - b[1]));
const sine = new Float32Array(48000 * 2).map((_, i) => 0.5 * Math.sin(2 * Math.PI * 997 * Math.floor(i / 2) / 48000));
near(Mix.rmsDb(sine, 0, 1), 20 * Math.log10(0.5 / Math.SQRT2), 0.01); assert.equal(Mix.rmsDb(new Float32Array(9600), 0, 0.1), -Infinity);
const oneCue = { kind: "sound", name: "Glass Point", scene: 1, cue: 1, start: 0.5, seconds: 0.8, gain: 0.5, pan: 0 };
const alone = Mix.render({ seconds: 2, items: [oneCue] }, new Map());
assert.equal(alone.mix.length, 96000 * 2); assert.equal(Mix.rmsDb(alone.mix, 0, 0.5), -Infinity); assert(Mix.rmsDb(alone.mix, 0.5, 0.9) > -40);
near(Mix.rmsDb(alone.cues, 0.5, 0.9), Mix.soloDb(oneCue, 0.4), 1e-9); near(Mix.soloDb(Object.assign({}, oneCue, {gain: 1}), 0.4) - Mix.soloDb(oneCue, 0.4), 20 * Math.log10(2), 1e-6);
const hardLeft = Mix.render({ seconds: 1, items: [Object.assign({}, oneCue, {start: 0, pan: -1})] }, new Map());
assert(hardLeft.cues.some((v, i) => i % 2 === 0 && v !== 0) && hardLeft.cues.every((v, i) => i % 2 === 0 || Math.abs(v) < 1e-12));
assert.deepEqual(adapter.panSides(0).map(v => Math.round(v * 1000)), [940, 940]);
const keys = Mix.keyWords(moving.project); assert(keys.some(word => word.text === "Small.") && keys.some(word => word.text === "Friday,") && keys.length < moving.project.voice.words.length);
assert.equal(Mix.keyWords(moving.project, true).length, moving.project.voice.words.length); assert.deepEqual(Mix.keyWords(p), []);
// A Voice Under Each Cue: A Loud Voice Clears The Margin, And A Quiet One Is Listed To Check.
const spokenTrack = (amplitude) => {
  const track = new Float32Array(Math.round(mixPlan.seconds * 48000) * 2);
  for (const word of moving.project.voice.words) for (let n = Math.round(word[0] * 48000); n < Math.round(word[1] * 48000); n++) track[n * 2] = track[n * 2 + 1] = amplitude * Math.sin(2 * Math.PI * 220 * n / 48000);
  return track;
};
const voicedPlan = { seconds: mixPlan.seconds, items: mixPlan.items.concat([{ kind: "film-voice", name: "Film Voice", start: 0, seconds: mixPlan.seconds, gain: 1, pan: 0 }]), silent: [] };
const loudVoice = Mix.analyse(moving.project, voicedPlan, { voice: spokenTrack(0.8) }), quietVoice = Mix.analyse(moving.project, voicedPlan, { voice: spokenTrack(0.02) });
assert.equal(loudVoice.cues.length, 17); assert(loudVoice.overlaps.length >= 5 && loudVoice.overlaps.some(item => item.under > 6 && !item.check));
assert(quietVoice.overlaps.some(item => item.check && item.under < 6)); assert(loudVoice.overlaps.filter(item => item.check).length < quietVoice.overlaps.filter(item => item.check).length); assert(Mix.analyse(moving.project, mixPlan, { voice: spokenTrack(0) }).cues.every(cue => cue.voiceDb === null && !cue.check));
const told = Mix.describe(moving.project, voicedPlan, { integrated: -19.2, range: 4, truePeak: -0.4, silent: false }, quietVoice, { target: -14, peak: -1.5 }, exampleStatus);
assert(told.checks.some(m => m.includes("5.2 LU Under")) && told.checks.some(m => m.includes("1.1 dB Over The Ceiling")) && told.checks.some(m => m.includes("The Voice On")));
assert(told.lines.some(m => m.includes("Stand-In")) && told.lines.some(m => m.includes("Carries All 17")));
const packedMix = Mix.wavBytes(new Float32Array([0, 0, 2, -2, 0.5, -0.5])); assert.equal(packedMix.clipped, 2); assert.equal(packedMix.bytes.readUInt16LE(22), 2); assert.equal(packedMix.bytes.readInt16LE(48), 32767);
// The FFmpeg Module Reads A Loudness Summary And Refuses Any Run That Could Write A File.
const summary = "[Parsed_ebur128_0 @ 0x1] Summary:\n\n  Integrated loudness:\n    I:         -16.3 LUFS\n    Threshold: -26.6 LUFS\n\n  Loudness range:\n    LRA:         5.1 LU\n    Threshold: -36.5 LUFS\n    LRA low:   -19.9 LUFS\n    LRA high:  -14.8 LUFS\n\n  True peak:\n    Peak:        -1.2 dBFS\n";
assert.deepEqual(Meter.parseLoudness(summary), { integrated: -16.3, range: 5.1, truePeak: -1.2, silent: false });
assert.equal(Meter.parseLoudness(summary.replace("-16.3", "-70.0").replace("-1.2", "-inf")).silent, true); assert.throws(() => Meter.parseLoudness("No Summary Here"), /Loudness Summary/);
for (const args of [Meter.decodeArgs("voice.wav"), Meter.measureFileArgs("cut.bin"), Meter.measureSamplesArgs()]) assert.equal(args.filter(arg => arg === "-i").length, 1);
assert.throws(() => Meter.assertSink(["-i", "a.wav", "out.wav"])); assert.throws(() => Meter.assertSink(["-i", "a.wav", "-f", "null", "-", "out.bin"])); assert.throws(() => Meter.assertSink(["-i", "a.wav", "-i", "b.wav", "-f", "null", "-"]));
assert.throws(() => Meter.assertSink(["-i", "a.wav", "-f", "f32le", "pipe:1"])); assert.throws(() => Meter.locate("ffmpeg", path.join(os.tmpdir(), "no-such-tool-here")), /Does Not Install/);
// The Export Check Compares A File's Facts With The Storyboard.
const facts = (change = {}) => Object.assign({ bytes: 4200000, loudness: { integrated: -14.4, range: 5, truePeak: -1.9, silent: false }, probe: { format: { duration: "13.6" }, streams: [
  { codec_type: "video", width: 1080, height: 1920, avg_frame_rate: "30/1", r_frame_rate: "30/1" }, { codec_type: "audio", codec_name: "aac", channels: 2, sample_rate: "48000" }] } }, change);
const verdict = change => ExportCheck.judge(p, facts(change));
assert.deepEqual([verdict().failures, verdict().checks], [[], []]); assert.equal(ExportCheck.expectsSound(p), true); assert.equal(ExportCheck.expectsSound(P.cleanProject({version: 1, scenes: [{}]})), false);
const probeWith = (video, format, audio = true) => ({ probe: { format: Object.assign({ duration: "13.6" }, format), streams: [Object.assign({ codec_type: "video", width: 1080, height: 1920, avg_frame_rate: "30/1" }, video)].concat(audio ? [{ codec_type: "audio" }] : []) } });
assert(verdict(probeWith({ width: 1920, height: 1080 })).failures.some(m => m.includes("Frame Size"))); assert(verdict(probeWith({ avg_frame_rate: "24/1" })).failures.some(m => m.includes("Frame Rate")));
assert(verdict(probeWith({}, { duration: "12.9" })).failures.some(m => m.includes("Length"))); assert(verdict(probeWith({}, {}, false)).failures.some(m => m.includes("No Sound")));
assert.deepEqual(verdict(Object.assign(probeWith({ avg_frame_rate: "0/0", r_frame_rate: "30/1" }, { duration: "N/A" }), { lastFrame: 13.6 - 1 / 30 })).failures, []);
assert(verdict({ bytes: 0 }).failures.some(m => m.includes("Empty"))); assert(verdict({ loudness: { integrated: -70, range: 0, truePeak: -Infinity, silent: true } }).failures.some(m => m.includes("Silent")));
assert.equal(verdict({ loudness: { integrated: -20, range: 5, truePeak: -0.5, silent: false } }).checks.length, 2); assert.deepEqual(verdict({ loudness: { integrated: -20, range: 5, truePeak: -0.5, silent: false } }).failures, []);
assert(ExportCheck.judge(moving.project, facts(probeWith({}, { duration: "12.3" }))).failures.some(m => m.includes("Stand-In")));

// ---------------------------------------------------------------- The Commands, Run As An Agent Runs Them, On A Film In A Temporary Project Folder
const projectDir = fs.mkdtempSync(path.join(os.tmpdir(), "motion-studio-film-check-")), filmDir = path.join(projectDir, "my-film");
const runTool = (script, args, cwd = projectDir) => spawnSync(process.execPath, [path.join(root, script), ...args], { cwd, encoding: "utf8", windowsHide: true });
const runRender = project => spawnSync(process.execPath, [path.join(project, "render-reviewed.cjs"), "Cut.mp4"], { cwd: project, encoding: "utf8", windowsHide: true, input: "" });
const passed = (out, what) => { assert.equal(out.status, 0, what + ": " + out.stderr + out.stdout); return out; };
const refused = (out, pattern, what) => { assert.equal(out.status, 1, what); assert(pattern.test(out.stderr), what + ": " + out.stderr); return out; };
const json = file => JSON.parse(fs.readFileSync(file, "utf8"));
try {
  fs.cpSync(travels, filmDir, { recursive: true }); fs.rmSync(path.join(filmDir, "storyboard.timed.json")); fs.rmSync(path.join(filmDir, "words.json"));
  const authored = json(path.join(filmDir, "storyboard.json"));
  authored.scenes[0].cues = [{ type: "Sound", at: 0.2, sound: "Low Bloom", gain: 0.4 }];
  fs.writeFileSync(path.join(filmDir, "storyboard.json"), JSON.stringify(authored, null, 2));
  const timedFile = path.join(filmDir, "storyboard.timed.json"), retimeArgs = ["my-film/storyboard.json", "my-film/words.json", "my-film/storyboard.timed.json", "--overwrite"];
  passed(runTool("tools/standin-words.cjs", ["my-film/script.txt", "my-film/words.json"]), "Stand-In Words");
  const firstRun = passed(runTool("tools/retime.cjs", retimeArgs), "Retime");
  assert(firstRun.stdout.includes("Placed 17 Event Sounds In The Timed Storyboard.") && firstRun.stdout.includes("Not Ready For Export"));
  const firstTimed = json(timedFile);
  assert.equal(eventCues(firstTimed).length, 17); assert.equal(firstTimed.scenes[0].cues.filter(cue => !cue.event).length, 1); assert.equal(firstTimed.voice.standIn, true);
  assert.deepEqual(firstTimed, P.cleanProject(firstTimed)); assert(!fs.readdirSync(filmDir).some(name => name.includes(".writing-")));
  // Running It Again Changes Nothing. A Slower Reading Moves Every Sound, And Neither Doubles Nor Drops One.
  passed(runTool("tools/retime.cjs", retimeArgs), "Retime Again"); assert.deepEqual(json(timedFile), firstTimed);
  passed(runTool("tools/standin-words.cjs", ["my-film/script.txt", "my-film/words.json", "--wpm", "110", "--overwrite"]), "Slower Words");
  passed(runTool("tools/retime.cjs", retimeArgs), "Retime Slower");
  const slowTimed = json(timedFile), eventTime = (board, id) => { let start = 0; for (const scene of board.scenes) { const cue = scene.cues.find(item => item.event === id); if (cue) return start + cue.at; start += scene.duration; } };
  assert.equal(eventCues(slowTimed).length, 17); assert(eventTime(slowTimed, "town-lights") > eventTime(firstTimed, "town-lights") + 1);
  assert.deepEqual(slowTimed.scenes[0].cues.filter(cue => !cue.event), [{ type: "Sound", at: 0.2, gain: 0.4, sound: "Low Bloom" }]);
  assert(!eventCues(slowTimed).some(cue => cue.event === "count.count-start")); assert(eventCues(slowTimed).some(cue => cue.sound === "Paper Tap" && cue.gain === 0.25));
  // The Events Tool Reports The State And Refreshes The Same File In Place.
  assert(passed(runTool("tools/events.cjs", ["my-film/storyboard.timed.json"]), "Events").stdout.includes("Carries All 17 Event Sounds"));
  const untouched = fs.readFileSync(timedFile);
  assert(passed(runTool("tools/events.cjs", ["my-film/storyboard.timed.json", "--update"]), "Events Update").stdout.includes("Nothing Was Written")); assert.deepEqual(fs.readFileSync(timedFile), untouched);
  passed(runTool("tools/retime.cjs", retimeArgs.concat("--no-sounds")), "Retime Without Sounds"); assert.equal(eventCues(json(timedFile)).length, 0);
  assert(passed(runTool("tools/events.cjs", ["my-film/storyboard.timed.json"]), "Events Missing").stdout.includes("None Are Placed"));
  const quietProject = passed(runTool("adapter/prepare-remotion.cjs", ["my-film/storyboard.timed.json", "my-film-quiet"]), "Prepare Without Sounds");
  assert(/WARNING: .*None Are Placed/.test(quietProject.stderr) && /WARNING: .*Stand-In Voice Timing/.test(quietProject.stderr));
  assert(passed(runTool("tools/events.cjs", ["my-film/storyboard.timed.json", "--update"]), "Events Update").stdout.includes("Placed 17 Sound Cues"));
  assert.deepEqual(json(timedFile), slowTimed); assert(!fs.readdirSync(filmDir).some(name => name.includes(".writing-")));
  // A Scene Module That Cannot Be Read Yet Does Not Stop The Timing, And The Warning Is Loud.
  fs.renameSync(path.join(filmDir, "scenes", "idea.js"), path.join(filmDir, "scenes", "idea.js.away"));
  const early = passed(runTool("tools/retime.cjs", retimeArgs), "Retime Before The Module Exists");
  assert(/Warning: Event Sounds Were Not Placed\. Scene Module Not Found/.test(early.stderr)); assert.equal(eventCues(json(timedFile)).length, 0);
  fs.renameSync(path.join(filmDir, "scenes", "idea.js.away"), path.join(filmDir, "scenes", "idea.js"));
  passed(runTool("tools/retime.cjs", retimeArgs), "Retime"); assert.deepEqual(json(timedFile), slowTimed);
  // A Remotion Project Prepared From The Timed Storyboard Carries Every Event Sound, And Refuses To Render On Stand-In Timing.
  const standInProject = path.join(projectDir, "my-film-remotion");
  const preparedOut = passed(runTool("adapter/prepare-remotion.cjs", ["my-film/storyboard.timed.json", "my-film-remotion"]), "Prepare");
  assert(preparedOut.stdout.includes("Including 17 Event Sounds") && preparedOut.stdout.includes("No Video Was Written") && /WARNING: .*Stand-In Voice Timing/.test(preparedOut.stderr) && !/Event Sound/.test(preparedOut.stderr));
  const preparedTimeline = json(path.join(standInProject, "src", "timeline.json"));
  assert.equal(preparedTimeline.audio.length, 18); assert.equal(preparedTimeline.standIn, true); assert.equal(preparedTimeline.eventSounds.state, "current");
  for (const cue of preparedTimeline.audio) assert(fs.statSync(path.join(standInProject, "public", cue.file)).size > 44);
  assert.equal(eventCues(json(path.join(standInProject, "source-storyboard.json"))).length, 17);
  refused(runRender(standInProject), /Stand-In Voice Timing, So It Is Not Ready For Export/, "The Reviewed Render Must Refuse Stand-In Timing");
  assert(Reviewed.standInReason(standInProject).includes("Stand-In")); assert.equal(fs.existsSync(path.join(standInProject, "Cut.mp4")), false);
  // With A Recording And Its Word Timings The Mark Is Gone, And The Render Waits For The Owner At An Interactive Terminal.
  const realWords = json(path.join(filmDir, "words.json")); delete realWords.standIn; delete realWords.note;
  fs.writeFileSync(path.join(filmDir, "words.json"), JSON.stringify(realWords));
  const tone = new Float32Array(Math.ceil((realWords.words[realWords.words.length - 1].end + 0.5) * 48000));
  for (const word of realWords.words) for (let n = Math.round(word.start * 48000); n < Math.round(word.end * 48000); n++) tone[n] = 0.5 * Math.sin(2 * Math.PI * 220 * n / 48000);
  fs.writeFileSync(path.join(filmDir, "voice.wav"), Buffer.from(Audio.wav(tone)));
  const realRun = passed(runTool("tools/retime.cjs", retimeArgs.concat("--voice", "my-film/voice.wav")), "Retime To The Recording");
  assert(!realRun.stdout.includes("Stand-In")); assert.equal(json(timedFile).voice.standIn, undefined); assert.equal(json(timedFile).voice.file, "voice.wav"); assert.equal(eventCues(json(timedFile)).length, 17);
  const realOut = passed(runTool("adapter/prepare-remotion.cjs", ["my-film/storyboard.timed.json", "my-film-final"]), "Prepare Final"); assert.equal(realOut.stderr, "");
  assert.equal(Reviewed.standInReason(path.join(projectDir, "my-film-final")), "");
  refused(runRender(path.join(projectDir, "my-film-final")), /Interactive Terminal/, "The Reviewed Render Must Still Wait For The Owner");
  // A Film With No Narration: Stand-In Words Leave No Mark, And A Film With Numbers Only Needs No Words At All.
  authored.narration = "None"; fs.writeFileSync(path.join(filmDir, "storyboard.json"), JSON.stringify(authored, null, 2));
  passed(runTool("tools/standin-words.cjs", ["my-film/script.txt", "my-film/words.json", "--overwrite"]), "Reading Pace");
  const silentRun = passed(runTool("tools/retime.cjs", retimeArgs), "Retime Without Narration");
  assert(silentRun.stdout.includes("Declares No Narration") && !silentRun.stdout.includes("Not Ready For Export")); assert.equal(json(timedFile).voice.standIn, undefined); assert.equal(json(timedFile).narration, "None");
  assert(/WARNING: .*Declares No Narration/.test(passed(runTool("adapter/prepare-remotion.cjs", ["my-film/storyboard.timed.json", "my-film-text"]), "Prepare Text-Led").stderr));
  assert.equal(Reviewed.standInReason(path.join(projectDir, "my-film-text")), "");
  refused(runTool("tools/retime.cjs", ["my-film/storyboard.json", "--no-words", "my-film/storyboard.timed.json", "--overwrite"]), /Nothing Was Written/, "Phrases Need Words");
  const numbers = path.join(projectDir, "numbers-film"); fs.cpSync(path.join(root, "examples", "first-code-scene"), numbers, { recursive: true });
  refused(runTool("tools/retime.cjs", ["numbers-film/storyboard.json", "--no-words", "numbers-film/storyboard.timed.json"]), /narration/, "A Film Must Declare That It Has No Narration");
  fs.writeFileSync(path.join(numbers, "storyboard.json"), JSON.stringify(Object.assign(json(path.join(numbers, "storyboard.json")), { narration: "None" })));
  assert(passed(runTool("tools/retime.cjs", ["numbers-film/storyboard.json", "--no-words", "numbers-film/storyboard.timed.json"]), "Retime Without Words").stdout.includes("Placed 2 Event Sounds"));
  const numbersTimed = json(path.join(numbers, "storyboard.timed.json")); assert.equal(eventCues(numbersTimed).length, 2); assert.equal(numbersTimed.voice, undefined); assert.equal(P.standIn(numbersTimed), false);
  // A Music-Led Film Names Its Track In The Authored Storyboard, And The Track Travels Into The Remotion Project.
  fs.copyFileSync(path.join(filmDir, "voice.wav"), path.join(numbers, "music.wav"));
  fs.writeFileSync(path.join(numbers, "storyboard.json"), JSON.stringify(Object.assign(json(path.join(numbers, "storyboard.json")), { voice: { file: "music.wav", gain: 0.8 } })));
  passed(runTool("tools/retime.cjs", ["numbers-film/storyboard.json", "--no-words", "numbers-film/storyboard.timed.json", "--overwrite"]), "Retime A Music-Led Film");
  assert.deepEqual(json(path.join(numbers, "storyboard.timed.json")).voice, { file: "music.wav", gain: 0.8, offset: 0 });
  passed(runTool("adapter/prepare-remotion.cjs", ["numbers-film/storyboard.timed.json", "numbers-remotion"]), "Prepare A Music-Led Film");
  const musicTimeline = json(path.join(projectDir, "numbers-remotion", "src", "timeline.json"));
  assert(musicTimeline.audio.some(cue => cue.id === "film-voice" && cue.gain === 0.8)); assert.equal(musicTimeline.audio.length, 3); assert.equal(musicTimeline.narration, "None"); assert.equal(Reviewed.standInReason(path.join(projectDir, "numbers-remotion")), "");
  // Every Tool Refuses To Write Into The Skill Folder.
  const inside = path.join(root, "examples", "an-idea-travels"), outside = /Outside The Skill Folder/;
  refused(runTool("tools/standin-words.cjs", [path.join(inside, "script.txt"), path.join(root, "my-film", "words.json")]), outside, "Stand-In Words Inside The Skill");
  refused(runTool("tools/retime.cjs", [path.join(inside, "storyboard.json"), path.join(inside, "words.json"), path.join(inside, "storyboard.timed.json"), "--overwrite"]), outside, "Retime Inside The Skill");
  refused(runTool("tools/events.cjs", [path.join(inside, "storyboard.timed.json"), "--update"]), outside, "Events Update Inside The Skill");
  refused(runTool("tools/events.cjs", [path.join(inside, "storyboard.timed.json"), "--sheet", path.join(root, "Events.txt")]), outside, "Events Sheet Inside The Skill");
  refused(runTool("tools/stills.cjs", [path.join(inside, "storyboard.timed.json"), path.join(root, "Board"), "--browser", process.execPath]), outside, "Stills Inside The Skill");
  refused(runTool("tools/motion.cjs", [path.join(inside, "storyboard.timed.json"), "--browser", process.execPath, "--report", path.join(root, "Motion.json")]), outside, "Motion Report Inside The Skill");
  refused(runTool("adapter/prepare-remotion.cjs", [path.join(inside, "storyboard.timed.json"), path.join(root, "My-Project")]), outside, "Remotion Project Inside The Skill");
  refused(runTool("tools/audio.cjs", [path.join(inside, "storyboard.timed.json"), "--wav", path.join(root, "Mix.wav")]), outside, "Check Mix Inside The Skill");
  refused(runTool("tools/export-check.cjs", [path.join(filmDir, "voice.wav"), path.join(inside, "storyboard.timed.json"), "--report", path.join(root, "Check.json")]), outside, "Export Report Inside The Skill");
  for (const name of ["my-film", "Board", "My-Project", "Events.txt", "Motion.json", "Mix.wav", "Check.json"]) assert.equal(fs.existsSync(path.join(root, name)), false, name);
  assert.deepEqual(json(path.join(inside, "storyboard.timed.json")), timedExample);
  // With FFmpeg Present, Measure Real Sound Through The Null Sink.
  if (ffmpegFound) {
    const ffmpeg = Meter.locate("ffmpeg"), reference = new Float32Array(48000 * 2 * 4).map((_, i) => 0.1 * Math.sin(2 * Math.PI * 997 * Math.floor(i / 2) / 48000)), heard = Meter.loudness(ffmpeg, reference);
    near(heard.integrated, -20, 0.5); near(heard.truePeak, -20, 0.5); assert.equal(heard.silent, false); assert.equal(Meter.loudness(ffmpeg, new Float32Array(48000 * 2)).silent, true);
    const decodedVoice = Meter.decode(ffmpeg, path.join(filmDir, "voice.wav")); assert.equal(decodedVoice.length, tone.length * 2); near(decodedVoice[2 * 20000], tone[20000], 1e-3);
    authored.narration = "Voice"; fs.writeFileSync(path.join(filmDir, "storyboard.json"), JSON.stringify(authored, null, 2));
    fs.writeFileSync(path.join(filmDir, "words.json"), JSON.stringify(realWords));
    passed(runTool("tools/retime.cjs", retimeArgs.concat("--voice", "my-film/voice.wav")), "Retime To The Recording");
    const mixRun = passed(runTool("tools/audio.cjs", ["my-film/storyboard.timed.json", "--wav", "my-film/check-mix.wav", "--report", "my-film/audio.json"]), "Sound Mix Check");
    assert(mixRun.stdout.includes("Integrated Loudness") && mixRun.stdout.includes("Voice Recording Included") && mixRun.stdout.includes("Carries All 17 Event Sounds") && mixRun.stdout.includes("No Video Was Written"));
    const mixReport = json(path.join(filmDir, "audio.json")), mixWav = fs.readFileSync(path.join(filmDir, "check-mix.wav"));
    assert(mixReport.loudness.integrated > -30 && mixReport.loudness.integrated < -5 && mixReport.loudness.truePeak < 3 && mixReport.voiceRecording === true);
    assert.equal(mixReport.cues.length, 18); assert(mixReport.cues.filter(cue => cue.voiceDb !== null && cue.under !== null).length >= 8); assert(mixReport.overlaps.length >= 5 && mixReport.overlaps.every(item => item.words.length));
    assert.equal(mixWav.toString("ascii", 0, 4), "RIFF"); assert.equal(mixWav.length, 44 + Math.round(mixReport.seconds * 48000) * 4);
    refused(runTool("tools/audio.cjs", ["my-film/storyboard.timed.json", "--margin", "40", "--strict"]), /To Check, And --strict Is Set/, "Strict Sound Mix Check");
    refused(runTool("tools/audio.cjs", ["my-film/storyboard.timed.json", "--ffmpeg", path.join(projectDir, "no-ffmpeg-here")]), /Does Not Install/, "Missing FFmpeg");
    refused(runTool("tools/audio.cjs", ["my-film/storyboard.timed.json", "--wav", "my-film/check-mix.mov"]), /\.wav File/, "The Check Mix Is Sound Only");
    const soundOnly = refused(runTool("tools/export-check.cjs", ["my-film/check-mix.wav", "my-film/storyboard.timed.json"]), /No Picture Stream/, "A Sound File Is Not A Finished Export");
    assert(soundOnly.stdout.includes("Sound Stream Present") && soundOnly.stdout.includes("Integrated Loudness") && soundOnly.stdout.includes("Read And Not Changed"));
  }
  const videos = fs.readdirSync(projectDir, { recursive: true }).filter(name => /\.(mp4|mov|webm|mkv|avi|gif)$/i.test(String(name)));
  assert.deepEqual(videos, [], "No Check May Write A Video");
} finally {
  const scratch = fs.realpathSync(projectDir);
  if (path.dirname(scratch) === fs.realpathSync(os.tmpdir()) && path.basename(scratch).startsWith("motion-studio-film-check-")) fs.rmSync(scratch, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
}

// ---------------------------------------------------------------- The Guides Agree With Each Other And With The Tools
const guideNames = ["SKILL.md", "DIRECTING.md", "STYLE-FRAMES.md", "CODE-SCENES.md", "VOICE-TIMING.md", "PARTS.md", "REVIEW-TOOLS.md", "REVIEW.md", "HANDOFFS.md", "PRESENTER.md", "adapter/README.md", "scenarios/README.md"];
const guides = Object.fromEntries(guideNames.map(name => [name, fs.readFileSync(path.join(root, name), "utf8")])), everyGuide = Object.values(guides).join("\n");
// One Storyboard: No Guide Names A Second File, And The Guides That Build A Film Name The Timed One.
assert(!/storyboard\.sound\.json|--place\s+my-film/.test(everyGuide));
for (const name of ["SKILL.md", "CODE-SCENES.md", "VOICE-TIMING.md", "REVIEW-TOOLS.md", "REVIEW.md", "adapter/README.md"]) assert(guides[name].includes("storyboard.timed.json"), name + " Must Name The Timed Storyboard");
// One Home For A Film: Tool Commands Are Run From The User's Project With The Skill's Path Spelled Out, Never As A Bare Path Inside The Skill.
for (const [name, text] of Object.entries(guides)) for (const line of text.split("\n")) {
  if (/^\s*node (tools|adapter)\//.test(line)) assert(/^node tools\/(build-assets|make-examples|check|check-browser)\.cjs/.test(line), name + " Runs A Film Command From Inside The Skill: " + line);
  if (/\$SKILL\/(tools|adapter)\/[\w-]+\.cjs/.test(line)) { const script = /\$SKILL\/((?:tools|adapter)\/[\w-]+\.cjs)/.exec(line)[1]; assert(fs.existsSync(path.join(root, script)), name + " Names A Tool That Does Not Exist: " + script); }
}
for (const name of ["SKILL.md", "CODE-SCENES.md"]) assert(/Never Inside The Skill Folder/.test(guides[name]), name + " Must State Where A Film Folder Lives");
// One Editor For The Owner's Review: Remotion Studio By Default, Motion Studio When Node Packages Cannot Be Installed.
for (const name of ["SKILL.md", "CODE-SCENES.md", "VOICE-TIMING.md", "REVIEW-TOOLS.md", "REVIEW.md", "HANDOFFS.md", "PRESENTER.md", "adapter/README.md"]) {
  assert(guides[name].includes("Remotion Studio"), name + " Must Name Remotion Studio For The Owner's Review");
  assert(!/Reviews? (The |It |The Editable |The Timed )?(Storyboard |Project )?In (Motion Studio|The Editor)\b(?! Only| When)/.test(guides[name]), name + " Sends The Owner's Review To The Wrong Editor");
}
assert(/Motion Studio.{0,200}Only When Node(\.js)? Packages Cannot Be Installed/s.test(guides["SKILL.md"]));
// The Numbered Workflow Asks Only For What Earlier Steps Made.
const stepOrder = ["**Settle The Brief.**", "**Set Up The Film Folder.**", "**Find The Film.**", "**Choose The Look From Stills.**", "**Draw The Scenes.**", "**Check From Stills And Numbers.**", "**Judge It.**", "**Retime To The Real Voice.**", "**Hand The Film To The Owner In Remotion Studio.**", "**Export After Approval, Then Check The File.**"];
const stepPlaces = stepOrder.map(step => guides["SKILL.md"].indexOf(step));
assert(stepPlaces.every((at, i) => at > 0 && (!i || at > stepPlaces[i - 1])), "The Workflow Steps Are Missing Or Out Of Order");
stepOrder.forEach((step, i) => assert(guides["SKILL.md"].includes("\n" + (i + 1) + ". " + step), "Step " + (i + 1) + " Should Be " + step));
assert(/Rough Direction Stills/.test(guides["SKILL.md"]) && /Rough Direction Stills/.test(guides["DIRECTING.md"]) && /No Finished Scene/.test(guides["DIRECTING.md"]));
// Stand-In Timing, No Narration, Transcription, Sound Measurement, And Style Frames Are Each Documented Where An Agent Looks.
assert(/"narration": "None"/.test(guides["VOICE-TIMING.md"]) && /Never Use It To Get Past A Missing Recording/.test(guides["VOICE-TIMING.md"]));
assert(/video-edit\/scripts\/edit_video\.py" setup/.test(guides["VOICE-TIMING.md"]) && /video-edit\/scripts\/speech\.py" transcribe/.test(guides["VOICE-TIMING.md"]) && guides["VOICE-TIMING.md"].includes("--backend faster-whisper") && guides["VOICE-TIMING.md"].includes("--backend whisper-cli") && !guides["VOICE-TIMING.md"].includes("/path/to/model"));
for (const name of ["REVIEW-TOOLS.md", "REVIEW.md"]) assert(guides[name].includes("tools/audio.cjs") && guides[name].includes("tools/export-check.cjs"), name + " Must Name The Sound Tools");
assert(/-14 LUFS/.test(guides["REVIEW-TOOLS.md"]) && /-1\.5 dBTP/.test(guides["REVIEW-TOOLS.md"]) && /Never Applied/.test(guides["REVIEW-TOOLS.md"]));
assert(/Asks For One Style Frame/.test(guides["STYLE-FRAMES.md"]) && /One Message/.test(guides["DIRECTING.md"]) && /Each (Stop )?Still Needs (Its Own |An )?Explicit Yes/.test(guides["DIRECTING.md"]));
// Every Usage Line A Guide Prints For A Tool Lists The Options The Tool Accepts.
for (const [script, guide] of [["retime.cjs", "VOICE-TIMING.md"], ["events.cjs", "REVIEW-TOOLS.md"], ["audio.cjs", "REVIEW-TOOLS.md"], ["export-check.cjs", "REVIEW-TOOLS.md"], ["stills.cjs", "REVIEW-TOOLS.md"], ["motion.cjs", "REVIEW-TOOLS.md"]]) {
  const flags = new Set(fs.readFileSync(path.join(__dirname, script), "utf8").split("\n").find(line => line.startsWith("const usage")).match(/--[a-z-]+/g));
  for (const flag of flags) assert(guides[guide].includes(flag), guide + " Does Not Mention " + flag + " Of " + script);
}
// House Style: Prose In The Guides Capitalises Every Word.
for (const [name, text] of Object.entries(guides)) {
  let fenced = false;
  text.split("\n").forEach((line, at) => {
    if (/^\s*(```|~~~)/.test(line)) { fenced = !fenced; return; }
    if (fenced || /^---$|^name: |^description: /.test(line)) return;
    // Code Spans, Link Targets, And File Paths Are Not Prose. Units Such As kHz And dBTP Keep Their Own Spelling.
    const prose = line.replace(/`[^`]*`/g, " ").replace(/\]\([^)]*\)/g, "] ");
    const strays = prose.split(/[\s|*\[\]()“”"—–,;:!?]+/).map(word => word.replace(/\.+$/, "")).filter(word => /^[a-z]+(?:[’'][a-z]+)?$/.test(word));
    assert.deepEqual(strays, [], name + " Line " + (at + 1) + " Has Words That Are Not In Title Case: " + line.slice(0, 120));
  });
}

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
console.log("Passed One-Storyboard Event Sound, Stand-In Export Gate, No-Narration, Film Folder, Sound Mix, Export Check, And Guide Consistency Checks." + (ffmpegFound ? "" : " FFmpeg Was Not Found, So The Loudness Measurements Were Skipped."));
