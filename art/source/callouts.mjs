import { R, mv, rot, draw, pop, appear } from "./kit.mjs";

const fall = "0%{transform:translateY(-6px);opacity:0}55%{transform:translateY(.7px);opacity:1}100%{transform:none}";

export default [
  { name: "elbow-arrow", title: "Elbow Arrow", usage: "Connect A Side Label To A Specific Screen Control.", tags: "connector pointer leader line",
    motion: "The Line Runs Around The Corner And The Arrowhead Arrives At The Target.",
    parts: [["l", '<path pathLength="1" d="M3 5.5h8.25Q14 5.5 14 8.25V16.5h6.5"/>', 1], ["h", '<path d="M17 13l3.75 3.5L17 20"/>']],
    anim: { l: [draw(0), 600, "ease-in-out"], h: ["0%,65%{transform:translateX(-3px);opacity:0}100%{transform:none;opacity:1}", 800, "ease-out"] } },
  { name: "curved-return", title: "Curved Return", usage: "Bring Attention Back To A Prior Detail.", tags: "back arc undo revisit arrow",
    motion: "The Arc Sweeps Back Over The Top And The Arrowhead Lands On The Earlier Point.",
    parts: [["c", '<path pathLength="1" d="M21 16.5C18.75 6 7.5 4.9 4.5 12.75"/>', 1], ["h", '<path d="m3.4 7.5.75 6 6-1.5"/>']],
    anim: { c: [draw(0), 650, "ease-in-out"], h: ["0%,60%{transform:translate(1.5px,-2px);opacity:0}100%{transform:none;opacity:1}", 850, "ease-out"] } },
  { name: "measurement-span", title: "Measurement Span", usage: "Show The Width Or Duration Of A Selected Region.", tags: "width duration ruler distance size",
    motion: "The Two End Stops Squeeze Inward With The Span And Spread Back To Full Width.",
    parts: [["l", '<path d="M3 6.5v11"/>'], ["r", '<path d="M21 6.5v11"/>'], ["s", '<g><path d="M4.5 12h15"/><path d="M6.75 9.5 4.25 12l2.5 2.5M17.25 9.5l2.5 2.5-2.5 2.5"/></g>', 1]],
    anim: { l: [mv(3.4, 0, 45), 800], r: [mv(-3.4, 0, 45), 800], s: [`${R}45%{transform:scaleX(.58)}`, 800] } },
  { name: "detail-bracket", title: "Detail Bracket", usage: "Frame An Interface Detail Without Covering Its Center.", tags: "focus frame target corners crop",
    motion: "The Four Corners Tighten Around The Center Mark And Ease Back Out.",
    parts: [["c", '<path d="M7.5 3.5h-4v5M16.5 3.5h4v5M20.5 16v4.5H16M8 20.5H3.5V16"/>', 1], ["p", '<path d="M10 12h4M12 10v4"/>']],
    anim: { c: [`${R}40%{transform:scale(.7)}65%{transform:scale(.76)}`, 800], p: ["0%{transform:rotate(0)}100%{transform:rotate(90deg)}", 800] } },
  { name: "waypoint-route", title: "Waypoint Route", usage: "Trace The Order Of Three On-Screen Steps.", tags: "path steps journey sequence map",
    motion: "The Route Draws From Stop To Stop And Each Stop Lights As It Is Reached.",
    parts: [["a", '<circle cx="4" cy="16.5" r="1.6"/>', 1], ["p", '<path pathLength="1" d="M5.6 16c3.75-.75 1.5-7.75 4.65-8.4"/>'], ["b", '<circle cx="11.75" cy="7.5" r="1.6"/>', 1], ["q", '<path pathLength="1" d="M13.4 7.5c4.5 0 1.1 5.5 5 5.5"/>'], ["c", '<circle cx="20" cy="13" r="1.6"/>', 1]],
    anim: { p: [draw(0), 400, "linear"], b: [pop(40), 600, "ease-out", "11.75px 7.5px"], q: [draw(50), 800, "linear"], c: [pop(75), 1000, "ease-out", "20px 13px"] } },
  { name: "spotlight-beam", title: "Spotlight Beam", usage: "Direct Attention From A Caption Toward A Detail.", tags: "light lamp focus stage highlight",
    motion: "The Lamp Tilts And Its Beam Fans Open Across The Stage.",
    parts: [["l", '<path d="m3.5 3.5 5.5 3-2.75 4.75L2 7z"/>', 1], ["b", '<path d="m7.25 12 3.4 8.25L21 13.1 10.1 9.4"/>', 1], ["r", '<path d="M5.75 3.9 8 2M9.75 5.9 12 4.75"/>']],
    anim: { l: [rot(-12, 40), 750, "ease-in-out", "5.5px 7px"], b: ["0%{transform:scale(.25);opacity:0}100%{transform:none;opacity:1}", 750, "ease-out", "7.5px 10px"], r: [appear(60), 750] } },
  { name: "step-ladder", title: "Step Ladder", usage: "Explain A Sequence With Three Ordered Levels.", tags: "stairs levels progress stages",
    motion: "The Staircase Draws Upward And A Marker Appears Above Each Step In Order.",
    parts: [["s", '<path pathLength="1" d="M2.5 19H8v-5.5h5.5V8h8"/>', 1], ["a", '<path d="M3.5 16h2.5"/>'], ["b", '<path d="M9.5 10.5H12"/>'], ["c", '<path d="M15.5 5H19"/>']],
    anim: { s: [draw(0), 700, "linear"], a: [appear(25), 500], b: [appear(50), 700], c: [appear(75), 900] } },
  { name: "anchor-pin", title: "Anchor Pin", usage: "Fix A Note To An Exact Point In A Screen Recording.", tags: "location marker place map point",
    motion: "The Pin Falls Onto Its Point And The Ground Marks Spread On Impact.",
    parts: [["p", '<path d="M12 20.5S5.5 13.5 5.5 8.75a6.5 6.5 0 0 1 13 0c0 4.75-6.5 11.75-6.5 11.75z"/>'], ["d", '<circle cx="12" cy="8.75" r="2.25"/>', 1], ["g", '<path d="M6 21.5h3M15 21.5h3"/>', 1]],
    anim: { p: [fall, 600, "ease-in"], d: [fall, 600, "ease-in"], g: [`${R}60%{transform:scaleX(1.3)}`, 600] } }
];
