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
// The Part Examples Are Kept As Cleaned Storyboards. Rewriting Them Here Keeps Their Shape Current.
const parts = fs.readdirSync(dir).filter(name => /^part-.*\.json$/.test(name));
for (const name of parts) fs.writeFileSync(path.join(dir, name), JSON.stringify(P.cleanProject(JSON.parse(fs.readFileSync(path.join(dir, name), "utf8"))), null, 2) + "\n");
// The Voiced Example: Stand-In Words From Its Script, Then The Timed Storyboard From Its Authored One.
const Timing = require("../studio/timing.js"), film = path.join(dir, "an-idea-travels");
const words = Timing.standIn(fs.readFileSync(path.join(film, "script.txt"), "utf8"), { wpm: 150, start: 0.3 });
fs.writeFileSync(path.join(film, "words.json"), JSON.stringify({ standIn: true, note: "Stand-In Word Timings Made From Script Text At 150 Words Per Minute. Replace Them With Timings From The Real Recording.", wpm: 150, words }, null, 2) + "\n");
const timed = Timing.retime(P.cleanProject(JSON.parse(fs.readFileSync(path.join(film, "storyboard.json"), "utf8"))), Timing.readWords({ standIn: true, words }));
if (timed.problems.length) throw new Error(timed.problems.join(" "));
fs.writeFileSync(path.join(film, "storyboard.timed.json"), JSON.stringify(P.cleanProject(timed.project), null, 2) + "\n");
console.log("Wrote Two Built-In Storyboards, " + parts.length + " Part Examples, And The Timed Storyboard For An Idea Travels.");
