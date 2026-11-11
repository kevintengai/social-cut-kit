"use strict";
const fs = require("node:fs"), path = require("node:path");
const P = require("../studio/project.js");
const dir = path.resolve(__dirname, "../examples");
fs.mkdirSync(dir, {recursive: true});
function save(name, p) {
  p.scenes.forEach((s, i) => { s.id = name + "-" + (i + 1); });
  fs.writeFileSync(path.join(dir, name + ".json"), JSON.stringify(P.cleanProject(p), null, 2) + "\n");
}
save("give-an-idea-shape", P.demo());
const turn = Object.assign(P.scene("3D Object"), {
  duration: 5, eyebrow: "Material Study", title: "Follow The Facets", body: "A Slow Orbit Brings The Highlight Across The Front Face.",
  background: "#172233", accent: "#a1c4ff", material: "#91accb", light: "#fff2db",
  shape: "Crystal", azimuth: -48, elevation: 18, orbit: 86, spin: -24, distance: 6.4, gloss: 0.84, mark: "Focus",
  cues: [{ type: "Sound", at: 0, sound: "Room Air", gain: 0.7 }, { type: "Sound", at: 2.8, sound: "Glass Point", gain: 0.6 }]
});
const hold = Object.assign(P.scene("3D Object"), {
  duration: 4, eyebrow: "Second Angle", title: "Hold The Last Angle", body: "A Longer Hold Gives The Viewer Time To Read.",
  background: "#172233", accent: "#c0f2d1", material: "#83bfae", light: "#c5f1ff",
  shape: "Prism", azimuth: 24, elevation: 27, orbit: 14, spin: 52, distance: 6.6, gloss: 0.30, mark: "Orbit",
  cues: [{ type: "Sound", at: 0.1, sound: "Air Sweep", gain: 0.55 }, { type: "Voice", at: 0.5, text: "Hold The Last Angle.", gain: 1, clip: "" }]
});
save("facet-turntable", { version: 1, title: "Facet Turntable", aspect: "Landscape", fps: 24, scenes: [turn, hold] });
console.log("Wrote Two Editable Storyboards.");
