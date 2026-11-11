// Offline checks for the icon library. Run with: node --test art/
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import vm from "node:vm";
import { icon, hydrate, icons, motions, groups } from "./icons.js";
import { loadSource, render, stale } from "./build.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const read = path => readFileSync(join(here, path), "utf8").replace(/\r\n/g, "\n");
const names = Object.keys(icons);
const css = read("icons.css");
const catalog = JSON.parse(read("catalog.json"));

const ORIGINAL = ["anchor-pin", "audience-retention", "beat-marker", "captions", "clip-handle", "comment-thread", "community-group", "crossfade", "curved-return", "cutaway", "detail-bracket", "elbow-arrow", "feature-zoom", "headline-card", "headphone-check", "keyboard-shortcut", "keyframe-pair", "loop-region", "lower-third", "measurement-span", "music-bed", "notification-bell", "peak-meter", "pinned-reply", "pointer-click", "profile-badge", "ripple-delete", "room-tone", "safe-margins", "save-bookmark", "screen-share", "settings-dial", "share-link", "slider-control", "speaker-label", "split-clip", "spotlight-beam", "step-ladder", "stereo-balance", "text-baseline", "touch-gesture", "track-stack", "transcript-match", "version-history", "vertical-crop", "voice-track", "waypoint-route", "word-highlight"];
const OVERLAYS = ["beat-bars", "focus-lock", "path-trace", "swipe-cue", "tap-ripple", "word-underline"];

function titleCase(sentence) {
  return /\.$/.test(sentence) && !sentence.includes("!") && sentence.split(/[\s-]+/).every(word => {
    const first = word.replace(/^[^A-Za-z0-9]+/, "")[0];
    return first === undefined || first === first.toUpperCase();
  });
}

function wellFormed(markup) {
  const stack = [];
  for (const [, close, tag, selfClose] of markup.matchAll(/<(\/?)([a-zA-Z]+)[^<>]*?(\/?)>/g)) {
    if (selfClose) continue;
    if (close) {
      if (stack.pop() !== tag) return false;
    } else stack.push(tag);
  }
  return stack.length === 0 && !/<[^>]*</.test(markup);
}

test("The Library Holds At Least 96 Icons And Keeps Every Original Name", () => {
  assert.ok(names.length >= 96, "Found " + names.length);
  for (const name of ORIGINAL) assert.ok(name in icons, name);
});

test("An Unknown Name Throws", () => {
  assert.throws(() => icon("no-such-icon"), RangeError);
  assert.throws(() => icon("toString"), RangeError);
  assert.throws(() => icon(undefined), RangeError);
});

test("Icons Are Decorative By Default And Named With A Label", () => {
  const plain = icon("notification-bell");
  assert.match(plain, /aria-hidden="true"/);
  assert.match(plain, /focusable="false"/);
  assert.doesNotMatch(plain, /role="img"/);
  const named = icon("notification-bell", { label: 'Alerts & "News" <3' });
  assert.match(named, /role="img"/);
  assert.match(named, /aria-label="Alerts &amp; &quot;News&quot; &lt;3"/);
  assert.doesNotMatch(named, /aria-hidden/);
  assert.ok(wellFormed(named));
});

test("The Size, Stroke, And Class Options Shape The Markup", () => {
  assert.match(icon("captions"), /width="24" height="24"/);
  assert.match(icon("captions", { size: 40 }), /width="40" height="40"/);
  assert.match(icon("captions", { size: "1.5em" }), /width="1.5em" height="1.5em"/);
  assert.match(icon("captions"), /stroke-width="1.5"/);
  assert.match(icon("captions", { strokeWidth: 2 }), /stroke-width="2"/);
  assert.match(icon("captions", { class: "big muted" }), /class="sck-icon sck-captions big muted"/);
  assert.match(icon("captions", { class: ["a", "b"] }), /class="sck-icon sck-captions a b"/);
  assert.throws(() => icon("captions", { size: -1 }), TypeError);
  assert.throws(() => icon("captions", { size: '24" onload="x' }), TypeError);
  assert.throws(() => icon("captions", { class: 'x" onload="y' }), TypeError);
});

