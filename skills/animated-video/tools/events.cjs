// Gather The Picture Events That Code Scenes Declare Into A Cue Sheet, And Optionally Place Bank Sounds On Them.
// Events Come From The Same Constants That Draw The Picture, So Moving A Beat And Running This Again Moves Its Sound.
"use strict";
const fs = require("node:fs"), path = require("node:path");
const { parseArgs } = require("node:util");
const Film = require("./lib/film.cjs");
const P = require("../studio/project.js");

const usage = "Usage: node tools/events.cjs Storyboard.json [--sheet Events.txt] [--json Events.json] [--place WithSounds.json] [--overwrite]";
const stamp = value => value.toFixed(2) + "s";

// Every Event In Film Order, With The Sound It Would Receive: The Scene's Own sounds Entry By Event id, Then By Kind, Then The Module's Suggestion.
function gather(scope, project) {
  const notes = [], events = [];
  project.scenes.forEach((scene, index) => {
    for (const event of scope.MotionScenes.sceneEvents(project, index)) {
      if (event.at < 0 || event.at > scene.duration - 0.01) { notes.push("Scene " + (index + 1) + " Event " + event.id + " Falls Outside Its Scene At " + stamp(event.at) + " And Was Left Out."); continue; }
      const chosen = scene.sounds && (scene.sounds[event.id] || (event.kind && scene.sounds[event.kind]));
      if (chosen) { if (chosen.sound === "None") { delete event.sound; delete event.gain; } else { event.sound = chosen.sound; event.gain = chosen.gain; } }
      else if (event.sound && !P.sounds.includes(event.sound)) { notes.push("Scene " + (index + 1) + " Event " + event.id + " Suggests A Sound That Is Not In The Bank: " + event.sound + "."); delete event.sound; delete event.gain; }
      events.push(event);
    }
  });
  return { events, notes };
}
function sheet(project, events) {
  const lines = [project.title + " | Picture Events", project.scenes.length + " Scenes · " + stamp(P.duration(project)) + " · " + events.length + " Events", ""];
  project.scenes.forEach((scene, index) => {
    const own = events.filter(event => event.scene === index + 1);
    if (!own.length) return;
    lines.push("Scene " + (index + 1) + " | " + (scene.draw || scene.mode) + " | Starts " + stamp(P.start(project, index)));
    for (const event of own) lines.push(stamp(event.time) + " | " + event.what + " | " + event.id + (event.pan ? " | Pan " + event.pan.toFixed(2) : "") + (event.sound ? " | " + event.sound + " At Gain " + event.gain.toFixed(2) : " | No Sound"));
    lines.push("");
  });
  return lines.join("\n");
}
// A Copy Of The Storyboard Whose Event Sounds Are Timed Sound Cues. Cues From An Earlier Run Are Replaced.
function place(project, events) {
  const out = JSON.parse(JSON.stringify(project));
  let placed = 0;
  out.scenes.forEach((scene, index) => {
    scene.cues = scene.cues.filter(cue => !cue.event);
    for (const event of events.filter(item => item.scene === index + 1 && item.sound)) {
      const cue = { type: "Sound", at: event.at, gain: event.gain, sound: event.sound, event: event.id };
      if (event.pan) cue.pan = event.pan;
      scene.cues.push(cue); placed++;
    }
    if (scene.cues.length > 64) throw new Error("Scene " + (index + 1) + " Would Hold More Than 64 Cues. Silence Some Events With A sounds Entry Of None.");
    scene.cues.sort((a, b) => a.at - b.at);
  });
  return { project: P.cleanProject(out), placed };
}

function main() {
  const { values: options, positionals } = parseArgs({ allowPositionals: true, options: { sheet: { type: "string" }, json: { type: "string" }, place: { type: "string" }, overwrite: { type: "boolean" }, help: { type: "boolean" } } });
  if (options.help) { console.log(usage); return; }
  if (positionals.length !== 1) throw new Error(usage);
  const targets = ["sheet", "json", "place"].filter(name => options[name]).map(name => path.resolve(options[name]));
  for (const target of targets) {
    if (target === path.resolve(positionals[0])) throw new Error("Write To A New File, Not Over The Storyboard.");
    if (fs.existsSync(target) && !options.overwrite) throw new Error("Choose A New Output File, Or Add --overwrite: " + target);
  }
  const { scope, project } = Film.openFilm(positionals[0]), { events, notes } = gather(scope, project), text = sheet(project, events);
  if (options.sheet) fs.writeFileSync(path.resolve(options.sheet), text + "\n"); else console.log(text);
  if (options.json) fs.writeFileSync(path.resolve(options.json), JSON.stringify({ title: project.title, duration: P.duration(project), events }, null, 2) + "\n");
  for (const note of notes) console.log("Note: " + note);
  if (options.place) {
    const result = place(project, events);
    fs.writeFileSync(path.resolve(options.place), JSON.stringify(result.project, null, 2) + "\n");
    console.log("Placed " + result.placed + " Sound Cue" + (result.placed === 1 ? "" : "s") + " On Picture Events. Wrote " + path.resolve(options.place));
  }
  console.log("Gathered " + events.length + " Event" + (events.length === 1 ? "" : "s") + " From " + project.scenes.filter(scene => scene.mode === "Code Scene").length + " Code Scenes.");
}
module.exports = { gather, sheet, place };
if (require.main === module) { try { main(); } catch (error) { console.error(error.message); process.exitCode = 1; } }
