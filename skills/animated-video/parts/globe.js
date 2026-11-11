// Globe: A Rotating Sphere With Markers Placed By Latitude And Longitude And Arcs That Draw On Between Points.
//
// The Globe Ships No Map Data And Traces None. The Graticule Style Draws Only Lines Of Latitude And Longitude.
// The Dots Style Scatters An Abstract Pattern Made From Seeded Noise. It Is Illustrative, Not Geographic, And
// Must Not Be Presented As A Map Of Real Places. Markers And Arcs Are Still Placed By True Latitude And Longitude.
//
// Options (All Optional, Set In The Scene Params):
//   style        "Graticule" Or "Dots".
//   center       [x, y] As Fractions Of The Frame. Default [0.5, 0.5].
//   radius       Sphere Radius As A Fraction Of The Short Side Of The Frame. Default 0.36.
//   latitude     Latitude Facing The Viewer At The Start, In Degrees. Default 18.
//   longitude    Longitude Facing The Viewer At The Start, In Degrees. Default 0.
//   spin         Steady Rotation In Degrees Per Second. Default 6. Use 0 To Hold Still.
//   views        Eased Moves: [{ at, duration, latitude, longitude, ease }]. Each Turns The Globe So That Point Faces
//                The Viewer When The Move Ends. The Spin Then Carries On From There.
//   markers      [{ id, lat, lon, label, at }]. Each Pops In At Its Time With A Pulse Ring. Far-Side Markers Are Hidden.
//   arcs         [{ from, to, at, duration, lift }]. from And to Are A Marker id Or [lat, lon]. The Arc Follows The
//                Great Circle, Rises Above The Surface By lift (Default 0.16 Of The Radius), And Draws On.
//   labels       false Hides Marker Labels. labelSize Scales Them.
//   step         Degrees Between Graticule Lines. Default 30.
//   seeThrough   true Shows Far-Side Graticule Lines Faintly.
//   dotStep      Degrees Between Dots In The Dots Style. Default 4.
//   land         Share Of Dots Drawn Bold In The Dots Style, From 0 To 1. Default 0.45.
//   seed         Chooses The Dot Pattern.
//   colors       Overrides: { sphere, line, dot, faint, marker, arc, label, rim }.
// Every Time Option Takes Seconds Since The Scene Began Or The Name Of A Beat.
//
// Events: marker.<id> (A Marker Appears), arc.<n>.start And arc.<n>.land (An Arc Leaves And Arrives),
// view.<n> (A View Move Begins). Each Carries A Left-Right Position From Where It Happens On Screen.
//
// Example Scene:
//   { "mode": "Code Scene", "draw": "Globe", "duration": 6, "params": { "style": "Graticule",
//     "markers": [{ "id": "a", "lat": 40, "lon": -74, "label": "Start", "at": 0.6 }, { "id": "b", "lat": 51, "lon": 0, "label": "Finish", "at": 1.4 }],
//     "arcs": [{ "from": "a", "to": "b", "at": 2, "duration": 1.4 }] } }
(function () {
  "use strict";
  const K = MotionKit, RAD = Math.PI / 180;
  const defaults = { style: "Graticule", center: [0.5, 0.5], radius: 0.36, latitude: 18, longitude: 0, spin: 6, views: [], markers: [], arcs: [],
    labels: true, labelSize: 1, step: 30, seeThrough: false, dotStep: 4, land: 0.45, seed: 1, colors: {} };
  const unitAt = (lat, lon) => [Math.cos(lat * RAD) * Math.sin(lon * RAD), Math.sin(lat * RAD), Math.cos(lat * RAD) * Math.cos(lon * RAD)];

  // Turn The Options Into One Timeline That Both The Picture And The Events Read.
  function plan(s) {
    const p = s.params, radius = p.radius * s.min, cx = p.center[0] * s.width, cy = p.center[1] * s.height;
    const keys = [[0, [p.latitude, p.longitude]]];
    let lat = p.latitude, base = p.longitude;
    const views = (p.views || []).map((view, n) => ({ n: n + 1, at: s.when(view.at, 0), duration: view.duration ?? 1.2, view })).sort((a, b) => a.at - b.at);
    for (const move of views) {
      const end = move.at + move.duration;
      keys.push([move.at, [lat, base]]);
      base += K.wrap((move.view.longitude ?? base + p.spin * end) - (base + p.spin * end), -180, 180);
      lat = move.view.latitude ?? lat;
      keys.push([end, [lat, base], move.view.ease || "inOutCubic"]);
    }
    // A Projector For One Moment: Unit Vector In, Screen Point Out. `lift` Scales The Distance From The Centre.
    const projector = time => {
      const pose = K.track(keys, time), a = (pose[1] + p.spin * time) * RAD, b = pose[0] * RAD, ca = Math.cos(a), sa = Math.sin(a), cb = Math.cos(b), sb = Math.sin(b);
      return (v, lift = 1) => {
        const x = v[0] * ca - v[2] * sa, z1 = v[0] * sa + v[2] * ca, y = v[1] * cb - z1 * sb, z = v[1] * sb + z1 * cb;
        return { x: cx + radius * lift * x, y: cy - radius * lift * y, z, seen: z > 0 || lift * Math.hypot(x, y) > 1 };
      };
    };
    const markers = (p.markers || []).map((marker, n) => ({ id: String(marker.id ?? n + 1), label: marker.label || "", at: s.when(marker.at, 0), v: unitAt(marker.lat, marker.lon) }));
    const end = ref => Array.isArray(ref) ? unitAt(ref[0], ref[1]) : (markers.find(marker => marker.id === String(ref)) || {}).v;
    const arcs = (p.arcs || []).map((arc, n) => ({ n: n + 1, at: s.when(arc.at, 0), duration: arc.duration ?? 1.2, lift: arc.lift ?? 0.16, a: end(arc.from), b: end(arc.to) }))
      .filter(arc => arc.a && arc.b);
    return { p, radius, cx, cy, projector, markers, arcs, views };
  }
  // Points Along The Great Circle Between Two Unit Vectors, Each With Its Height Above The Surface.
  function arcPoints(arc, count) {
    const dot = K.clamp(arc.a[0] * arc.b[0] + arc.a[1] * arc.b[1] + arc.a[2] * arc.b[2], -1, 1), angle = Math.acos(dot), out = [];
    if (angle < 1e-4 || angle > Math.PI - 1e-4) return out;
    for (let i = 0; i <= count; i++) {
      const u = i / count, wa = Math.sin((1 - u) * angle) / Math.sin(angle), wb = Math.sin(u * angle) / Math.sin(angle);
      out.push({ v: [arc.a[0] * wa + arc.b[0] * wb, arc.a[1] * wa + arc.b[1] * wb, arc.a[2] * wa + arc.b[2] * wb], lift: 1 + arc.lift * Math.sin(Math.PI * u) });
    }
    return out;
  }
  // Stroke The Parts Of A Projected Line That Are Seen, Or The Parts That Are Hidden.
  function strokeSeen(c, points, wanted) {
    let open = false;
    c.beginPath();
    for (const point of points) {
      if (point.seen !== wanted) { open = false; continue; }
      if (open) c.lineTo(point.x, point.y); else c.moveTo(point.x, point.y);
      open = true;
    }
    c.stroke();
  }

  function draw(c, s) {
    const g = plan(s), p = g.p, t = s.time, project = g.projector(t), R = g.radius, u = s.min / 100;
    const tone = Object.assign({
      sphere: K.mixColor(s.colors.background, s.colors.foreground, 0.09), line: K.rgba(s.colors.foreground, 0.34), dot: K.rgba(s.colors.foreground, 0.9),
      faint: K.rgba(s.colors.foreground, 0.16), marker: s.colors.accent, arc: s.colors.accent, label: s.colors.foreground, rim: K.rgba(s.colors.foreground, 0.5)
    }, p.colors);
    // The Sphere: A Soft Lit Disc.
    const glow = c.createRadialGradient(g.cx - R * 0.35, g.cy - R * 0.4, R * 0.1, g.cx, g.cy, R);
    glow.addColorStop(0, K.mixColor(tone.sphere, s.colors.foreground, 0.1)); glow.addColorStop(1, K.mixColor(tone.sphere, s.colors.background, 0.45));
    c.fillStyle = glow; c.beginPath(); c.arc(g.cx, g.cy, R, 0, K.TAU); c.fill();
    c.lineCap = "round"; c.lineJoin = "round";
    if (p.style === "Dots") {
      const step = Math.max(2, p.dotStep), seed = K.hash("globe", p.seed), cut = (0.5 - K.clamp(p.land)) * 0.5, bold = [], light = [];
      for (let lat = -90 + step / 2, row = 0; lat < 90; lat += step, row++) {
        const count = Math.max(1, Math.round(360 / step * Math.cos(lat * RAD)));
        for (let j = 0; j < count; j++) {
          const v = unitAt(lat, (j + (row % 2) * 0.5) * 360 / count), at = project(v);
          if (at.z <= 0.02) continue;
          const f = 3.3, value = (K.noise2(v[0] * f + 11, v[1] * f, seed) + K.noise2(v[1] * f + 37, v[2] * f, seed + 1) + K.noise2(v[2] * f + 71, v[0] * f, seed + 2)) / 3;
          (value > cut ? bold : light).push(at);
        }
      }
      for (const [list, fill, size] of [[light, tone.faint, 0.006], [bold, tone.dot, 0.0105]]) {
        c.fillStyle = fill; c.beginPath();
        for (const at of list) { const r = R * size * (0.45 + 0.55 * at.z); c.moveTo(at.x + r, at.y); c.arc(at.x, at.y, r, 0, K.TAU); }
        c.fill();
      }
    } else {
      const step = Math.max(5, p.step), lines = [];
      for (let lon = 0; lon < 360; lon += step) { const line = []; for (let lat = -90; lat <= 90; lat += 5) line.push(project(unitAt(lat, lon))); lines.push(line); }
      for (let lat = -90 + step; lat < 90; lat += step) { const line = []; for (let lon = 0; lon <= 360; lon += 5) line.push(project(unitAt(lat, lon))); lines.push(line); }
      c.lineWidth = Math.max(1, u * 0.22);
      if (p.seeThrough) { c.strokeStyle = tone.faint; for (const line of lines) strokeSeen(c, line, false); }
      c.strokeStyle = tone.line;
      for (const line of lines) strokeSeen(c, line, true);
    }
    c.strokeStyle = tone.rim; c.lineWidth = Math.max(1, u * 0.3); c.beginPath(); c.arc(g.cx, g.cy, R, 0, K.TAU); c.stroke();
    // Arcs Draw On From Their Start Point And Carry A Bright Head While They Travel.
    for (const arc of g.arcs) {
      const progress = K.ease.inOutCubic(K.between(t, arc.at, arc.at + arc.duration));
      if (progress <= 0) continue;
      const count = 48, all = arcPoints(arc, count), reach = progress * count, shown = [];
      if (!all.length) continue;
      for (let i = 0; i < all.length && i <= reach; i++) shown.push(project(all[i].v, all[i].lift));
      const whole = Math.floor(reach);
      if (whole < count) {
        const a = all[whole], b = all[whole + 1], f = reach - whole, mixed = [0, 1, 2].map(k => a.v[k] + (b.v[k] - a.v[k]) * f), size = Math.hypot(mixed[0], mixed[1], mixed[2]);
        shown.push(project(mixed.map(value => value / size), a.lift + (b.lift - a.lift) * f));
      }
      c.strokeStyle = tone.arc; c.lineWidth = Math.max(1.5, u * 0.55);
      strokeSeen(c, shown, true);
      const head = shown[shown.length - 1];
      if (head.seen && progress < 1) { c.fillStyle = tone.arc; c.beginPath(); c.arc(head.x, head.y, u * 0.9, 0, K.TAU); c.fill(); }
    }
    // Markers Pop In, Ring Once, And Fade As They Near The Edge Of The Sphere.
    const size = u * 3 * p.labelSize;
    for (const marker of g.markers) {
      const age = t - marker.at, at = project(marker.v);
      if (age < 0 || at.z <= 0.03) continue;
      const near = K.smooth(at.z / 0.3), pop = K.spring(age, "bouncy"), ring = K.between(age, 0, 0.9);
      c.save(); c.globalAlpha = near;
      if (ring < 1) { c.strokeStyle = K.rgba(tone.marker, (1 - ring) * 0.8); c.lineWidth = u * 0.35; c.beginPath(); c.arc(at.x, at.y, u * (1.2 + ring * 4.2), 0, K.TAU); c.stroke(); }
      c.fillStyle = tone.marker; c.beginPath(); c.arc(at.x, at.y, Math.max(0, u * 1.25 * pop), 0, K.TAU); c.fill();
      c.fillStyle = K.readable(tone.marker); c.beginPath(); c.arc(at.x, at.y, Math.max(0, u * 0.45 * pop), 0, K.TAU); c.fill();
      if (p.labels && marker.label) {
        c.font = K.font(size, 700);
        const width = c.measureText(marker.label).width, flip = at.x + u * 2.4 + width > s.width - u * 3, x = flip ? at.x - u * 2.4 - width : at.x + u * 2.4;
        c.globalAlpha = near * K.between(age, 0.1, 0.4);
        c.fillStyle = K.rgba(s.colors.background, 0.72); K.roundRect(c, x - size * 0.4, at.y - size * 0.78, width + size * 0.8, size * 1.56, size * 0.4); c.fill();
        c.fillStyle = tone.label; c.textAlign = "left"; c.textBaseline = "middle"; c.fillText(marker.label, x, at.y);
      }
      c.restore();
    }
  }

  function events(s) {
    const g = plan(s), out = [], pan = (v, time, lift) => K.clamp(g.projector(time)(v, lift).x / s.width * 2 - 1, -1, 1);
    for (const marker of g.markers) out.push({ id: "marker." + marker.id, at: marker.at, what: "Marker Appears" + (marker.label ? ": " + marker.label : ""), kind: "marker", pan: pan(marker.v, marker.at), sound: "Glass Point", gain: 0.5 });
    for (const arc of g.arcs) {
      out.push({ id: "arc." + arc.n + ".start", at: arc.at, what: "Arc " + arc.n + " Leaves", kind: "arc-start", pan: pan(arc.a, arc.at), sound: "Air Sweep", gain: 0.45 });
      out.push({ id: "arc." + arc.n + ".land", at: arc.at + arc.duration, what: "Arc " + arc.n + " Lands", kind: "arc-land", pan: pan(arc.b, arc.at + arc.duration), sound: "Paper Tap", gain: 0.6 });
    }
    for (const move of g.views) out.push({ id: "view." + move.n, at: move.at, what: "Globe Turns To A New View", kind: "move", pan: K.clamp(g.cx / s.width * 2 - 1, -1, 1) });
    return out;
  }

  MotionScenes.register("Globe", draw, { defaults, events, about: "A Rotating Sphere With Markers By Latitude And Longitude And Arcs That Draw On. Illustrative, Not A Map." });
})();
