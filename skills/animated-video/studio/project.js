(function (root) {
  "use strict";

  const modes = ["Kinetic Type", "Process Diagram", "3D Object"];
  const motions = ["Word Rise", "Side Sweep", "Scale Pulse"];
  const shapes = ["Prism", "Orbit Ring", "Crystal"];
  const marks = ["Aperture", "Signal", "Focus", "Route", "Spark", "Orbit"];
  const sounds = ["Paper Tap", "Glass Point", "Air Sweep", "Low Bloom", "Twin Tick", "Orbit Rise", "Room Air"];
  const aspects = { "Portrait": [1080, 1920], "Landscape": [1920, 1080], "Square": [1080, 1080] };
  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
  const uid = () => root.crypto?.randomUUID?.() || Math.random().toString(36).slice(2);
  const isData = value => typeof value === "string" && /^data:(?:audio\/[a-z0-9-.+]+|video\/mp4|application\/octet-stream)?;base64,[a-z0-9+/=]+$/i.test(value);

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
    const seen = new Set();
    const scenes = input.scenes.map(raw => {
      if (!raw || typeof raw !== "object") fail("Every Scene Needs A Storyboard Entry.");
      const s = scene();
      s.id = string(raw.id, s.id, 100) || s.id;
      if (seen.has(s.id)) s.id = uid();
      seen.add(s.id);
      s.mode = choice(raw.mode, modes, s.mode);
      for (const key of ["eyebrow", "title", "body"]) s[key] = string(raw[key], s[key], key === "body" ? 320 : 110);
      for (const key of ["background", "foreground", "accent", "material", "light"]) s[key] = color(raw[key], s[key]);
      for (const [key, min, max] of [["duration", 1, 60], ["azimuth", -180, 180], ["elevation", -70, 70], ["orbit", -180, 180], ["spin", -450, 450], ["distance", 3.5, 9], ["gloss", 0, 1], ["lightYaw", -180, 180], ["lightElevation", -90, 90], ["intensity", 0, 2]])
        s[key] = number(raw[key], s[key], min, max);
      s.motion = choice(raw.motion, motions, s.motion);
      s.mark = choice(raw.mark, marks, s.mark);
      s.shape = choice(raw.shape, shapes, s.shape);
      if (Array.isArray(raw.steps) && raw.steps.length) s.steps = raw.steps.slice(0, 5).map(v => string(v, "", 72));
      if (Array.isArray(raw.cues)) s.cues = raw.cues.slice(0, 64).map(c => {
        if (!c || !["Sound", "Voice"].includes(c.type)) fail("A Cue Uses An Unknown Type.");
        const cue = { type: c.type, at: number(c.at, 0, 0, s.duration - 0.01), gain: number(c.gain, 0.8, 0, 1) };
        if (c.type === "Sound") cue.sound = choice(c.sound, sounds, sounds[0]);
        else {
          if (c.clip && !isData(c.clip)) fail("Voice Audio Must Be Embedded In The Project.");
          cue.text = string(c.text, "", 320);
          cue.clip = c.clip || "";
        }
        return cue;
      });
      return s;
    });
    return { version: 1, title: string(input.title, "Untitled Storyboard", 100), aspect: choice(input.aspect, Object.keys(aspects), "Portrait"),
      fps: choice(input.fps, [24, 30, 60], 30), scenes };
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
  const api = { demo, scene, cleanProject, duration, start, locate, modes, motions, shapes, marks, sounds, aspects, clamp };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.MotionProject = api;
})(globalThis);
