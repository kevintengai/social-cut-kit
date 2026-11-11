// Phone: A Generic Handset Whose Screen Shows A Chat Thread Driven By A Plain List Of State Changes.
//
// The Handset And Its Interface Are Original And Generic. They Copy No Real App, Operating System, Or Brand.
// Restyle Them Freely, But Do Not Dress Them As A Real Product Unless The Owner Has The Right To Show It.
//
// Options (All Optional, Set In The Scene Params):
//   contact      The Name In The Header. Default "Sam". Its First Letter Fills The Round Avatar.
//   steps        The State Changes, In Any Order. Each Has `at` And `do`:
//                  { "at": 0.4, "do": "message", "from": "them", "text": "..." }   A Bubble Appears. from Is "them" Or "me".
//                  { "at": 1.6, "do": "typing", "for": 1.2 }                       The Other Person's Typing Dots Show.
//                                                                                  They End Early When Their Next Message Lands.
//                  { "at": 3.0, "do": "compose", "text": "...", "for": 1.0 }       Text Types Into The Message Field.
//                  { "at": 4.1, "do": "send" }                                     The Composed Text Becomes An Outgoing Bubble.
//                  { "at": 4.8, "do": "delivered" }                                A Delivered Label Appears Under The Last Outgoing Bubble.
//                  { "at": 6.0, "do": "notify", "title": "...", "text": "...", "for": 2.2 }   A Banner Drops From The Top.
//   center       [x, y] Of The Handset As Fractions Of The Frame. Default [0.5, 0.5].
//   height       Handset Height As A Fraction Of The Frame Height. Default 0.82. It Shrinks To Fit A Narrow Frame.
//   tilt         Rotation In Degrees. Default 0.
//   enter        Seconds The Handset Takes To Rise Into Place At The Start. Default 0.5. Use 0 To Begin In Place.
//   placeholder  The Hint In The Empty Message Field. Default "Message".
//   deliveredText  The Label Under A Delivered Bubble. Default "Delivered".
//   textSize     Scales All Screen Text. Default 1.
//   colors       Overrides: { body, rim, screen, bar, incoming, outgoing, text, outgoingText, muted, banner }.
// Every `at` Takes Seconds Since The Scene Began Or The Name Of A Beat.
//
// Events: step.<n>.receive, step.<n>.typing, step.<n>.compose, step.<n>.send, step.<n>.delivered, step.<n>.notify,
// Where <n> Is The Position Of The Step In The List, Counting From One.
//
// Example Scene:
//   { "mode": "Code Scene", "draw": "Phone", "duration": 6, "params": { "contact": "Sam", "steps": [
//     { "at": 0.5, "do": "message", "from": "them", "text": "Are We Still On For Friday?" },
//     { "at": 1.8, "do": "compose", "text": "Yes. Seven Works." }, { "at": 3.2, "do": "send" }, { "at": 3.9, "do": "delivered" } ] } }
(function () {
  "use strict";
  const K = MotionKit;
  const defaults = { contact: "Sam", steps: [], center: [0.5, 0.5], height: 0.82, tilt: 0, enter: 0.5, placeholder: "Message", deliveredText: "Delivered", textSize: 1, colors: {} };

  // Turn The Step List Into Thread Items, Drafts, And Banners That Both The Picture And The Events Read.
  function plan(s) {
    const p = s.params, items = [], drafts = [], banners = [], happenings = [];
    const steps = (p.steps || []).map((step, n) => Object.assign({}, step, { n: n + 1, at: s.when(step.at, 0) })).sort((a, b) => a.at - b.at || a.n - b.n);
    let draft = null, lastOut = null;
    for (const step of steps) {
      if (step.do === "message") {
        const item = { kind: "bubble", me: step.from === "me", text: String(step.text ?? ""), at: step.at };
        items.push(item);
        if (item.me) lastOut = item;
        happenings.push({ id: "step." + step.n + (item.me ? ".send" : ".receive"), at: step.at, what: item.me ? "Message Sent" : "Message Received", kind: item.me ? "send" : "receive", sound: item.me ? "Air Sweep" : "Glass Point", gain: 0.5 });
      } else if (step.do === "typing") {
        items.push({ kind: "typing", at: step.at, end: step.at + (step.for ?? 1.2) });
        happenings.push({ id: "step." + step.n + ".typing", at: step.at, what: "Typing Dots Appear", kind: "typing" });
      } else if (step.do === "compose") {
        const text = String(step.text ?? "");
        draft = { text, at: step.at, end: step.at + (step.for ?? Math.max(0.5, text.length * 0.045)), sent: Infinity };
        drafts.push(draft);
        happenings.push({ id: "step." + step.n + ".compose", at: step.at, what: "Reply Is Typed", kind: "compose", sound: "Twin Tick", gain: 0.35 });
      } else if (step.do === "send" && draft) {
        draft.sent = step.at;
        lastOut = { kind: "bubble", me: true, text: draft.text, at: step.at };
        items.push(lastOut); draft = null;
        happenings.push({ id: "step." + step.n + ".send", at: step.at, what: "Message Sent", kind: "send", sound: "Air Sweep", gain: 0.5 });
      } else if (step.do === "delivered" && lastOut && lastOut.delivered == null) {
        lastOut.delivered = step.at;
        happenings.push({ id: "step." + step.n + ".delivered", at: step.at, what: "Message Delivered", kind: "delivered", sound: "Paper Tap", gain: 0.45 });
      } else if (step.do === "notify") {
        banners.push({ title: String(step.title ?? ""), text: String(step.text ?? ""), at: step.at, end: step.at + (step.for ?? 2.2) });
        happenings.push({ id: "step." + step.n + ".notify", at: step.at, what: "Notification Arrives" + (step.title ? ": " + step.title : ""), kind: "notify", sound: "Glass Point", gain: 0.55 });
      }
    }
    for (const item of items) if (item.kind === "typing") {
      const next = items.find(other => other.kind === "bubble" && !other.me && other.at > item.at);
      if (next) item.end = Math.min(item.end, next.at);
    }
    const tall = Math.min(s.height * p.height, s.width * 0.9 * 2), wide = tall * 0.5;
    return { p, items, drafts, banners, happenings, tall, wide, cx: p.center[0] * s.width, cy: p.center[1] * s.height };
  }
  function clipText(c, text, width) {
    if (c.measureText(text).width <= width) return text;
    let cut = text;
    while (cut.length > 1 && c.measureText(cut + "…").width > width) cut = cut.slice(0, -1);
    return cut.trimEnd() + "…";
  }

  function draw(c, s) {
    const g = plan(s), p = g.p, t = s.time, W = g.wide, H = g.tall;
    const screen = p.colors.screen || K.mixColor(s.colors.background, s.colors.foreground, 0.94), ink = K.readable(screen, s.colors.foreground, s.colors.background);
    const tone = Object.assign({
      body: K.mixColor(s.colors.background, "#000000", 0.45), rim: K.rgba(s.colors.foreground, 0.32), screen, bar: K.mixColor(screen, ink, 0.06), incoming: K.mixColor(screen, ink, 0.12),
      outgoing: s.colors.accent, text: ink, outgoingText: K.readable(s.colors.accent, "#ffffff", "#10151a"), muted: K.mixColor(screen, ink, 0.5), banner: K.mixColor(ink, screen, 0.08)
    }, p.colors);
    const rise = p.enter > 0 ? (1 - K.ease.outCubic(K.between(t, 0, p.enter))) * s.height * 0.7 : 0;
    c.save();
    c.translate(g.cx, g.cy + rise); c.rotate(K.rad(p.tilt)); c.translate(-W / 2, -H / 2);
    // The Handset Body And Screen.
    c.fillStyle = tone.body; K.roundRect(c, 0, 0, W, H, W * 0.13); c.fill();
    c.strokeStyle = tone.rim; c.lineWidth = Math.max(1, W * 0.006); c.stroke();
    const inset = W * 0.04, sw = W - inset * 2, sh = H - inset * 2, fs = W * 0.056 * p.textSize, lh = fs * 1.28, pad = fs * 0.62, gap = fs * 0.5;
    c.translate(inset, inset);
    K.roundRect(c, 0, 0, sw, sh, W * 0.095); c.clip();
    c.fillStyle = tone.screen; c.fillRect(0, 0, sw, sh);
    const head = sh * 0.105, foot = sh * 0.092, side = sw * 0.045, areaTop = head, areaHeight = sh - head - foot;
    // The Thread: Measure Every Item, Stack Them, And Scroll So The Newest Stays In View.
    c.font = K.font(fs, 400);
    const placed = [];
    let cursor = 0;
    for (const item of g.items) {
      if (t < item.at) continue;
      const grow = K.ease.outCubic(K.between(t, item.at, item.at + 0.22));
      if (item.kind === "typing") {
        const here = grow * (1 - K.between(t, item.end, item.end + 0.12));
        if (here <= 0) continue;
        placed.push({ item, y: cursor, height: lh + pad * 1.4, width: fs * 3.4, here });
        cursor += (lh + pad * 1.4 + gap) * here;
      } else {
        const lines = K.wrapText(c, item.text, sw * 0.7 - pad * 2), width = Math.max(...lines.map(line => c.measureText(line).width)) + pad * 2, height = lines.length * lh + pad * 1.4;
        const label = item.delivered != null ? K.ease.outCubic(K.between(t, item.delivered, item.delivered + 0.2)) : 0;
        placed.push({ item, y: cursor, height, width, lines, here: grow, label });
        cursor += (height + gap) * grow + fs * 1.15 * label;
      }
    }
    const scroll = Math.max(0, cursor + pad - areaHeight);
    c.save();
    c.beginPath(); c.rect(0, areaTop, sw, areaHeight); c.clip();
    c.textBaseline = "middle";
    for (const row of placed) {
      const item = row.item, top = areaTop + pad + row.y - scroll, left = item.me ? sw - side - row.width : side, age = t - item.at;
      if (top > areaTop + areaHeight || top + row.height + fs * 1.3 < areaTop) continue;
      const pop = item.kind === "typing" ? row.here : Math.max(0, K.spring(age, "snappy"));
      c.save();
      c.globalAlpha = item.kind === "typing" ? row.here : K.between(age, 0, 0.1);
      c.translate(item.me ? left + row.width : left, top + row.height); c.scale(pop, pop); c.translate(-(item.me ? left + row.width : left), -(top + row.height));
      c.fillStyle = item.me ? tone.outgoing : tone.incoming;
      K.roundRect(c, left, top, row.width, row.height, Math.min(row.height / 2, fs * 0.95)); c.fill();
      if (item.kind === "typing") {
        c.fillStyle = tone.muted;
        for (let i = 0; i < 3; i++) {
          const hop = Math.max(0, Math.sin(age * 7 - i * 0.9)) * fs * 0.2;
          c.beginPath(); c.arc(left + row.width / 2 + (i - 1) * fs * 0.62, top + row.height / 2 - hop, fs * 0.19, 0, K.TAU); c.fill();
        }
      } else {
        c.fillStyle = item.me ? tone.outgoingText : tone.text; c.textAlign = "left"; c.font = K.font(fs, 400);
        row.lines.forEach((line, i) => c.fillText(line, left + pad, top + pad * 0.7 + (i + 0.5) * lh));
      }
      c.restore();
      if (row.label > 0) {
        c.save(); c.globalAlpha = row.label; c.fillStyle = tone.muted; c.font = K.font(fs * 0.68, 600); c.textAlign = "right";
        c.fillText(p.deliveredText, sw - side - fs * 0.2, top + row.height + fs * 0.62); c.restore();
      }
    }
    c.restore();
    // The Header: A Round Avatar With The Contact's Initial, And The Name.
    c.fillStyle = tone.bar; c.fillRect(0, 0, sw, head);
    c.fillStyle = K.rgba(tone.text, 0.1); c.fillRect(0, head - Math.max(1, W * 0.003), sw, Math.max(1, W * 0.003));
    const name = String(p.contact), avatar = head * 0.27, mid = head * 0.58;
    c.fillStyle = K.mixColor(tone.bar, tone.outgoing, 0.55); c.beginPath(); c.arc(side + avatar, mid, avatar, 0, K.TAU); c.fill();
    c.fillStyle = K.readable(K.mixColor(tone.bar, tone.outgoing, 0.55), "#ffffff", "#10151a"); c.font = K.font(avatar * 1.05, 700); c.textAlign = "center"; c.textBaseline = "middle";
    c.fillText(name.slice(0, 1).toUpperCase(), side + avatar, mid + avatar * 0.06);
    c.fillStyle = tone.text; c.font = K.font(fs * 1.02, 700); c.textAlign = "left";
    c.fillText(clipText(c, name, sw - side * 3 - avatar * 2), side + avatar * 2 + fs * 0.6, mid);
    // The Message Field And Send Button.
    const footTop = sh - foot, button = foot * 0.3, fieldHeight = foot * 0.6, fieldTop = footTop + (foot - fieldHeight) * 0.42, fieldWidth = sw - side * 2 - button * 2 - fs * 0.5;
    c.fillStyle = tone.bar; c.fillRect(0, footTop, sw, foot);
    c.fillStyle = tone.screen; K.roundRect(c, side, fieldTop, fieldWidth, fieldHeight, fieldHeight / 2); c.fill();
    c.strokeStyle = K.rgba(tone.text, 0.14); c.lineWidth = Math.max(1, W * 0.003); c.stroke();
    const live = g.drafts.filter(draft => t >= draft.at && t < draft.sent).pop(), sent = g.drafts.filter(draft => draft.sent <= t).pop();
    let typed = live ? K.typeOn(live.text, K.between(t, live.at, live.end)) : "";
    c.font = K.font(fs * 0.92, 400); c.textAlign = "left";
    const room = fieldWidth - fs * 1.5;
    if (typed) {
      let shown = typed;
      while (shown.length > 1 && c.measureText("…" + shown).width > room) shown = shown.slice(1);
      if (shown !== typed) shown = "…" + shown;
      c.fillStyle = tone.text; c.fillText(shown, side + fs * 0.75, fieldTop + fieldHeight / 2);
      if (t < live.end || Math.floor((t - live.end) * 2.5) % 2 === 0) c.fillRect(side + fs * 0.82 + c.measureText(shown).width, fieldTop + fieldHeight * 0.24, Math.max(1.5, fs * 0.07), fieldHeight * 0.52);
    } else { c.fillStyle = tone.muted; c.fillText(p.placeholder, side + fs * 0.75, fieldTop + fieldHeight / 2); }
    const press = sent ? K.pulse(t, sent.sent, 0.28) : 0, bx = sw - side - button, by = fieldTop + fieldHeight / 2, br = button * (1 - 0.18 * press);
    c.fillStyle = typed || press > 0 ? tone.outgoing : K.mixColor(tone.bar, tone.muted, 0.5); c.beginPath(); c.arc(bx, by, br, 0, K.TAU); c.fill();
    c.strokeStyle = typed || press > 0 ? tone.outgoingText : tone.screen; c.lineWidth = br * 0.2; c.lineCap = "round"; c.lineJoin = "round";
    c.beginPath(); c.moveTo(bx, by + br * 0.42); c.lineTo(bx, by - br * 0.42); c.moveTo(bx - br * 0.36, by - br * 0.06); c.lineTo(bx, by - br * 0.42); c.lineTo(bx + br * 0.36, by - br * 0.06); c.stroke();
    // Notification Banners Drop From The Top Edge And Leave The Same Way.
    for (const banner of g.banners) {
      if (t < banner.at || t > banner.end + 0.3) continue;
      const height = fs * 3.5, margin = sw * 0.035, shown = K.ease.outBack(K.between(t, banner.at, banner.at + 0.38)) - K.ease.inCubic(K.between(t, banner.end, banner.end + 0.3));
      const top = -height + (height + margin) * shown, icon = fs * 1.9;
      c.fillStyle = tone.banner; K.roundRect(c, margin, top, sw - margin * 2, height, fs * 0.9); c.fill();
      c.fillStyle = tone.outgoing; K.roundRect(c, margin + fs * 0.75, top + (height - icon) / 2, icon, icon, icon * 0.28); c.fill();
      const x = margin + fs * 0.75 + icon + fs * 0.7, room = sw - margin - fs * 0.8 - x, lettering = K.readable(tone.banner, "#ffffff", "#10151a");
      c.textAlign = "left"; c.textBaseline = "middle";
      c.fillStyle = lettering; c.font = K.font(fs * 0.86, 700); c.fillText(clipText(c, banner.title, room), x, top + height * 0.34);
      c.fillStyle = K.rgba(lettering, 0.78); c.font = K.font(fs * 0.82, 400); c.fillText(clipText(c, banner.text, room), x, top + height * 0.68);
    }
    c.restore();
  }

  function events(s) {
    const g = plan(s), pan = K.clamp(g.cx / s.width * 2 - 1, -1, 1);
    return g.happenings.map(event => Object.assign({ pan }, event));
  }

  MotionScenes.register("Phone", draw, { defaults, events, about: "A Generic Handset With A Chat Thread Driven By A List Of State Changes." });
})();
