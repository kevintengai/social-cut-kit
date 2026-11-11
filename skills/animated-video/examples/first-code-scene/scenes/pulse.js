// First Code Scene: A Title That Builds Word By Word, A Line That Draws On, And A Dot That Lands With A Spring.
// Copy This File, Rename The Draw Function, And Change What It Draws.
(function () {
  "use strict";
  // Times In Seconds Since The Scene Began. The Picture And The Events Both Read These.
  const LINE_STARTS = 0.4, LINE_SECONDS = 1.4, DOT_LANDS = LINE_STARTS + LINE_SECONDS;

  function draw(c, s) {
    const k = s.kit, u = s.unit, p = s.params;

    // The Title: Each Word Rises In, One After Another.
    const block = k.layoutWords(c, p.title, { width: s.safe.w, size: u * 11, weight: 800 });
    c.fillStyle = s.colors.foreground; c.textAlign = "left"; c.textBaseline = "middle";
    for (const word of block.words) {
      const q = k.stagger(s.time, word.index, { start: 0.15, each: 0.09, duration: 0.5, ease: "outCubic" });
      c.globalAlpha = q;
      c.fillText(word.text, s.safe.left + word.x, s.safe.top + u * 12 + word.y + (1 - q) * u * 3);
    }
    c.globalAlpha = 1;

    // The Line: A Smooth Curve That Draws On From Left To Right.
    const y = s.safe.top + s.safe.h * 0.62;
    const curve = k.splinePoints([[s.safe.left, y], [s.safe.left + s.safe.w * 0.3, y - u * 14], [s.safe.left + s.safe.w * 0.62, y + u * 9], [s.safe.right - u * 6, y - u * 6]]);
    c.strokeStyle = s.colors.accent; c.lineWidth = u * 1.1; c.lineCap = "round"; c.lineJoin = "round";
    const tip = k.drawOn(c, curve, k.ease.inOutCubic(k.between(s.time, LINE_STARTS, LINE_STARTS + LINE_SECONDS)));

    // The Dot: Rides The Tip Of The Line, Then Settles With A Spring When The Line Ends.
    if (tip) {
      const radius = u * 2.2 * (s.time < DOT_LANDS ? 1 : k.spring(s.time - DOT_LANDS, { from: 1.9, to: 1, stiffness: 260, damping: 14 }));
      c.fillStyle = s.colors.accent;
      c.beginPath(); c.arc(tip.x, tip.y, radius, 0, k.TAU); c.fill();
    }
    k.grain(c, s, { amount: 0.05, seed: s.seed, step: k.boilStep(s.time, 8) });
  }

  // What Happens In The Picture, For The Sound Cue Sheet.
  function events(s) {
    return [
      { id: "line-starts", at: LINE_STARTS, what: "The Line Starts To Draw", kind: "travel", pan: -0.8, sound: "Air Sweep", gain: 0.5 },
      { id: "dot-lands", at: DOT_LANDS, what: "The Dot Lands", kind: "land", pan: 0.7, sound: "Glass Point", gain: 0.6 }
    ];
  }

  MotionScenes.register("First Pulse", draw, { events, defaults: { title: "Draw It In Code" } });
})();
