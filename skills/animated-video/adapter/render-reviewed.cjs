"use strict";
const {createInterface} = require("node:readline/promises");
const {spawnSync} = require("node:child_process");
const fs = require("node:fs"), path = require("node:path");

// A Reason This Project Must Not Be Rendered, Or An Empty String. Stand-In Voice Timing Is A Guess At A Recording That Does Not Exist Yet.
function standInReason(root) {
  const load = name => { try { return JSON.parse(fs.readFileSync(path.join(root, name), "utf8")); } catch { return null; } };
  const marked = [load("source-storyboard.json"), load("src/frame-project.json")].some(p => Boolean(p && p.voice && p.voice.standIn === true)) || Boolean((load("src/timeline.json") || {}).standIn);
  return marked ? "This Project Uses Stand-In Voice Timing, So It Is Not Ready For Export. Retime The Storyboard To The Real Recording With The Timing Tool, Prepare A Fresh Project, And Review That One. " +
    "A Film That Will Never Have A Spoken Voice Declares \"narration\": \"None\" In Its Storyboard Instead, And Only The Owner Decides That." : "";
}
async function main() {
  const root = __dirname, refusal = standInReason(root);
  if (refusal) throw new Error(refusal);
  if (!process.stdin.isTTY) throw new Error("Open An Interactive Terminal For Personal Review Confirmation.");
  const target = path.resolve(process.argv[2] || "approved-cut.mp4");
  if (fs.existsSync(target)) throw new Error("Choose A New Output File.");
  const p = JSON.parse(fs.readFileSync(path.join(root, "source-storyboard.json"), "utf8"));
  if (p.narration === "None") console.log("This Film Is Declared As Having No Narration. If A Spoken Voice Was Planned, Cancel And Have The Storyboard Corrected.");
  const input = createInterface({input: process.stdin, output: process.stdout});
  let reply;
  try {
    reply = await input.question("After Personally Reviewing The Entire Current Composition In Remotion Studio, Type APPROVE To Export " + p.title + ", Or Press Enter To Cancel. ");
  } finally { input.close(); }
  if (reply.trim() !== "APPROVE") { console.log("Export Cancelled."); return; }
  const packagePath = path.join(root, "node_modules", "@remotion", "cli", "package.json");
  const cli = JSON.parse(fs.readFileSync(packagePath, "utf8"));
  const bin = typeof cli.bin === "string" ? cli.bin : cli.bin.remotion;
  const outcome = spawnSync(process.execPath, [path.join(path.dirname(packagePath), bin), "render", "src/index.jsx", "MotionStoryboard", target], {cwd: root, stdio: "inherit"});
  if (outcome.error) throw outcome.error;
  process.exitCode = outcome.status ?? 1;
}
module.exports = {standInReason};
if (require.main === module) main().catch(e => { console.error(e.message); process.exitCode = 1; });
