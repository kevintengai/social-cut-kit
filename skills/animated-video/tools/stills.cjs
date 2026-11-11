// Render PNG Stills Of A Storyboard With A Local Browser And Lay Them Out On A Review Board.
// This Tool Writes Individual PNG Images, One HTML Page, And One JSON List. It Never Writes A Video.
"use strict";
const fs = require("node:fs"), path = require("node:path");
const { parseArgs } = require("node:util");
const Film = require("./lib/film.cjs"), Browser = require("./lib/browser.cjs");
const P = require("../studio/project.js"), Timing = require("../studio/timing.js");

const usage = "Usage: node tools/stills.cjs Storyboard.json OutputFolder --browser BrowserPath [--times 1,2.5,7] [--every 2] [--scenes] [--strip 3.2] [--strip-frames 7] [--no-captions] [--silent] [--half] [--columns 4] [--overwrite]";
const written = name => /^still-\d+-[\d.]+s\.png$/.test(name) || ["board.html", "contact-sheet.png", "stills.json"].includes(name);
const stamp = time => time.toFixed(2) + "s";
const escape = text => String(text).replace(/[&<>"]/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;" })[ch]);
const numbers = (text, what) => String(text).split(",").map(part => {
  const value = Number(part.trim());
  if (!part.trim() || !Number.isFinite(value) || value < 0) throw new Error(what + " Needs Seconds Such As 1,2.5,7.");
  return value;
});

// Choose The Film Times To Render. Every Time Is Snapped To A Real Frame.
function chooseTimes(project, options) {
  const fps = project.fps, total = P.duration(project), lastFrame = Math.max(0, Math.ceil(total * fps - 1e-7) - 1), picks = [];
  const frameOf = time => Math.min(lastFrame, Math.max(0, Math.round(time * fps)));
  const add = (frame, extra) => picks.push(Object.assign({ frame, time: frame / fps }, extra));
  if (options.times) for (const time of numbers(options.times, "--times")) {
    if (time > total + 1e-6) throw new Error("The Time " + stamp(time) + " Is Past The End Of The Film At " + stamp(total) + ".");
    add(frameOf(time));
  }
  if (options.every) {
    const step = Number(options.every);
    if (!(step > 0)) throw new Error("--every Needs A Positive Number Of Seconds.");
    if (total / step > 400) throw new Error("That Interval Would Render More Than 400 Stills. Choose A Longer Interval.");
    for (let time = 0; time < total - 1e-6; time += step) add(frameOf(time));
  }
  if (options.strip) {
    const count = Number(options["strip-frames"] ?? 7);
    if (!Number.isInteger(count) || count < 2 || count > 60) throw new Error("--strip-frames Needs A Whole Number From 2 To 60.");
    numbers(options.strip, "--strip").forEach((time, n) => {
      const centre = frameOf(time), first = Math.max(0, Math.min(lastFrame - count + 1, centre - Math.floor(count / 2)));
      for (let i = 0; i < count && first + i <= lastFrame; i++) add(first + i, { strip: n + 1 });
    });
  }
  if (options.scenes || !picks.length) {
    let start = 0;
    for (const scene of project.scenes) { add(frameOf(start + scene.duration * 0.6)); start += scene.duration; }
  }
  const seen = new Set();
  return picks.filter(pick => { const key = pick.frame + "|" + (pick.strip || 0); if (seen.has(key)) return false; seen.add(key); return true; })
    .sort((a, b) => (a.strip || 0) - (b.strip || 0) || a.frame - b.frame);
}
// The Caption Line On Screen Or The Words Being Spoken At A Film Time.
function lineAt(project, time) {
  const out = {}, lines = project.captions ? project.captions.lines : [];
  const caption = lines.filter(line => line.at != null && time >= line.at - 1e-6 && time < line.end - 1e-6).pop();
  if (caption) out.caption = caption.text;
  const spoken = Timing.wordsBetween(project.voice, time - 0.4, time + 0.7).map(word => word.text).join(" ");
  if (spoken) out.spoken = spoken;
  else {
    const located = P.locate(project, time), voiced = located.scene.cues.filter(cue => cue.type === "Voice" && cue.text && cue.at <= located.local + 1e-6).pop();
    if (voiced) out.spoken = voiced.text;
  }
  return out;
}

