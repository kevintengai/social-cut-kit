// Captions: A Project-Level Track Of Hand-Written Lines Drawn Over Every Scene Kind.
(function (root) {
  "use strict";
  const K = root.MotionKit, P = root.MotionProject;
  const base = { font: "Arial", weight: 800, color: "#ffffff", outline: "#10151a", highlight: "#ffe45c", position: "Bottom", mode: "Line", motion: "Pop", case: "As Written",
    width: 0.86, maxLines: 2, margin: 0.02, hold: 0.3, minimum: 0.7, plateOpacity: 0.72 };

  // The Complete Style For A Storyboard: Its Own Choices Over The Defaults, With Sizes In Output Pixels.
  function styleFor(project) {
    const size = P.size(project), given = project.captions && project.captions.style || {}, style = Object.assign({}, base, given);
    if (given.size == null) style.size = Math.round(Math.min(size[0], size[1]) * 0.052);
    if (given.stroke == null) style.stroke = given.plate ? 0 : Math.round(style.size * 0.16);
    style.family = (style.font.includes(" ") ? "\"" + style.font + "\"" : style.font) + ", Arial, sans-serif";
    return style;
  }
  // The Caption Line On Screen At A Film Time, Or Null.
  function lineAt(project, time) {
    const lines = project.captions && project.captions.lines;
    if (!lines) return null;
    let found = null;
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (line.at != null && time >= line.at - 1e-6 && time < line.end - 1e-6 && (!found || line.at >= found.line.at)) found = { line, index: i };
    }
    return found;
  }
  // When Each Shown Word Begins. Spoken Times Come From The Timing Tool. Otherwise Words Share The Line Evenly By Length.
  function wordTimes(line, words, hold) {
    if (Array.isArray(line.words) && line.words.length === words.length) return line.words;
    const span = Math.max(0.1, line.end - line.at - hold), total = words.reduce((sum, word) => sum + word.length + 1, 0);
    let walked = 0;
    return words.map(word => { const at = line.at + span * walked / total; walked += word.length + 1; return at; });
  }

  function draw(c, canvas, project, time) {
    const captions = project.captions;
    if (!captions || captions.show === false) return null;
    const active = lineAt(project, time);
    if (!active) return null;
    const size = P.size(project), width = size[0], height = size[1], safe = P.safe(project), style = styleFor(project), line = active.line;
    const text = style.case === "Upper" ? line.text.toUpperCase() : line.text, age = time - line.at;
    c.setTransform(canvas.width / width, 0, 0, canvas.height / height, 0, 0);
    c.save();
    c.globalAlpha = 1;
    const fitted = K.fitText(c, text, { width: safe.w * style.width, size: style.size, minSize: style.size * 0.45, weight: style.weight, family: style.family, maxLines: style.maxLines, lineHeight: 1.18 });
    const blockHeight = fitted.height, gap = style.margin * height, pad = fitted.size * 0.42;
    const top = style.position === "Top" ? safe.top + gap + (style.plate ? pad : 0) : style.position === "Center" ? safe.cy - blockHeight / 2 : safe.bottom - gap - blockHeight - (style.plate ? pad : 0);
    const cx = safe.cx, cy = top + blockHeight / 2;
    let alpha = 1;
    if (style.motion === "Pop") {
      const scale = 0.9 + 0.1 * K.ease.outBack(K.between(age, 0, 0.18));
      alpha = K.between(age, 0, 0.07);
      c.translate(cx, cy); c.scale(scale, scale); c.translate(-cx, -cy);
    } else if (style.motion === "Rise") {
      alpha = K.between(age, 0, 0.12);
      c.translate(0, (1 - K.ease.outCubic(K.between(age, 0, 0.22))) * fitted.size * 0.45);
    }
    c.globalAlpha = alpha;
    if (style.plate) {
      c.fillStyle = K.rgba(style.plate, style.plateOpacity);
      K.roundRect(c, cx - fitted.width / 2 - pad * 1.5, top - pad, fitted.width + pad * 3, blockHeight + pad * 2, fitted.size * 0.36);
      c.fill();
    }
    // Place Every Word So Word Modes Can Reveal Or Highlight One At A Time.
    const placed = [], space = c.measureText(" ").width;
    fitted.lines.forEach((row, r) => {
      let x = cx - c.measureText(row).width / 2;
      for (const word of row.split(" ").filter(Boolean)) { placed.push({ word, x, y: top + (r + 0.5) * fitted.lineHeight }); x += c.measureText(word).width + space; }
    });
    const starts = wordTimes(line, placed.map(item => item.word), style.hold);
    let current = -1;
    for (let i = 0; i < starts.length; i++) if (time >= starts[i] - 1e-6) current = i;
    const visible = i => style.mode === "Word Build" ? K.between(time, starts[i], starts[i] + 0.07) : 1;
    c.textAlign = "left"; c.textBaseline = "middle"; c.lineJoin = "round";
    if (style.stroke > 0) {
      c.strokeStyle = style.outline; c.lineWidth = style.stroke * fitted.size / style.size;
      placed.forEach((item, i) => { const show = visible(i); if (show > 0) { c.globalAlpha = alpha * show; c.strokeText(item.word, item.x, item.y); } });
    }
    placed.forEach((item, i) => {
      const show = visible(i);
      if (show <= 0) return;
      c.globalAlpha = alpha * show;
      c.fillStyle = style.mode === "Word Highlight" && i === current ? style.highlight : style.color;
      c.fillText(item.word, item.x, item.y);
    });
    c.restore();
    return active;
  }

  root.MotionCaptions = { draw, lineAt, styleFor, defaults: base };
})(globalThis);
