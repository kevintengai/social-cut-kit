"use strict";
// The Only Command In This Project That Writes A Video. It Asks The Owner In Person And Never Replaces A File.
const {createInterface} = require("node:readline/promises");
const {spawnSync} = require("node:child_process");
const fs = require("node:fs"), path = require("node:path");

async function main() {
  const root = __dirname, target = path.resolve(process.argv[2] || "approved-cut.mp4");
  if (path.extname(target).toLowerCase() !== ".mp4") throw new Error("Choose An MP4 Output Filename.");
  if (fs.existsSync(target)) throw new Error("Choose A New Output File.");
  if (!fs.existsSync(path.dirname(target))) throw new Error("Output Folder Does Not Exist.");
  if (!process.stdin.isTTY) throw new Error("Open An Interactive Terminal For Personal Review Confirmation.");
  const cut = JSON.parse(fs.readFileSync(path.join(root, "src", "cut.json"), "utf8"));
  const packagePath = path.join(root, "node_modules", "@remotion", "cli", "package.json");
  if (!fs.existsSync(packagePath)) throw new Error("Run npm install In This Project First.");
  for (const warning of cut.warnings) console.log("Warning: " + warning);
  const input = createInterface({input: process.stdin, output: process.stdout});
  let reply;
  try {
    reply = await input.question("After Personally Reviewing The Entire Current Composition In Remotion Studio, Type APPROVE To Export " + cut.title + ", Or Press Enter To Cancel. ");
  } finally { input.close(); }
  if (reply.trim() !== "APPROVE") { console.log("Export Cancelled."); return; }
  const cli = JSON.parse(fs.readFileSync(packagePath, "utf8"));
  const bin = typeof cli.bin === "string" ? cli.bin : cli.bin.remotion;
  const outcome = spawnSync(process.execPath, [path.join(path.dirname(packagePath), bin), "render", "src/index.jsx", "VideoEdit", target], {cwd: root, stdio: "inherit"});
  if (outcome.error) throw outcome.error;
  process.exitCode = outcome.status ?? 1;
}
main().catch(e => { console.error(e.message); process.exitCode = 1; });
