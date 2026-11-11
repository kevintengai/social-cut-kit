// Make Clearly Labelled Stand-In Word Timings From Script Text So Building Can Start Before The Voice Exists.
"use strict";
const fs = require("node:fs"), path = require("node:path");
const { parseArgs } = require("node:util");
const Timing = require("../studio/timing.js"), Film = require("./lib/film.cjs");

const usage = "Usage: node tools/standin-words.cjs Script.txt Words.json [--wpm 150] [--start 0.3] [--overwrite]";
function main() {
  const { values: options, positionals } = parseArgs({ allowPositionals: true, options: { wpm: { type: "string" }, start: { type: "string" }, overwrite: { type: "boolean" }, help: { type: "boolean" } } });
  if (options.help) { console.log(usage); return; }
  if (positionals.length !== 2) throw new Error(usage);
  const [source, target] = positionals.map(item => path.resolve(item));
  if (!fs.existsSync(source)) throw new Error("Script Not Found: " + positionals[0]);
  Film.guardOutput(target, "The Word Timings");
  if (fs.existsSync(target) && !options.overwrite) throw new Error("Choose A New Output File, Or Add --overwrite.");
  const wpm = options.wpm == null ? 150 : Number(options.wpm), start = options.start == null ? 0.3 : Number(options.start);
  if (!Number.isFinite(start) || start < 0 || start > 60) throw new Error("--start Needs A Number Of Seconds From 0 To 60.");
  const words = Timing.standIn(fs.readFileSync(source, "utf8").replace(/^﻿/, ""), { wpm, start });
  const out = { standIn: true, note: "Stand-In Word Timings Made From Script Text At " + wpm + " Words Per Minute. Replace Them With Timings From The Real Recording.", wpm, words };
  fs.writeFileSync(target, JSON.stringify(out, null, 2) + "\n");
  console.log("Wrote " + words.length + " Stand-In Words Ending At " + Timing.clock(words[words.length - 1].end) + ". These Are Not Timings From A Recording.");
  console.log("Wrote " + target);
}
if (require.main === module) { try { main(); } catch (error) { console.error(error.message); process.exitCode = 1; } }
