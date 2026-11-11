// The single source description for the icon library. Edit the group files, then run node art/build.mjs.
import timeline from "./timeline.mjs";
import sound from "./sound.mjs";
import text from "./text.mjs";
import product from "./product.mjs";
import social from "./social.mjs";
import callouts from "./callouts.mjs";
import ui from "./interface.mjs";
import files from "./files.mjs";
import devices from "./devices.mjs";
import people from "./people.mjs";
import commerce from "./commerce.mjs";
import status from "./status.mjs";

export const groups = [
  { name: "Timeline", icons: timeline },
  { name: "Sound", icons: sound },
  { name: "Text", icons: text },
  { name: "Product", icons: product },
  { name: "Social", icons: social },
  { name: "Callouts", icons: callouts },
  { name: "Interface", icons: ui },
  { name: "Files", icons: files },
  { name: "Devices", icons: devices },
  { name: "People", icons: people },
  { name: "Commerce", icons: commerce },
  { name: "Status", icons: status }
];

// Hand-authored looping overlays. Their SVG files are kept as written and are only listed here.
export const overlays = [
  { title: "Tap Ripple", usage: "Mark A Tap Target With Two Outward Ripples.", file: "motion/tap-ripple.svg" },
  { title: "Focus Lock", usage: "Settle Four Focus Corners Around A Detail.", file: "motion/focus-lock.svg" },
  { title: "Beat Bars", usage: "Cue A Music Beat With A Three-Bar Motion.", file: "motion/beat-bars.svg" },
  { title: "Path Trace", usage: "Lead The Eye From An Origin Toward An Arrowhead.", file: "motion/path-trace.svg" },
  { title: "Word Underline", usage: "Draw A Short Emphasis Line Beneath A Headline.", file: "motion/word-underline.svg" },
  { title: "Swipe Cue", usage: "Prompt A Horizontal Gesture With A Moving Chevron.", file: "motion/swipe-cue.svg" }
];
