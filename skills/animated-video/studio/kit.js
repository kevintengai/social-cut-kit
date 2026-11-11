// Motion Kit: Framework-Free Drawing Helpers For Code Scenes.
// Every Helper Is A Pure Function Of Its Arguments. Nothing Here Reads A Clock Or Math.random.
// The Kit Runs Unchanged In Motion Studio, In The Remotion Adapter, And In Node.
(function (root) {
  "use strict";
  const TAU = Math.PI * 2;

  // ---------------------------------------------------------------- Numbers
  const clamp = (value, min = 0, max = 1) => value < min ? min : value > max ? max : value;
  const lerp = (a, b, t) => a + (b - a) * t;
  const unlerp = (a, b, value) => a === b ? (value >= b ? 1 : 0) : (value - a) / (b - a);
  const remap = (value, inMin, inMax, outMin, outMax, clamped = true) => {
    const u = unlerp(inMin, inMax, value);
    return lerp(outMin, outMax, clamped ? clamp(u) : u);
  };
  // Progress Of A Time Window: 0 Before Start, 1 After End.
  const between = (t, start, end) => end <= start ? (t >= start ? 1 : 0) : clamp((t - start) / (end - start));
  const smooth = x => { const u = clamp(x); return u * u * (3 - 2 * u); };
  const wrap = (value, min, max) => { const span = max - min; return span <= 0 ? min : min + ((((value - min) % span) + span) % span); };
  const snap = (value, step) => step > 0 ? Math.round(value / step) * step : value;
  const rad = degrees => degrees * Math.PI / 180;
  const deg = radians => radians * 180 / Math.PI;
  // A Smooth Bump That Rises From 0 To 1 And Falls Back Across One Window.
  const pulse = (t, start, duration) => { const u = between(t, start, start + duration); return Math.sin(u * Math.PI) ** 2; };

  // ---------------------------------------------------------------- Easing
  const bounceOut = x => {
    const n = 7.5625, d = 2.75;
    if (x < 1 / d) return n * x * x;
    if (x < 2 / d) { x -= 1.5 / d; return n * x * x + 0.75; }
    if (x < 2.5 / d) { x -= 2.25 / d; return n * x * x + 0.9375; }
    x -= 2.625 / d; return n * x * x + 0.984375;
  };
  const power = n => ({
    in: x => Math.pow(x, n),
    out: x => 1 - Math.pow(1 - x, n),
    inOut: x => x < 0.5 ? Math.pow(2 * x, n) / 2 : 1 - Math.pow(2 - 2 * x, n) / 2
  });
  const quad = power(2), cubic = power(3), quart = power(4), quint = power(5);
  const back = 1.70158, backWide = back * 1.525;
  const ease = {
    linear: x => x,
    hold: x => x >= 1 ? 1 : 0,
    inQuad: quad.in, outQuad: quad.out, inOutQuad: quad.inOut,
    inCubic: cubic.in, outCubic: cubic.out, inOutCubic: cubic.inOut,
    inQuart: quart.in, outQuart: quart.out, inOutQuart: quart.inOut,
    inQuint: quint.in, outQuint: quint.out, inOutQuint: quint.inOut,
    inSine: x => 1 - Math.cos(x * Math.PI / 2),
    outSine: x => Math.sin(x * Math.PI / 2),
    inOutSine: x => (1 - Math.cos(Math.PI * x)) / 2,
    inExpo: x => x <= 0 ? 0 : Math.pow(2, 10 * x - 10),
    outExpo: x => x >= 1 ? 1 : 1 - Math.pow(2, -10 * x),
    inOutExpo: x => x <= 0 ? 0 : x >= 1 ? 1 : x < 0.5 ? Math.pow(2, 20 * x - 10) / 2 : (2 - Math.pow(2, 10 - 20 * x)) / 2,
    inCirc: x => 1 - Math.sqrt(1 - x * x),
    outCirc: x => Math.sqrt(1 - (x - 1) * (x - 1)),
    inOutCirc: x => x < 0.5 ? (1 - Math.sqrt(1 - 4 * x * x)) / 2 : (Math.sqrt(1 - (2 - 2 * x) * (2 - 2 * x)) + 1) / 2,
    inBack: x => (back + 1) * x * x * x - back * x * x,
    outBack: x => 1 + (back + 1) * Math.pow(x - 1, 3) + back * Math.pow(x - 1, 2),
    inOutBack: x => x < 0.5
      ? Math.pow(2 * x, 2) * ((backWide + 1) * 2 * x - backWide) / 2
      : (Math.pow(2 * x - 2, 2) * ((backWide + 1) * (2 * x - 2) + backWide) + 2) / 2,
    outElastic: x => x <= 0 ? 0 : x >= 1 ? 1 : Math.pow(2, -10 * x) * Math.sin((10 * x - 0.75) * TAU / 3) + 1,
    inElastic: x => x <= 0 ? 0 : x >= 1 ? 1 : -Math.pow(2, 10 * x - 10) * Math.sin((10 * x - 10.75) * TAU / 3),
    outBounce: bounceOut,
    inBounce: x => 1 - bounceOut(1 - x)
  };
  // A CSS-Style Cubic Curve Through (0,0), (x1,y1), (x2,y2), (1,1).
  function bezier(x1, y1, x2, y2) {
    const axis = (a, b, t) => ((1 - 3 * b + 3 * a) * t + (3 * b - 6 * a)) * t * t + 3 * a * t;
    const slope = (a, b, t) => 3 * (1 - 3 * b + 3 * a) * t * t + 2 * (3 * b - 6 * a) * t + 3 * a;
    return x => {
      if (x <= 0) return 0;
      if (x >= 1) return 1;
      let t = x;
      for (let i = 0; i < 6; i++) {
        const d = slope(x1, x2, t);
        if (Math.abs(d) < 1e-6) break;
        t = clamp(t - (axis(x1, x2, t) - x) / d);
      }
      let low = 0, high = 1;
      for (let i = 0; i < 24 && Math.abs(axis(x1, x2, t) - x) > 1e-6; i++) {
        if (axis(x1, x2, t) < x) low = t; else high = t;
        t = (low + high) / 2;
      }
      return axis(y1, y2, t);
    };
  }
  const steps = count => x => Math.min(1, Math.floor(clamp(x) * count) / Math.max(1, count - 1));
  function easing(value) {
    if (typeof value === "function") return value;
    if (value == null) return ease.linear;
    if (Object.prototype.hasOwnProperty.call(ease, value)) return ease[value];
    throw new Error("Unknown Easing Name: " + value);
  }
  // Move From One Value To Another Across A Time Window.
  const tween = (t, start, duration, from, to, curve) => lerp(from, to, easing(curve)(between(t, start, start + duration)));

  // ---------------------------------------------------------------- Spring
  const springs = {
    soft: { stiffness: 90, damping: 18 },
    smooth: { stiffness: 170, damping: 26 },
    snappy: { stiffness: 320, damping: 28 },
    bouncy: { stiffness: 230, damping: 12 },
    heavy: { stiffness: 120, damping: 30, mass: 2 }
  };
  // Closed-Form Damped Spring. The Value At Any Time Needs No Earlier Frame.
  function spring(t, options = {}) {
    const o = typeof options === "string" ? springs[options] : options;
    if (!o) throw new Error("Unknown Spring Preset: " + options);
    const from = o.from ?? 0, to = o.to ?? 1;
    if (!(t > 0)) return from;
    const mass = o.mass ?? 1, stiffness = o.stiffness ?? 170, damping = o.damping ?? 26, velocity = o.velocity ?? 0;
    const natural = Math.sqrt(stiffness / mass), ratio = damping / (2 * Math.sqrt(stiffness * mass));
    const x0 = from - to, decay = Math.exp(-ratio * natural * t);
    let offset;
    if (ratio < 1 - 1e-6) {
      const w = natural * Math.sqrt(1 - ratio * ratio);
      offset = decay * (x0 * Math.cos(w * t) + (velocity + ratio * natural * x0) / w * Math.sin(w * t));
    } else if (ratio > 1 + 1e-6) {
      const w = natural * Math.sqrt(ratio * ratio - 1);
      offset = decay * (x0 * Math.cosh(w * t) + (velocity + ratio * natural * x0) / w * Math.sinh(w * t));
    } else offset = Math.exp(-natural * t) * (x0 + (velocity + natural * x0) * t);
    return to + offset;
  }
  // Eased Progress For Item Number `index` When Items Start One After Another.
  function stagger(t, index, options = {}) {
    const start = options.start ?? 0, each = options.each ?? 0.08, duration = options.duration ?? 0.5;
    return easing(options.ease ?? "outCubic")(between(t, start + index * each, start + index * each + duration));
  }

  // ---------------------------------------------------------------- Random And Noise
  function hash() {
    let h = 0x811c9dc5;
    for (let i = 0; i < arguments.length; i++) {
      const part = arguments[i];
      const text = typeof part === "number" ? (Number.isInteger(part) ? "#" + part : "#" + part.toPrecision(12)) : String(part);
      for (let j = 0; j < text.length; j++) { h ^= text.charCodeAt(j); h = Math.imul(h, 0x01000193); }
      h ^= 0x7c; h = Math.imul(h, 0x01000193);
    }
    h ^= h >>> 16; h = Math.imul(h, 0x7feb352d); h ^= h >>> 15; h = Math.imul(h, 0x846ca68b); h ^= h >>> 16;
    return h >>> 0;
  }
  // A Stateless Random Number In [0, 1) Named By Its Arguments.
  const rand = (...parts) => hash(...parts) / 4294967296;
  // A Seeded Generator. The Same Seed Always Yields The Same Sequence.
  function rng(seed = 1) {
    let state = hash("rng", seed) || 0x2545f491;
    const next = () => {
      state ^= state << 13; state ^= state >>> 17; state ^= state << 5;
      return (Math.imul(state, 0x9e3779b1) >>> 0) / 4294967296;
    };
    next.range = (min, max) => min + (max - min) * next();
    next.int = (min, max) => Math.floor(min + (max - min + 1) * next());
    next.pick = list => list[Math.floor(next() * list.length)];
    next.sign = () => next() < 0.5 ? -1 : 1;
    next.chance = (probability = 0.5) => next() < probability;
    next.gauss = () => (next() + next() + next() + next() - 2) * 0.866;
    next.shuffle = list => {
      const copy = list.slice();
      for (let i = copy.length - 1; i > 0; i--) { const j = Math.floor(next() * (i + 1)); const hold = copy[i]; copy[i] = copy[j]; copy[j] = hold; }
      return copy;
    };
    next.fork = key => rng(hash(seed, "fork", key));
    return next;
  }
  function lattice(ix, iy, seed) {
    let h = Math.imul(ix | 0, 0x27d4eb2d) ^ Math.imul(iy | 0, 0x165667b1) ^ Math.imul(seed | 0, 0x3c6ef372);
    h = Math.imul(h ^ (h >>> 15), 0x2c1b3c6d); h = Math.imul(h ^ (h >>> 12), 0x297a2d39); h ^= h >>> 15;
    return (h >>> 0) / 2147483648 - 1;
  }
  const fade = f => f * f * f * (f * (f * 6 - 15) + 10);
  const seedOf = seed => typeof seed === "number" && Number.isInteger(seed) ? seed : hash("noise", seed ?? 0);
  // Smooth Noise In [-1, 1]. Nearby Inputs Give Nearby Outputs.
  function noise(x, seed) {
    const s = seedOf(seed), i = Math.floor(x), f = x - i;
    return lerp(lattice(i, 0, s), lattice(i + 1, 0, s), fade(f));
  }
  function noise2(x, y, seed) {
    const s = seedOf(seed), ix = Math.floor(x), iy = Math.floor(y), u = fade(x - ix), v = fade(y - iy);
    return lerp(lerp(lattice(ix, iy, s), lattice(ix + 1, iy, s), u), lerp(lattice(ix, iy + 1, s), lattice(ix + 1, iy + 1, s), u), v);
  }
  function fbm(x, y, options = {}) {
    const octaves = options.octaves ?? 4, gain = options.gain ?? 0.5, lacunarity = options.lacunarity ?? 2, s = seedOf(options.seed);
    let sum = 0, weight = 1, total = 0, scale = 1;
    for (let i = 0; i < octaves; i++) { sum += noise2(x * scale, y * scale, s + i * 101) * weight; total += weight; weight *= gain; scale *= lacunarity; }
    return total ? sum / total : 0;
  }

  // ---------------------------------------------------------------- Colour
  const named = { black: [0, 0, 0, 1], white: [255, 255, 255, 1], transparent: [0, 0, 0, 0] };
  function hslToRgb(h, s, l) {
    const hue = wrap(h, 0, 360) / 60, c = (1 - Math.abs(2 * l - 1)) * s, x = c * (1 - Math.abs(hue % 2 - 1)), m = l - c / 2;
    const [r, g, b] = hue < 1 ? [c, x, 0] : hue < 2 ? [x, c, 0] : hue < 3 ? [0, c, x] : hue < 4 ? [0, x, c] : hue < 5 ? [x, 0, c] : [c, 0, x];
    return [(r + m) * 255, (g + m) * 255, (b + m) * 255];
  }
  // Read A Colour Into [Red, Green, Blue, Alpha] With Channels 0 To 255 And Alpha 0 To 1.
  function parseColor(value) {
    if (Array.isArray(value)) return [value[0], value[1], value[2], value[3] ?? 1];
    if (typeof value !== "string") throw new Error("A Colour Must Be A String Or A Channel List.");
    const text = value.trim().toLowerCase();
    if (named[text]) return named[text].slice();
    if (text[0] === "#") {
      const hex = text.slice(1);
      if (/^[0-9a-f]{3,4}$/.test(hex)) { const n = [...hex].map(ch => parseInt(ch + ch, 16)); return [n[0], n[1], n[2], n.length > 3 ? n[3] / 255 : 1]; }
      if (/^[0-9a-f]{6}([0-9a-f]{2})?$/.test(hex)) return [parseInt(hex.slice(0, 2), 16), parseInt(hex.slice(2, 4), 16), parseInt(hex.slice(4, 6), 16), hex.length > 6 ? parseInt(hex.slice(6, 8), 16) / 255 : 1];
    }
    const call = /^(rgba?|hsla?)\(([^)]*)\)$/.exec(text);
    if (call) {
      const parts = call[2].split(/[\s,\/]+/).filter(Boolean);
      const num = (part, scale) => part.endsWith("%") ? parseFloat(part) / 100 * scale : parseFloat(part);
      if (parts.length >= 3) {
        const a = parts.length > 3 ? clamp(num(parts[3], 1)) : 1;
        if (call[1].startsWith("rgb")) return [num(parts[0], 255), num(parts[1], 255), num(parts[2], 255), a];
        const rgb = hslToRgb(parseFloat(parts[0]), clamp(num(parts[1], 1)), clamp(num(parts[2], 1)));
        return [rgb[0], rgb[1], rgb[2], a];
      }
    }
    throw new Error("Unreadable Colour: " + value);
  }
  function rgba(color, alpha) {
    const c = parseColor(color), a = alpha === undefined ? c[3] : alpha;
    const channel = v => Math.round(clamp(v, 0, 255));
    return a >= 1 ? "rgb(" + channel(c[0]) + "," + channel(c[1]) + "," + channel(c[2]) + ")"
      : "rgba(" + channel(c[0]) + "," + channel(c[1]) + "," + channel(c[2]) + "," + Math.round(clamp(a) * 1000) / 1000 + ")";
  }
  const withAlpha = (color, alpha) => rgba(color, alpha);
  function mixColor(a, b, t) {
    const x = parseColor(a), y = parseColor(b), u = clamp(t);
    return rgba([lerp(x[0], y[0], u), lerp(x[1], y[1], u), lerp(x[2], y[2], u), lerp(x[3], y[3], u)]);
  }
  const lighten = (color, amount) => mixColor(color, [255, 255, 255, parseColor(color)[3]], amount);
  const darken = (color, amount) => mixColor(color, [0, 0, 0, parseColor(color)[3]], amount);
  const hsl = (h, s, l, alpha = 1) => { const c = hslToRgb(h, clamp(s), clamp(l)); return rgba([c[0], c[1], c[2], alpha]); };
  function toHsl(color) {
    const c = parseColor(color), r = c[0] / 255, g = c[1] / 255, b = c[2] / 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b), l = (max + min) / 2, d = max - min;
    if (!d) return [0, 0, l, c[3]];
    const s = d / (1 - Math.abs(2 * l - 1));
    const h = max === r ? ((g - b) / d + 6) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
    return [h * 60, s, l, c[3]];
  }
  const shiftHue = (color, degrees) => { const c = toHsl(color); return hsl(c[0] + degrees, c[1], c[2], c[3]); };
  function luminance(color) {
    const linear = v => { const u = v / 255; return u <= 0.03928 ? u / 12.92 : Math.pow((u + 0.055) / 1.055, 2.4); };
    const c = parseColor(color);
    return 0.2126 * linear(c[0]) + 0.7152 * linear(c[1]) + 0.0722 * linear(c[2]);
  }
  const contrast = (a, b) => { const x = luminance(a), y = luminance(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  // Pick Whichever Ink Reads Better On A Background.
  const readable = (background, light = "#ffffff", dark = "#111111") => contrast(background, light) >= contrast(background, dark) ? light : dark;
  // Sample A Colour Ramp With Evenly Spaced Stops.
  function ramp(colors, t) {
    if (colors.length === 1) return rgba(colors[0]);
    const x = clamp(t) * (colors.length - 1), i = Math.min(colors.length - 2, Math.floor(x));
    return mixColor(colors[i], colors[i + 1], x - i);
  }

  // ---------------------------------------------------------------- Keyframe Tracks
  function blend(a, b, u) {
    if (typeof a === "number" && typeof b === "number") return lerp(a, b, u);
    if (typeof a === "string" && typeof b === "string") {
      try { return mixColor(a, b, u); } catch (error) { return u < 1 ? a : b; }
    }
    if (Array.isArray(a) && Array.isArray(b)) return a.map((value, i) => blend(value, b[i] ?? value, u));
    if (a && b && typeof a === "object" && typeof b === "object") {
      const out = {};
      for (const key of Object.keys(a)) out[key] = key in b ? blend(a[key], b[key], u) : a[key];
      return out;
    }
    return u < 1 ? a : b;
  }
  // Keys Are [Time, Value, Easing]. The Easing On A Key Shapes The Move That Arrives At It.
  function track(keys, t) {
    if (!keys.length) throw new Error("A Track Needs At Least One Key.");
    const time = key => Array.isArray(key) ? key[0] : key.t;
    const value = key => Array.isArray(key) ? key[1] : key.value;
    const curve = key => Array.isArray(key) ? key[2] : key.ease;
    if (t <= time(keys[0])) return value(keys[0]);
    for (let i = 1; i < keys.length; i++) {
      if (t < time(keys[i])) {
        const u = easing(curve(keys[i]))(between(t, time(keys[i - 1]), time(keys[i])));
        return blend(value(keys[i - 1]), value(keys[i]), u);
      }
    }
    return value(keys[keys.length - 1]);
  }

  // ---------------------------------------------------------------- Paths
  // A Path Is A List Of [x, y] Points. Curves Are Sampled Into Points So Any Path Can Be Measured And Drawn On.
  const linePoints = (x1, y1, x2, y2, count = 2) => Array.from({ length: count }, (_, i) => [lerp(x1, x2, i / (count - 1)), lerp(y1, y2, i / (count - 1))]);
  function arcPoints(cx, cy, radius, start, end, count) {
    const n = count ?? Math.max(8, Math.ceil(Math.abs(end - start) / TAU * 72));
    return Array.from({ length: n + 1 }, (_, i) => { const a = lerp(start, end, i / n); return [cx + Math.cos(a) * radius, cy + Math.sin(a) * radius]; });
  }
  const circlePoints = (cx, cy, radius, count = 72) => arcPoints(cx, cy, radius, -Math.PI / 2, Math.PI * 1.5, count);
  function ellipsePoints(cx, cy, rx, ry, count = 72, rotation = 0) {
    const cos = Math.cos(rotation), sin = Math.sin(rotation);
    return Array.from({ length: count + 1 }, (_, i) => { const a = i / count * TAU, x = Math.cos(a) * rx, y = Math.sin(a) * ry; return [cx + x * cos - y * sin, cy + x * sin + y * cos]; });
  }
  const quadPoints = (p0, control, p1, count = 24) => Array.from({ length: count + 1 }, (_, i) => {
    const t = i / count, u = 1 - t;
    return [u * u * p0[0] + 2 * u * t * control[0] + t * t * p1[0], u * u * p0[1] + 2 * u * t * control[1] + t * t * p1[1]];
  });
  const cubicPoints = (p0, c1, c2, p1, count = 32) => Array.from({ length: count + 1 }, (_, i) => {
    const t = i / count, u = 1 - t, a = u * u * u, b = 3 * u * u * t, c = 3 * u * t * t, d = t * t * t;
    return [a * p0[0] + b * c1[0] + c * c2[0] + d * p1[0], a * p0[1] + b * c1[1] + c * c2[1] + d * p1[1]];
  });
  // A Smooth Curve Through Every Listed Point.
  function splinePoints(points, options = {}) {
    const segments = options.segments ?? 12, closed = Boolean(options.closed), n = points.length;
    if (n < 3) return points.map(p => [p[0], p[1]]);
    const at = i => closed ? points[((i % n) + n) % n] : points[clamp(i, 0, n - 1)];
    const out = [], last = closed ? n : n - 1;
    for (let i = 0; i < last; i++) {
      const p0 = at(i - 1), p1 = at(i), p2 = at(i + 1), p3 = at(i + 2);
      for (let j = 0; j < segments; j++) {
        const t = j / segments, t2 = t * t, t3 = t2 * t;
        out.push([0, 1].map(k => 0.5 * (2 * p1[k] + (p2[k] - p0[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2 + (3 * p1[k] - p0[k] - 3 * p2[k] + p3[k]) * t3)));
      }
    }
    out.push(closed ? [out[0][0], out[0][1]] : [points[n - 1][0], points[n - 1][1]]);
    return out;
  }
  function polygonPoints(cx, cy, radius, sides, rotation = -Math.PI / 2) {
    return Array.from({ length: sides + 1 }, (_, i) => { const a = rotation + i / sides * TAU; return [cx + Math.cos(a) * radius, cy + Math.sin(a) * radius]; });
  }
  function starPoints(cx, cy, outer, inner, tips = 5, rotation = -Math.PI / 2) {
    return Array.from({ length: tips * 2 + 1 }, (_, i) => { const a = rotation + i / (tips * 2) * TAU, r = i % 2 ? inner : outer; return [cx + Math.cos(a) * r, cy + Math.sin(a) * r]; });
  }
  function rectPoints(x, y, width, height, radius = 0, perCorner = 6) {
    const r = Math.min(radius, width / 2, height / 2);
    if (r <= 0) return [[x, y], [x + width, y], [x + width, y + height], [x, y + height], [x, y]];
    const out = [];
    const corner = (cx, cy, start) => { for (let i = 0; i <= perCorner; i++) { const a = start + i / perCorner * Math.PI / 2; out.push([cx + Math.cos(a) * r, cy + Math.sin(a) * r]); } };
    corner(x + width - r, y + r, -Math.PI / 2); corner(x + width - r, y + height - r, 0);
    corner(x + r, y + height - r, Math.PI / 2); corner(x + r, y + r, Math.PI);
    out.push([out[0][0], out[0][1]]);
    return out;
  }
  function pathLength(points) {
    let total = 0;
    for (let i = 1; i < points.length; i++) total += Math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]);
    return total;
  }
  // The Position And Heading At A Fraction Of The Path Length.
  function pointAt(points, fraction) {
    if (points.length === 1) return { x: points[0][0], y: points[0][1], angle: 0 };
    const target = clamp(fraction) * pathLength(points);
    let walked = 0;
    for (let i = 1; i < points.length; i++) {
      const a = points[i - 1], b = points[i], span = Math.hypot(b[0] - a[0], b[1] - a[1]);
      if (walked + span >= target || i === points.length - 1) {
        const u = span ? clamp((target - walked) / span) : 0;
        return { x: lerp(a[0], b[0], u), y: lerp(a[1], b[1], u), angle: Math.atan2(b[1] - a[1], b[0] - a[0]) };
      }
      walked += span;
    }
  }
  // The Part Of A Path Between Two Fractions Of Its Length.
  function slicePath(points, from, to) {
    const total = pathLength(points), start = clamp(Math.min(from, to)) * total, end = clamp(Math.max(from, to)) * total, out = [];
    if (!(end > start) || points.length < 2) return out;
    let walked = 0;
    for (let i = 1; i < points.length; i++) {
      const a = points[i - 1], b = points[i], span = Math.hypot(b[0] - a[0], b[1] - a[1]), next = walked + span;
      if (next >= start && walked <= end && span > 0) {
        const u0 = clamp((start - walked) / span), u1 = clamp((end - walked) / span);
        if (!out.length) out.push([lerp(a[0], b[0], u0), lerp(a[1], b[1], u0)]);
        out.push([lerp(a[0], b[0], u1), lerp(a[1], b[1], u1)]);
      }
      walked = next;
    }
    return out;
  }
  function tracePath(c, points, closed = false) {
    c.beginPath();
    for (let i = 0; i < points.length; i++) i ? c.lineTo(points[i][0], points[i][1]) : c.moveTo(points[i][0], points[i][1]);
    if (closed) c.closePath();
  }
  // Stroke The First Part Of A Path. Progress 0 Draws Nothing And 1 Draws It All.
  function drawOn(c, points, progress, options = {}) {
    const from = options.from ?? 0, p = clamp(progress);
    if (p <= from || points.length < 2) return null;
    const part = p >= 1 && from <= 0 ? points : slicePath(points, from, p);
    if (part.length < 2) return null;
    tracePath(c, part, Boolean(options.closed) && p >= 1 && from <= 0);
    c.stroke();
    const tip = part[part.length - 1], before = part[part.length - 2];
    return { x: tip[0], y: tip[1], angle: Math.atan2(tip[1] - before[1], tip[0] - before[0]) };
  }
  function roundRect(c, x, y, width, height, radius = 0) {
    const r = Math.max(0, Math.min(radius, width / 2, height / 2));
    c.beginPath();
    c.moveTo(x + r, y); c.lineTo(x + width - r, y); c.arc(x + width - r, y + r, r, -Math.PI / 2, 0);
    c.lineTo(x + width, y + height - r); c.arc(x + width - r, y + height - r, r, 0, Math.PI / 2);
    c.lineTo(x + r, y + height); c.arc(x + r, y + height - r, r, Math.PI / 2, Math.PI);
    c.lineTo(x, y + r); c.arc(x + r, y + r, r, Math.PI, Math.PI * 1.5);
    c.closePath();
  }
  // Spread Points Evenly Along A Path So Displacement Looks Even.
  function resample(points, spacing) {
    const total = pathLength(points), count = Math.max(1, Math.round(total / Math.max(1, spacing)));
    return Array.from({ length: count + 1 }, (_, i) => { const p = pointAt(points, i / count); return [p.x, p.y]; });
  }
  // Line Boil: Displace A Path With Smooth Noise. Change `step` A Few Times A Second For A Hand-Drawn Shimmer.
  function boilPath(points, options = {}) {
    const amount = options.amount ?? 2, seed = hash("boil", options.seed ?? 0, options.step ?? 0), scale = options.scale ?? 0.02;
    const source = options.spacing ? resample(points, options.spacing) : points;
    return source.map((p, i) => [p[0] + noise2(p[0] * scale + i * 0.013, p[1] * scale, seed) * amount, p[1] + noise2(p[0] * scale, p[1] * scale + i * 0.013, seed + 7919) * amount]);
  }
  // The Whole-Number Boil Step For A Time. Eight Steps A Second Suits Most Hand-Drawn Looks.
  const boilStep = (time, rate = 8) => Math.floor(time * rate + 1e-6);
  // Time Rounded Down To A Held Drawing. stepTime(t, 24, 2) Advances Twelve Times A Second, So Nothing Slides Between Drawings.
  const stepTime = (time, fps = 24, frames = 2) => Math.floor(time * fps / frames + 1e-6) * frames / fps;
  // A Stroke Drawn As A Filled Ribbon Whose Width Swells Through The Middle And Tapers At Both Ends.
  // Options: width, taper (The Share Of The Length That Tapers At Each End), tip (Width Share Left At The Tips), progress, wobble, seed.
  function ribbon(c, points, options = {}) {
    const progress = options.progress ?? 1, path = progress >= 1 ? points : slicePath(points, 0, progress);
    if (path.length < 2) return;
    const half = (options.width ?? 6) / 2, taper = Math.max(1e-6, options.taper ?? 0.3), tip = options.tip ?? 0.12, wobble = options.wobble ?? 0, seed = hash("ribbon", options.seed ?? 0);
    const total = pathLength(path), left = [], right = [];
    let walked = 0;
    for (let i = 0; i < path.length; i++) {
      const before = path[Math.max(0, i - 1)], after = path[Math.min(path.length - 1, i + 1)];
      if (i) walked += Math.hypot(path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1]);
      const u = total ? walked / total : 0, span = Math.hypot(after[0] - before[0], after[1] - before[1]) || 1;
      const nx = -(after[1] - before[1]) / span, ny = (after[0] - before[0]) / span;
      const w = half * lerp(tip, 1, smooth(Math.min(u, 1 - u) / taper)) * (1 + wobble * noise(walked * 0.05, seed));
      left.push([path[i][0] + nx * w, path[i][1] + ny * w]); right.push([path[i][0] - nx * w, path[i][1] - ny * w]);
    }
    tracePath(c, left.concat(right.reverse()), true);
    c.fill();
  }
  // The Middle Joint Of A Two-Bone Limb, Such As A Knee Or An Elbow, From Its Two Ends And Fixed Bone Lengths.
  // `bend` Is 1 Or -1 And Picks The Side The Joint Bends Toward. A Target Out Of Reach Is Pulled Back To The Limb's Full Length.
  function joint(ax, ay, bx, by, upper, lower, bend = 1) {
    const dx = bx - ax, dy = by - ay, reach = Math.hypot(dx, dy) || 1e-6, ux = dx / reach, uy = dy / reach;
    const d = clamp(reach, Math.abs(upper - lower) + 1e-6, upper + lower - 1e-6);
    const along = (upper * upper - lower * lower + d * d) / (2 * d), off = Math.sqrt(Math.max(0, upper * upper - along * along)) * bend;
    return { x: ax + ux * along - uy * off, y: ay + uy * along + ux * off, endX: ax + ux * d, endY: ay + uy * d };
  }
  // A Rectangle With Uneven Torn Edges For Paper Collage Shapes.
  function tornRect(x, y, width, height, options = {}) {
    const tooth = options.tooth ?? 14, depth = options.depth ?? 5, random = rng(hash("torn", options.seed ?? 0)), out = [];
    const edge = (x1, y1, x2, y2, nx, ny) => {
      const count = Math.max(2, Math.round(Math.hypot(x2 - x1, y2 - y1) / tooth));
      for (let i = 0; i < count; i++) { const u = i / count, push = (random() - 0.5) * 2 * depth; out.push([lerp(x1, x2, u) + nx * push, lerp(y1, y2, u) + ny * push]); }
    };
    edge(x, y, x + width, y, 0, 1); edge(x + width, y, x + width, y + height, 1, 0);
    edge(x + width, y + height, x, y + height, 0, 1); edge(x, y + height, x, y, 1, 0);
    out.push([out[0][0], out[0][1]]);
    return out;
  }
  function arrowHead(c, x, y, angle, size) {
    c.beginPath();
    c.moveTo(x + Math.cos(angle) * size * 0.2, y + Math.sin(angle) * size * 0.2);
    c.lineTo(x + Math.cos(angle + 2.6) * size, y + Math.sin(angle + 2.6) * size);
    c.lineTo(x + Math.cos(angle - 2.6) * size, y + Math.sin(angle - 2.6) * size);
    c.closePath(); c.fill();
  }

  // ---------------------------------------------------------------- Text
  const font = (size, weight = 400, family = "Arial, sans-serif") => weight + " " + Math.round(size * 100) / 100 + "px " + family;
  // Break Text Into Lines That Fit A Width. A Newline Forces A Break. The Context Font Must Already Be Set.
  function wrapText(c, text, width) {
    const lines = [];
    for (const paragraph of String(text).split("\n")) {
      let line = "";
      for (const word of paragraph.trim().split(/\s+/u).filter(Boolean)) {
        if (line && c.measureText(line + " " + word).width > width) { lines.push(line); line = ""; }
        if (c.measureText(word).width > width) {
          for (const letter of word) {
            if (line && c.measureText(line + letter).width > width) { lines.push(line); line = ""; }
            line += letter;
          }
        } else line += (line ? " " : "") + word;
      }
      lines.push(line);
    }
    while (lines.length > 1 && !lines[lines.length - 1]) lines.pop();
    return lines;
  }
  // Find The Largest Size At Which Text Fits A Box. The Context Font Is Left At That Size.
  function fitText(c, text, box = {}) {
    const weight = box.weight ?? 700, family = box.family ?? "Arial, sans-serif", leading = box.lineHeight ?? 1.14;
    const min = box.minSize ?? 10, width = box.width ?? Infinity, height = box.height ?? Infinity, maxLines = box.maxLines ?? Infinity;
    let low = min, high = Math.max(min, box.size ?? 96), best = null;
    const attempt = size => {
      c.font = font(size, weight, family);
      const lines = wrapText(c, text, width), widest = Math.max(0, ...lines.map(line => c.measureText(line).width));
      return { lines, size, lineHeight: size * leading, width: widest, height: lines.length * size * leading, weight, family, font: font(size, weight, family),
        fits: lines.length <= maxLines && lines.length * size * leading <= height + 0.01 && widest <= width + 0.01 };
    };
    const top = attempt(high);
    if (top.fits) best = top;
    else {
      for (let i = 0; i < 14 && high - low > 0.5; i++) {
        const middle = (low + high) / 2, result = attempt(middle);
        if (result.fits) { best = result; low = middle; } else high = middle;
      }
      if (!best) best = attempt(min);
    }
    c.font = best.font;
    return best;
  }
  // Draw Wrapped Or Fitted Text. `layout` Is A String, A Line List, Or The Result Of fitText.
  function drawText(c, layout, x, y, options = {}) {
    const lines = typeof layout === "string" ? layout.split("\n") : Array.isArray(layout) ? layout : layout.lines;
    if (layout && layout.font) c.font = layout.font;
    const size = layout && layout.size ? layout.size : parseFloat(/(\d+(?:\.\d+)?)px/.exec(c.font)?.[1] ?? "16");
    const lineHeight = options.lineHeight ?? (layout && layout.lineHeight) ?? size * 1.14, total = lines.length * lineHeight;
    const align = options.align ?? "left", valign = options.valign ?? "top";
    const top = valign === "middle" ? y - total / 2 : valign === "bottom" ? y - total : y;
    c.textAlign = align; c.textBaseline = "middle";
    for (let i = 0; i < lines.length; i++) {
      const lineY = top + (i + 0.5) * lineHeight;
      if (options.stroke) c.strokeText(lines[i], x, lineY);
      if (options.fill !== false) c.fillText(lines[i], x, lineY);
    }
    return { width: Math.max(0, ...lines.map(line => c.measureText(line).width)), height: total, top };
  }
  // Place Every Word Of A Text Block So A Scene Can Animate Words One By One.
  // Positions Are Relative To The Top Left Of The Block. Draw Each Word With textAlign Left And textBaseline Middle.
  function layoutWords(c, text, box = {}) {
    const fitted = fitText(c, text, box), align = box.align ?? "left", space = c.measureText(" ").width, words = [];
    let index = 0;
    fitted.lines.forEach((line, row) => {
      const lineWidth = c.measureText(line).width;
      let x = align === "center" ? (fitted.width - lineWidth) / 2 : align === "right" ? fitted.width - lineWidth : 0;
      for (const word of line.split(" ").filter(Boolean)) {
        const width = c.measureText(word).width;
        words.push({ text: word, x, y: (row + 0.5) * fitted.lineHeight, width, line: row, index: index++ });
        x += width + space;
      }
    });
    return { words, size: fitted.size, font: fitted.font, lineHeight: fitted.lineHeight, width: fitted.width, height: fitted.height, lines: fitted.lines };
  }
  // The Visible Part Of A Line While It Types On.
  const typeOn = (text, progress) => { const letters = [...String(text)]; return letters.slice(0, Math.round(clamp(progress) * letters.length)).join(""); };

  // ---------------------------------------------------------------- Counters
  function formatNumber(value, options = {}) {
    const decimals = options.decimals ?? 0, fixed = Math.abs(value).toFixed(decimals), [whole, fraction] = fixed.split(".");
    const group = options.group ?? ",", padded = whole.padStart(options.pad ?? 0, "0");
    const grouped = group ? padded.replace(/\B(?=(\d{3})+(?!\d))/g, group) : padded;
    const sign = value < 0 && Number(fixed) !== 0 ? "-" : options.sign && value > 0 ? "+" : "";
    return (options.prefix ?? "") + sign + grouped + (fraction ? (options.point ?? ".") + fraction : "") + (options.suffix ?? "");
  }
  // A Number On Its Way From One Value To Another.
  const count = (from, to, progress, curve = "outCubic") => lerp(from, to, easing(curve)(clamp(progress)));

  // ---------------------------------------------------------------- Texture
  // Film Grain As Small Light And Dark Specks. `step` Chooses The Pattern, So Hold It For A Still Grain Or Change It To Boil.
  function grain(c, view, options = {}) {
    const size = options.size ?? Math.max(1.5, Math.min(view.width, view.height) / 420), amount = options.amount ?? 0.07;
    const specks = Math.min(options.max ?? 5000, Math.round(view.width * view.height / (size * size) * (options.density ?? 0.012)));
    const random = rng(hash("grain", options.seed ?? 0, options.step ?? 0));
    c.save();
    for (const tone of [options.dark ?? "#000000", options.light ?? "#ffffff"]) {
      c.fillStyle = tone; c.globalAlpha = amount;
      for (let i = 0; i < specks / 2; i++) { const scale = 0.6 + random() * 1.1; c.fillRect(random() * view.width, random() * view.height, size * scale, size * scale); }
    }
    c.restore();
  }
  // Darken The Frame Edges.
  function vignette(c, view, options = {}) {
    const cx = view.width / 2, cy = view.height / 2, reach = Math.hypot(cx, cy);
    const shade = c.createRadialGradient(cx, cy, reach * (options.inner ?? 0.45), cx, cy, reach);
    shade.addColorStop(0, rgba(options.color ?? "#000000", 0)); shade.addColorStop(1, rgba(options.color ?? "#000000", options.strength ?? 0.35));
    c.save(); c.fillStyle = shade; c.fillRect(0, 0, view.width, view.height); c.restore();
  }

  // ---------------------------------------------------------------- Camera
  // Slow Wandering Offsets Like A Camera Held By Hand.
  function drift(t, options = {}) {
    const amount = options.amount ?? 8, speed = options.speed ?? 0.35, seed = hash("drift", options.seed ?? 0);
    return { x: noise(t * speed, seed) * amount, y: noise(t * speed, seed + 1) * amount, rotate: noise(t * speed * 0.8, seed + 2) * (options.rotate ?? 0.25), zoom: 0 };
  }
  // A Decaying Shake That Starts At `at`.
  function shake(t, options = {}) {
    const at = options.at ?? 0, duration = options.duration ?? 0.4, u = (t - at) / duration;
    if (!(u >= 0 && u < 1)) return { x: 0, y: 0, rotate: 0, zoom: 0 };
    const amount = (options.amount ?? 14) * (1 - u) * (1 - u), rate = options.frequency ?? 24, seed = hash("shake", options.seed ?? 0);
    return { x: noise((t - at) * rate, seed) * amount, y: noise((t - at) * rate, seed + 1) * amount, rotate: noise((t - at) * rate, seed + 2) * (options.rotate ?? 0) * (1 - u), zoom: 0 };
  }
  // A 2D Camera. The Pose Names The World Point At The Frame Centre, A Zoom, And A Rotation In Degrees.
  // Extra Arguments Such As drift() And shake() Results Are Added To The Pose.
  function camera(view, pose = {}, ...extras) {
    let x = pose.x ?? view.width / 2, y = pose.y ?? view.height / 2, zoom = pose.zoom ?? 1, rotate = pose.rotate ?? 0;
    for (const extra of extras) if (extra) { x += extra.x ?? 0; y += extra.y ?? 0; rotate += extra.rotate ?? 0; zoom *= 1 + (extra.zoom ?? 0); }
    const cx = view.width / 2, cy = view.height / 2;
    const zoomAt = depth => 1 + (zoom - 1) * depth, angleAt = depth => rad(rotate) * clamp(depth);
    const cam = {
      x, y, zoom, rotate, width: view.width, height: view.height,
      // Depth 1 Follows The Camera Fully. Depth 0 Stays Pinned To The Frame. Values Between Move Less, Like Distant Layers.
      begin(c, depth = 1) {
        c.save(); c.translate(cx, cy); c.rotate(-angleAt(depth)); c.scale(zoomAt(depth), zoomAt(depth));
        c.translate(-lerp(cx, x, depth), -lerp(cy, y, depth));
      },
      end(c) { c.restore(); },
      layer(c, depth, paint) { cam.begin(c, depth); try { paint(); } finally { cam.end(c); } },
      toScreen(worldX, worldY, depth = 1) {
        const z = zoomAt(depth), a = -angleAt(depth), dx = (worldX - lerp(cx, x, depth)) * z, dy = (worldY - lerp(cy, y, depth)) * z;
        return { x: cx + dx * Math.cos(a) - dy * Math.sin(a), y: cy + dx * Math.sin(a) + dy * Math.cos(a) };
      },
      toWorld(screenX, screenY, depth = 1) {
        const z = zoomAt(depth), a = angleAt(depth), dx = screenX - cx, dy = screenY - cy;
        return { x: (dx * Math.cos(a) - dy * Math.sin(a)) / z + lerp(cx, x, depth), y: (dx * Math.sin(a) + dy * Math.cos(a)) / z + lerp(cy, y, depth) };
      },
      // The World Rectangle That Surely Covers The Frame At A Depth. Use It To Skip Offscreen Drawing.
      bounds(depth = 1) {
        const reach = Math.hypot(cx, cy) / zoomAt(depth), mx = lerp(cx, x, depth), my = lerp(cy, y, depth);
        return { left: mx - reach, top: my - reach, right: mx + reach, bottom: my + reach };
      }
    };
    return cam;
  }

  const api = {
    TAU, clamp, lerp, unlerp, remap, between, smooth, wrap, snap, rad, deg, pulse,
    ease, easing, bezier, steps, tween, spring, springs, stagger,
    hash, rand, rng, noise, noise2, fbm,
    parseColor, rgba, withAlpha, mixColor, lighten, darken, hsl, toHsl, shiftHue, luminance, contrast, readable, ramp,
    track,
    linePoints, arcPoints, circlePoints, ellipsePoints, quadPoints, cubicPoints, splinePoints, polygonPoints, starPoints, rectPoints,
    pathLength, pointAt, slicePath, tracePath, drawOn, roundRect, resample, boilPath, boilStep, stepTime, ribbon, joint, tornRect, arrowHead,
    font, wrapText, fitText, drawText, layoutWords, typeOn,
    formatNumber, count,
    grain, vignette,
    drift, shake, camera
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.MotionKit = api;
})(globalThis);
