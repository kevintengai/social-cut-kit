"use strict";
const fs = require("node:fs"), path = require("node:path"), os = require("node:os");
const { pathToFileURL } = require("node:url"), { spawn } = require("node:child_process"), assert = require("node:assert/strict");
const root = path.resolve(__dirname, "..");
const browser = process.argv[2];
if (!browser) throw new Error("Supply The Path To A Chromium Browser Executable.");
const profile = fs.mkdtempSync(path.join(os.tmpdir(), "motion-studio-check-"));
const child = spawn(browser, ["--headless=new", "--no-first-run", "--disable-default-apps", "--disable-sync", "--disable-background-networking",
  "--disable-gpu", "--autoplay-policy=no-user-gesture-required", "--remote-debugging-pipe", "--user-data-dir=" + profile, "about:blank"],
  {windowsHide: true, stdio: ["ignore", "ignore", "ignore", "pipe", "pipe"]});
let id = 0, remaining = Buffer.alloc(0), sessionId, seenError;
const pending = new Map();
child.stdio[4].on("data", bytes => {
  remaining = Buffer.concat([remaining, bytes]); let stop;
  while ((stop = remaining.indexOf(0)) >= 0) {
    const packet = JSON.parse(remaining.subarray(0, stop)); remaining = remaining.subarray(stop + 1);
    if (packet.method === "Runtime.exceptionThrown") seenError = packet.params.exceptionDetails;
    const entry = pending.get(packet.id); if (!entry) continue;
    pending.delete(packet.id); clearTimeout(entry.timer);
    packet.error ? entry.reject(new Error(packet.error.message)) : entry.resolve(packet.result);
  }
});
function request(method, params = {}, session = sessionId) {
  const key = ++id;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { pending.delete(key); reject(new Error("Browser Check Timed Out At " + method)); }, 15000);
    pending.set(key, { resolve, reject, timer });
    child.stdio[3].write(JSON.stringify({ id: key, method, params, sessionId: session }) + "\0");
  });
}
async function evaluate(expression, awaitPromise = false) {
  const out = await request("Runtime.evaluate", {expression, awaitPromise, returnByValue: true, userGesture: true});
  if (out.exceptionDetails) throw new Error(out.exceptionDetails.exception?.description || out.exceptionDetails.text);
  return out.result.value;
}
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));
async function waitFor(expression) {
  for (let i = 0; i < 160; i++) { if (await evaluate(expression)) return; await wait(60); }
  throw new Error("Browser Condition Timed Out: " + expression);
}
async function run() {
  const {targetId} = await request("Target.createTarget", {url: "about:blank"});
  sessionId = (await request("Target.attachToTarget", {targetId, flatten: true})).sessionId;
  await request("Page.enable"); await request("Runtime.enable");
  await request("Page.navigate", {url: pathToFileURL(path.join(root, "studio/index.html")).href});
  await waitFor("document.querySelectorAll('.scene').length === 3");
  assert.equal(await evaluate("document.querySelector('#export').disabled"), true);
  const png = await evaluate("(" + function() {
    const demo = MotionProject.demo(), frame = document.createElement("canvas"), sheet = document.createElement("canvas");
    frame.width = 360; frame.height = 640; sheet.width = 1112; sheet.height = 656;
    const c = sheet.getContext("2d"); c.fillStyle = "#e8edf0"; c.fillRect(0, 0, sheet.width, sheet.height);
    [1.9, 6.9, 11.2].forEach((time, i) => { MotionFrame.draw(frame, demo, time); c.drawImage(frame, 8 + i * 368, 8); });
    return sheet.toDataURL("image/png").split(",")[1];
  }.toString() + ")()");
  if (process.argv.includes("--stills")) fs.writeFileSync(path.join(root, "assets/storyboard-stills.png"), Buffer.from(png, "base64"));
  const adapterSource = require("../adapter/prepare-remotion.cjs").painterSource();
  const parity = await evaluate("(" + async function(source) {
    const url = URL.createObjectURL(new Blob([source], {type: "text/javascript"}));
    const {MotionFrame: externalPainter} = await import(url); URL.revokeObjectURL(url);
    const board = MotionProject.demo(), a = document.createElement("canvas"), b = document.createElement("canvas");
    for (const aspect of Object.keys(MotionProject.aspects)) {
      const [w, h] = MotionProject.aspects[aspect];
      a.width = b.width = w / 4; a.height = b.height = h / 4; board.aspect = aspect;
      for (const frame of [16, 58, 136, 203, 294, 377]) {
        MotionFrame.draw(a, board, frame / board.fps); externalPainter.draw(b, board, frame / board.fps);
        if (a.toDataURL() !== b.toDataURL()) return false;
      }
    }
    return true;
  }.toString() + ")(" + JSON.stringify(adapterSource) + ")", true);
  assert.equal(parity, true);
  await evaluate("(" + function() {
    window.changeValue = (id, value, eventName = "change") => {
      const input = document.getElementById(id); input.value = value; input.dispatchEvent(new Event(eventName, {bubbles: true}));
    };
    for (let i = 0; i < 3; i++) { document.querySelectorAll(".scene")[i].click(); changeValue("duration", "1.2"); }
    changeValue("shape", "Crystal"); changeValue("aspect", "Landscape");
    document.querySelectorAll(".scene")[0].click();
    const input = document.querySelector('#cues input[type=file]'), transfer = new DataTransfer();
    const wav = MotionSound.wav(MotionSound.make("Glass Point", 24000), 24000);
    transfer.items.add(new File([wav], "Recorded-Line.wav", {type: "audio/wav"}));
    input.files = transfer.files; input.dispatchEvent(new Event("change"));
  }.toString() + ")()");
  await waitFor("document.querySelector('#cues').innerText.includes('Recorded Audio Embedded.')");
  await evaluate("document.getElementById('review').click()");
  await waitFor("document.getElementById('play').textContent === 'Pause'");
  await waitFor("!document.getElementById('approve').disabled");
  assert.equal(await evaluate("document.getElementById('approve').checked"), false);
  assert.equal(await evaluate("document.getElementById('export').disabled"), true);
  await evaluate("changeValue('title', 'Updated Headline', 'input')");
  assert.equal(await evaluate("document.getElementById('approve').disabled"), true);
  await evaluate("document.getElementById('addScene').click(); document.getElementById('duplicate').click()");
  assert.equal(await evaluate("document.querySelectorAll('.scene').length"), 5);
  await evaluate("document.getElementById('up').click(); document.getElementById('remove').click()");
  assert.equal(await evaluate("document.querySelectorAll('.scene').length"), 4);
  await evaluate("(" + function() {
    const old = HTMLAnchorElement.prototype.click;
    HTMLAnchorElement.prototype.click = function() {
      if (this.download.endsWith(".json")) window.saved = fetch(this.href).then(r => r.json());
      else old.call(this);
    };
    document.getElementById("save").click();
    HTMLAnchorElement.prototype.click = old;
  }.toString() + ")()");
  const saved = await evaluate("window.saved", true);
  assert.equal(saved.scenes.length, 4); assert(saved.scenes[0].cues.some(c => c.clip?.startsWith("data:audio/wav;base64,")));
  assert.equal(saved.scenes[2].title, "Updated Headline");
  await evaluate("(" + function(input) {
    const d = new DataTransfer(); d.items.add(new File([JSON.stringify(input)], "Restored.json", {type:"application/json"}));
    const target = document.getElementById("openFile"); target.files = d.files; target.dispatchEvent(new Event("change"));
  }.toString() + ")(" + JSON.stringify(saved) + ")");
  await waitFor("document.getElementById('status').textContent === 'Storyboard Opened.'");
  assert.equal(await evaluate("document.getElementById('export').disabled"), true);
  // Open A Code-Scene Film The Way An Owner Does: The Storyboard Together With Its Scene Module.
  const filmDir = path.join(root, "examples/an-idea-travels");
  const filmBoard = fs.readFileSync(path.join(filmDir, "storyboard.timed.json"), "utf8"), filmModule = fs.readFileSync(path.join(filmDir, "scenes/idea.js"), "utf8");
  const openFilm = (board, module) => evaluate("(" + function(board, module) {
    document.getElementById("status").textContent = "";
    const d = new DataTransfer(); d.items.add(new File([board], "storyboard.timed.json", {type: "application/json"}));
    if (module) d.items.add(new File([module], "idea.js", {type: "text/javascript"}));
    const target = document.getElementById("openFile"); target.files = d.files; target.dispatchEvent(new Event("change"));
  }.toString() + ")(" + JSON.stringify(board) + "," + JSON.stringify(module) + ")");
  await openFilm(filmBoard, "");
  await waitFor("document.getElementById('status').textContent === 'Storyboard Opened With Missing Files.'");
  assert(await evaluate("document.getElementById('filmNote').textContent.includes('scenes/idea.js')"));
  assert.equal(await evaluate("MotionScenes.problems().some(p => p.kind === 'missing')"), true);
  await openFilm(filmBoard, filmModule);
  await waitFor("document.getElementById('status').textContent === 'Storyboard Opened.'");
  assert.equal(await evaluate("document.querySelectorAll('.scene').length"), 4);
  assert(await evaluate("document.querySelector('.scene span').textContent.startsWith('Idea Seed')"));
  assert.equal(await evaluate("document.getElementById('codeFields').hidden"), false);
  assert.equal(await evaluate("document.getElementById('drawName').value"), "Idea Seed");
  assert.equal(await evaluate("document.getElementById('captionsField').hidden"), false);
  assert.equal(await evaluate("document.getElementById('export').disabled"), true);
  assert(await evaluate("document.getElementById('filmNote').textContent.includes('Stand-In')"));
  const filmSource = require("../adapter/prepare-remotion.cjs").painterSource([{name: "scenes/idea.js", source: filmModule}]);
  const film = await evaluate("(" + async function(source, board) {
    const url = URL.createObjectURL(new Blob([source], {type: "text/javascript"}));
    const {MotionFrame: externalPainter} = await import(url); URL.revokeObjectURL(url);
    const project = MotionProject.cleanProject(JSON.parse(board)), a = document.createElement("canvas"), b = document.createElement("canvas");
    a.width = b.width = 270; a.height = b.height = 480;
    const out = {same: true, twice: true, distinct: new Set(), captions: false};
    MotionScenes.clearProblems();
    for (const time of [0.4, 1.8, 3.6, 4.9, 6.4, 8.1, 9.9, 11.7]) {
      MotionFrame.draw(a, project, time); const first = a.toDataURL();
      externalPainter.draw(b, project, time); if (first !== b.toDataURL()) out.same = false;
      MotionFrame.draw(b, project, 0.1); MotionFrame.draw(b, project, time); if (first !== b.toDataURL()) out.twice = false;
      out.distinct.add(first);
      MotionFrame.draw(b, project, time, {captions: false}); if (first !== b.toDataURL()) out.captions = true;
    }
    out.distinct = out.distinct.size; out.problems = MotionScenes.problems().length;
    return out;
  }.toString() + ")(" + JSON.stringify(filmSource) + "," + JSON.stringify(filmBoard) + ")", true);
  assert.deepEqual(film, {same: true, twice: true, distinct: 8, captions: true, problems: 0});
  // Hiding Captions And Editing Parameters Both Change The Picture And Clear Any Review.
  const shot = () => evaluate("document.getElementById('frame').toDataURL()");
  await evaluate("changeValue('seek', '1.8', 'input')");
  const captioned = await shot();
  await evaluate("document.getElementById('showCaptions').click()");
  assert.notEqual(await shot(), captioned);
  await evaluate("document.getElementById('showCaptions').click()");
  assert.equal(await shot(), captioned);
  await evaluate("changeValue('params', '{\"line\": 5', 'input')");
  assert(await evaluate("document.getElementById('paramsNote').textContent.includes('JSON Object')"));
  assert.equal(await shot(), captioned);
  await evaluate("document.querySelectorAll('.scene')[3].click(); changeValue('params', '{\"people\": 12, \"block\": \"#3355aa\"}', 'input')");
  assert.equal(await evaluate("document.getElementById('paramsNote').textContent"), "");
  await evaluate("changeValue('aspect', 'Custom'); changeValue('customWidth', '1080'); changeValue('customHeight', '1350')");
  assert.equal(await evaluate("document.getElementById('frame').width + 'x' + document.getElementById('frame').height"), "768x960");
  assert.equal(await evaluate("MotionScenes.problems().length"), 0);
  assert.equal(await evaluate("document.getElementById('approve').disabled && document.getElementById('export').disabled"), true);
  assert(!seenError, JSON.stringify(seenError));
  console.log("Passed Browser Playback, Voice Import, Scene Editing, Project Round Trip, And Review Invalidation Checks. No Video Recorded.");
  console.log("Passed Code Scene Film Opening, Module Loading, Painter Parity, Caption Toggle, Parameter Editing, And Custom Frame Checks. No Video Recorded.");
}
run().catch(e => { console.error(e); process.exitCode = 1; }).finally(async () => {
  try { await request("Browser.close", {}, undefined); } catch {}
  child.kill();
  const tempDir = fs.realpathSync(os.tmpdir()), testDir = fs.realpathSync(profile);
  if (path.dirname(testDir) === tempDir && path.basename(testDir).startsWith("motion-studio-check-")) {
    try { fs.rmSync(testDir, {recursive: true, force: true, maxRetries: 5, retryDelay: 100}); } catch {}
  }
});
