import { R, mv, draw, blink } from "./kit.mjs";

const tray = '<path d="M4 16.5V19a1.5 1.5 0 0 0 1.5 1.5h13A1.5 1.5 0 0 0 20 19v-2.5"/>';

export default [
  { name: "menu-toggle", title: "Menu Toggle", usage: "Open Or Close A Navigation Menu.", tags: "hamburger navigation bars drawer",
    motion: "The Outer Bars Fold Into A Cross Over The Hidden Middle Bar And Unfold Again.",
    parts: [["a", '<path d="M4 7h16"/>'], ["b", '<path d="M4 12h16"/>', 1], ["c", '<path d="M4 17h16"/>']],
    anim: { a: [`${R}35%,65%{transform:translateY(5px) rotate(45deg)}`, 900, "ease-in-out", "12px 7px"], b: ["0%,100%{opacity:1}35%,65%{opacity:0}", 900], c: [`${R}35%,65%{transform:translateY(-5px) rotate(-45deg)}`, 900, "ease-in-out", "12px 17px"] } },
  { name: "close-cross", title: "Close Cross", usage: "Dismiss A Panel, Dialog, Or Selection.", tags: "x cancel remove exit dismiss",
    motion: "The Two Strokes Of The Cross Strike Through One After The Other.",
    parts: [["a", '<path pathLength="1" d="m6 6 12 12"/>'], ["b", '<path pathLength="1" d="M18 6 6 18"/>', 1]],
    anim: { a: [draw(0), 300, "ease-out"], b: [draw(45), 600, "ease-out"] } },
  { name: "search-lens", title: "Search Lens", usage: "Start A Search Or Mark A Search Field.", tags: "find magnifier query look",
    motion: "The Lens Roams In A Small Loop As If Hunting For A Match.",
    parts: [["g", '<g><circle cx="10.5" cy="10.5" r="6.5"/><path d="m15.5 15.5 5 5"/></g>'], ["s", '<path d="M7.5 10.25a3 3 0 0 1 2.75-2.75"/>', 1]],
    anim: { g: [`${R}25%{transform:translate(1.6px,-1.6px)}50%{transform:translate(2.4px,1px)}75%{transform:translate(-1px,1.5px)}`, 900], s: [`${R}25%{transform:translate(1.6px,-1.6px)}50%{transform:translate(2.4px,1px)}75%{transform:translate(-1px,1.5px)}`, 900] } },
  { name: "download-tray", title: "Download Tray", usage: "Save A File From The Page To The Device.", tags: "save export get arrow down",
    motion: "The Arrow Falls From Above And Lands In The Tray, Which Dips Under It.",
    parts: [["a", '<path d="M12 3.5v11M7.75 10.5 12 14.75l4.25-4.25"/>', 1], ["t", tray]],
    anim: { a: ["0%{transform:translateY(-6px);opacity:0}55%{transform:translateY(1.3px);opacity:1}100%{transform:none}", 650, "ease-in"], t: [mv(0, 0.9, 60), 650] } },
  { name: "upload-tray", title: "Upload Tray", usage: "Send A File From The Device To The Page.", tags: "import send publish arrow up",
    motion: "The Arrow Launches Up Out Of The Tray And A Fresh One Rises Into Place.",
    parts: [["a", '<path d="M12 15V4M7.75 8.25 12 4l4.25 4.25"/>', 1], ["t", tray]],
    anim: { a: ["0%{transform:none;opacity:1}40%{transform:translateY(-5px);opacity:0}41%{transform:translateY(4px);opacity:0}100%{transform:none;opacity:1}", 800, "ease-in-out"], t: [mv(0, -0.7, 20), 800] } },
  { name: "crop-frame", title: "Crop Frame", usage: "Trim The Edges Of A Picture Or Frame.", tags: "trim resize cut bounds",
    motion: "The Two Crop Corners Slide Toward Each Other To Tighten The Frame.",
    parts: [["a", '<path d="M6.5 2.5v13a2 2 0 0 0 2 2h13"/>'], ["b", '<path d="M2.5 6.5h13a2 2 0 0 1 2 2v13"/>', 1]],
    anim: { a: [mv(1.6, -1.6, 50), 750], b: [mv(-1.6, 1.6, 50), 750] } },
  { name: "visibility-eye", title: "Visibility Eye", usage: "Show Or Hide A Layer, Field, Or Preview.", tags: "view watch show preview see",
    motion: "The Eye Blinks Shut And Then Glances To One Side.",
    parts: [["o", '<path d="M2 12s3.75-6.5 10-6.5S22 12 22 12s-3.75 6.5-10 6.5S2 12 2 12z"/>'], ["p", '<circle cx="12" cy="12" r="2.75"/>', 1]],
    anim: { o: [`${R}30%,42%{transform:scaleY(.1)}`, 900], p: [`${R}30%,42%{transform:scaleY(.1)}75%{transform:translateX(1.4px)}`, 900] } },
  { name: "refresh-cycle", title: "Refresh Cycle", usage: "Reload Content Or Run A Step Again.", tags: "reload sync retry update rotate",
    motion: "Both Arrows Chase Each Other Through One Full Turn.",
    parts: [["a", '<path d="M20 11A8 8 0 0 0 5.5 7.25M4 4v4h4"/>'], ["b", '<path d="M4 13a8 8 0 0 0 14.5 3.75M20 20v-4h-4"/>', 1]],
    anim: { a: ["0%{transform:rotate(0)}100%{transform:rotate(360deg)}", 850], b: ["0%{transform:rotate(0)}100%{transform:rotate(360deg)}", 850] } }
];