test("Hydrate Fills Every Element Carrying A Data Icon Attribute", () => {
  const element = attributes => ({
    innerHTML: "",
    getAttribute: key => (key in attributes ? attributes[key] : null)
  });
  const first = element({ "data-icon": "save-bookmark" });
  const second = element({ "data-icon": "trash-bin", "data-icon-size": "32", "data-icon-label": "Delete", "data-icon-class": "danger", "data-icon-stroke": "2" });
  const asked = [];
  const stub = { querySelectorAll: selector => (asked.push(selector), [first, second]) };
  assert.equal(hydrate(stub), 2);
  assert.deepEqual(asked, ["[data-icon]"]);
  assert.equal(first.innerHTML, icon("save-bookmark"));
  assert.equal(second.innerHTML, icon("trash-bin", { size: "32", label: "Delete", class: "danger", strokeWidth: "2" }));
  assert.throws(() => hydrate({ querySelectorAll: () => [element({ "data-icon": "missing" })] }), RangeError);
  assert.throws(() => hydrate({}), TypeError);
  assert.throws(() => hydrate(), TypeError, "No Document Exists In Node");
});

test("Every Icon Has Markup, A Motion Sentence, And A Motion Rule", () => {
  assert.deepEqual(Object.keys(motions), names);
  for (const name of names) {
    const markup = icon(name);
    assert.ok(wellFormed(markup), name + " Markup");
    assert.match(markup, /viewBox="0 0 24 24"/);
    assert.match(markup, /stroke="currentColor"/);
    assert.doesNotMatch(icons[name], /fill=|stroke=|style=|#[0-9a-fA-F]{3}/, name + " Carries Paint");
    assert.ok(titleCase(motions[name]), name + " Motion Sentence: " + motions[name]);
    const parts = [...icons[name].matchAll(/class="k-([a-z0-9]+)/g)].map(match => match[1]);
    const moving = parts.filter(key => css.includes(".sck-" + name + " .k-" + key + ",") && css.includes("@keyframes sck-" + name + "-" + key + "{"));
    assert.ok(moving.length > 0, name + " Has No Motion Rule");
  }
});

test("Every Motion Rule Targets A Real Part And Plays Once", () => {
  const rules = [...css.matchAll(/\) \.sck-([a-z0-9-]+) \.k-([a-z0-9]+),/g)];
  assert.ok(rules.length >= names.length);
  for (const [, name, key] of rules) {
    assert.ok(name in icons, name);
    assert.ok(icons[name].includes('class="k-' + key), name + " " + key);
  }
  assert.doesNotMatch(css, /infinite/);
});

test("Motion Runs Only Inside The Reduced Motion Guard", () => {
  const guard = css.indexOf("@media (prefers-reduced-motion: no-preference){");
  assert.ok(guard > 0);
  assert.equal(css.slice(0, guard).includes("animation"), false);
  assert.equal(css.slice(0, guard).includes("@keyframes"), false);
  assert.equal(css.trimEnd().endsWith("}"), true);
});

test("No Two Icons Share The Same Motion", async () => {
  const source = await loadSource();
  const seen = new Set(source.icons.map(item => JSON.stringify(Object.values(item.anim))));
  assert.equal(seen.size, source.icons.length);
});

test("Groups List Every Icon Once In Display Order", () => {
  const listed = groups.flatMap(group => group.icons);
  assert.deepEqual(listed, names);
  assert.equal(new Set(listed).size, listed.length);
  assert.ok(groups.length >= 12);
  for (const name of ["Timeline", "Sound", "Text", "Product", "Social", "Callouts", "Interface", "Files", "Devices", "People", "Commerce", "Status"]) {
    assert.ok(groups.some(group => group.name === name), name);
  }
  assert.ok(Object.isFrozen(icons) && Object.isFrozen(motions) && Object.isFrozen(groups));
});

test("The Catalog Matches The Files On Disk", () => {
  const iconFiles = readdirSync(join(here, "icons")).sort();
  assert.deepEqual(iconFiles, names.map(name => name + ".svg").sort());
  const motionFiles = readdirSync(join(here, "motion")).sort();
  assert.deepEqual(motionFiles, OVERLAYS.map(name => name + ".svg"));
  const listed = catalog.assets.map(asset => asset.file).sort();
  assert.deepEqual(listed, [...iconFiles.map(file => "icons/" + file), ...motionFiles.map(file => "motion/" + file)].sort());
  for (const asset of catalog.assets) {
    assert.ok(existsSync(join(here, asset.file)), asset.file);
    assert.ok(titleCase(asset.usage), asset.usage);
    assert.equal(asset.animated, asset.file.startsWith("motion/"));
    const file = read(asset.file);
    assert.ok(file.includes("<title id=\"title\">" + asset.title + "</title>"), asset.file + " Title");
    assert.ok(file.includes("<desc id=\"desc\">" + asset.usage + "</desc>"), asset.file + " Description");
    assert.ok(wellFormed(file.replace(/<style>[\s\S]*?<\/style>/, "")), asset.file);
    if (!asset.animated) {
      assert.equal(asset.motion, motions[asset.name]);
      assert.match(file, /viewBox="0 0 24 24"/);
      assert.doesNotMatch(file, /<style|animation/);
    }
  }
  assert.deepEqual(catalog.groups, [...groups.map(group => group.name), "Motion"]);
});

test("Icon Geometry Stays Inside The 24 Unit Grid", () => {
  for (const name of names) {
    for (const [, attribute, value] of icons[name].matchAll(/\b(x|y|cx|cy)="([\d.]+)"/g)) {
      assert.ok(Number(value) >= 0 && Number(value) <= 24, name + " " + attribute + " " + value);
    }
    for (const [, x, y] of icons[name].matchAll(/M(-?[\d.]+)[ ,]?(-?[\d.]+)/g)) {
      assert.ok(Number(x) >= 1 && Number(x) <= 23 && Number(y) >= 1 && Number(y) <= 23, name + " Starts A Path Outside The Grid");
    }
  }
});

test("The Generated Files Are Current", async () => {
  assert.deepEqual(stale(render(await loadSource())), []);
  const run = spawnSync(process.execPath, [join(here, "build.mjs"), "--check"], { encoding: "utf8" });
  assert.equal(run.status, 0, run.stderr);
});

test("The Global Build Offers The Same API To Pages Opened From Disk", () => {
  const scope = {};
  vm.runInNewContext(read("icons.global.js"), { globalThis: scope });
  const kit = scope.SocialCutIcons;
  assert.deepEqual(Object.keys(kit.icons), names);
  assert.equal(kit.icon("gift-box", { size: 32, label: "Bonus" }), icon("gift-box", { size: 32, label: "Bonus" }));
  assert.equal(kit.catalog.assets.length, catalog.assets.length);
  assert.throws(() => kit.icon("nope"));
});

test("The Type Declarations Name Every Icon", () => {
  const types = read("icons.d.ts");
  for (const name of names) assert.ok(types.includes('| "' + name + '"'), name);
  for (const word of ["icon(", "hydrate(", "icons:", "motions:", "groups:"]) assert.ok(types.includes(word), word);
});

test("The Guide States The Current Counts And Follows The House Style", () => {
  const guide = read("README.md");
  assert.ok(guide.includes("Library Of " + names.length + " Animated Line Icons"), "Icon Count In README.md");
  assert.equal(groups.length, 12, "README.md Says Twelve Groups");
  const prose = guide.replace(/```[\s\S]*?```/g, "").replace(/`[^`]*`/g, "").replace(/\]\([^)]*\)/g, "]");
  assert.doesNotMatch(prose, /!/);
  const lower = prose.match(/(?<![A-Za-z’'])[a-z][a-z’']*/g) || [];
  assert.deepEqual(lower, [], "Lowercase Words In Prose");
});

test("The Gallery Loads Only Local Files", () => {
  const page = read("index.html");
  for (const file of ["icons.css", "gallery.css", "icons.global.js", "gallery.js"]) assert.ok(page.includes('"' + file + '"'), file);
  for (const file of ["index.html", "gallery.js", "gallery.css", "icons.css", "icons.js", "icons.global.js"]) {
    assert.doesNotMatch(read(file).replace(/http:\/\/www\.w3\.org\/2000\/svg/g, ""), /https?:\/\/|@import|url\(/, file);
  }
});
