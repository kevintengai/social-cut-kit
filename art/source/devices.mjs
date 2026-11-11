import { R, scl, pop, blink } from "./kit.mjs";

const buzz = `${R}15%{transform:rotate(-7deg)}30%{transform:rotate(6deg)}45%{transform:rotate(-5deg)}60%{transform:rotate(4deg)}75%{transform:rotate(-2deg)}`;
const seat = `${R}40%{transform:translateY(2.4px)}60%{transform:translateY(1.7px)}`;

export default [
  { name: "phone-portrait", title: "Phone Portrait", usage: "Represent A Phone Held Upright For Vertical Video.", tags: "mobile smartphone handset vertical",
    motion: "The Phone Buzzes From Side To Side Like An Incoming Alert.",
    parts: [["b", '<g><rect x="6.5" y="2.5" width="11" height="19" rx="2.25"/><path d="M10.5 5.25h3"/></g>'], ["h", '<path d="M10.5 18.5h3"/>', 1]],
    anim: { b: [buzz, 700], h: [buzz, 700] } },
  { name: "laptop-open", title: "Laptop Open", usage: "Represent A Laptop Used For Editing Or Review.", tags: "computer notebook workstation",
    motion: "The Screen Swings Up From The Keyboard Deck Until The Laptop Is Open.",
    parts: [["s", '<path d="M5.5 16V6.5A1.5 1.5 0 0 1 7 5h10a1.5 1.5 0 0 1 1.5 1.5V16"/>'], ["b", '<path d="M2.5 16h19l-1 2.4a1 1 0 0 1-.9.6H4.4a1 1 0 0 1-.9-.6z"/>', 1]],
    anim: { s: ["0%{transform:scaleY(.1)}70%{transform:scaleY(1.06)}100%{transform:none}", 650, "ease-out", "12px 16px"] } },
  { name: "camera-body", title: "Camera Body", usage: "Mark A Recording, A Shot, Or A Photo Capture.", tags: "photo shoot record capture lens",
    motion: "The Iris Closes Down, The Flash Fires, And The Lens Opens Again.",
    parts: [["b", '<path d="M3 8.5A1.5 1.5 0 0 1 4.5 7h2.75l1.5-2.5h6.5l1.5 2.5h2.75A1.5 1.5 0 0 1 21 8.5v9a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 17.5z"/>'], ["l", '<circle cx="12" cy="13" r="3.5"/>', 1], ["f", '<path d="M17.75 10h.01"/>']],
    anim: { l: [scl(0.5, 40), 700, "ease-in-out", "12px 13px"], f: ["0%,30%,100%{transform:none;opacity:1}40%{transform:scale(2.4);opacity:1}55%{opacity:.2}", 700, "ease-out", "17.75px 10px"] } },
  { name: "desktop-monitor", title: "Desktop Monitor", usage: "Represent A Desktop Display Or A Playback Screen.", tags: "screen display computer playback",
    motion: "The Screen Wakes And The Play Mark Pops Onto It.",
    parts: [["f", '<rect x="2.5" y="3.5" width="19" height="13" rx="1.5"/>'], ["s", '<path d="M12 16.5v4M8 20.5h8"/>'], ["p", '<path d="m10.5 7.75 4 2.25-4 2.25z"/>', 1]],
    anim: { f: [blink(0.35, 20), 700], p: [pop(25), 700, "ease-out", "12px 10px"] } },
  { name: "webcam-lens", title: "Webcam Lens", usage: "Mark A Face Camera Or A Live Recording Source.", tags: "camera live stream facecam",
    motion: "The Lens Racks Focus In And Out While The Recording Light Blinks.",
    parts: [["b", '<circle cx="12" cy="10" r="7.5"/>'], ["l", '<circle cx="12" cy="10" r="2.75"/>', 1], ["d", '<path d="M12 5h.01"/>'], ["s", '<path d="M12 17.5V20M7.5 21.5q4.5-3 9 0"/>']],
    anim: { l: [`${R}35%{transform:scale(1.5)}65%{transform:scale(.8)}`, 800, "ease-in-out", "12px 10px"], d: ["0%,100%{opacity:1}25%,75%{opacity:.1}50%{opacity:1}", 800] } },
  { name: "battery-level", title: "Battery Level", usage: "Show Remaining Power On A Device.", tags: "power charge energy cell",
    motion: "The Three Cells Fill One By One From Empty To Full.",
    parts: [["s", '<path d="M4 7.5h13.5A1.5 1.5 0 0 1 19 9v6a1.5 1.5 0 0 1-1.5 1.5H4A1.5 1.5 0 0 1 2.5 15V9A1.5 1.5 0 0 1 4 7.5zM21.5 10.5v3"/>'], ["a", '<path d="M6.25 10.5v3"/>', 1], ["b", '<path d="M10.75 10.5v3"/>', 1], ["c", '<path d="M15.25 10.5v3"/>', 1]],
    anim: { a: ["0%,12%{opacity:0}28%,100%{opacity:1}", 900], b: ["0%,38%{opacity:0}54%,100%{opacity:1}", 900], c: ["0%,64%{opacity:0}80%,100%{opacity:1}", 900] } },
  { name: "wifi-signal", title: "Wifi Signal", usage: "Show A Wireless Connection Or Its Strength.", tags: "wireless network internet connection",
    motion: "The Signal Arcs Light Up Outward From The Source Dot.",
    parts: [["d", '<path d="M12 19h.01"/>'], ["a", '<path d="M8.5 15.5a5 5 0 0 1 7 0"/>'], ["b", '<path d="M5.25 12a9.5 9.5 0 0 1 13.5 0"/>'], ["c", '<path d="M2 8.5a14 14 0 0 1 20 0"/>', 1]],
    anim: { a: ["0%,8%{opacity:.12}30%,100%{opacity:1}", 900], b: ["0%,32%{opacity:.12}54%,100%{opacity:1}", 900], c: ["0%,56%{opacity:.12}78%,100%{opacity:1}", 900] } },
  { name: "memory-card", title: "Memory Card", usage: "Represent Camera Media Or An Import Source.", tags: "sd storage media import footage",
    motion: "The Card Pushes Down Into Its Slot And Springs Back Out.",
    parts: [["c", '<path d="M6.5 2.5H15L18.5 6v14a1.5 1.5 0 0 1-1.5 1.5H7A1.5 1.5 0 0 1 5.5 20V3.5a1 1 0 0 1 1-1z"/>'], ["p", '<path d="M9 6v2.5M12 6v2.5"/>', 1], ["l", '<path d="M9 17.5h6"/>']],
    anim: { c: [seat, 750], p: [seat, 750], l: [seat, 750] } }
];
