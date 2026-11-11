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
for (const filename of fs.readdirSync(path.join(root, "examples"))) {
  const example = JSON.parse(fs.readFileSync(path.join(root, "examples", filename)));
  assert.deepEqual(example, P.cleanProject(example));
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
