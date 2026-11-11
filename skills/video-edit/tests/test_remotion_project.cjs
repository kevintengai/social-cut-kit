// Remotion Project Generation From Real Timelines. Nothing Here Installs Remotion Or Writes A Video.
const assert = require("node:assert/strict");
const {spawnSync} = require("node:child_process");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const {after, test} = require("node:test");

const SKILL = path.resolve(__dirname, "..");
const ADAPTER = path.join(SKILL, "remotion");
const Prepare = require("../remotion/prepare-remotion.cjs");
const Cut = require("../remotion/cut-plan.cjs");
const base = fs.mkdtempSync(path.join(os.tmpdir(), "cut remotion "));
after(() => fs.rmSync(base, {recursive: true, force: true}));

const json = file => JSON.parse(fs.readFileSync(file, "utf8"));
const python = [process.env.PYTHON, "python", "python3", "py"].filter(Boolean)
  .find(name => spawnSync(name, ["-c", "print(1)"], {encoding: "utf8"}).status === 0);
const bundled = path.join(SKILL, "../../examples/repair-desk/timeline.json");
const unbundled = !fs.existsSync(bundled) && "The Bundled Example Is Not Beside This Skill.";
const animated = path.join(SKILL, "../animated-video/adapter/prepare-remotion.cjs");

function tree(folder, prefix = "") {
  return fs.readdirSync(folder, {withFileTypes: true}).flatMap(entry => entry.isDirectory()
    ? tree(path.join(folder, entry.name), prefix + entry.name + "/") : [prefix + entry.name]).sort();
}
function noVideo(folder) {
  assert.deepEqual(tree(folder).filter(name => /\.(mp4|mov|m4v|webm|mkv|avi|gif)$/i.test(name)), [], "No Video File May Be Written");
}
function checkShell(project) {
  const pack = json(path.join(project, "package.json"));
  assert.deepEqual(pack.scripts, {studio: "remotion studio src/index.jsx", "render-reviewed": "node render-reviewed.cjs"});
  assert.deepEqual(pack.dependencies, Prepare.PACKAGES);
  assert.equal(pack.private, true);
  for (const [name, placed] of [["cut-plan.cjs", "src/cut-plan.cjs"], ["remotion-entry.jsx", "src/index.jsx"], ["render-reviewed.cjs", "render-reviewed.cjs"]])
    assert.deepEqual(fs.readFileSync(path.join(project, placed)), fs.readFileSync(path.join(ADAPTER, name)), placed);
  assert.ok(!fs.existsSync(path.join(project, "node_modules")), "Packages Are Installed Separately");
}

test("The Package Versions Match The Animated Video Adapter", {skip: !fs.existsSync(animated) && "The Animated Video Skill Is Not Beside This Skill."}, () => {
  const source = fs.readFileSync(animated, "utf8");
  const declared = JSON.parse(source.match(/dependencies: (\{[^}]+\})/)[1].replace(/(\{|, )(\w+):/g, '$1"$2":'));
  assert.deepEqual(Prepare.PACKAGES, declared);
});

