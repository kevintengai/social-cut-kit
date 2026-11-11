"use strict";
const {createInterface} = require("node:readline/promises");
const {spawnSync} = require("node:child_process");
const fs = require("node:fs"), path = require("node:path");

async function main() {
  if (!process.stdin.isTTY) throw new Error("Open An Interactive Terminal For Personal Review Confirmation.");
  const root = __dirname, target = path.resolve(process.argv[2] || "approved-cut.mp4");
  if (fs.existsSync(target)) throw new Error("Choose A New Output File.");
  const p = JSON.parse(fs.readFileSync(path.join(root, "source-storyboard.json"), "utf8"));
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
main().catch(e => { console.error(e.message); process.exitCode = 1; });
