import { R, sway } from "./kit.mjs";

const thumb = `${R}35%{transform:rotate(-16deg)}65%{transform:rotate(5deg)}`;

export default [
  { name: "person-circle", title: "Person Circle", usage: "Represent An Account, A Viewer, Or A Signed-In User.", tags: "user account avatar profile member",
    motion: "The Head Dips In A Short Nod Of Greeting.",
    parts: [["r", '<circle cx="12" cy="12" r="9.5"/>'], ["h", '<circle cx="12" cy="9.5" r="3"/>'], ["s", '<path d="M6 18.75a6.5 6.5 0 0 1 12 0"/>', 1]],
    anim: { h: [`${R}30%{transform:translateY(1.2px)}60%{transform:translateY(-.4px)}`, 650], s: [`${R}30%{transform:scaleY(.86)}`, 650, "ease-in-out", "12px 19px"] } },
  { name: "add-person", title: "Add Person", usage: "Invite A Collaborator Or Follow A Creator.", tags: "invite follow user plus join",
    motion: "The Plus Mark Spins In Beside The Person.",
    parts: [["h", '<circle cx="9.5" cy="7.5" r="3.5"/>'], ["b", '<path d="M3 20v-1.5A5.5 5.5 0 0 1 8.5 13h2a5.5 5.5 0 0 1 3 .9"/>'], ["p", '<path d="M18.5 13.5v6M15.5 16.5h6"/>', 1]],
    anim: { p: ["0%{transform:rotate(-180deg) scale(.3);opacity:0}70%{transform:rotate(10deg) scale(1.1);opacity:1}100%{transform:none}", 650, "ease-out", "18.5px 16.5px"] } },
  { name: "team-pair", title: "Team Pair", usage: "Represent Two Collaborators Or A Shared Workspace.", tags: "users partners duo collaborators",
    motion: "The Second Person Steps Out From Behind The First.",
    parts: [["a", '<g><circle cx="8.5" cy="8" r="3.25"/><path d="M2.5 19.5v-1A5.5 5.5 0 0 1 8 13h1a5.5 5.5 0 0 1 5.5 5.5v1"/></g>'], ["b", '<path d="M15 4.9a3.25 3.25 0 0 1 0 6.2M17.5 13.4a5.5 5.5 0 0 1 4 5.1v1"/>', 1]],
    anim: { b: ["0%{transform:translateX(-4px);opacity:0}100%{transform:none;opacity:1}", 600, "ease-out"] } },
  { name: "podium-speaker", title: "Podium Speaker", usage: "Mark A Talk, A Lesson, Or A Presenter Segment.", tags: "presenter talk lecture teacher host",
    motion: "The Speaker Leans From Side To Side Behind The Podium While Talking.",
    parts: [["h", '<circle cx="12" cy="5.5" r="2.75"/>'], ["p", '<path d="M4.5 11.5h15M7 11.5l1 9h8l1-9M10.5 15h3"/>', 1]],
    anim: { h: [`${R}25%{transform:translate(-1.3px,.3px)}50%{transform:translate(1.3px,.3px)}75%{transform:translate(-.6px,0)}`, 850] } },
  { name: "heart-reaction", title: "Heart Reaction", usage: "Mark A Like Or An Appreciative Response.", tags: "like love favorite appreciate",
    motion: "The Heart Beats Twice.",
    parts: [["h", '<path d="M12 20.5S3.5 15 3.5 9A4.5 4.5 0 0 1 12 6.95 4.5 4.5 0 0 1 20.5 9c0 6-8.5 11.5-8.5 11.5z"/>', 1]],
    anim: { h: [`${R}18%{transform:scale(1.2)}36%{transform:scale(.95)}54%{transform:scale(1.12)}`, 800, "ease-in-out", "12px 13px"] } },
  { name: "thumbs-up", title: "Thumbs Up", usage: "Mark Approval Or A Positive Review.", tags: "approve like agree good yes",
    motion: "The Hand Rocks Upward From The Wrist To Give Its Approval.",
    parts: [["c", '<path d="M3 10.5h4v10H3z"/>'], ["t", '<path d="m7 10.5 3.75-7.5A2.25 2.25 0 0 1 13 5.25V9h5.4a2 2 0 0 1 1.95 2.45l-1.6 7a2.5 2.5 0 0 1-2.45 2.05H7"/>', 1]],
    anim: { c: [thumb, 700, "ease-in-out", "4px 20.5px"], t: [thumb, 700, "ease-in-out", "4px 20.5px"] } },
  { name: "id-lanyard", title: "ID Lanyard", usage: "Represent A Pass, A Role, Or Event Access.", tags: "badge pass access credential event",
    motion: "The Badge Swings From Its Strap And Comes To Rest.",
    parts: [["s", '<path d="M10 2.5v4h4v-4M12 6.5v2"/>'], ["c", '<g><rect x="5.5" y="8.5" width="13" height="13" rx="1.5"/><circle cx="12" cy="13.25" r="2"/><path d="M9 18h6"/></g>', 1]],
    anim: { c: [sway(9, -7, 3), 900, "ease-in-out", "12px 8.5px"] } },
  { name: "person-speaking", title: "Person Speaking", usage: "Mark Dialogue, Narration, Or A Speaking Turn.", tags: "talk voice say narrate dialogue",
    motion: "Two Sound Waves Leave The Speaker One After The Other.",
    parts: [["p", '<g><circle cx="8.5" cy="8" r="3.25"/><path d="M2.5 20v-1.5A5.5 5.5 0 0 1 8 13h1a5.5 5.5 0 0 1 5.5 5.5V20"/></g>'], ["a", '<path d="M15.5 5.5a3.5 3.5 0 0 1 0 5"/>', 1], ["b", '<path d="M18.25 3.25a7 7 0 0 1 0 9.5"/>', 1]],
    anim: { a: ["0%,10%{transform:translateX(-2px);opacity:0}45%,100%{transform:none;opacity:1}", 800, "ease-out"], b: ["0%,40%{transform:translateX(-2px);opacity:0}80%,100%{transform:none;opacity:1}", 800, "ease-out"] } }
];