test("The Bundled Example Becomes A Complete Standalone Project", {skip: unbundled}, () => {
  const target = path.join(base, "Repair Desk Project");
  const summary = Prepare.prepare(bundled, target);
  assert.deepEqual([summary.composition, summary.width, summary.height, summary.fps, summary.frames], ["VideoEdit", 720, 1280, 30, 240]);
  assert.deepEqual([summary.shots, summary.overlays, summary.audio_cues, summary.captions, summary.media_files], [3, 0, 1, 3, 3]);
  assert.deepEqual(tree(target), ["package.json", "public/media/01-all-jobs.png", "public/media/02-ready-job.png", "public/media/03-button-up.wav",
    "render-reviewed.cjs", "source-timeline.json", "src/cut-plan.cjs", "src/cut.json", "src/index.jsx"]);
  checkShell(target);
  noVideo(target);
  const cut = json(path.join(target, "src/cut.json")), source = json(bundled);
  assert.equal(cut.title, source.title);
  assert.deepEqual(cut.shots.map(s => [s.from, s.frames, s.file, s.kind]), [[0, 90, "media/01-all-jobs.png", "image"],
    [90, 90, "media/02-ready-job.png", "image"], [180, 60, "media/02-ready-job.png", "image"]]);
  for (const shot of cut.shots) {
    assert.deepEqual(shot.box, {left: 0, top: 0, width: 720, height: 1280});
    assert.deepEqual(shot.media, {left: 0, top: 0, width: 720, height: 1280});
    assert.equal(shot.sound, null);
  }
  assert.deepEqual(cut.audio, [{id: "audio-1", asset: "tap", file: "media/03-button-up.wav", from: 90, frames: 3, start: 0, trim: 0, gain: 0.36, fadeIn: 0, fadeOut: 0}]);
  assert.deepEqual(cut.captions.map(c => [c.from, c.frames, c.position]), [[5, 81, "bottom"], [95, 81, "bottom"], [185, 51, "bottom"]]);
  assert.deepEqual(cut.captionStyle, {font: "Arial", size: 61, color: "#FFFFFF", outline: "#101010", stroke: 4, margin: 7});
  assert.ok(cut.warnings.every(note => /^Captions Are Drawn By Chrome/.test(note)));
  // The Media Is Byte For Byte The Source, And The Timeline Copy Points At It.
  const root = path.dirname(bundled), copy = json(path.join(target, "source-timeline.json"));
  for (const [key, asset] of Object.entries(source.assets)) {
    assert.match(copy.assets[key].path, /^public\/media\//);
    assert.deepEqual(fs.readFileSync(path.join(target, copy.assets[key].path)), fs.readFileSync(path.resolve(root, asset.path)), key);
    assert.equal(copy.assets[key].kind, asset.kind);
  }
  assert.deepEqual({...copy, assets: null}, {...source, assets: null});
  // The Copy Is A Valid Timeline In Its New Home.
  const again = Prepare.build(copy, target);
  assert.deepEqual(again.plan.shots.map(s => [s.from, s.frames]), cut.shots.map(s => [s.from, s.frames]));
});

test("An Example Folder From The Editor Carries Overlays, Color, Captions, And Sound", {skip: !python && "No Python Launcher Was Found."}, () => {
  const folder = path.join(base, "First Cut");
  const made = spawnSync(python, ["-B", path.join(SKILL, "scripts/edit_video.py"), "example", folder], {encoding: "utf8"});
  assert.equal(made.status, 0, made.stderr);
  const target = path.join(base, "First Cut Project");
  const summary = Prepare.prepare(path.join(folder, "timeline.json"), target, {linkMedia: true});
  assert.deepEqual([summary.width, summary.height, summary.fps, summary.frames, summary.overlays], [360, 640, 24, 96, 1]);
  checkShell(target);
  noVideo(target);
  const cut = json(path.join(target, "src/cut.json"));
  assert.deepEqual(cut.shots.map(s => [s.from, s.frames, s.filter]), [[0, 48, null], [48, 48, "brightness(1.05) contrast(1.04) saturate(1.12)"]]);
  // 160 By 100 Art On A 360 By 640 Canvas: Cover Keeps 56 Columns, And The 1.2 Zoom Keeps 47 By 83.
  assert.deepEqual(cut.shots[0].box, {left: 0, top: 0, width: 360, height: 640});
  assert.deepEqual(cut.shots[0].media, {left: 0 - 52 * (360 / 56), top: 0, width: 160 * (360 / 56), height: 640});
  assert.deepEqual(cut.shots[1].media, {left: 0 - 65 * (360 / 47), top: 0 - 8 * (640 / 83), width: 160 * (360 / 47), height: 100 * (640 / 83)});
  assert.deepEqual(cut.overlays, [{id: "overlay-1", asset: "Second", kind: "image", file: "media/02-Second-Frame.png", from: 24, frames: 18,
    start: 0, trim: 0.499, toneMapped: true, left: 18, top: 54, width: 120, height: 76}]);
  assert.deepEqual(cut.audio.map(a => [a.file, a.from, a.frames, a.gain]), [["media/03-Stereo-Cue.wav", 0, 96, 0.7]]);
  assert.deepEqual(cut.captions.map(c => [c.from, c.frames, c.text, c.position]),
    [[6, 30, "Follow The Circle", "bottom"], [54, 30, "Now Change The Rhythm", "top"]]);
  assert.deepEqual(fs.readFileSync(path.join(target, "public/media/01-First-Frame.png")), fs.readFileSync(path.join(folder, "First Frame.png")));
});

test("Preparation Refuses An Existing Folder And Leaves Nothing Behind On Failure", {skip: unbundled}, () => {
  const taken = path.join(base, "Taken");
  fs.mkdirSync(taken);
  assert.throws(() => Prepare.prepare(bundled, taken), /Choose A New Output Directory\./);
  assert.deepEqual(fs.readdirSync(taken), []);
  const broken = path.join(base, "broken.json"), doc = json(bundled);
  for (const key of Object.keys(doc.assets)) doc.assets[key].path = path.resolve(path.dirname(bundled), doc.assets[key].path);
  doc.assets.B01.path = path.join(base, "missing.png");
  fs.writeFileSync(broken, JSON.stringify(doc));
  assert.throws(() => Prepare.prepare(broken, path.join(base, "Never")), error => error instanceof Cut.CutError && /Missing Asset/.test(error.message));
  assert.ok(!fs.existsSync(path.join(base, "Never")));
  assert.deepEqual(fs.readdirSync(base).filter(name => name.startsWith(".cut-prepare-")), []);
});

test("An HDR Source Stops Preparation Unless It Is Allowed", () => {
  const folder = path.join(base, "hdr");
  fs.mkdirSync(folder);
  fs.writeFileSync(path.join(folder, "phone.mov"), "Stand-In Bytes");
  const doc = {version: 1, title: "Phone Clip", assets: {Phone: {kind: "video", path: "phone.mov"}}, shots: [{asset: "Phone", in: 0, out: 1}]};
  const probe = () => Cut.probeSummary({format: {format_name: "mov,mp4,m4a,3gp,3g2,mj2", duration: "4"}, streams: [{codec_type: "video", codec_name: "hevc",
    width: 3840, height: 2160, pix_fmt: "yuv420p10le", color_transfer: "arib-std-b67", color_primaries: "bt2020", side_data_list: [{rotation: -90}]}]});
  assert.throws(() => Prepare.build(doc, folder, {probe}), /Asset Phone Is HLG HDR.*Deliver This Edit Through The FFmpeg Render/);
  const {plan, media} = Prepare.build(doc, folder, {probe, allowHdr: true});
  assert.equal(plan.warnings.filter(note => /HLG HDR|hevc Video|90 Degree Display Rotation/.test(note)).length, 3);
  assert.deepEqual(plan.shots[0].box, {left: 0, top: 0, width: 1080, height: 1920});
  assert.deepEqual([...media.keys()], ["public/media/01-phone.mov"]);
});

test("The Command Line Reports Usage, Warnings, And A JSON Summary", {skip: unbundled}, () => {
  const script = path.join(ADAPTER, "prepare-remotion.cjs");
  const usage = spawnSync(process.execPath, [script, bundled], {encoding: "utf8"});
  assert.equal(usage.status, 1);
  assert.match(usage.stderr, /^Usage: node remotion\/prepare-remotion\.cjs Timeline\.json NewProjectFolder/);
  assert.equal(spawnSync(process.execPath, [script, bundled, path.join(base, "Flag"), "--render"], {encoding: "utf8"}).status, 1);
  assert.ok(!fs.existsSync(path.join(base, "Flag")));
  const plain = spawnSync(process.execPath, [script, bundled, path.join(base, "Plain")], {encoding: "utf8"});
  assert.equal(plain.status, 0, plain.stderr);
  assert.match(plain.stdout, /^Warning: Captions Are Drawn By Chrome/);
  assert.match(plain.stdout, /Prepared 240 Frames At 30 FPS With 3 Shots, 0 Overlays, 1 Audio Cues, And 3 Captions\. No Video Was Written\./);
  const report = spawnSync(process.execPath, [script, bundled, path.join(base, "Report"), "--json"], {encoding: "utf8"});
  assert.equal(JSON.parse(report.stdout).frames, 240);
  const twice = spawnSync(process.execPath, [script, bundled, path.join(base, "Report")], {encoding: "utf8"});
  assert.equal(twice.status, 1);
  assert.equal(twice.stderr.trim(), "Choose A New Output Directory.");
});

test("The Render Command Needs The Owner In Person And Never Replaces A File", {skip: unbundled}, () => {
  const project = path.join(base, "Gate");
  Prepare.prepare(bundled, project);
  const run = (...args) => spawnSync(process.execPath, [path.join(project, "render-reviewed.cjs"), ...args], {cwd: project, encoding: "utf8", input: "APPROVE\n"});
  const piped = run("Approved.mp4");
  assert.equal(piped.status, 1);
  assert.match(piped.stderr, /Open An Interactive Terminal For Personal Review Confirmation\./);
  fs.writeFileSync(path.join(project, "Keep.mp4"), "Keep This");
  const existing = run("Keep.mp4");
  assert.equal(existing.status, 1);
  assert.match(existing.stderr, /Choose A New Output File\./);
  assert.equal(fs.readFileSync(path.join(project, "Keep.mp4"), "utf8"), "Keep This");
  assert.match(run("Approved.mov").stderr, /Choose An MP4 Output Filename\./);
  assert.deepEqual(tree(project).filter(name => /\.(mp4|mov)$/.test(name)), ["Keep.mp4"]);
  const source = fs.readFileSync(path.join(ADAPTER, "render-reviewed.cjs"), "utf8");
  assert.match(source, /Type APPROVE To Export/);
  assert.match(source, /reply\.trim\(\) !== "APPROVE"/);
  assert.ok(source.indexOf("isTTY") < source.indexOf("spawnSync(process.execPath"), "The Gate Comes Before The Render");
});

test("The Remotion Entry Is Thin Glue Over The Plan Module", () => {
  const entry = fs.readFileSync(path.join(ADAPTER, "remotion-entry.jsx"), "utf8");
  const imports = [...entry.matchAll(/from "([^"]+)"/g)].map(match => match[1]);
  assert.deepEqual(imports, ["react", "remotion", "./cut.json", "./cut-plan.cjs"]);
  for (const name of imports.filter(name => !name.startsWith("."))) assert.ok(name in Prepare.PACKAGES, name);
  assert.match(entry, /<Composition id="VideoEdit" component=\{Edit\} width=\{cut\.width\} height=\{cut\.height\} fps=\{cut\.fps\} durationInFrames=\{cut\.frames\}/);
  assert.match(entry, /levelAt\(row\.sound, frame, row\.frames, cut\.fps\)/);
  assert.match(entry, /captionLayout\(cut\.captionStyle, cut\.width, cut\.height\)/);
  assert.ok(entry.split("\n").length < 80, "Keep The Glue Short");
  assert.doesNotMatch(entry, /Math\.|useCurrentFrame|interpolate/, "Timing And Layout Belong In cut-plan.cjs");
});
