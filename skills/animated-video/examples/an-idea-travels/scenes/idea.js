// An Idea Travels: Four Draw Functions For A Short Voiced Explainer.
// The Idea Is One Warm Dot. It Appears, Is Spoken, Spreads Through A Network, And Lights A Town.
// Every Time Below Comes From A Beat In The Storyboard, So Retiming The Voice Moves The Picture And Its Sounds Together.
(function () {
  "use strict";
  const K = MotionKit;
  const paper = (c, s) => K.grain(c, s, { amount: 0.045, seed: 3, step: K.boilStep(s.time, 6), dark: "#3a2c1e", light: "#ffffff" });
  const dot = (c, x, y, radius, color) => { c.fillStyle = color; c.beginPath(); c.arc(x, y, Math.max(0, radius), 0, K.TAU); c.fill(); };

  // ---------------------------------------------------------------- Scene 1: The Idea Appears
  function seed(c, s) {
    const u = s.unit, pop = s.beat("small", 1.2), cx = s.cx, cy = s.safe.top + s.safe.h * 0.56;
    // Each Spoken Word Rises In As It Is Said.
    const line = s.words.length ? s.words.map(word => word.text).join(" ") : s.params.line;
    const block = K.layoutWords(c, line, { width: s.safe.w * 0.9, size: u * 10.5, weight: 800, align: "center" });
    c.textAlign = "left"; c.textBaseline = "middle"; c.fillStyle = s.colors.foreground;
    block.words.forEach((word, i) => {
      const at = s.words[i] ? s.words[i].start : 0.3 + i * 0.3, q = K.ease.outCubic(K.between(s.time, at - 0.05, at + 0.3));
      c.globalAlpha = q;
      c.fillText(word.text, cx - block.width / 2 + word.x, s.safe.top + s.safe.h * 0.16 + word.y + (1 - q) * u * 2.5);
    });
    c.globalAlpha = 1;
    // The Dot Arrives On The Word "Small" And Breathes With The Voice.
    const size = K.spring(s.time - pop, { from: 0, to: 1, stiffness: 240, damping: 13 }) * u * (3.4 + s.voice * 1.2);
    c.strokeStyle = K.rgba(s.colors.accent, 0.35 * K.between(s.time, pop, pop + 0.2)); c.lineWidth = u * 0.5;
    c.beginPath(); c.arc(cx, cy, size + u * 3 * K.ease.outCubic(K.between(s.time, pop, pop + 0.9)), 0, K.TAU); c.stroke();
    dot(c, cx, cy, size, s.colors.accent);
    paper(c, s);
  }
  const seedEvents = s => [{ id: "idea-appears", at: s.beat("small", 1.2), what: "The Idea Dot Appears", kind: "appear", pan: 0, sound: "Glass Point", gain: 0.55 }];

  // ---------------------------------------------------------------- Scene 2: The Idea Is Spoken
  function spoken(c, s) {
    const u = s.unit, leave = s.beat("move", 1.6), figure = { x: 0.3, ground: 0.66, size: 0.4 };
    s.use(c, "Doodle Character", Object.assign({ talk: true, pose: "Talk", poses: [{ at: leave - 0.15, pose: "Point", duration: 0.35 }] }, figure));
    // The Dot Rises From The Speaker, Hangs In A Bubble, Then Leaves To The Right On The Word "Move".
    const from = [s.width * 0.42, s.height * 0.36], hang = [s.width * 0.6, s.height * 0.22], away = [s.width * 1.08, s.height * 0.16];
    const rise = K.ease.outBack(K.between(s.time, 0.25, 0.8)), go = K.ease.inCubic(K.between(s.time, leave, leave + 0.55));
    const x = K.lerp(K.lerp(from[0], hang[0], rise), away[0], go), y = K.lerp(K.lerp(from[1], hang[1], rise), away[1], go) + Math.sin(s.time * 2.2) * u * 0.8 * (1 - go);
    const bubble = K.between(s.time, 0.5, 0.9) * (1 - K.between(s.time, leave, leave + 0.2));
    if (bubble > 0) {
      c.globalAlpha = bubble; c.strokeStyle = s.colors.foreground; c.lineWidth = u * 0.7; c.lineJoin = "round";
      K.tracePath(c, K.boilPath(K.ellipsePoints(hang[0], hang[1], u * 13, u * 9.5, 40), { amount: u * 0.35, seed: 5, step: K.boilStep(s.time, 6) }), true); c.stroke();
      K.tracePath(c, [[hang[0] - u * 9, hang[1] + u * 7], [hang[0] - u * 13, hang[1] + u * 12.5], [hang[0] - u * 5.5, hang[1] + u * 9]]); c.stroke();
      c.globalAlpha = 1;
    }
    // A Tapered Trail Follows The Dot As It Leaves.
    if (go > 0 && go < 1) {
      c.fillStyle = K.rgba(s.colors.accent, 0.5);
      K.ribbon(c, K.linePoints(K.lerp(hang[0], x, 0.35), K.lerp(hang[1], y, 0.35), x, y, 8), { width: u * 3, taper: 0.5 });
    }
    dot(c, x, y, u * 3.4 * K.between(s.time, 0.2, 0.45), s.colors.accent);
    paper(c, s);
  }
  const spokenEvents = s => [
    { id: "idea-spoken", at: 0.25, what: "The Idea Leaves The Speaker", kind: "appear", pan: -0.2, sound: "Paper Tap", gain: 0.5 },
    { id: "idea-moves", at: s.beat("move", 1.6), what: "The Idea Flies Off To The Right", kind: "travel", pan: 0.6, sound: "Air Sweep", gain: 0.55 }
  ];

  // ---------------------------------------------------------------- Scene 3: The Idea Spreads
  // The Network Lives In World Units Around (0, 0). The Camera Pulls Back As Each Ring Arrives.
  function network(s) {
    const three = s.beat("three", 0.8), nine = s.beat("nine", 2.2), nodes = [{ x: 0, y: 0, at: 0.1, parent: -1, ring: 0 }];
    for (let i = 0; i < 3; i++) { const a = -Math.PI / 2 + i * K.TAU / 3; nodes.push({ x: Math.cos(a) * 250, y: Math.sin(a) * 250, at: three + i * 0.14, parent: 0, ring: 1 }); }
    for (let i = 0; i < 9; i++) { const a = -Math.PI / 2 + (i - 1) * K.TAU / 9; nodes.push({ x: Math.cos(a) * 560, y: Math.sin(a) * 560, at: nine + i * 0.07, parent: 1 + Math.floor(i / 3), ring: 2 }); }
    return { three, nine, nodes };
  }
  function spread(c, s) {
    const u = s.unit, plan = network(s), fit = s.min / 1080;
    const pose = K.track([[0, { zoom: 2.1 * fit }], [plan.three + 0.7, { zoom: 1.35 * fit }, "inOutCubic"], [plan.nine + 0.9, { zoom: 0.72 * fit }, "inOutCubic"]], s.time);
    const cam = K.camera(s, { x: 0, y: 0, zoom: pose.zoom }, K.drift(s.time, { amount: 6, seed: 2 }));
    // A Far Layer Of Faint Dots Moves Less Than The Network, Which Gives The Pull-Back Depth.
    cam.layer(c, 0.35, () => {
      const random = s.rng("stars");
      c.fillStyle = K.rgba(s.colors.foreground, 0.12);
      for (let i = 0; i < 70; i++) { c.beginPath(); c.arc(random.range(-1400, 1400) + s.cx, random.range(-1800, 1800) + s.cy, random.range(3, 9), 0, K.TAU); c.fill(); }
    });
    cam.layer(c, 1, () => {
      c.lineCap = "round"; c.strokeStyle = K.rgba(s.colors.foreground, 0.75); c.lineWidth = 7;
      for (const node of plan.nodes) if (node.parent >= 0) {
        const parent = plan.nodes[node.parent];
        K.drawOn(c, K.linePoints(parent.x, parent.y, node.x, node.y, 2), K.ease.outCubic(K.between(s.time, node.at - 0.3, node.at)));
      }
      for (const node of plan.nodes) {
        const q = K.spring(s.time - node.at, { from: 0, to: 1, stiffness: 300, damping: 15 });
        dot(c, node.x, node.y, (node.ring === 0 ? 46 : node.ring === 1 ? 36 : 28) * q, node.ring === 2 && q < 0.02 ? s.colors.foreground : s.colors.accent);
      }
    });
    // The Count Sits In Screen Space, Outside The Camera.
    const told = plan.nodes.filter(node => s.time >= node.at).length;
    c.fillStyle = s.colors.foreground; c.font = K.font(u * 9, 800); c.textAlign = "center"; c.textBaseline = "middle";
    c.fillText(String(told), s.cx, s.safe.top + u * 8);
    c.font = K.font(u * 3.4, 600); c.fillStyle = K.rgba(s.colors.foreground, 0.7);
    c.fillText(told === 1 ? "Person Knows" : "People Know", s.cx, s.safe.top + u * 15);
    paper(c, s);
  }
  function spreadEvents(s) {
    const cam = K.camera(s, { x: 0, y: 0, zoom: 0.72 * s.min / 1080 });
    return network(s).nodes.slice(1).map((node, i) => ({ id: "told-" + (i + 1), at: node.at, what: "Person " + (i + 2) + " Hears The Idea", kind: node.ring === 1 ? "first-ring" : "second-ring",
      pan: K.clamp((cam.toScreen(node.x, node.y).x / s.width) * 2 - 1, -1, 1), sound: node.ring === 1 ? "Twin Tick" : "Paper Tap", gain: node.ring === 1 ? 0.5 : 0.3 }));
  }

  // ---------------------------------------------------------------- Scene 4: The Town Knows
  // A Small Town Of Blocks In 3D. Windows Of Colour Spread Outward From The Middle While The Camera Orbits.
  function town(c, s) {
    const u = s.unit, space = s.space, random = s.rng("town"), start = s.beat("town", 0.6), blocks = [];
    for (let gx = -3; gx <= 3; gx++) for (let gz = -3; gz <= 3; gz++) {
      const height = random.range(0.5, 1.7), reach = Math.hypot(gx, gz), lit = K.between(s.time, start + reach * 0.22, start + reach * 0.22 + 0.35);
      blocks.push({ mesh: space.box(0.62, height, 0.62), place: { position: [gx * 0.95, height / 2, gz * 0.95] }, color: K.mixColor(s.params.block, s.colors.accent, lit), gloss: 0.2 });
    }
    const view = space.view({ cx: s.cx, cy: s.safe.top + s.safe.h * 0.52, size: s.min * 0.5, yaw: K.lerp(-38, 14, K.ease.inOutSine(s.progress)), pitch: 34, distance: 13, target: [0, 0.4, 0] });
    space.render(c, view, [{ mesh: space.plane(8.2, 8.2), color: s.params.ground, flat: true, twoSided: true }].concat(blocks), { yaw: -50, elevation: 52, color: "#fff4dc", intensity: 1.05 });
    s.use(c, "Chart", { kind: "Counter", from: 13, to: s.params.people, at: start, duration: 2.4, label: "People Know By Friday", ticks: 0 }, { x: 0, y: s.safe.top, w: s.width, h: s.safe.h * 0.36, key: "count" });
    paper(c, s);
  }
  const townEvents = s => [{ id: "town-lights", at: s.beat("town", 0.6), what: "The Town Starts To Light Up", kind: "swell", pan: 0, sound: "Orbit Rise", gain: 0.5 }]
    .concat(s.events("Chart", { kind: "Counter", from: 13, to: s.params.people, at: s.beat("town", 0.6), duration: 2.4 }, { x: 0, y: s.safe.top, w: s.width, h: s.safe.h * 0.36, key: "count" }));

  MotionScenes.register("Idea Seed", seed, { events: seedEvents, defaults: { line: "Every Idea Starts Small." } });
  MotionScenes.register("Idea Spoken", spoken, { events: spokenEvents });
  MotionScenes.register("Idea Spread", spread, { events: spreadEvents });
  MotionScenes.register("Idea Town", town, { events: townEvents, defaults: { people: 4812, block: "#cdbfa8", ground: "#e2d6c2" } });
})();
