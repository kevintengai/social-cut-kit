import { R, scl, draw, drop, pop } from "./kit.mjs";

const wipe = "0%{transform:scaleX(0)}100%{transform:none}";

export default [
  { name: "captions", title: "Captions", usage: "Introduce Or Inspect The Caption Layer.", tags: "subtitles cc closed text",
    motion: "The Two Caption Lines Type Across The Frame In Turn.",
    parts: [["f", '<rect x="2.5" y="5" width="19" height="14" rx="2"/>'], ["a", '<path d="M6 11h6M15 11h3"/>', 1], ["b", '<path d="M6 14.5h3M12 14.5h6"/>', 1]],
    anim: { a: [wipe, 380, "ease-out", "6px 11px"], b: [wipe, 380, "ease-out", "6px 14.5px", 260] } },
  { name: "safe-margins", title: "Safe Margins", usage: "Check Caption And Headline Placement On Screen.", tags: "title safe guides frame bounds",
    motion: "The Corner Guides Close In Toward The Text Block And Release.",
    parts: [["c", '<path d="M3 8V3h5M16 3h5v5M21 16v5h-5M8 21H3v-5"/>'], ["t", '<g><rect x="7" y="7.5" width="10" height="9" rx="1"/><path d="M9.5 11h5M9.5 13.5h3"/></g>', 1]],
    anim: { c: [scl(0.84, 50), 800] } },
  { name: "lower-third", title: "Lower Third", usage: "Mark A Speaker Name Or Role Plate.", tags: "name plate title chyron",
    motion: "The Name Plate Slides In From The Left Edge Of The Frame.",
    parts: [["f", '<rect x="2.5" y="4" width="19" height="16" rx="1.5"/>'], ["p", '<g><path d="M2.5 13.5h12v4h-12"/><path d="M5.5 15.5h5"/></g>', 1]],
    anim: { p: [drop(-6, 0, 70), 600, "ease-out"] } },
  { name: "word-highlight", title: "Word Highlight", usage: "Point Out The Word That Carries Emphasis.", tags: "emphasis keyword marker",
    motion: "The Highlight Box Sweeps Across The Chosen Word From Its First Letter.",
    parts: [["l", '<path d="M3 6h7M13 6h5.5M3 10h15.5M3 20h12"/>'], ["b", '<rect x="3" y="13" width="8.5" height="4" rx="1"/>', 1], ["r", '<path d="M14 15h6"/>']],
    anim: { b: ["0%{transform:scaleX(0)}70%{transform:scaleX(1.1)}100%{transform:none}", 550, "ease-out", "3px 15px"] } },
  { name: "text-baseline", title: "Text Baseline", usage: "Align Two Text Treatments To The Same Baseline.", tags: "align type typography letters",
    motion: "The Second Letter Drops And Lands On The Shared Baseline.",
    parts: [["a", '<path d="M5 15.5 8.5 6l3.5 9.5M6.5 12h4"/>'], ["t", '<path d="M14 9.5h5.5M16.75 9.5v6"/>'], ["b", '<path d="M2.5 18h19M4 19.75v1M20 19.75v1"/>', 1]],
    anim: { t: ["0%{transform:translateY(-3.5px)}55%{transform:translateY(.5px)}100%{transform:none}", 600, "ease-in"], b: [`${R}62%{transform:translateY(.5px)}`, 600] } },
  { name: "speaker-label", title: "Speaker Label", usage: "Identify A Speaker Before Their First Line.", tags: "name tag person identify",
    motion: "The Name Tag Pops Out From Beside The Speaker.",
    parts: [["h", '<circle cx="8" cy="8" r="2.75"/>'], ["s", '<path d="M3.5 16.5Q3.5 12 8 12q3 0 4.25 2.25"/>'], ["t", '<g><rect x="10.5" y="14.5" width="11" height="5" rx="1.25"/><path d="M13 17h5.5"/></g>', 1]],
    anim: { t: [pop(15), 600, "ease-out", "10.5px 17px"], h: [`${R}30%{transform:translateY(.7px)}`, 600] } },
  { name: "transcript-match", title: "Transcript Match", usage: "Mark Confirmed Agreement Between Speech And Text.", tags: "verify document check approved",
    motion: "The Check Mark Draws Itself Across The Corner Of The Page.",
    parts: [["p", '<path d="M5 3h9.5L18 6.5V11M14.25 3.25v3.5h3.5M5 3v17.5h6.5M7.5 9.5H14M7.5 12.5H12"/>'], ["c", '<path pathLength="1" d="m13 16.5 2.5 2.75L21 12.5"/>', 1]],
    anim: { c: [draw(10), 600, "ease-out"] } },
  { name: "headline-card", title: "Headline Card", usage: "Introduce The Main Promise At The Opening Frame.", tags: "title hook opening text",
    motion: "The Headline Writes In Line By Line From The Top Of The Card.",
    parts: [["f", '<rect x="2.5" y="4.5" width="19" height="15" rx="1.5"/>'], ["a", '<path d="M5.5 8H8M5.5 10.75h13"/>', 1], ["b", '<path d="M5.5 13.5h9"/>', 1], ["c", '<path d="M5.5 16.5h5"/>', 1]],
    anim: { a: [wipe, 320, "ease-out", "5.5px 9px"], b: [wipe, 320, "ease-out", "5.5px 13.5px", 180], c: [wipe, 320, "ease-out", "5.5px 16.5px", 360] } }
];