// ---------------------------------------------------------------- Functions That Run Inside The Page
function pageStill(time, scale, captions) {
  const size = MotionProject.size(window.film), canvas = document.createElement("canvas");
  canvas.width = Math.round(size[0] * scale); canvas.height = Math.round(size[1] * scale);
  MotionScenes.clearProblems();
  MotionFrame.draw(canvas, window.film, time, { captions });
  window.lastStill = canvas;
  return { png: canvas.toDataURL("image/png").split(",")[1], problems: MotionScenes.problems() };
}
function pageSheetStart(layout, heading, summary) {
  const sheet = document.createElement("canvas");
  sheet.width = layout.width; sheet.height = layout.height;
  const c = sheet.getContext("2d");
  c.fillStyle = "#e8edf0"; c.fillRect(0, 0, sheet.width, sheet.height);
  c.fillStyle = "#14242b"; c.textBaseline = "middle";
  c.font = "700 26px Arial, sans-serif"; c.fillText(heading, layout.pad, layout.pad + 16);
  c.font = "400 17px Arial, sans-serif"; c.fillStyle = "#3d5158"; c.fillText(summary, layout.pad, layout.pad + 46);
  window.sheet = sheet; window.sheetLayout = layout;
  return true;
}
function pageSheetAdd(index, heading, detail, line) {
  const layout = window.sheetLayout, c = window.sheet.getContext("2d"), column = index % layout.columns, row = Math.floor(index / layout.columns);
  const x = layout.pad + column * (layout.cellWidth + layout.pad), y = layout.top + row * (layout.cellHeight + layout.labelHeight + layout.pad);
  c.imageSmoothingQuality = "high";
  c.drawImage(window.lastStill, x, y, layout.cellWidth, layout.cellHeight);
  c.strokeStyle = "#b9c4c9"; c.lineWidth = 1; c.strokeRect(x + 0.5, y + 0.5, layout.cellWidth - 1, layout.cellHeight - 1);
  const clip = (text, font) => {
    c.font = font;
    if (c.measureText(text).width <= layout.cellWidth) return text;
    let cut = text;
    while (cut.length > 1 && c.measureText(cut + "…").width > layout.cellWidth) cut = cut.slice(0, -1);
    return cut.trimEnd() + "…";
  };
  c.textBaseline = "top"; c.fillStyle = "#14242b";
  c.fillText(clip(heading, "700 15px Arial, sans-serif"), x, y + layout.cellHeight + 7);
  c.fillStyle = "#3d5158";
  c.fillText(clip(detail, "400 13px Arial, sans-serif"), x, y + layout.cellHeight + 27);
  if (line) {
    c.font = "400 13px Arial, sans-serif"; c.fillStyle = "#14242b";
    const words = line.split(/\s+/), rows = [];
    let current = "";
    for (const word of words) {
      if (current && c.measureText(current + " " + word).width > layout.cellWidth) { rows.push(current); current = word; } else current += (current ? " " : "") + word;
    }
    if (current) rows.push(current);
    rows.slice(0, 2).forEach((text, i) => c.fillText(i === 1 && rows.length > 2 ? clip(text + " …", c.font) : clip(text, c.font), x, y + layout.cellHeight + 46 + i * 17));
  }
  return true;
}
function pageSheetEnd() { return window.sheet.toDataURL("image/png").split(",")[1]; }

