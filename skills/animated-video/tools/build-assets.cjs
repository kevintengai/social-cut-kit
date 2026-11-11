"use strict";
const fs = require("node:fs");
const path = require("node:path");
const { make, wav, lengths } = require("../studio/sound.js");
const { paths } = require("../studio/marks.js");
const root = path.resolve(__dirname, "../assets");
const slug = s => s.toLowerCase().replaceAll(" ", "-");
for (const dir of ["sounds", "marks", "overlays"]) fs.mkdirSync(path.join(root, dir), { recursive: true });
for (const name of Object.keys(lengths)) fs.writeFileSync(path.join(root, "sounds", slug(name) + ".wav"), wav(make(name)));
for (const [name, lines] of Object.entries(paths)) {
  const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="168" height="168" viewBox="0 0 42 42" fill="none" stroke="#62bf83" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><title>' + name + '</title>' + lines.map(d => '<path d="' + d + '"/>').join("") + '</svg>\n';
  fs.writeFileSync(path.join(root, "marks", slug(name) + ".svg"), svg);
}
const overlay = (title, children) => '<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920" fill="none"><title>' + title + '</title>' + children + '</svg>\n';
const ticks = Array.from({ length: 19 }, (_, i) => '<path d="M32 ' + (240 + i * 80) + 'h' + (i % 3 === 0 ? 35 : 13) + '"/>').join("");
fs.writeFileSync(path.join(root, "overlays", "edge-register.svg"), overlay("Edge Register", '<g stroke="#a5ffd2" stroke-width="3" opacity=".78"><path d="M36 142V46h96M944 46h96v96M1040 1778v96h-96M132 1874H36v-96"/>' + ticks + '</g>'));
const arcs = Array.from({ length: 7 }, (_, i) => '<ellipse cx="1000" cy="1630" rx="' + (190 + 54 * i) + '" ry="' + (62 + 22 * i) + '" transform="rotate(-28 1000 1630)" opacity="' + (0.70 - i * 0.07).toFixed(2) + '"/>').join("");
fs.writeFileSync(path.join(root, "overlays", "orbit-contour.svg"), overlay("Orbit Contour", '<g stroke="#c7a4ff" stroke-width="3">' + arcs + '</g>'));
console.log("Wrote Seven Sounds, Six Marks, And Two Overlays.");
