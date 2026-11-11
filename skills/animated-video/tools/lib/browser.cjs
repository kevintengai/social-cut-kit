// A Small Headless Browser Driver For The Still And Motion Tools. It Talks To A Local Chromium Over A Pipe,
// Loads The Painter Into A Blank Page, And Never Records Or Encodes Video.
"use strict";
const fs = require("node:fs"), path = require("node:path"), os = require("node:os");
const { spawn } = require("node:child_process");
const Film = require("./film.cjs");

// Find The Browser Path From A Tool's Options Or The MOTION_STUDIO_BROWSER Environment Variable.
function browserPath(given) {
  const chosen = given || process.env.MOTION_STUDIO_BROWSER;
  if (!chosen) throw new Error("Supply The Path To A Chromium Browser Executable With --browser.");
  if (!fs.existsSync(chosen)) throw new Error("No Browser Was Found At " + chosen);
  return chosen;
}
async function launch(executable) {
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), "motion-studio-tool-"));
  const child = spawn(executable, ["--headless=new", "--no-first-run", "--disable-default-apps", "--disable-sync", "--disable-background-networking", "--disable-gpu",
    "--hide-scrollbars", "--force-device-scale-factor=1", "--remote-debugging-pipe", "--user-data-dir=" + profile, "about:blank"],
  { windowsHide: true, stdio: ["ignore", "ignore", "ignore", "pipe", "pipe"] });
  let id = 0, remaining = Buffer.alloc(0), sessionId, closed = false;
  const pending = new Map();
  const failAll = error => { for (const entry of pending.values()) { clearTimeout(entry.timer); entry.reject(error); } pending.clear(); };
  child.on("error", error => failAll(new Error("The Browser Could Not Start: " + error.message)));
  child.on("exit", () => { if (!closed) failAll(new Error("The Browser Closed Before The Work Finished.")); });
  child.stdio[4].on("data", bytes => {
    remaining = Buffer.concat([remaining, bytes]);
    let stop;
    while ((stop = remaining.indexOf(0)) >= 0) {
      const packet = JSON.parse(remaining.subarray(0, stop));
      remaining = remaining.subarray(stop + 1);
      const entry = pending.get(packet.id);
      if (!entry) continue;
      pending.delete(packet.id); clearTimeout(entry.timer);
      packet.error ? entry.reject(new Error(packet.error.message)) : entry.resolve(packet.result);
    }
  });
  function request(method, params = {}, session = sessionId, seconds = 120) {
    const key = ++id;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => { pending.delete(key); reject(new Error("The Browser Did Not Answer In Time At " + method + ".")); }, seconds * 1000);
      pending.set(key, { resolve, reject, timer });
      child.stdio[3].write(JSON.stringify({ id: key, method, params, sessionId: session }) + "\0");
    });
  }
  async function evaluate(expression, awaitPromise = false) {
    const out = await request("Runtime.evaluate", { expression, awaitPromise, returnByValue: true });
    if (out.exceptionDetails) throw new Error(out.exceptionDetails.exception?.description || out.exceptionDetails.text);
    return out.result.value;
  }
  // Call A Function Written In This File Inside The Page, With JSON Arguments.
  const call = (fn, ...args) => evaluate("(" + fn.toString() + ")(" + args.map(arg => JSON.stringify(arg)).join(",") + ")", true);
  async function close() {
    closed = true;
    try { await request("Browser.close", {}, undefined, 5); } catch {}
    child.kill();
    try {
      const temp = fs.realpathSync(os.tmpdir()), dir = fs.realpathSync(profile);
      if (path.dirname(dir) === temp && path.basename(dir).startsWith("motion-studio-tool-")) fs.rmSync(dir, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
    } catch {}
  }
  try {
    const { targetId } = await request("Target.createTarget", { url: "about:blank" }, undefined);
    sessionId = (await request("Target.attachToTarget", { targetId, flatten: true }, undefined)).sessionId;
    await request("Page.enable"); await request("Runtime.enable");
  } catch (error) { await close(); throw error; }
  return { request, evaluate, call, close };
}
// Open A Blank Page With The Painter, The Kit's Parts, And A Film's Scene Modules Loaded, And The Storyboard In window.film.
async function openFilmPage(executable, film) {
  const page = await launch(executable);
  try {
    for (const item of Film.studioSources()) await page.evaluate(item.source + "\n//# sourceURL=" + item.name);
    for (const item of Film.partSources()) await page.evaluate("(function () {\n" + item.source + "\n})();\n//# sourceURL=" + item.name);
    await page.evaluate("MotionScenes.seal()");
    for (const item of film.modules) await page.evaluate("(function () {\n" + item.source + "\n})();\n//# sourceURL=" + item.name.replace(/\s/g, "-"));
    await page.evaluate("window.film = MotionProject.cleanProject(" + JSON.stringify(film.raw) + "); true");
  } catch (error) { await page.close(); throw error; }
  return page;
}

module.exports = { browserPath, launch, openFilmPage };
