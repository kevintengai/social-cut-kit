(function (root) {
  "use strict";
  const P = root.MotionProject;
  const ease = x => 1 - Math.pow(1 - P.clamp(x, 0, 1), 3);
  const paths = new Map();
  function mark(c, name, x, y, size, color) {
    c.save(); c.translate(x, y); c.scale(size / 42, size / 42);
    c.lineWidth = 1.8; c.strokeStyle = color; c.lineJoin = "round"; c.lineCap = "round";
    if (!paths.has(name)) paths.set(name, root.MotionMarks.paths[name].map(d => new Path2D(d)));
    for (const p of paths.get(name)) c.stroke(p);
    c.restore();
  }

  function linesFor(c, value, width) {
    const lines = []; let line = "";
    for (const word of value.trim().split(/\s+/u)) {
      if (line && c.measureText(line + " " + word).width > width) { lines.push(line); line = ""; }
      if (c.measureText(word).width > width) {
        for (const letter of word) {
          if (line && c.measureText(line + letter).width > width) { lines.push(line); line = ""; }
          line += letter;
        }
      } else line += (line ? " " : "") + word;
    }
    if (line) lines.push(line);
    return lines;
  }

  function textBlock(c, text, x, y, width, height, maxFont, fill, weight, movement, t) {
    if (!text) return;
    let font = maxFont, lines;
    const fit = () => {
      c.font = weight + " " + font + "px Arial, sans-serif";
      lines = linesFor(c, text, width);
    };
    fit();
    while (font > 10 && lines.length * font * 1.1 > height) { font -= 2; fit(); }
    c.fillStyle = fill; c.textBaseline = "top";
    let order = 0;
    for (let i = 0; i < lines.length; i++) {
      let left = x;
      for (const word of lines[i].split(" ")) {
        const delay = Math.min(order, 10) * 0.048;
        const q = movement ? ease((t - delay) / 0.53) : 1;
        c.save(); c.globalAlpha *= q;
        c.translate(left + (movement === "Side Sweep" ? (1 - q) * -30 : 0), y + i * font * 1.1 + (movement === "Word Rise" ? (1 - q) * 34 : 0));
        if (movement === "Scale Pulse") c.scale(0.68 + q * 0.32, 0.68 + q * 0.32);
        c.fillText(word, 0, 0);
        c.restore();
        left += c.measureText(word + " ").width; order++;
      }
    }
  }

  // Options: { captions: false } Hides The Caption Track. { strict: true } Rethrows A Code Scene Error.
  function draw(canvas, project, time, options) {
    const located = P.locate(project, time), c = canvas.getContext("2d", { alpha: false });
    if (located.scene.mode === "Code Scene") root.MotionScenes.paint(c, canvas, project, located, time, options);
    else builtIn(c, canvas, located.scene, located.local);
    if (project.captions && !(options && options.captions === false))
      root.MotionCaptions.draw(c, canvas, project, P.clamp(time, 0, P.duration(project)));
  }

  function builtIn(c, canvas, s, t) {
    const w = 1000, h = canvas.height / canvas.width * w, landscape = h < 720, square = !landscape && h < 1200, margin = landscape ? 52 : 70;
    const u = Math.min(1, t / s.duration), width = w - 2 * margin;
    c.setTransform(canvas.width / w, 0, 0, canvas.height / h, 0, 0);
    c.globalAlpha = 1; c.fillStyle = s.background; c.fillRect(0, 0, w, h);
    c.save(); c.globalAlpha = 0.13;
    const glow = c.createRadialGradient(820, h * 0.43, 0, 820, h * 0.43, 730);
    glow.addColorStop(0, s.accent); glow.addColorStop(1, s.background);
    c.fillStyle = glow; c.fillRect(0, 0, w, h); c.restore();
    const top = landscape ? 39 : square ? 54 : 94;
    mark(c, s.mark, margin, top, landscape ? 33 : 46, s.accent);
    const tagX = margin + (landscape ? 49 : 64);
    textBlock(c, s.eyebrow, tagX, top + 5, w - tagX - margin, 47, landscape ? 19 : 28, s.accent, 650, "", t);
    if (s.mode === "Kinetic Type") {
      const headingY = h * (landscape ? 0.30 : 0.33);
      textBlock(c, s.title, margin, headingY, width * 0.97, h * 0.32, landscape ? 87 : 115, s.foreground, 750, s.motion, t);
      const q = ease((t - 0.22) / 0.6);
      c.save(); c.globalAlpha = q; c.fillStyle = s.accent;
      c.fillRect(margin, h * 0.70, width * 0.20 * q, landscape ? 3 : 5); c.restore();
      textBlock(c, s.body, margin, h * 0.74, width * 0.93, h * 0.16, landscape ? 30 : 45, s.foreground, 400, "Word Rise", t - 0.18);
    } else if (s.mode === "Process Diagram") {
      const x = landscape ? 534 : margin, y = landscape ? h * 0.23 : h * 0.43, trackH = h * (landscape ? 0.62 : 0.45);
      textBlock(c, s.title, margin, h * (landscape ? 0.28 : 0.19), landscape ? 410 : width, h * (landscape ? 0.43 : 0.22), landscape ? 68 : 94, s.foreground, 750, s.motion, t);
      const gap = trackH / Math.max(1, s.steps.length), radius = Math.min(21, gap * 0.19);
      const onset = i => (0.35 + i * 0.68) * Math.min(1, s.duration / (1.65 + (s.steps.length - 1) * 0.68));
      for (let i = 0; i < s.steps.length; i++) {
        const at = y + (i + 0.5) * gap, q = ease((t - onset(i)) / Math.min(0.47, s.duration * 0.22));
        const centerX = x + radius + 2;
        if (i < s.steps.length - 1) {
          c.save(); c.globalAlpha = 0.25; c.strokeStyle = s.accent; c.lineWidth = 3;
          c.beginPath(); c.moveTo(centerX, at + radius); c.lineTo(centerX, at + gap - radius); c.stroke(); c.restore();
        }
        c.save(); c.globalAlpha = 0.22 + q * 0.78; c.strokeStyle = s.accent; c.fillStyle = s.accent; c.lineWidth = 3;
        c.beginPath(); c.arc(centerX, at, radius, 0, Math.PI * 2); c.stroke();
        c.beginPath(); c.arc(centerX, at, radius * (0.2 + 0.33 * q), 0, Math.PI * 2); c.fill(); c.restore();
        const font = Math.min(landscape ? 30 : 49, gap * 0.49);
        textBlock(c, s.steps[i], x + radius * 2 + 24, at - font * 0.50, w - x - margin - radius * 2 - 24, gap * 0.86, font, s.foreground, 600, "Side Sweep", (t - onset(i)) * 1.6);
      }
    } else {
      const cx = landscape ? 741 : 500, cy = h * (landscape ? 0.51 : 0.415), size = landscape ? 510 : square ? 500 : 720;
      c.save(); c.globalAlpha = 0.14; c.strokeStyle = s.accent; c.lineWidth = 2;
      for (let i = 0; i < 3; i++) {
        c.beginPath(); c.ellipse(cx, cy + size * 0.22 + i * 6, size * (0.34 + i * 0.025), size * (0.042 + i * 0.008), 0, 0, Math.PI * 2); c.stroke();
      }
      c.restore();
      root.MotionSpace.draw(c, s, u, cx, cy, size);
      textBlock(c, s.title, margin, h * (landscape ? 0.33 : 0.67), landscape ? 418 : width, h * (landscape ? 0.31 : 0.15), landscape ? 69 : 90, s.foreground, 750, s.motion, t);
      textBlock(c, s.body, margin, h * (landscape ? 0.68 : 0.84), landscape ? 403 : width, h * (landscape ? 0.19 : 0.10), landscape ? 24 : 36, s.accent, 450, "Word Rise", t - 0.16);
    }
  }

  root.MotionFrame = { draw };
})(globalThis);
