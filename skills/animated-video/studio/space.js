(function (root) {
  "use strict";
  const rad = n => n * Math.PI / 180;
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const sub = (a, b) => a.map((v, i) => v - b[i]);
  const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const unit = a => { const m = Math.hypot(...a) || 1; return a.map(v => v / m); };
  const rgb = hex => [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16));
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

  const api = { draw, faces };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.MotionSpace = api;
})(globalThis);
