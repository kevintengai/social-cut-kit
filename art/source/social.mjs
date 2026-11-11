import { R, mv, scl, sway, draw, pop, blink } from "./kit.mjs";

const land = "0%{transform:translateY(-5px);opacity:0}55%{transform:translateY(.8px);opacity:1}78%{transform:translateY(-.4px)}100%{transform:none}";

export default [
  { name: "comment-thread", title: "Comment Thread", usage: "Invite A Response Or Mark A Viewer Question.", tags: "chat reply message speech bubble",
    motion: "A Reply Bubble Pops Up Beneath The First Comment.",
    parts: [["a", '<g><path d="M3 4.5h13.5v9h-8L5 16.5v-3H3z"/><path d="M5.75 8h8M5.75 10.5h5.5"/></g>'], ["b", '<path d="M10.5 16H14l4.5 3v-3H21V9h-2"/>', 1]],
    anim: { b: [pop(20), 650, "ease-out", "21px 16px"], a: [mv(-0.6, -0.6, 45), 650] } },
  { name: "save-bookmark", title: "Save Bookmark", usage: "Point To The Save Action For A Reference Clip.", tags: "favorite keep later ribbon",
    motion: "The Bookmark Drops Into Place And The Plus Mark Confirms The Save.",
    parts: [["r", '<path d="M6 3.5h12V21l-6-4.5L6 21z"/>'], ["p", '<path d="M9 8.5h6M12 5.5v6"/>', 1]],
    anim: { r: [land, 650, "ease-out"], p: [pop(55), 800, "ease-out", "12px 8.5px"] } },
  { name: "share-link", title: "Share Link", usage: "Cue A Resource Link In The Post.", tags: "chain url connect hyperlink",
    motion: "The Two Links Pull Apart And Snap Back Together.",
    parts: [["l", '<path d="m9.75 14.6-1.5 1.5a3.4 3.4 0 0 1-4.9-4.9L7.1 7.5a3.4 3.4 0 0 1 4.9 0"/>'], ["r", '<path d="m14.25 9.4 1.5-1.5a3.4 3.4 0 1 1 4.9 4.9l-3.75 3.7a3.4 3.4 0 0 1-4.9 0"/>'], ["c", '<path d="m8.75 14.75 6.5-5.5"/>', 1]],
    anim: { l: [`${R}35%{transform:translate(-1.3px,1.3px)}70%{transform:translate(.4px,-.4px)}`, 700], r: [`${R}35%{transform:translate(1.3px,-1.3px)}70%{transform:translate(-.4px,.4px)}`, 700], c: [`${R}35%{transform:scale(.6)}70%{transform:scale(1.08)}`, 700] } },
  { name: "community-group", title: "Community Group", usage: "Identify A Community Invitation.", tags: "people members team audience",
    motion: "The Two Outer Members Step In Toward The Person At The Center.",
    parts: [["c", '<circle cx="12" cy="8" r="3"/>'], ["b", '<path d="M6.75 19.5v-2a5.25 5.25 0 0 1 10.5 0v2z"/>', 1], ["l", '<g><circle cx="4.75" cy="10" r="1.9"/><path d="M2 18v-1.75a3.4 3.4 0 0 1 3.5-3.4"/></g>'], ["r", '<g><circle cx="19.25" cy="10" r="1.9"/><path d="M22 18v-1.75a3.4 3.4 0 0 0-3.5-3.4"/></g>']],
    anim: { l: [mv(1.3, 0, 55), 750], r: [mv(-1.3, 0, 55), 750], b: [scl(1.07, 55), 750, "ease-in-out", "12px 19.5px"] } },
  { name: "pinned-reply", title: "Pinned Reply", usage: "Flag A Reply That Should Stay Visible.", tags: "pin stick thumbtack keep",
    motion: "The Pin Swoops In And Sticks Into The Reply.",
    parts: [["t", '<path d="M3 6h6.5M3 9.5h4.5M3 15.75v3.5l4-3h4"/>'], ["p", '<path d="m14.6 5.25 4.9 3-1.9.75-1.9 3.4.4 1.9-6-3.4 1.9-.75 1.9-3.4zM13.1 12.75l-2.6 4.85"/>', 1]],
    anim: { p: ["0%{transform:translate(2px,-3.5px);opacity:0}60%{transform:translate(-.4px,.7px);opacity:1}100%{transform:none}", 600, "ease-in"] } },
  { name: "audience-retention", title: "Audience Retention", usage: "Show Where Viewers Leave A Sequence.", tags: "analytics graph drop chart viewers",
    motion: "The Retention Line Draws Across The Chart And The Drop Marker Appears.",
    parts: [["x", '<path d="M3 4v16h18"/>'], ["c", '<path pathLength="1" d="M5.25 7h3l2.25 2.25h3l2.25 4.25H20"/>'], ["m", '<path d="m15.5 16 2 2 2-2"/>', 1]],
    anim: { c: [draw(0), 700, "linear"], m: [pop(60), 1000, "ease-out", "17.5px 17px"] } },
  { name: "notification-bell", title: "Notification Bell", usage: "Mark A Reminder Or Subscription Prompt.", tags: "alert ring remind subscribe",
    motion: "The Bell Swings From Its Crown While The Ring Lines Flash.",
    parts: [["b", '<path d="m5 16 1.5-2.25v-3.4a5.5 5.5 0 0 1 11 0v3.4L19 16z"/>'], ["c", '<path d="M9.5 18.5a2.6 2.6 0 0 0 5 0"/>'], ["r", '<path d="M3 9.75q0-3.75 3-6M21 9.75q0-3.75-3-6"/>', 1]],
    anim: { b: [sway(15, -12, 6), 800, "ease-in-out", "12px 4.5px"], c: [`${R}25%{transform:translateX(-1.6px)}55%{transform:translateX(1.3px)}80%{transform:translateX(-.5px)}`, 800], r: [blink(0.1, 40), 800] } },
  { name: "profile-badge", title: "Profile Badge", usage: "Call Attention To A Creator Profile.", tags: "id card account creator bio",
    motion: "The Portrait Leans Forward And The Profile Lines Write In Beside It.",
    parts: [["f", '<rect x="2.5" y="4.5" width="19" height="15" rx="2"/>'], ["h", '<circle cx="8.25" cy="9.75" r="2.25"/>'], ["s", '<path d="M4.5 15.75q.4-3.25 3.75-3.25t3.75 3.25"/>', 1], ["l", '<path d="M14.5 9.5h4.5M14.5 12.5h3.25M14.5 15.5h2"/>']],
    anim: { h: [scl(1.15, 40), 700, "ease-in-out", "8.25px 12.5px"], s: [scl(1.15, 40), 700, "ease-in-out", "8.25px 12.5px"], l: ["0%,25%{transform:scaleX(0)}100%{transform:none}", 700, "ease-out", "14.5px 12.5px"] } }
];
