(function (root) {
  "use strict";

  const modes = ["Kinetic Type", "Process Diagram", "3D Object", "Code Scene"];
  const motions = ["Word Rise", "Side Sweep", "Scale Pulse"];
  const shapes = ["Prism", "Orbit Ring", "Crystal"];
  const marks = ["Aperture", "Signal", "Focus", "Route", "Spark", "Orbit"];
  const sounds = ["Paper Tap", "Glass Point", "Air Sweep", "Low Bloom", "Twin Tick", "Orbit Rise", "Room Air"];
  const aspects = { "Portrait": [1080, 1920], "Landscape": [1920, 1080], "Square": [1080, 1080] };
  const aspectNames = [...Object.keys(aspects), "Custom"];
  // Margins As Fractions Of The Frame: Top, Right, Bottom, Left. The Platform Rows Are Conservative Estimates Written For This Kit.
  const safeAreas = {
    "None": [0, 0, 0, 0],
    "Title Safe": [0.05, 0.05, 0.05, 0.05],
    "Vertical Feed": [0.13, 0.14, 0.24, 0.06],
    "TikTok": [0.08, 0.13, 0.24, 0.06],
    "Reels": [0.13, 0.10, 0.22, 0.06],
    "Shorts": [0.12, 0.14, 0.24, 0.06]
  };
  const captionOptions = {
    font: ["Arial", "Georgia", "Verdana", "Tahoma", "Trebuchet MS"],
    position: ["Bottom", "Center", "Top"],
    mode: ["Line", "Word Build", "Word Highlight"],
    motion: ["Pop", "Rise", "None"],
    case: ["As Written", "Upper"]
  };
  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
  const uid = () => root.crypto?.randomUUID?.() || Math.random().toString(36).slice(2);
  const isData = value => typeof value === "string" && /^data:(?:audio\/[a-z0-9-.+]+|video\/mp4|application\/octet-stream)?;base64,[a-z0-9+/=]+$/i.test(value);
  const isObject = value => Boolean(value) && typeof value === "object" && !Array.isArray(value);
  const relativePath = /^(?!.*(?:^|\/)\.\.?(?:\/|$))[A-Za-z0-9_][A-Za-z0-9_ .()-]*(?:\/[A-Za-z0-9_][A-Za-z0-9_ .()-]*)*$/;
  const freeze = value => {
    if (value && typeof value === "object" && !Object.isFrozen(value)) { Object.freeze(value); for (const key of Object.keys(value)) freeze(value[key]); }
    return value;
  };

  function scene(mode = "Kinetic Type") {
    return {
      id: uid(), mode, duration: 4, eyebrow: "", title: "Your Next Idea", body: "",
      background: "#101925", foreground: "#f4f6f9", accent: "#8fefa8", motion: "Word Rise", mark: "Spark",
      steps: ["Start Here", "Find A Pattern", "Show The Result"], shape: "Orbit Ring", material: "#96ecc2",
      light: "#fff0bf", lightYaw: -37, lightElevation: 44, intensity: 1, azimuth: -34, elevation: 24, orbit: 52, spin: 110, distance: 5.5, gloss: 0.65,
      cues: []
    };
  }

  function demo() {
    const a = Object.assign(scene(), { duration: 3.8, eyebrow: "Motion Study", title: "Give An Idea Shape", body: "Start With One Clear Sentence.", mark: "Aperture",
      cues: [{ type: "Sound", at: 0.14, sound: "Paper Tap", gain: 0.7 }, { type: "Voice", at: 0.4, text: "Give An Idea Shape.", clip: "", gain: 1 }] });
    const b = Object.assign(scene("Process Diagram"), { duration: 5.2, eyebrow: "The Sequence", title: "Build It In Three Moves", background: "#122a2e",
      steps: ["Name The Idea", "Map The Steps", "Show The Change"], mark: "Route",
      cues: [0, 1, 2].map((i) => ({ type: "Sound", at: 0.85 + i * 0.68, sound: "Twin Tick", gain: 0.48 })) });
    const c = Object.assign(scene("3D Object"), { duration: 4.6, eyebrow: "Spatial Study", title: "Change The View", body: "Let The Light Reveal The Surface.", background: "#191828",
      accent: "#f1b0e9", material: "#c98cbf", light: "#e5f3ff", mark: "Orbit",
      cues: [{ type: "Sound", at: 0.07, sound: "Orbit Rise", gain: 0.62 }] });
    return { version: 1, title: "Give An Idea Shape", aspect: "Portrait", fps: 30, scenes: [a, b, c] };
  }

  function cleanProject(input) {
    const fail = message => { throw new Error(message); };
    if (!input || input.version !== 1 || !Array.isArray(input.scenes) || !input.scenes.length || input.scenes.length > 80)
      fail("Choose A Version One Storyboard With One To Eighty Scenes.");
    const string = (v, fallback = "", max = 1600) => typeof v === "string" ? v.slice(0, max) : fallback;
    const number = (v, fallback, min, max) => Number.isFinite(v) ? clamp(v, min, max) : fallback;
    const choice = (v, allowed, fallback) => allowed.includes(v) ? v : fallback;
    const color = (v, fallback) => /^#[0-9a-f]{6}$/i.test(v) ? v : fallback;
    const seconds = v => Math.round(v * 1000) / 1000;
    // A Phrase Anchor Ties A Time To Spoken Words. The Voice Timing Tool Resolves It.
    function anchor(raw, what) {
      if (typeof raw === "string") raw = { phrase: raw };
      if (!isObject(raw) || typeof raw.phrase !== "string" || !raw.phrase.trim()) fail(what + " Needs A Spoken Phrase.");
      const out = { phrase: raw.phrase.trim().slice(0, 240) };
      if (raw.occurrence != null) {
        if (!Number.isInteger(raw.occurrence) || raw.occurrence < 1 || raw.occurrence > 999) fail(what + " Uses An Occurrence That Is Not A Whole Number From One.");
        out.occurrence = raw.occurrence;
      }
      if (raw.edge != null) {
        if (raw.edge !== "start" && raw.edge !== "end") fail(what + " Uses An Edge Other Than start Or end.");
        out.edge = raw.edge;
      }
      if (raw.offset != null) {
        if (!Number.isFinite(raw.offset)) fail(what + " Uses An Offset That Is Not A Number Of Seconds.");
        if (raw.offset) out.offset = clamp(raw.offset, -30, 30);
      }
      return out;
    }
    function cleanBeats(raw, label) {
      if (!isObject(raw)) fail(label + " Lists Beats As Named Entries.");
      const names = Object.keys(raw);
      if (names.length > 96) fail(label + " Has More Than 96 Beats.");
      const out = {};
      for (const name of names) {
        if (!name.trim() || name.length > 60) fail(label + " Has A Beat Name That Is Empty Or Longer Than 60 Characters.");
        let entry = raw[name];
        if (typeof entry === "number") entry = { at: entry };
        if (typeof entry === "string") entry = { phrase: entry };
        if (!isObject(entry)) fail(label + " Beat " + name + " Needs A Time Or A Spoken Phrase.");
        const beat = entry.phrase != null ? anchor(entry, label + " Beat " + name) : {};
        if (Number.isFinite(entry.at)) beat.at = seconds(clamp(entry.at, -3600, 3600));
        if (beat.at === undefined && beat.phrase === undefined) fail(label + " Beat " + name + " Needs A Time Or A Spoken Phrase.");
        out[name] = beat;
      }
      return out;
    }
    function cleanSounds(raw, label) {
      if (!isObject(raw)) fail(label + " Lists Event Sounds As Named Entries.");
      const names = Object.keys(raw);
      if (names.length > 96) fail(label + " Has More Than 96 Event Sounds.");
      const out = {};
      for (const name of names) {
        let entry = raw[name];
        if (typeof entry === "string") entry = { sound: entry };
        if (!name.trim() || name.length > 120 || !isObject(entry)) fail(label + " Has An Event Sound Entry That Cannot Be Read.");
        if (entry.sound === "None") { out[name] = { sound: "None" }; continue; }
        if (!sounds.includes(entry.sound)) fail(label + " Names A Sound That Is Not In The Bank: " + String(entry.sound));
        out[name] = { sound: entry.sound, gain: number(entry.gain, 0.6, 0, 1) };
      }
      return out;
    }
    function cleanParams(raw, label) {
      if (raw == null) return freeze({});
      if (!isObject(raw)) fail(label + " Needs Its Parameters As A JSON Object.");
      let text;
      try { text = JSON.stringify(raw); } catch { fail(label + " Has Parameters That Cannot Be Saved As JSON."); }
      if (text.length > 200000) fail(label + " Has More Than 200,000 Characters Of Parameters.");
      return freeze(JSON.parse(text));
    }
    const seen = new Set();
    const scenes = input.scenes.map((raw, index) => {
      if (!raw || typeof raw !== "object") fail("Every Scene Needs A Storyboard Entry.");
      const label = "Scene " + (index + 1);
      const s = scene();
      s.id = string(raw.id, s.id, 100) || s.id;
      if (seen.has(s.id)) s.id = uid();
      seen.add(s.id);
      s.mode = choice(raw.mode, modes, s.mode);
      for (const key of ["eyebrow", "title", "body"]) s[key] = string(raw[key], s[key], key === "body" ? 320 : 110);
      for (const key of ["background", "foreground", "accent", "material", "light"]) s[key] = color(raw[key], s[key]);
      for (const [key, min, max] of [["duration", 0.25, 600], ["azimuth", -180, 180], ["elevation", -70, 70], ["orbit", -180, 180], ["spin", -450, 450], ["distance", 3.5, 9], ["gloss", 0, 1], ["lightYaw", -180, 180], ["lightElevation", -90, 90], ["intensity", 0, 2]])
        s[key] = number(raw[key], s[key], min, max);
      s.motion = choice(raw.motion, motions, s.motion);
      s.mark = choice(raw.mark, marks, s.mark);
      s.shape = choice(raw.shape, shapes, s.shape);
      if (Array.isArray(raw.steps) && raw.steps.length) s.steps = raw.steps.slice(0, 5).map(v => string(v, "", 72));
      if (Array.isArray(raw.cues)) s.cues = raw.cues.slice(0, 64).map((c, j) => {
        if (!c || !["Sound", "Voice"].includes(c.type)) fail("A Cue Uses An Unknown Type.");
        const cue = { type: c.type, at: number(c.at, 0, 0, s.duration - 0.01), gain: number(c.gain, 0.8, 0, 1) };
        if (c.type === "Sound") cue.sound = choice(c.sound, sounds, sounds[0]);
        else {
          if (c.clip && !isData(c.clip)) fail("Voice Audio Must Be Embedded In The Project.");
          cue.text = string(c.text, "", 320);
          cue.clip = c.clip || "";
        }
        if (c.anchor != null) cue.anchor = anchor(c.anchor, label + " Cue " + (j + 1));
        if (typeof c.event === "string" && c.event) cue.event = c.event.slice(0, 120);
        if (Number.isFinite(c.pan) && c.pan) cue.pan = clamp(c.pan, -1, 1);
        return cue;
      });
      if (s.mode === "Code Scene") {
        s.draw = string(raw.draw, "", 80);
        s.params = cleanParams(raw.params, label);
        if (Number.isFinite(raw.seed)) s.seed = raw.seed;
      }
      if (raw.start != null) s.start = anchor(raw.start, label + " Start");
      if (raw.end != null) s.end = anchor(raw.end, label + " End");
      if (raw.beats != null) s.beats = cleanBeats(raw.beats, label);
      if (raw.sounds != null) s.sounds = cleanSounds(raw.sounds, label);
      return s;
    });
    const out = { version: 1, title: string(input.title, "Untitled Storyboard", 100), aspect: choice(input.aspect, aspectNames, "Portrait"),
      fps: choice(input.fps, [24, 30, 60], 30), scenes };
    if (out.aspect === "Custom") {
      const size = input.size;
      if (!Array.isArray(size) || size.length !== 2 || !size.every(v => Number.isInteger(v) && v >= 240 && v <= 4096 && v % 2 === 0))
        fail("A Custom Frame Needs A Size Of Two Even Whole Numbers From 240 To 4096.");
      out.size = [size[0], size[1]];
    }
    if (input.modules != null) {
      if (!Array.isArray(input.modules) || input.modules.length > 64) fail("List Up To 64 Scene Modules.");
      out.modules = input.modules.map(name => {
        if (typeof name !== "string" || name.length > 200 || !relativePath.test(name) || !/\.js$/i.test(name))
          fail("List Each Scene Module As A Relative Path To A .js File Beside The Storyboard.");
        return name;
      });
      if (new Set(out.modules).size !== out.modules.length) fail("A Scene Module Is Listed Twice.");
    }
    if (input.safe != null) {
      if (typeof input.safe === "string") {
        if (!(input.safe in safeAreas)) fail("Choose A Safe Area From: " + Object.keys(safeAreas).join(", ") + ".");
        out.safe = input.safe;
      } else if (isObject(input.safe)) {
        out.safe = {};
        for (const key of ["top", "right", "bottom", "left"]) out.safe[key] = number(input.safe[key], 0, 0, 0.45);
      } else fail("A Safe Area Is A Preset Name Or Four Margins.");
    }
    if (input.captions != null) {
      const raw = input.captions;
      if (!isObject(raw) || !Array.isArray(raw.lines) || raw.lines.length > 2000) fail("Captions Need A List Of Up To 2,000 Lines.");
      const style = {}, given = isObject(raw.style) ? raw.style : {};
      for (const key of Object.keys(captionOptions)) if (given[key] != null) {
        if (!captionOptions[key].includes(given[key])) fail("Caption Style " + key + " Must Be One Of: " + captionOptions[key].join(", ") + ".");
        style[key] = given[key];
      }
      for (const [key, min, max] of [["size", 12, 400], ["stroke", 0, 60], ["width", 0.3, 1], ["margin", 0, 0.4], ["hold", 0, 3], ["minimum", 0, 5], ["plateOpacity", 0, 1]])
        if (given[key] != null) { if (!Number.isFinite(given[key])) fail("Caption Style " + key + " Must Be A Number."); style[key] = clamp(given[key], min, max); }
      for (const key of ["weight", "maxLines"]) if (given[key] != null) {
        const allowed = key === "weight" ? [400, 500, 600, 700, 800, 900] : [1, 2, 3, 4];
        if (!allowed.includes(given[key])) fail("Caption Style " + key + " Must Be One Of: " + allowed.join(", ") + ".");
        style[key] = given[key];
      }
      for (const key of ["color", "outline", "plate", "highlight"]) if (given[key] != null) {
        if (!/^#[0-9a-f]{6}$/i.test(given[key])) fail("Caption Style " + key + " Must Be A Six-Digit Hex Color.");
        style[key] = given[key];
      }
      const lines = raw.lines.map((line, i) => {
        const label = "Caption Line " + (i + 1);
        if (typeof line === "string") line = { text: line };
        if (!isObject(line) || typeof line.text !== "string" || !line.text.trim()) fail(label + " Needs Text.");
        const entry = { text: line.text.trim().slice(0, 240) };
        if (line.phrase != null || line.occurrence != null) {
          const spoken = anchor({ phrase: line.phrase ?? line.text, occurrence: line.occurrence }, label);
          if (line.phrase != null) entry.phrase = spoken.phrase;
          if (spoken.occurrence) entry.occurrence = spoken.occurrence;
        }
        if (line.until != null) {
          if (typeof line.until !== "string" || !line.until.trim()) fail(label + " Uses An Until Phrase That Cannot Be Read.");
          entry.until = line.until.trim().slice(0, 240);
        }
        if (line.at != null || line.end != null) {
          if (!Number.isFinite(line.at) || !Number.isFinite(line.end) || line.at < 0 || line.end <= line.at) fail(label + " Needs A Start Time And A Later End Time.");
          entry.at = seconds(Math.min(line.at, 36000)); entry.end = seconds(Math.min(line.end, 36000));
        }
        if (line.words != null) {
          if (!Array.isArray(line.words) || line.words.length > 80 || !line.words.every(Number.isFinite)) fail(label + " Has Word Times That Cannot Be Read.");
          entry.words = line.words.map(seconds);
        }
        return entry;
      });
      out.captions = { show: raw.show !== false, style, lines };
    }
    if (input.voice != null) {
      const raw = input.voice, voice = {};
      if (!isObject(raw)) fail("The Film Voice Entry Cannot Be Read.");
      if (raw.file != null) {
        if (typeof raw.file !== "string" || raw.file.length > 200 || !relativePath.test(raw.file) || !/\.(wav|mp3|m4a|aac|ogg|flac|webm)$/i.test(raw.file))
          fail("Name The Film Voice Recording As A Relative Path To An Audio File Beside The Storyboard.");
        voice.file = raw.file;
      }
      if (raw.clip) {
        if (!isData(raw.clip)) fail("Voice Audio Must Be Embedded In The Project.");
        voice.clip = raw.clip;
      }
      voice.gain = number(raw.gain, 1, 0, 1);
      voice.offset = seconds(number(raw.offset, 0, -600, 600));
      if (raw.standIn === true) voice.standIn = true;
      if (raw.words != null) {
        if (!Array.isArray(raw.words) || raw.words.length > 20000) fail("The Film Voice Lists Up To 20,000 Words.");
        voice.words = raw.words.map(word => {
          if (!Array.isArray(word) || word.length !== 3 || !Number.isFinite(word[0]) || !Number.isFinite(word[1]) || word[0] < 0 || word[1] < word[0] || typeof word[2] !== "string" || !word[2])
            fail("Each Film Voice Word Is A Start Time, An End Time, And Its Text.");
          return [seconds(word[0]), seconds(word[1]), word[2].slice(0, 80)];
        });
      }
      if (raw.levels != null) {
        const levels = raw.levels;
        if (!isObject(levels) || !Array.isArray(levels.values) || levels.values.length > 400000 || !levels.values.every(Number.isFinite)) fail("The Film Voice Levels Cannot Be Read.");
        voice.levels = { rate: number(levels.rate, 30, 1, 120), values: levels.values.map(v => Math.round(clamp(v, 0, 1) * 100) / 100) };
        if (levels.estimated === true) voice.levels.estimated = true;
      }
      out.voice = voice;
    }
    // A Film With No Spoken Voice Says So. Its Timings Are The Author's Own, Not Stand-Ins For A Recording.
    if (input.narration != null) {
      if (input.narration !== "Voice" && input.narration !== "None") fail("Narration Is Voice Or None.");
      if (input.narration === "None") out.narration = "None";
    }
    return out;
  }

  const duration = p => p.scenes.reduce((sum, s) => sum + s.duration, 0);
  const start = (p, index) => p.scenes.slice(0, index).reduce((sum, s) => sum + s.duration, 0);
  function locate(p, time) {
    let t = clamp(time, 0, duration(p));
    for (let index = 0; index < p.scenes.length; index++) {
      const s = p.scenes[index];
      if (t < s.duration - 0.000001 || index === p.scenes.length - 1) return { index, scene: s, local: Math.min(t, s.duration) };
      t -= s.duration;
    }
  }
  // The Full Output Size In Pixels.
  const size = p => p.aspect === "Custom" && Array.isArray(p.size) ? [p.size[0], p.size[1]] : aspects[p.aspect] || aspects.Portrait;
  // The Safe Area In Output Pixels. A Storyboard Without A Choice Uses Title Safe Margins.
  function safe(p) {
    const [width, height] = size(p), chosen = p.safe ?? "Title Safe";
    const m = typeof chosen === "string" ? safeAreas[chosen] || safeAreas["Title Safe"] : [chosen.top, chosen.right, chosen.bottom, chosen.left];
    const left = m[3] * width, top = m[0] * height, right = width - m[1] * width, bottom = height - m[2] * height;
    return { x: left, y: top, w: right - left, h: bottom - top, left, top, right, bottom, cx: (left + right) / 2, cy: (top + bottom) / 2 };
  }
  // True While The Film's Timing Comes From Stand-In Words Instead Of A Recording. Such A Film Is Not Ready For Export.
  const standIn = p => Boolean(p && p.voice && p.voice.standIn === true);
  const api = { demo, scene, cleanProject, standIn, duration, start, locate, size, safe, modes, motions, shapes, marks, sounds, aspects, aspectNames, safeAreas, captionOptions, clamp };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.MotionProject = api;
})(globalThis);
