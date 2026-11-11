import { R, scl, draw } from "./kit.mjs";

const bounce = `${R}25%{transform:translateY(-1.75px)}50%{transform:none}75%{transform:translateY(-1px)}`;

export default [
  { name: "voice-track", title: "Voice Track", usage: "Identify The Spoken Performance On A Track.", tags: "microphone mic speech record",
    motion: "The Microphone Capsule Pulses Twice As If Picking Up A Spoken Phrase.",
    parts: [["m", '<rect x="9" y="2.5" width="6" height="11" rx="3"/>'], ["c", '<path d="M6 11v1a6 6 0 0 0 12 0v-1M12 18v3M9 21h6"/>', 1]],
    anim: { m: [`${R}20%{transform:scale(1.12)}45%{transform:scale(.95)}70%{transform:scale(1.07)}`, 800, "ease-in-out", "12px 13.5px"] } },
  { name: "room-tone", title: "Room Tone", usage: "Mark A Room Tone Sample Between Dialogue Takes.", tags: "ambience noise floor silence",
    motion: "The Quiet Waveform Flutters Inside The Room And Settles.",
    parts: [["h", '<path d="M3 20V6l9-3 9 3v14M3 20h18"/>'], ["w", '<path d="M5.5 15h2l1.5-2 1.5 4 1.5-7 1.5 6.5 1.5-2.5 1.5 1h2"/>', 1]],
    anim: { w: [`${R}20%{transform:scaleY(.35)}40%{transform:scaleY(1.15)}60%{transform:scaleY(.55)}80%{transform:scaleY(1.05)}`, 900, "ease-in-out", "12px 15px"] } },
  { name: "stereo-balance", title: "Stereo Balance", usage: "Compare Left And Right Channel Levels.", tags: "pan left right channels speakers",
    motion: "Sound Leaves The Left Speaker First And Then The Right Speaker.",
    parts: [["l", '<path d="M2 10h2l3-2.5v9L4 14H2z"/>'], ["r", '<path d="M22 10h-2l-3-2.5v9l3-2.5h2z"/>'], ["a", '<path d="M9.5 9.5q2 2.5 0 5"/>', 1], ["b", '<path d="M14.5 9.5q-2 2.5 0 5"/>', 1]],
    anim: { a: ["0%,50%,100%{transform:none;opacity:1}20%{transform:translateX(1.2px);opacity:.2}", 900], b: ["0%,45%,100%{transform:none;opacity:1}70%{transform:translateX(-1.2px);opacity:.2}", 900] } },
  { name: "crossfade", title: "Crossfade", usage: "Show Two Audio Levels Crossing In A Transition.", tags: "fade transition blend dissolve",
    motion: "The Outgoing Level Draws Downward While The Incoming Level Draws Upward Across It.",
    parts: [["x", '<path d="M3 5v15h18"/>'], ["a", '<path pathLength="1" d="M5 7.5c6 0 6.5 9 14.5 9"/>'], ["b", '<path pathLength="1" d="M5 16.5c7 0 7.5-9 14.5-9"/>', 1]],
    anim: { a: [draw(0), 700], b: [draw(25), 900] } },
  { name: "peak-meter", title: "Peak Meter", usage: "Point Out A Peak In Recorded Audio.", tags: "level gauge loudness volume",
    motion: "The Needle Sweeps Up From Silence, Overshoots The Peak, And Settles.",
    parts: [["d", '<path d="M3 17a9 9 0 0 1 18 0M4.6 13l1.4.7M8.2 8.6l.8 1.5M15.8 8.6l-.8 1.5M19.4 13l-1.4.7"/>'], ["n", '<path d="m12 17 5-6M12 17h.01"/>', 1]],
    anim: { n: ["0%{transform:rotate(-85deg)}55%{transform:rotate(16deg)}78%{transform:rotate(-6deg)}100%{transform:none}", 900, "ease-out", "12px 17px"] } },
  { name: "beat-marker", title: "Beat Marker", usage: "Mark The Beat That Anchors A Visual Cut.", tags: "metronome tempo rhythm",
    motion: "The Metronome Arm Swings Across To The Other Side And Back Onto The Beat.",
    parts: [["m", '<path d="M5 18 9.5 4h5L19 18zM4 20.5h16"/>'], ["a", '<g><path d="m12 15.5 4.2-6.3"/><circle cx="16.75" cy="8.25" r="1.25"/></g>', 1]],
    anim: { a: [`${R}35%{transform:rotate(-66deg)}70%{transform:rotate(9deg)}`, 900, "ease-in-out", "12px 15.5px"] } },
  { name: "headphone-check", title: "Headphone Check", usage: "Cue A Close Listen At An Edit Boundary.", tags: "listen monitor headset audio",
    motion: "The Left Cup Thumps And Then The Right Cup Answers.",
    parts: [["h", '<path d="M4 14v-2a8 8 0 0 1 16 0v2M20 18.5q0 3-4.5 3"/>'], ["l", '<rect x="3" y="12.5" width="4" height="7.5" rx="2"/>', 1], ["r", '<rect x="17" y="12.5" width="4" height="7.5" rx="2"/>', 1]],
    anim: { l: [scl(1.25, 25), 800, "ease-in-out", "5px 16.25px"], r: [scl(1.25, 65), 800, "ease-in-out", "19px 16.25px"] } },
  { name: "music-bed", title: "Music Bed", usage: "Identify A Music Layer Under Spoken Audio.", tags: "song notes score soundtrack",
    motion: "The Notes Bounce Twice Above The Bed Line.",
    parts: [["s", '<path d="M9 16V7l10-2.5V14M9 10l10-2.5"/>'], ["n", '<g><ellipse cx="6.5" cy="16.25" rx="2.5" ry="2"/><ellipse cx="16.5" cy="14.25" rx="2.5" ry="2"/></g>', 1], ["b", '<path d="M3 21h18"/>']],
    anim: { s: [bounce, 800], n: [bounce, 800], b: [`${R}50%{transform:scaleX(.8)}`, 800] } }
];