function boardPage(info, stills) {
  const figures = stills.map(still => "<figure" + (still.strip ? " class=\"strip\"" : "") + "><img src=\"" + escape(still.file) + "\" alt=\"Still At " + stamp(still.time) + "\" loading=\"lazy\">" +
    "<figcaption><strong>" + stamp(still.time) + " · Frame " + still.frame + "</strong><span>Scene " + still.scene + " · " + escape(still.label) + (still.strip ? " · Strip " + still.strip : "") + "</span>" +
    (still.caption ? "<p><em>Caption</em> " + escape(still.caption) + "</p>" : still.spoken ? "<p><em>Spoken</em> " + escape(still.spoken) + "</p>" : "") + "</figcaption></figure>").join("\n");
  return "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n<title>" + escape(info.title) + " | Still Board</title>\n<style>\n" +
    "body{margin:0;font:15px/1.45 Arial,sans-serif;color:#14242b;background:#e8edf0}header{background:#101c22;color:#fff;padding:18px 24px}h1{margin:0 0 4px;font-size:22px}header p{margin:2px 0;color:#c5d2d6;font-size:14px}" +
    ".flag{display:inline-block;background:#ffe45c;color:#14242b;font-weight:700;padding:2px 8px;border-radius:4px;margin-right:6px}" +
    "main{display:grid;grid-template-columns:repeat(auto-fill,minmax(" + info.column + "px,1fr));gap:16px;padding:16px 24px}figure{margin:0;background:#fff;border:1px solid #d3dbdf;border-radius:8px;overflow:hidden}" +
    "figure.strip{border-color:#3d8e62}img{display:block;width:100%;height:auto;background:#243039}figcaption{padding:9px 11px 11px}figcaption strong,figcaption span{display:block}figcaption span{color:#3d5158;font-size:13px}" +
    "figcaption p{margin:6px 0 0;font-size:14px}em{font-style:normal;font-weight:700;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:#1c754c;margin-right:4px}\n</style>\n</head>\n<body>\n<header><h1>" + escape(info.title) + "</h1>" +
    "<p>" + escape(info.summary) + "</p><p>" + info.flags.map(flag => "<span class=\"flag\">" + escape(flag) + "</span>").join("") + "These Are Still Images For Review. No Video Has Been Exported.</p></header>\n<main>\n" + figures + "\n</main>\n</body>\n</html>\n";
}

