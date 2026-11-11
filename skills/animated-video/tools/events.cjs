// Gather The Picture Events That Code Scenes Declare Into A Cue Sheet, And Place Bank Sounds On Them.
// Events Come From The Same Constants That Draw The Picture, So Moving A Beat And Placing Again Moves Its Sound.
// The Timing Tool Places Event Sounds In The Timed Storyboard Itself. This Tool Lists Them, Checks Them, And Refreshes Them In Place.
"use strict";
const fs = require("node:fs"), path = require("node:path");
const { parseArgs } = require("node:util");
const Film = require("./lib/film.cjs");
const P = require("../studio/project.js");

const usage = "Usage: node tools/events.cjs Storyboard.json [--sheet Events.txt] [--json Events.json] [--update] [--place Copy.json] [--overwrite]";
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
// A Copy Of The Storyboard Whose Event Sounds Are Timed Sound Cues. Cues From An Earlier Run Are Replaced. Cues Added By Hand Are Kept.
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
    if (scene.cues.length > 64) throw Object.assign(new Error("Scene " + (index + 1) + " Would Hold More Than 64 Cues. Silence Some Events With A sounds Entry Of None."), { tooMany: true });
    scene.cues.sort((a, b) => a.at - b.at);
  });
  return { project: P.cleanProject(out), placed };
}
// Gather And Place In One Step: The Storyboard With Its Event Sounds In Place.
function placeEvents(scope, project) {
  const { events, notes } = gather(scope, project), result = place(project, events);
  return { project: result.project, placed: result.placed, events, notes };
}
// Compare The Event Sounds A Storyboard Holds With The Ones Its Scenes Declare Now.
// state Is "current", "none" When No Event Has A Sound, "missing" When None Are Placed, Or "stale" When They Differ.
function status(scope, project) {
  const { events, notes } = gather(scope, project), want = place(project, events).project;
  const listed = board => board.scenes.map(scene => scene.cues.filter(cue => cue.event)
    .map(cue => [cue.event, cue.at, cue.sound, cue.gain, cue.pan || 0]).sort((a, b) => a[1] - b[1] || (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0)));
  const have = listed(project), expect = listed(want), placed = have.flat().length, expected = expect.flat().length;
  const state = JSON.stringify(have) === JSON.stringify(expect) ? (expected ? "current" : "none") : placed ? "stale" : "missing";
  return { state, placed, expected, events, notes };
}
// One Sentence About A Status, For Any Tool That Reports It.
function describe(result) {
  if (result.state === "current") return "The Storyboard Carries All " + result.expected + " Event Sound" + (result.expected === 1 ? "" : "s") + " Its Scenes Declare.";
  if (result.state === "none") return "No Scene Declares An Event With A Sound.";
  if (result.state === "missing") return "The Scenes Declare " + result.expected + " Event Sound" + (result.expected === 1 ? "" : "s") + ", And None Are Placed In The Storyboard. Run tools/retime.cjs Again, Or tools/events.cjs With --update.";
  return "The Placed Event Sounds Are Out Of Date: " + result.placed + " Placed, " + result.expected + " Declared, Or Their Times And Sounds Differ. Run tools/retime.cjs Again, Or tools/events.cjs With --update.";
}
// Put The Placed Event Cues Into The Storyboard As It Is Written On Disk, Leaving Every Other Field As The Author Wrote It.
function updateRaw(raw, placedProject) {
  raw.scenes.forEach((scene, index) => {
    const kept = (Array.isArray(scene.cues) ? scene.cues : []).filter(cue => !(cue && cue.event));
    const added = placedProject.scenes[index].cues.filter(cue => cue.event).map(cue => {
      const out = { type: "Sound", at: cue.at, gain: cue.gain, sound: cue.sound, event: cue.event };
      if (cue.pan) out.pan = cue.pan;
      return out;
    });
    if (!added.length && !Array.isArray(scene.cues)) return;
    const all = kept.concat(added);
    scene.cues = all.every(cue => cue && Number.isFinite(cue.at)) ? all.sort((a, b) => a.at - b.at) : all;
  });
  return raw;
}

function main() {
  const { values: options, positionals } = parseArgs({ allowPositionals: true, options: { sheet: { type: "string" }, json: { type: "string" }, place: { type: "string" }, update: { type: "boolean" }, overwrite: { type: "boolean" }, help: { type: "boolean" } } });
  if (options.help) { console.log(usage); return; }
  if (positionals.length !== 1) throw new Error(usage);
  if (options.update && options.place) throw new Error("Use --update To Refresh The Storyboard Itself, Or --place To Write A Separate Copy, Not Both.");
  const source = path.resolve(positionals[0]);
  const targets = ["sheet", "json", "place"].filter(name => options[name]).map(name => path.resolve(options[name]));
  for (const target of targets) {
    if (target === source) throw new Error("Write To A New File, Not Over The Storyboard. To Refresh The Placed Sounds In The Storyboard Itself, Use --update.");
    Film.guardOutput(target, "The Output File");
    if (fs.existsSync(target) && !options.overwrite) throw new Error("Choose A New Output File, Or Add --overwrite: " + target);
  }
  if (options.update) Film.guardOutput(source, "The Updated Storyboard");
  const { film, scope, project } = Film.openFilm(positionals[0]), before = status(scope, project), { events, notes } = before, text = sheet(project, events);
  if (options.sheet) fs.writeFileSync(path.resolve(options.sheet), text + "\n"); else console.log(text);
  if (options.json) fs.writeFileSync(path.resolve(options.json), JSON.stringify({ title: project.title, duration: P.duration(project), eventSounds: { state: before.state, placed: before.placed, expected: before.expected }, events }, null, 2) + "\n");
  for (const note of notes) console.log("Note: " + note);
  if (options.update) {
    if (before.state === "current" || before.state === "none") console.log(describe(before) + " Nothing Was Written.");
    else {
      const result = place(project, events);
      Film.writeSafely(source, JSON.stringify(updateRaw(film.raw, result.project), null, 2) + "\n");
      console.log("Placed " + result.placed + " Sound Cue" + (result.placed === 1 ? "" : "s") + " On Picture Events In The Storyboard Itself. Wrote " + source);
    }
  } else if (options.place) {
    const result = place(project, events);
    fs.writeFileSync(path.resolve(options.place), JSON.stringify(result.project, null, 2) + "\n");
    console.log("Placed " + result.placed + " Sound Cue" + (result.placed === 1 ? "" : "s") + " On Picture Events. Wrote " + path.resolve(options.place));
    console.log("This Is A Separate Copy. No Other Tool Or Guide Reads It. The Storyboard To Review And Export Is The Timed One, Which tools/retime.cjs Or --update Keeps Current.");
  } else console.log(describe(before));
  console.log("Gathered " + events.length + " Event" + (events.length === 1 ? "" : "s") + " From " + project.scenes.filter(scene => scene.mode === "Code Scene").length + " Code Scenes.");
}
module.exports = { gather, sheet, place, placeEvents, status, describe, updateRaw };
if (require.main === module) { try { main(); } catch (error) { console.error(error.message); process.exitCode = 1; } }
