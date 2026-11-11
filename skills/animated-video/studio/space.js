(function (root) {
  "use strict";
  const rad = n => n * Math.PI / 180;
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const sub = (a, b) => a.map((v, i) => v - b[i]);
  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const unit = a => { const m = Math.hypot(...a) || 1; return a.map(v => v / m); };
  const rgb = hex => hex[0] === "#" ? [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16)) : (hex.match(/[0-9.]+/g) || [0, 0, 0]).slice(0, 3).map(Number);
  const tau = Math.PI * 2;
  const meshes = {};
  function faces(shape) {
    if (meshes[shape]) return meshes[shape];
    const mesh = [];
    function face(points, outward) {
      let normal = unit(cross(sub(points[1], points[0]), sub(points[2], points[0])));
      if (dot(normal, outward) < 0) normal = normal.map(v => -v);
      mesh.push({ points, normal });
    }
    if (shape === "Orbit Ring") {
      const point = (u, v) => [(1.02 + 0.37 * Math.cos(v)) * Math.cos(u), 0.37 * Math.sin(v), (1.02 + 0.37 * Math.cos(v)) * Math.sin(u)];
      for (let i = 0; i < 32; i++) for (let j = 0; j < 12; j++) {
        const u = i / 32 * tau, u2 = (i + 1) / 32 * tau, v = j / 12 * tau, v2 = (j + 1) / 12 * tau;
        const um = (u + u2) / 2, vm = (v + v2) / 2;
        face([point(u, v), point(u, v2), point(u2, v2), point(u2, v)], [Math.cos(vm) * Math.cos(um), Math.sin(vm), Math.cos(vm) * Math.sin(um)]);
      }
    } else if (shape === "Crystal") {
      const ring = Array.from({length: 7}, (_, i) => [Math.cos(i / 7 * tau), 0, Math.sin(i / 7 * tau)]);
      for (let i = 0; i < ring.length; i++) {
        const a = ring[i], b = ring[(i + 1) % ring.length];
        face([a, b, [0.18, 1.53, 0.08]], [a[0] + b[0], 0.8, a[2] + b[2]]);
        face([b, a, [-0.14, -1.21, 0]], [a[0] + b[0], -0.8, a[2] + b[2]]);
      }
    } else {
      const sides = 6, r = 0.98, height = 0.93;
      const point = (i, y) => [r * Math.cos(i / sides * tau), y, r * Math.sin(i / sides * tau)];
      for (let i = 0; i < sides; i++) face([point(i, -height), point(i + 1, -height), point(i + 1, height), point(i, height)], point(i + 0.5, 0));
      for (const y of [-height, height]) face(Array.from({length: sides}, (_, i) => point(i, y)), [0, y, 0]);
    }
    meshes[shape] = mesh;
    return mesh;
  }

  function draw(ctx, scene, fraction, cx, cy, size) {
    const yaw = rad(scene.azimuth + scene.orbit * fraction), pitch = rad(scene.elevation), dist = scene.distance;
    const camera = [dist * Math.sin(yaw) * Math.cos(pitch), dist * Math.sin(pitch), dist * Math.cos(yaw) * Math.cos(pitch)];
    const forward = unit(camera.map(v => -v)), right = unit(cross(forward, [0, 1, 0])), up = cross(right, forward);
    const angle = rad(scene.spin * fraction + 12), tilt = rad(scene.shape === "Orbit Ring" ? 35 : -12);
    const coat = rgb(scene.material), lamp = rgb(scene.light);
    const lightYaw = rad(scene.lightYaw), lightPitch = rad(scene.lightElevation);
    const key = [Math.sin(lightYaw) * Math.cos(lightPitch), Math.sin(lightPitch), Math.cos(lightYaw) * Math.cos(lightPitch)];
    function rotate(p) {
      const y = p[1] * Math.cos(tilt) - p[2] * Math.sin(tilt), z = p[1] * Math.sin(tilt) + p[2] * Math.cos(tilt);
      return [p[0] * Math.cos(angle) + z * Math.sin(angle), y, -p[0] * Math.sin(angle) + z * Math.cos(angle)];
    }
    const distanceY = Math.sin(fraction * Math.PI * 2) * 0.07;
    const queue = [];
    for (const face of faces(scene.shape)) {
      const points = face.points.map(p => { const result = rotate(p); result[1] += distanceY; return result; });
      const centre = [0, 1, 2].map(i => points.reduce((sum, p) => sum + p[i], 0) / points.length);
      const normal = rotate(face.normal), view = unit(sub(camera, centre));
      if (dot(normal, view) <= 0) continue;
      const projected = points.map(p => {
        const v = sub(p, camera), z = dot(v, forward);
        return [cx + dot(v, right) * size * 1.8 / z, cy - dot(v, up) * size * 1.8 / z, z];
      });
      const diffuse = Math.max(0, dot(normal, key)), half = unit(view.map((v, i) => v + key[i]));
      const shine = Math.pow(Math.max(0, dot(normal, half)), 4 + 66 * scene.gloss) * scene.gloss;
      const rim = Math.pow(1 - Math.max(0, dot(normal, view)), 3) * 0.22;
      const shade = coat.map((channel, i) => Math.round(Math.max(0, Math.min(255, channel * (0.25 + 0.83 * diffuse * scene.intensity * lamp[i] / 255) + lamp[i] * (shine * scene.intensity * 0.7 + rim)))));
      queue.push({ p: projected, z: projected.reduce((sum, p) => sum + p[2], 0) / points.length, fill: "rgb(" + shade.join(",") + ")" });
    }
    queue.sort((a, b) => b.z - a.z);
    for (const face of queue) {
      ctx.beginPath();
      face.p.forEach(([x, y], i) => i ? ctx.lineTo(x, y) : ctx.moveTo(x, y));
      ctx.closePath(); ctx.fillStyle = face.fill; ctx.strokeStyle = face.fill; ctx.lineWidth = 0.7; ctx.fill(); ctx.stroke();
    }
  }

  // ---------------------------------------------------------------- Geometry And Cameras For Code Scenes
  // A Mesh Is A List Of Faces. A Face Is { points, normal } With Points As [x, y, z] And Y Pointing Up.
  function faceOf(points, outward) {
    let normal = unit(cross(sub(points[1], points[0]), sub(points[2], points[0])));
    if (dot(normal, outward) < 0) normal = normal.map(v => -v);
    return { points, normal };
  }
  function box(width = 1, height = 1, depth = 1) {
    const x = width / 2, y = height / 2, z = depth / 2;
    return [
      faceOf([[-x, -y, z], [x, -y, z], [x, y, z], [-x, y, z]], [0, 0, 1]), faceOf([[-x, -y, -z], [x, -y, -z], [x, y, -z], [-x, y, -z]], [0, 0, -1]),
      faceOf([[x, -y, -z], [x, -y, z], [x, y, z], [x, y, -z]], [1, 0, 0]), faceOf([[-x, -y, -z], [-x, -y, z], [-x, y, z], [-x, y, -z]], [-1, 0, 0]),
      faceOf([[-x, y, -z], [x, y, -z], [x, y, z], [-x, y, z]], [0, 1, 0]), faceOf([[-x, -y, -z], [x, -y, -z], [x, -y, z], [-x, -y, z]], [0, -1, 0])
    ];
  }
  // A Flat Rectangle Facing Up. Render It With twoSided When The Camera Can Pass Below It.
  const plane = (width = 1, depth = 1) => [faceOf([[-width / 2, 0, -depth / 2], [width / 2, 0, -depth / 2], [width / 2, 0, depth / 2], [-width / 2, 0, depth / 2]], [0, 1, 0])];
  function sphere(radius = 1, segments = 20, rings = 12) {
    const point = (i, j) => { const u = i / segments * tau, v = j / rings * Math.PI; return [radius * Math.sin(v) * Math.cos(u), radius * Math.cos(v), radius * Math.sin(v) * Math.sin(u)]; };
    const mesh = [];
    for (let j = 0; j < rings; j++) for (let i = 0; i < segments; i++) {
      const corners = j === 0 ? [point(i, 0), point(i, 1), point(i + 1, 1)] : j === rings - 1 ? [point(i, j), point(i, j + 1), point(i + 1, j)] : [point(i, j), point(i, j + 1), point(i + 1, j + 1), point(i + 1, j)];
      mesh.push(faceOf(corners, point(i + 0.5, j + 0.5)));
    }
    return mesh;
  }
  // A Cylinder Around The Y Axis. A Top Radius Of Zero Makes A Cone.
  function cylinder(radius = 1, height = 2, sides = 24, topRadius = radius) {
    const y = height / 2, ring = (r, level, i) => [r * Math.cos(i / sides * tau), level, r * Math.sin(i / sides * tau)], mesh = [];
    for (let i = 0; i < sides; i++) {
      const outward = [Math.cos((i + 0.5) / sides * tau), topRadius < radius ? (radius - topRadius) / height : 0, Math.sin((i + 0.5) / sides * tau)];
      mesh.push(faceOf(topRadius > 0 ? [ring(radius, -y, i), ring(radius, -y, i + 1), ring(topRadius, y, i + 1), ring(topRadius, y, i)] : [ring(radius, -y, i), ring(radius, -y, i + 1), [0, y, 0]], outward));
    }
    mesh.push(faceOf(Array.from({ length: sides }, (_, i) => ring(radius, -y, i)), [0, -1, 0]));
    if (topRadius > 0) mesh.push(faceOf(Array.from({ length: sides }, (_, i) => ring(topRadius, y, i)), [0, 1, 0]));
    return mesh;
  }
  function torus(major = 1, minor = 0.35, around = 32, across = 12) {
    const point = (u, v) => [(major + minor * Math.cos(v)) * Math.cos(u), minor * Math.sin(v), (major + minor * Math.cos(v)) * Math.sin(u)], mesh = [];
    for (let i = 0; i < around; i++) for (let j = 0; j < across; j++) {
      const u = i / around * tau, u2 = (i + 1) / around * tau, v = j / across * tau, v2 = (j + 1) / across * tau, um = (u + u2) / 2, vm = (v + v2) / 2;
      mesh.push(faceOf([point(u, v), point(u, v2), point(u2, v2), point(u2, v)], [Math.cos(vm) * Math.cos(um), Math.sin(vm), Math.cos(vm) * Math.sin(um)]));
    }
    return mesh;
  }
  // Give A Flat Outline Of [x, y] Points Thickness Along Z. The Outline May Be Concave But Must Not Cross Itself.
  function extrude(outline, depth = 0.2) {
    const z = depth / 2, mesh = [];
    let area = 0;
    for (let i = 0; i < outline.length; i++) { const a = outline[i], b = outline[(i + 1) % outline.length]; area += a[0] * b[1] - b[0] * a[1]; }
    const turn = area >= 0 ? 1 : -1;
    mesh.push({ points: outline.map(p => [p[0], p[1], z]), normal: [0, 0, 1] }, { points: outline.map(p => [p[0], p[1], -z]), normal: [0, 0, -1] });
    for (let i = 0; i < outline.length; i++) {
      const a = outline[i], b = outline[(i + 1) % outline.length];
      if (a[0] === b[0] && a[1] === b[1]) continue;
      mesh.push({ points: [[a[0], a[1], -z], [b[0], b[1], -z], [b[0], b[1], z], [a[0], a[1], z]], normal: unit([(b[1] - a[1]) * turn, -(b[0] - a[0]) * turn, 0]) });
    }
    return mesh;
  }
  // Position, Turn, And Size A Mesh. Rotation Is In Degrees Around X, Then Y, Then Z.
  function place(options = {}) {
    const position = options.position || [0, 0, 0], turn = (options.rotate || [0, 0, 0]).map(rad);
    const size = typeof options.scale === "number" ? [options.scale, options.scale, options.scale] : options.scale || [1, 1, 1];
    const [cx, cy, cz] = turn.map(Math.cos), [sx, sy, sz] = turn.map(Math.sin);
    const spin = p => {
      const y1 = p[1] * cx - p[2] * sx, z1 = p[1] * sx + p[2] * cx;
      const x2 = p[0] * cy + z1 * sy, z2 = -p[0] * sy + z1 * cy;
      return [x2 * cz - y1 * sz, x2 * sz + y1 * cz, z2];
    };
    return {
      point: p => { const r = spin([p[0] * size[0], p[1] * size[1], p[2] * size[2]]); return [r[0] + position[0], r[1] + position[1], r[2] + position[2]]; },
      normal: n => unit(spin([n[0] / (size[0] || 1e-6), n[1] / (size[1] || 1e-6), n[2] / (size[2] || 1e-6)]))
    };
  }
  // A Perspective Camera That Looks At A Target From A Yaw, Pitch, And Distance. Angles Are In Degrees.
  // cx And cy Place The Target On The Canvas. size Sets How Large One Unit Appears.
  function view(options = {}) {
    const target = options.target || [0, 0, 0], yaw = rad(options.yaw ?? 0), pitch = rad(options.pitch ?? 20), distance = options.distance ?? 6;
    const cx = options.cx ?? 0, cy = options.cy ?? 0, reach = (options.size ?? 500) * (options.lens ?? 1.8);
    const position = [target[0] + distance * Math.sin(yaw) * Math.cos(pitch), target[1] + distance * Math.sin(pitch), target[2] + distance * Math.cos(yaw) * Math.cos(pitch)];
    const forward = unit(sub(target, position)), right = unit(cross(forward, [0, 1, 0])), up = cross(right, forward);
    return {
      position, forward, right, up, target,
      // Returns [x, y, depth]. A Depth At Or Below Zero Means The Point Is Behind The Camera.
      project(p) {
        const v = sub(p, position), z = dot(v, forward), safe = z > 0.0001 ? z : 0.0001;
        return [cx + dot(v, right) * reach / safe, cy - dot(v, up) * reach / safe, z];
      },
      // How Many Pixels One Unit Covers At A Point.
      scaleAt(p) { const z = dot(sub(p, position), forward); return z > 0.0001 ? reach / z : 0; }
    };
  }
  // A Directional Light. Yaw And Elevation Are In Degrees.
  function light(options = {}) {
    const yaw = rad(options.yaw ?? -37), elevation = rad(options.elevation ?? 44);
    return { direction: [Math.sin(yaw) * Math.cos(elevation), Math.sin(elevation), Math.cos(yaw) * Math.cos(elevation)], color: rgb(options.color || "#ffffff"), intensity: options.intensity ?? 1, ambient: options.ambient ?? 0.25 };
  }
  function shade(normal, toViewer, surface, lamp, gloss) {
    const diffuse = Math.max(0, dot(normal, lamp.direction)), half = unit(toViewer.map((v, i) => v + lamp.direction[i]));
    const shine = Math.pow(Math.max(0, dot(normal, half)), 4 + 66 * gloss) * gloss, rim = Math.pow(1 - Math.max(0, dot(normal, toViewer)), 3) * 0.22;
    return surface.map((channel, i) => Math.round(Math.max(0, Math.min(255, channel * (lamp.ambient + 0.83 * diffuse * lamp.intensity * lamp.color[i] / 255) + lamp.color[i] * (shine * lamp.intensity * 0.7 + rim)))));
  }
  // Draw Lit Meshes Through A Camera, Far Faces First.
  // Each Item Is { mesh, color, gloss, place, twoSided, flat, opacity, outline }. `place` Is A place() Result Or Its Options.
  function render(ctx, camera, items, lamp) {
    const key = lamp && lamp.direction ? lamp : light(lamp || {}), queue = [];
    for (const item of items) {
      const move = item.place ? (typeof item.place.point === "function" ? item.place : place(item.place)) : null, surface = rgb(item.color || "#9aa7b4");
      for (const face of item.mesh) {
        const points = move ? face.points.map(move.point) : face.points;
        let normal = move ? move.normal(face.normal) : face.normal;
        const centre = [0, 1, 2].map(i => points.reduce((sum, p) => sum + p[i], 0) / points.length), toViewer = unit(sub(camera.position, centre));
        if (dot(normal, toViewer) <= 0) { if (!item.twoSided) continue; normal = normal.map(v => -v); }
        const projected = points.map(camera.project);
        if (projected.some(p => p[2] <= 0.05)) continue;
        const tone = item.flat ? surface : shade(normal, toViewer, surface, key, item.gloss ?? 0.3);
        queue.push({ p: projected, z: projected.reduce((sum, p) => sum + p[2], 0) / projected.length, fill: "rgb(" + tone.join(",") + ")", outline: item.outline, opacity: item.opacity ?? 1 });
      }
    }
    queue.sort((a, b) => b.z - a.z);
    for (const face of queue) {
      ctx.beginPath();
      face.p.forEach((p, i) => i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]));
      ctx.closePath();
      if (face.opacity < 1) { ctx.save(); ctx.globalAlpha *= face.opacity; }
      ctx.fillStyle = face.fill; ctx.strokeStyle = face.outline || face.fill; ctx.lineWidth = face.outline ? 1.5 : 0.7; ctx.fill(); ctx.stroke();
      if (face.opacity < 1) ctx.restore();
    }
    return queue.length;
  }
  // Stroke A Line Through 3D Points With The Current Stroke Style. Parts Behind The Camera Are Skipped.
  function path(ctx, camera, points, closed = false) {
    const projected = points.map(camera.project);
    let open = false;
    ctx.beginPath();
    const count = closed ? projected.length + 1 : projected.length;
    for (let i = 0; i < count; i++) {
      const p = projected[i % projected.length];
      if (p[2] <= 0.05) { open = false; continue; }
      if (open) ctx.lineTo(p[0], p[1]); else ctx.moveTo(p[0], p[1]);
      open = true;
    }
    ctx.stroke();
  }

  const api = { draw, faces, box, plane, sphere, cylinder, torus, extrude, place, view, light, render, path };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.MotionSpace = api;
})(globalThis);