async function main() {
  const { values: options, positionals } = parseArgs({ allowPositionals: true, options: {
    browser: { type: "string" }, times: { type: "string" }, every: { type: "string" }, scenes: { type: "boolean" }, strip: { type: "string" }, "strip-frames": { type: "string" },
    "no-captions": { type: "boolean" }, silent: { type: "boolean" }, half: { type: "boolean" }, columns: { type: "string" }, overwrite: { type: "boolean" }, help: { type: "boolean" } } });
  if (options.help) { console.log(usage); return; }
  if (positionals.length !== 2) throw new Error(usage);
  Film.guardOutput(positionals[1], "The Stills");
  const film = Film.loadFilm(positionals[0]), project = film.project, target = path.resolve(positionals[1]), executable = Browser.browserPath(options.browser);
  if (fs.existsSync(target)) {
    const present = fs.readdirSync(target);
    if (present.length && !options.overwrite) throw new Error("Choose A New Output Folder, Or Add --overwrite To Replace The Stills In This One.");
    if (present.some(name => !written(name))) throw new Error("The Output Folder Holds Files This Tool Did Not Write. Choose Another Folder.");
    for (const name of present) fs.rmSync(path.join(target, name));
  }
  const picks = chooseTimes(project, options), size = P.size(project), scale = options.half ? 0.5 : 1, captions = !(options["no-captions"] || options.silent);
  if (picks.length > 400) throw new Error("That Selection Would Render More Than 400 Stills. Choose Fewer Times.");
  const long = Math.max(size[0], size[1]), thumb = Math.min(1, 480 / long), cellWidth = Math.round(size[0] * thumb), cellHeight = Math.round(size[1] * thumb);
  const columns = Math.max(1, Math.min(picks.length, Number(options.columns) || (size[0] >= size[1] ? 3 : 5))), rows = Math.ceil(picks.length / columns);
  const layout = { columns, cellWidth, cellHeight, labelHeight: options.silent ? 50 : 86, pad: 18, top: 86 };
  layout.width = layout.pad + columns * (cellWidth + layout.pad); layout.height = layout.top + rows * (cellHeight + layout.labelHeight + layout.pad);
  if (layout.height > 16000 || layout.width > 16000) throw new Error("The Contact Sheet Would Be Too Large. Choose Fewer Stills Or More Columns.");
  const flags = [];
  if (P.standIn(project)) flags.push("Stand-In Voice Timing");
  if (project.narration === "None") flags.push("No Narration Declared");
  if (options.silent) flags.push("Silent Review");
  else if (!captions) flags.push("Captions Hidden");
  if (options.half) flags.push("Half Size");
  const summary = project.aspect + " " + size[0] + " × " + size[1] + " · " + project.fps + " FPS · " + stamp(P.duration(project)) + " · " + project.scenes.length + " Scene" + (project.scenes.length === 1 ? "" : "s");
  fs.mkdirSync(target, { recursive: true });
  const page = await Browser.openFilmPage(executable, film), stills = [], problems = new Map();
  try {
    await page.call(pageSheetStart, layout, project.title + " | Still Board", summary + (flags.length ? " · " + flags.join(" · ") : ""));
    for (let i = 0; i < picks.length; i++) {
      const pick = picks[i], located = P.locate(project, pick.time), scene = located.scene;
      const result = await page.call(pageStill, pick.time, scale, captions);
      for (const problem of result.problems) problems.set(problem.scene + "|" + problem.message, problem);
      const file = "still-" + String(i + 1).padStart(3, "0") + "-" + pick.time.toFixed(2) + "s.png";
      fs.writeFileSync(path.join(target, file), Buffer.from(result.png, "base64"));
      const still = { file, time: Math.round(pick.time * 1000) / 1000, frame: pick.frame, scene: located.index + 1, label: scene.mode === "Code Scene" ? scene.draw : scene.title || scene.mode };
      if (pick.strip) still.strip = pick.strip;
      if (!options.silent) Object.assign(still, lineAt(project, pick.time));
      stills.push(still);
      await page.call(pageSheetAdd, i, stamp(still.time) + " · Frame " + still.frame + (still.strip ? " · Strip " + still.strip : ""), "Scene " + still.scene + " · " + still.label,
        still.caption ? "Caption: " + still.caption : still.spoken ? "Spoken: " + still.spoken : "");
    }
    fs.writeFileSync(path.join(target, "contact-sheet.png"), Buffer.from(await page.call(pageSheetEnd), "base64"));
  } finally { await page.close(); }
  fs.writeFileSync(path.join(target, "board.html"), boardPage({ title: project.title, summary, flags, column: Math.max(180, Math.round(cellWidth * 0.8)) }, stills));
  fs.writeFileSync(path.join(target, "stills.json"), JSON.stringify({ title: project.title, storyboard: path.basename(film.file), size, fps: project.fps, duration: P.duration(project),
    scale, captionsShown: captions, silent: Boolean(options.silent), standInVoice: P.standIn(project), narration: project.narration || "Voice", stills, problems: [...problems.values()] }, null, 2) + "\n");
  console.log("Rendered " + stills.length + " Still" + (stills.length === 1 ? "" : "s") + (options.half ? " At Half Size" : " At Full Size") + (captions ? "" : " With Captions Hidden") + ". No Video Was Written.");
  console.log("Board: " + path.join(target, "board.html"));
  console.log("Contact Sheet: " + path.join(target, "contact-sheet.png"));
  if (flags.includes("Stand-In Voice Timing")) console.log("The Storyboard Uses Stand-In Voice Timing. It Is Not Ready For Export. Retime It When The Recording Exists.");
  if (project.narration === "None") console.log("The Storyboard Declares No Narration. Its Timings Are The Author's Own.");
  if (problems.size) {
    for (const problem of problems.values()) console.error("Scene " + problem.scene + ": " + problem.message);
    throw new Error(problems.size + " Scene Problem" + (problems.size === 1 ? "" : "s") + " Found While Drawing. The Stills Show An Error Card Where A Scene Failed.");
  }
}
module.exports = { chooseTimes, lineAt };
if (require.main === module) main().catch(error => { console.error(error.message); process.exitCode = 1; });
