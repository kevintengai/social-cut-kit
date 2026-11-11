// Code Scenes: A Registry Of Named Draw Functions And The State Each One Receives.
// A Scene Module Calls MotionScenes.register(name, draw, extras). The Painter Calls The Draw Function With A 2D Context And A State.
// A Draw Function Must Be A Pure Function Of Its State So Any Frame Can Be Drawn Alone And Redrawn Identically.
(function (root) {
  "use strict";
  const K = root.MotionKit, P = root.MotionProject, T = root.MotionTiming;
  const parts = new Map(), film = new Map(), problems = new Map();
  const round = value => Math.round(value * 1000) / 1000;
  const freeze = value => {
    if (value && typeof value === "object" && !Object.isFrozen(value)) { Object.freeze(value); for (const key of Object.keys(value)) freeze(value[key]); }
    return value;
  };

  // register("Name", draw) Or register("Name", draw, { events, defaults, about }) Or register("Name", { draw, events, defaults, about }).
  function register(name, draw, extras) {
    const given = typeof draw === "function" ? Object.assign({}, extras, { draw }) : Object.assign({}, draw);
    if (typeof name !== "string" || !name.trim() || name.length > 80) throw new Error("A Draw Function Needs A Name Of Up To 80 Characters.");
    if (typeof given.draw !== "function") throw new Error("Register " + name + " With A Draw Function.");
    if (given.events != null && typeof given.events !== "function") throw new Error("Register " + name + " With Events As A Function.");
    let defaults = {};
    if (given.defaults != null) {
      try { defaults = JSON.parse(JSON.stringify(given.defaults)); } catch (error) { defaults = null; }
      if (!defaults || typeof defaults !== "object" || Array.isArray(defaults)) throw new Error("Register " + name + " With Defaults As A JSON Object.");
    }
    const entry = { name, draw: given.draw, events: given.events || null, defaults: freeze(defaults), about: String(given.about || "") };
    film.set(name, entry);
    return entry;
  }
  const get = name => film.get(name) || parts.get(name) || null;
  const has = name => Boolean(get(name));
  const names = () => [...new Set([...film.keys(), ...parts.keys()])];
  // Keep Everything Registered So Far As Built-In Parts. Motion Studio Seals After It Loads The Kit's Own Parts.
  function seal() { for (const [name, entry] of film) parts.set(name, entry); film.clear(); }
  // Forget The Draw Functions Of The Last Film. Built-In Parts Stay.
  function reset() { film.clear(); problems.clear(); }
  const isPart = name => !film.has(name) && parts.has(name);
  function note(kind, index, scene, message) {
    problems.set(index + "|" + kind + "|" + message, { kind, scene: index + 1, draw: scene.draw || "", message });
  }

  function makeState(o) {
    const { project, scene, index, sceneStart, shift, width, height, time, duration, name } = o;
    const fps = project.fps, globalTime = sceneStart + shift + time, voice = project.voice;
    let words = null, phraseIndex = null;
    const boxFor = box => Object.assign({ x: 0, y: 0, w: width, h: height }, box);
    const child = (partName, partParams, box) => {
      const entry = get(partName);
      if (!entry) throw new Error("Unknown Draw Function: " + partName + ". Register It Or List Its Module In The Storyboard.");
      const b = boxFor(box), start = b.start ?? 0, s = o.safe;
      const left = K.clamp(s.left - b.x, 0, b.w), top = K.clamp(s.top - b.y, 0, b.h), right = K.clamp(s.right - b.x, 0, b.w), bottom = K.clamp(s.bottom - b.y, 0, b.h);
      return { entry, box: b, state: makeState(Object.assign({}, o, {
        width: b.w, height: b.h, time: time - start, duration: b.duration ?? Math.max(0, duration - start), shift: shift + start, name: partName,
        safe: { x: left, y: top, w: right - left, h: bottom - top, left, top, right, bottom, cx: (left + right) / 2, cy: (top + bottom) / 2 },
        params: freeze(Object.assign({}, entry.defaults, partParams)), seed: K.hash(o.seed, partName, b.key ?? "")
      })) };
    };
    const state = {
      // The Frame, In Output Pixels. The Context Is Already Scaled, So Draw At This Size On Any Canvas.
      width, height, cx: width / 2, cy: height / 2, min: Math.min(width, height), max: Math.max(width, height), unit: Math.min(width, height) / 100,
      aspect: width / height, portrait: height > width * 1.05, landscape: width > height * 1.05,
      safe: Object.freeze(Object.assign({}, o.safe)),
      // Time. `time` Is Seconds Since This Scene Began. `progress` Runs From 0 To 1 Across The Scene.
      time, t: time, duration, progress: duration > 0 ? K.clamp(time / duration) : 1, remaining: duration - time,
      globalTime, frame: Math.round(globalTime * fps), fps,
      // The Scene's Own Data From The Storyboard.
      params: o.params,
      colors: Object.freeze({ background: scene.background, foreground: scene.foreground, accent: scene.accent }),
      text: Object.freeze({ eyebrow: scene.eyebrow, title: scene.title, body: scene.body }),
      scene: Object.freeze({ index, id: scene.id, count: project.scenes.length, name, film: project.title }),
      // Deterministic Randomness. `random()` Replays The Same Sequence On Every Frame. `rng(key)` Makes An Independent Generator.
      seed: o.seed, random: K.rng(o.seed), rng: key => K.rng(K.hash(o.seed, key)),
      // The Voice. `voice` Is The Speech Level From 0 To 1 At This Moment.
      voice: T.levelAt(voice, globalTime), voiceAt: at => T.levelAt(voice, sceneStart + shift + at),
      // Phrase Cues. A Beat Is A Named Moment In The Storyboard, In Seconds Since The Scene Began.
      beat(beatName, fallback) {
        const beat = scene.beats && scene.beats[beatName];
        if (beat && Number.isFinite(beat.at)) return beat.at - shift;
        if (fallback !== undefined) return fallback;
        throw new Error(beat ? "Beat " + beatName + " Has No Time Yet. Run The Voice Timing Tool Or Give The Beat An at Value."
          : "Unknown Beat: " + beatName + ". Add It To The Beats Of Scene " + (index + 1) + ".");
      },
      since: (beatName, fallback) => time - state.beat(beatName, fallback),
      // Read A Time Option That May Be Seconds Or The Name Of A Beat.
      when: (value, fallback) => typeof value === "string" ? state.beat(value, fallback) : Number.isFinite(value) ? value : fallback,
      // Look Up A Spoken Phrase Directly. Returns Seconds Since The Scene Began.
      phrase(text, occurrence) {
        if (!voice || !voice.words) throw new Error("The Storyboard Has No Word Timings Yet. Run The Voice Timing Tool.");
        if (!phraseIndex) phraseIndex = T.makeIndex(voice.words.map(word => ({ start: word[0], end: word[1], text: word[2] })), voice.offset || 0);
        return T.resolve(phraseIndex, { phrase: text, occurrence }, { label: "Draw Function " + name, span: [sceneStart, sceneStart + scene.duration] }).time - sceneStart - shift;
      },
      kit: K, space: root.MotionSpace,
      // Draw Another Registered Draw Function Inside A Box: use(c, "Phone", params, { x, y, w, h, start, duration, clip, key }).
      use(c, partName, partParams, box) {
        const sub = child(partName, partParams, box);
        c.save(); c.translate(sub.box.x, sub.box.y);
        if (sub.box.clip !== false) { c.beginPath(); c.rect(0, 0, sub.box.w, sub.box.h); c.clip(); }
        try { sub.entry.draw(c, sub.state); } finally { c.restore(); }
      },
      // The Events Another Draw Function Declares When Used Inside A Box, With Times And Positions Mapped To This Scene.
      events(partName, partParams, box) {
        const sub = child(partName, partParams, box);
        if (!sub.entry.events) return [];
        return (sub.entry.events(sub.state) || []).map(event => Object.assign({}, event, {
          id: (sub.box.key ? sub.box.key + "." : "") + event.id, at: event.at + (sub.box.start ?? 0),
          pan: K.clamp(((sub.box.x + ((event.pan ?? 0) + 1) / 2 * sub.box.w) / width) * 2 - 1, -1, 1)
        }));
      }
    };
    // The Words Spoken During This Scene, As { text, start, end } In Seconds Since The Scene Began.
    Object.defineProperty(state, "words", { enumerable: true, get() {
      if (!words) words = Object.freeze(T.wordsBetween(voice, sceneStart + shift, sceneStart + shift + duration)
        .map(word => Object.freeze({ text: word.text, start: word.start - sceneStart - shift, end: word.end - sceneStart - shift })));
      return words;
    } });
    return Object.freeze(state);
  }
  // The State A Scene's Draw Function Receives At A Scene-Local Time.
  function stateFor(project, index, local) {
    const scene = project.scenes[index], entry = get(scene.draw), size = P.size(project);
    return makeState({
      project, scene, index, sceneStart: P.start(project, index), shift: 0, width: size[0], height: size[1], safe: P.safe(project),
      time: local, duration: scene.duration, name: scene.draw || "",
      params: freeze(Object.assign({}, entry ? entry.defaults : null, scene.params)),
      seed: K.hash("scene", Number.isFinite(scene.seed) ? scene.seed : scene.draw || "")
    });
  }

  function card(c, width, height, scene, heading, lines) {
    const unit = Math.min(width, height) / 100, pad = unit * 8;
    c.save();
    c.fillStyle = scene.background; c.fillRect(0, 0, width, height);
    c.strokeStyle = scene.accent; c.lineWidth = unit * 0.5; c.setLineDash([unit * 2.4, unit * 1.6]);
    c.strokeRect(pad / 2, pad / 2, width - pad, height - pad); c.setLineDash([]);
    c.fillStyle = scene.accent;
    const title = K.fitText(c, heading, { width: width - pad * 2, size: unit * 6.4, weight: 700, maxLines: 3 });
    const top = height * 0.36;
    K.drawText(c, title, width / 2, top, { align: "center" });
    c.fillStyle = scene.foreground;
    const body = K.fitText(c, lines.join("\n"), { width: width - pad * 2, height: height * 0.4, size: unit * 3.6, weight: 400 });
    K.drawText(c, body, width / 2, top + title.height + unit * 4, { align: "center" });
    c.restore();
  }

  // Paint One Code Scene. Returns True When The Draw Function Ran Cleanly.
  function paint(c, canvas, project, located, time, options) {
    const scene = located.scene, index = located.index, size = P.size(project), width = size[0], height = size[1], entry = get(scene.draw);
    c.setTransform(canvas.width / width, 0, 0, canvas.height / height, 0, 0);
    c.globalAlpha = 1; c.fillStyle = scene.background; c.fillRect(0, 0, width, height);
    if (!entry) {
      const message = scene.draw ? "Draw Function " + scene.draw + " Is Not Loaded." : "Scene " + (index + 1) + " Has No Draw Function.";
      note("missing", index, scene, message);
      if (options && options.strict) throw new Error(message);
      card(c, width, height, scene, scene.draw ? "Scene Module Not Loaded" : "Choose A Draw Function",
        scene.draw ? ["Draw Function: " + scene.draw, "Open The Film Folder To Load Its Scene Modules."] : ["Pick A Draw Function For This Scene In The Scene Editor."]);
      return false;
    }
    // Count The Scene's Saves So Its Context State Never Leaks Into The Next Layer, Even After An Error.
    const save = c.save, restore = c.restore;
    let depth = 0, failure = null;
    c.save = function () { depth++; return save.call(c); };
    c.restore = function () { if (depth > 0) { depth--; return restore.call(c); } };
    save.call(c);
    try { entry.draw(c, stateFor(project, index, located.local)); }
    catch (error) { failure = error; }
    finally {
      while (depth > 0) { depth--; restore.call(c); }
      restore.call(c);
      delete c.save; delete c.restore;
    }
    if (!failure) return true;
    const message = String(failure && failure.message || failure);
    note("error", index, scene, message);
    if (options && options.strict) throw failure;
    card(c, width, height, scene, "This Scene Could Not Be Drawn", ["Scene " + (index + 1) + " · " + scene.draw, message]);
    return false;
  }

  // The Events One Scene Declares, With Scene Times And Film Times.
  function sceneEvents(project, index) {
    const scene = project.scenes[index], entry = scene.mode === "Code Scene" ? get(scene.draw) : null;
    if (!entry || !entry.events) return [];
    const start = P.start(project, index), listed = entry.events(stateFor(project, index, 0)) || [], seen = new Set();
    if (!Array.isArray(listed)) throw new Error("Draw Function " + scene.draw + " Must Return Its Events As A List.");
    return listed.map(event => {
      if (!event || typeof event.id !== "string" || !event.id || !Number.isFinite(event.at)) throw new Error("Draw Function " + scene.draw + " Declares An Event Without An id And A Time.");
      if (seen.has(event.id)) throw new Error("Draw Function " + scene.draw + " Declares The Event " + event.id + " Twice In Scene " + (index + 1) + ".");
      seen.add(event.id);
      const out = { scene: index + 1, id: event.id, at: round(event.at), time: round(start + event.at), what: String(event.what || event.id), pan: round(K.clamp(Number.isFinite(event.pan) ? event.pan : 0, -1, 1)) };
      if (typeof event.kind === "string" && event.kind) out.kind = event.kind;
      if (typeof event.sound === "string" && event.sound) { out.sound = event.sound; out.gain = K.clamp(Number.isFinite(event.gain) ? event.gain : 0.6); }
      return out;
    }).sort((a, b) => a.at - b.at);
  }
  const events = project => project.scenes.flatMap((scene, index) => sceneEvents(project, index));

  root.MotionScenes = { register, get, has, names, seal, reset, isPart, stateFor, paint, sceneEvents, events, problems: () => [...problems.values()], clearProblems: () => problems.clear() };
})(globalThis);
