// Chart: An Animated Bar Chart, Line Chart, Or Counter With A Neutral Look.
//
// Use It As A Scene Of Its Own, Or Inside Another Draw Function With s.use(c, "Chart", params, box).
// Copy This File Into A Film's Scenes Folder And Register It Under A New Name To Restyle It.
//
// Options (All Optional). Any Time Accepts Seconds Or The Name Of A Beat.
//   kind       "Bars", "Line", Or "Counter". Default "Bars".
//   title      A Heading Above The Chart.
//   data       For Bars And Line: A List Of { label, value } Entries Or Plain Numbers.
//   at         When The Chart Starts To Build. Default 0.3.
//   each       Bars: Seconds Between One Bar Starting And The Next. Default 0.14.
//   grow       Bars: Seconds Each Bar Takes To Rise. Default 0.7.
//   duration   Line: Seconds The Line Takes To Draw. Counter: Seconds The Count Takes. Default 1.6.
//   max, min   The Value Range Of The Vertical Scale. By Default It Runs From Zero To A Round Number Above The Largest Value.
//   ticks      How Many Divisions The Scale Shows. Zero Hides The Scale. Default 4.
//   highlight  Bars: The Index Of The One Bar Drawn In The Accent Colour, Counting From Zero. -1 Draws Every Bar In The Accent. Default -1.
//   values     Show Counting Value Labels. Default true.
//   area       Line: Shade The Area Under The Line. Default true.
//   dots       Line: Mark Each Data Point As The Line Passes It. Default true.
//   from, to   Counter: The First And Last Number. Defaults 0 And 100.
//   label      Counter: A Line Under The Number.
//   decimals, prefix, suffix   How Values Are Written, Such As { "prefix": "$", "suffix": "K" }.
//   colors     Overrides: { ink, accent, bar, muted, grid }. By Default They Come From The Scene Colours.
//
// Events Declared: bar-N When Each Bar Lands, line-start And line-end, count-start And count-end.
//
// Example Scene:
//   { "mode": "Code Scene", "draw": "Chart", "duration": 5,
//     "params": { "kind": "Bars", "title": "Orders Per Week", "data": [{ "label": "Mon", "value": 12 }, { "label": "Tue", "value": 19 }] } }
(function () {
  "use strict";
  const K = MotionKit;
  const defaults = {
    kind: "Bars", title: "", data: [{ label: "One", value: 12 }, { label: "Two", value: 19 }, { label: "Three", value: 27 }, { label: "Four", value: 34 }],
    at: 0.3, each: 0.14, grow: 0.7, duration: 1.6, max: null, min: 0, ticks: 4, highlight: -1, values: true, area: true, dots: true,
    from: 0, to: 100, label: "", decimals: 0, prefix: "", suffix: "", colors: {}
  };
  function roundUp(value) {
    if (!(value > 0)) return 1;
    const step = Math.pow(10, Math.floor(Math.log10(value)));
    for (const m of [1, 2, 2.5, 4, 5, 8, 10]) if (m * step >= value - 1e-9) return m * step;
    return 10 * step;
  }
  // Everything Both The Picture And The Events Depend On.
  function plan(s) {
    const p = s.params, safe = s.safe, u = Math.min(safe.w, safe.h) / 100, at = s.when(p.at, 0.3);
    const items = (Array.isArray(p.data) ? p.data : []).map(d => typeof d === "number" ? { label: "", value: d } : { label: String(d && d.label != null ? d.label : ""), value: Number(d && d.value) || 0 });
    const low = Number.isFinite(p.min) ? p.min : 0, peak = Math.max(low, ...items.map(item => item.value));
    const high = Number.isFinite(p.max) && p.max > low ? p.max : low + roundUp(peak - low);
    const titleHeight = p.title ? u * 16 : 0, gutter = p.ticks > 0 ? u * 13 : u * 2;
    const left = safe.left + gutter, right = safe.right - u * 3, width = right - left;
    const room = safe.h - titleHeight - u * 24, height = Math.max(u * 10, Math.min(room, width * 1.05));
    const blockTop = safe.top + (safe.h - (titleHeight + height + u * 24)) / 2;
    const top = blockTop + titleHeight + u * 11, bottom = top + height, slot = items.length ? width / items.length : width;
    const y = value => bottom - height * K.clamp((value - low) / (high - low));
    return { p, u, at, items, low, high, left, right, width, top, bottom, height, slot, y, titleTop: blockTop, each: p.each, grow: Math.max(0.01, p.grow), duration: Math.max(0.01, p.duration) };
  }
  function palette(s) {
    const o = s.params.colors || {}, fg = s.colors.foreground, bg = s.colors.background;
    return { ink: o.ink || fg, accent: o.accent || s.colors.accent, bar: o.bar || K.mixColor(fg, bg, 0.62), muted: o.muted || K.mixColor(fg, bg, 0.42), grid: o.grid || K.mixColor(fg, bg, 0.84) };
  }
  const write = (s, value) => K.formatNumber(value, { decimals: s.params.decimals, prefix: s.params.prefix, suffix: s.params.suffix });
  function label(c, text, x, y, size, weight, color, align, maxWidth) {
    if (!text) return;
    c.fillStyle = color;
    const fitted = K.fitText(c, text, { width: maxWidth, size, minSize: size * 0.45, weight, maxLines: 1 });
    K.drawText(c, fitted, x, y, { align, valign: "middle" });
  }
  // One Size For A Whole Row Of Labels: The Largest At Which The Longest Still Fits.
  function rowSize(c, texts, size, weight, maxWidth) {
    return texts.reduce((least, text) => text ? Math.min(least, K.fitText(c, text, { width: maxWidth, size, minSize: size * 0.45, weight, maxLines: 1 }).size) : least, size);
  }
  function frame(c, s, g, tone) {
    const t = s.time, show = K.between(t, g.at - 0.3, g.at + 0.1);
    if (g.p.title) {
      c.save(); c.globalAlpha *= K.between(t, 0, 0.35);
      c.fillStyle = tone.ink;
      const fitted = K.fitText(c, g.p.title, { width: s.safe.w, height: g.u * 15, size: g.u * 8, weight: 700, maxLines: 2 });
      K.drawText(c, fitted, s.safe.left, g.titleTop + (1 - K.ease.outCubic(K.between(t, 0, 0.45))) * g.u * 2, { align: "left" });
      c.restore();
    }
    if (g.p.kind === "Counter") return;
    c.save(); c.globalAlpha *= show;
    const ticks = Math.max(0, Math.round(g.p.ticks)), stepValue = ticks ? (g.high - g.low) / ticks : 0, places = [0, 1, 2, 3].find(d => Math.abs(stepValue - Number(stepValue.toFixed(d))) < 1e-9) ?? 3;
    c.lineWidth = Math.max(1, g.u * 0.25);
    for (let j = 1; j <= ticks; j++) {
      const y = g.y(g.low + stepValue * j);
      c.strokeStyle = tone.grid; c.beginPath(); c.moveTo(g.left, y); c.lineTo(g.left + g.width * show, y); c.stroke();
      label(c, K.formatNumber(g.low + stepValue * j, { decimals: places, prefix: g.p.prefix, suffix: g.p.suffix }), g.left - g.u * 1.6, y, g.u * 3.1, 400, tone.muted, "right", g.u * 11);
    }
    c.strokeStyle = tone.muted; c.lineWidth = Math.max(1.5, g.u * 0.45); c.lineCap = "round";
    c.beginPath(); c.moveTo(g.left, g.bottom); c.lineTo(g.left + g.width * show, g.bottom); c.stroke();
    c.restore();
  }
  function bars(c, s, g, tone) {
    const t = s.time, barWidth = g.slot * 0.62, size = Math.min(g.u * 4.6, g.slot * 0.34);
    const names = rowSize(c, g.items.map(item => item.label), Math.min(g.u * 3.8, g.slot * 0.3), 600, g.slot * 0.92);
    g.items.forEach((item, i) => {
      const start = g.at + i * g.each, raw = K.between(t, start, start + g.grow), rise = K.ease.outCubic(raw);
      const x = g.left + g.slot * (i + 0.5), top = g.y(g.low + (item.value - g.low) * rise);
      if (raw > 0) {
        c.fillStyle = g.p.highlight < 0 || g.p.highlight === i ? tone.accent : tone.bar;
        K.roundRect(c, x - barWidth / 2, top, barWidth, Math.max(0, g.bottom - top), Math.min(barWidth * 0.14, g.u * 1.4));
        c.fill();
        if (g.p.values) {
          c.save(); c.globalAlpha *= K.between(raw, 0, 0.25);
          label(c, write(s, K.count(0, item.value, raw, "outCubic")), x, top - size * 0.95, size, 700, tone.ink, "center", g.slot * 0.96);
          c.restore();
        }
      }
      c.save(); c.globalAlpha *= K.between(t, start - 0.1, start + 0.25);
      label(c, item.label, x, g.bottom + g.u * 4.6, names, 600, tone.muted, "center", g.slot * 0.92);
      c.restore();
    });
  }
  function line(c, s, g, tone) {
    const t = s.time, n = g.items.length;
    if (!n) return;
    const xAt = i => n > 1 ? g.left + g.width * i / (n - 1) : g.left + g.width / 2;
    const points = g.items.map((item, i) => [xAt(i), g.y(item.value)]);
    const drawn = K.ease.inOutCubic(K.between(t, g.at, g.at + g.duration)), total = K.pathLength(points);
    const names = rowSize(c, g.items.map(item => item.label), Math.min(g.u * 3.6, g.width / n * 0.3), 600, g.width / n * 0.92);
    g.items.forEach((item, i) => {
      c.save(); c.globalAlpha *= K.between(t, g.at - 0.2 + i * 0.03, g.at + 0.15 + i * 0.03);
      label(c, item.label, xAt(i), g.bottom + g.u * 4.6, names, 600, tone.muted, "center", g.width / n * 0.92);
      c.restore();
    });
    if (drawn <= 0 || n < 2) return;
    const part = drawn >= 1 ? points : K.slicePath(points, 0, drawn);
    if (part.length < 2) return;
    const tip = part[part.length - 1];
    if (g.p.area) {
      c.fillStyle = K.rgba(tone.accent, 0.16);
      K.tracePath(c, part.concat([[tip[0], g.bottom], [part[0][0], g.bottom]]), true); c.fill();
    }
    c.strokeStyle = tone.accent; c.lineWidth = Math.max(2, g.u * 0.9); c.lineCap = "round"; c.lineJoin = "round";
    K.tracePath(c, part); c.stroke();
    let walked = 0;
    if (g.p.dots) points.forEach((point, i) => {
      if (i) walked += Math.hypot(point[0] - points[i - 1][0], point[1] - points[i - 1][1]);
      const reached = total ? walked / total : 0;
      if (drawn < reached) return;
      const pop = Math.max(0, K.spring((drawn - reached) * 6, "bouncy"));
      c.fillStyle = s.colors.background; c.strokeStyle = tone.accent; c.lineWidth = Math.max(1.5, g.u * 0.6);
      c.beginPath(); c.arc(point[0], point[1], g.u * 1.5 * pop, 0, K.TAU); c.fill(); c.stroke();
    });
    c.fillStyle = tone.accent; c.beginPath(); c.arc(tip[0], tip[1], g.u * 1.7, 0, K.TAU); c.fill();
    if (g.p.values) {
      const value = g.low + (g.bottom - tip[1]) / g.height * (g.high - g.low), size = g.u * 4.6, near = tip[0] > g.right - g.u * 12;
      label(c, write(s, drawn >= 1 ? g.items[n - 1].value : value), tip[0], tip[1] - size * 1.15, size, 700, tone.ink, near ? "right" : "center", g.u * 30);
    }
  }
  function counter(c, s, g, tone) {
    const t = s.time, raw = K.between(t, g.at, g.at + g.duration), value = K.count(g.p.from, g.p.to, raw, "outCubic"), safe = s.safe;
    const settle = t >= g.at + g.duration ? 1 + 0.05 * (1 - K.spring(t - g.at - g.duration, "bouncy")) : 1;
    const widest = Math.abs(g.p.to) >= Math.abs(g.p.from) ? g.p.to : g.p.from, cy = safe.cy;
    c.save(); c.globalAlpha *= K.between(t, g.at - 0.25, g.at + 0.1);
    const fitted = K.fitText(c, write(s, widest), { width: safe.w * 0.94, height: Math.min(safe.h * 0.4, g.u * 34), size: g.u * 34, weight: 800, maxLines: 1 });
    c.translate(safe.cx, cy); c.scale(settle, settle); c.translate(-safe.cx, -cy);
    c.fillStyle = tone.ink; c.font = fitted.font; c.textAlign = "center"; c.textBaseline = "middle";
    c.fillText(write(s, value), safe.cx, cy);
    c.restore();
    const barY = cy + fitted.size * 0.72, barWidth = Math.min(safe.w * 0.5, fitted.width);
    c.save(); c.globalAlpha *= K.between(t, g.at - 0.25, g.at + 0.1);
    c.fillStyle = tone.grid; K.roundRect(c, safe.cx - barWidth / 2, barY, barWidth, g.u * 1.1, g.u * 0.55); c.fill();
    if (raw > 0) { c.fillStyle = tone.accent; K.roundRect(c, safe.cx - barWidth / 2, barY, barWidth * K.ease.outCubic(raw), g.u * 1.1, g.u * 0.55); c.fill(); }
    c.restore();
    if (g.p.label) {
      c.save(); c.globalAlpha *= K.between(t, g.at, g.at + 0.4);
      c.fillStyle = tone.muted;
      const text = K.fitText(c, g.p.label, { width: safe.w * 0.86, size: g.u * 5, weight: 600, maxLines: 2 });
      K.drawText(c, text, safe.cx, barY + g.u * 4.5, { align: "center" });
      c.restore();
    }
  }
  function draw(c, s) {
    const g = plan(s), tone = palette(s);
    frame(c, s, g, tone);
    if (g.p.kind === "Counter") counter(c, s, g, tone);
    else if (g.p.kind === "Line") line(c, s, g, tone);
    else bars(c, s, g, tone);
  }
  function events(s) {
    const g = plan(s), pan = x => K.clamp(x / s.width * 2 - 1, -1, 1);
    if (g.p.kind === "Counter") return [
      { id: "count-start", at: g.at, what: "Counter Starts", kind: "start", pan: 0, sound: "Air Sweep", gain: 0.35 },
      { id: "count-end", at: g.at + g.duration, what: "Counter Lands On " + write(s, g.p.to), kind: "land", pan: 0, sound: "Glass Point", gain: 0.5 }];
    if (g.p.kind === "Line") return g.items.length < 2 ? [] : [
      { id: "line-start", at: g.at, what: "Line Starts Drawing", kind: "start", pan: pan(g.left), sound: "Air Sweep", gain: 0.4 },
      { id: "line-end", at: g.at + g.duration, what: "Line Reaches " + write(s, g.items[g.items.length - 1].value), kind: "land", pan: pan(g.right), sound: "Glass Point", gain: 0.5 }];
    return g.items.map((item, i) => ({ id: "bar-" + (i + 1), at: g.at + i * g.each + g.grow, what: "Bar " + (item.label || i + 1) + " Lands", kind: "land", pan: pan(g.left + g.slot * (i + 0.5)), sound: "Paper Tap", gain: 0.35 }));
  }
  MotionScenes.register("Chart", draw, { defaults, events, about: "An Animated Bar Chart, Line Chart, Or Counter." });
})();
