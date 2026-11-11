(() => {
  "use strict";
  const P = MotionProject;
  const $ = id => document.getElementById(id);
  const canvas = $("frame"), cuesHost = $("cues"), timeline = $("seek");
  const selectOptions = (el, values) => el.replaceChildren(...values.map(v => new Option(v, v)));
  for (const [id, list] of Object.entries({ mode: P.modes, motion: P.motions, mark: P.marks, shape: P.shapes, aspect: Object.keys(P.aspects) })) selectOptions($(id), list);
  let project = P.demo(), selected = 0, position = 1.0, reviewed = false;
  let running = null, attempt = 0, preparing = false, audio, master;
  const cached = new Map();
  const getScene = () => project.scenes[selected];
  const say = value => { $("status").textContent = value; };
  const seconds = value => value.toFixed(2) + "s";
  const canRecord = () => typeof canvas.captureStream === "function" && typeof MediaRecorder !== "undefined" &&
    ["video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm"].some(m => MediaRecorder.isTypeSupported(m));

  function reviewControls() {
    $("approve").disabled = !reviewed || Boolean(running) || preparing;
    $("export").disabled = !reviewed || !$("approve").checked || Boolean(running) || preparing || !canRecord();
  }
  function invalidate() {
    reviewed = false; $("approve").checked = false; reviewControls();
  }
  function resize(full = false) {
    const [w, h] = P.aspects[project.aspect], scale = full ? 1 : Math.min(1, 960 / Math.max(w, h));
    canvas.width = Math.round(w * scale); canvas.height = Math.round(h * scale);
  }
  function draw() {
    MotionFrame.draw(canvas, project, position);
    timeline.max = P.duration(project); timeline.value = position;
    $("clock").textContent = seconds(position) + " / " + seconds(P.duration(project));
  }

  function renderList() {
    $("scenes").replaceChildren(...project.scenes.map((s, i) => {
      const b = document.createElement("button"), title = document.createElement("strong"), meta = document.createElement("span");
      title.textContent = s.title || "Untitled Scene";
      meta.textContent = s.mode + " · " + seconds(P.start(project, i)) + " · " + seconds(s.duration);
      b.className = "scene"; b.setAttribute("aria-current", String(i === selected)); b.append(title, meta);
      b.onclick = () => { halt(); selectScene(i); };
      return b;
    }));
    $("up").disabled = selected === 0; $("down").disabled = selected === project.scenes.length - 1;
    $("remove").disabled = project.scenes.length === 1; $("addScene").disabled = $("duplicate").disabled = project.scenes.length >= 80;
  }
  function selectScene(index, jump = true) {
    selected = index;
    if (jump) position = P.start(project, index) + Math.min(1, getScene().duration * 0.55);
    renderList(); inspector(); draw();
  }
  function inspector() {
    const s = getScene();
    for (const key of ["mode", "duration", "eyebrow", "title", "body", "motion", "mark", "shape", "material", "light", "lightYaw", "lightElevation", "intensity", "background", "foreground", "accent", "azimuth", "elevation", "orbit", "spin", "distance", "gloss"])
      $(key).value = s[key];
    $("steps").value = s.steps.join("\n");
    $("spaceFields").hidden = s.mode !== "3D Object"; $("stepsField").hidden = s.mode !== "Process Diagram"; $("bodyField").hidden = s.mode === "Process Diagram";
    showCues();
  }
  function showProject() {
    $("projectTitle").value = project.title; $("aspect").value = project.aspect; $("fps").value = project.fps;
    resize(); renderList(); inspector(); draw(); reviewControls();
  }
  function changed() {
    halt(); invalidate(); say("Edits Ready. Save Your Storyboard To Keep This Version.");
  }
  function setPosition(time) {
    position = P.clamp(time, 0, P.duration(project));
    const current = P.locate(project, position).index;
    if (current !== selected) selectScene(current, false);
    else draw();
  }
  timeline.oninput = () => { halt(); setPosition(Number(timeline.value)); };
  $("projectTitle").oninput = () => { changed(); project.title = $("projectTitle").value; };
  $("aspect").onchange = () => { changed(); project.aspect = $("aspect").value; resize(); draw(); };
  $("fps").onchange = () => { changed(); project.fps = Number($("fps").value); };
  for (const key of ["mode", "motion", "mark", "shape"]) $(key).onchange = () => {
    changed(); getScene()[key] = $(key).value; inspector(); renderList(); draw();
  };
  for (const key of ["eyebrow", "title", "body", "background", "foreground", "accent", "material", "light"]) $(key).oninput = () => {
    changed(); getScene()[key] = $(key).value; if (key === "title") renderList(); draw();
  };
  $("steps").oninput = () => { changed(); getScene().steps = $("steps").value.split("\n").slice(0, 5).map(v => v.slice(0, 72)); draw(); };
  for (const key of ["duration", "azimuth", "elevation", "orbit", "spin", "distance", "gloss", "lightYaw", "lightElevation", "intensity"]) $(key).onchange = () => {
    const el = $(key), val = el.valueAsNumber;
    if (!Number.isFinite(val)) { el.value = getScene()[key]; return; }
    changed(); const s = getScene();
    s[key] = P.clamp(val, Number(el.min), Number(el.max)); el.value = s[key];
    if (key === "duration") {
      s.cues.forEach(c => { c.at = Math.min(c.at, s.duration - 0.01); });
      position = P.clamp(position, P.start(project, selected), P.start(project, selected) + s.duration - 0.001);
      showCues(); renderList();
    }
    draw();
  };
  $("addScene").onclick = () => {
    if (project.scenes.length >= 80) return;
    changed(); project.scenes.splice(selected + 1, 0, P.scene()); selectScene(selected + 1);
  };
  $("duplicate").onclick = () => {
    if (project.scenes.length >= 80) return;
    changed(); const s = JSON.parse(JSON.stringify(getScene())); s.id = P.scene().id;
    project.scenes.splice(selected + 1, 0, s); selectScene(selected + 1);
  };
  $("remove").onclick = () => {
    if (project.scenes.length < 2) return;
    changed(); project.scenes.splice(selected, 1); selectScene(Math.min(selected, project.scenes.length - 1));
  };
  function move(delta) {
    const to = selected + delta;
    if (to < 0 || to >= project.scenes.length) return;
    changed(); project.scenes.splice(to, 0, project.scenes.splice(selected, 1)[0]); selectScene(to);
  }
  $("up").onclick = () => move(-1); $("down").onclick = () => move(1);

  function el(tag, className) {
    const item = document.createElement(tag);
    if (className) item.className = className;
    return item;
  }
  function field(label, control) {
    const row = el("label"); row.append(document.createTextNode(label), control); return row;
  }
  function cueNumber(cue, key, label, max) {
    const elem = el("input"); elem.type = "number"; elem.min = 0; elem.max = max; elem.step = 0.01; elem.value = cue[key];
    elem.onchange = () => {
      if (Number.isFinite(elem.valueAsNumber)) { changed(); cue[key] = P.clamp(elem.valueAsNumber, 0, max); }
      elem.value = cue[key];
    };
    return field(label, elem);
  }
  function showCues() {
    const s = getScene();
    cuesHost.replaceChildren(...s.cues.map(cue => {
      const box = el("div", "cue"), head = el("div", "cuehead"), name = el("strong"), remove = el("button");
      name.textContent = cue.type; remove.textContent = "Remove";
      remove.onclick = () => { changed(); s.cues.splice(s.cues.indexOf(cue), 1); showCues(); };
      head.append(name, remove); box.append(head);
      const pair = el("div", "pair"); pair.append(cueNumber(cue, "at", "Start Seconds", s.duration - 0.01), cueNumber(cue, "gain", "Gain", 1)); box.append(pair);
      if (cue.type === "Sound") {
        const picker = el("select"); selectOptions(picker, P.sounds); picker.value = cue.sound;
        picker.onchange = () => { changed(); cue.sound = picker.value; }; box.append(field("Sound", picker));
      } else {
        const script = el("textarea"); script.value = cue.text; script.rows = 2; script.maxLength = 320;
        script.oninput = () => { changed(); cue.text = script.value; }; box.append(field("Voice Line", script));
        const file = el("input"), meta = el("small"); file.type = "file"; file.accept = "audio/*,.wav,.mp3,.m4a,.ogg";
        file.onchange = async () => {
          const source = file.files[0];
          if (!source) return;
          try {
            if (source.size > 20 * 1024 * 1024) throw new Error("Choose A Voice Clip Under 20 MiB.");
            const reader = new FileReader();
            const data = await new Promise((resolve, reject) => { reader.onload = () => resolve(reader.result); reader.onerror = reject; reader.readAsDataURL(source); });
            await bufferFor({ type: "Voice", clip: data });
            if (!project.scenes.includes(s) || !s.cues.includes(cue)) return;
            changed(); cue.clip = data;
            if (s === getScene()) showCues();
            say("Voice Clip Embedded. Save The Storyboard To Keep It.");
          } catch { say("Voice Clip Could Not Be Loaded. Choose A Supported Audio File Under 20 MiB."); }
        };
        meta.textContent = cue.clip ? "Recorded Audio Embedded." : "Script Only. Add A Recording For Audible Voice.";
        box.append(field("Recorded Voice", file), meta);
        if (cue.clip) {
          const clear = el("button"); clear.textContent = "Clear Recording"; clear.onclick = () => { changed(); cue.clip = ""; showCues(); }; box.append(clear);
        }
      }
      return box;
    }));
    $("addSound").disabled = $("addVoice").disabled = s.cues.length >= 64;
  }
  function addCue(type) {
    const s = getScene(); if (s.cues.length >= 64) return;
    changed(); const cue = { type, at: 0, gain: 0.8 };
    if (type === "Sound") cue.sound = P.sounds[0]; else { cue.text = ""; cue.clip = ""; }
    s.cues.push(cue); showCues();
  }
  $("addSound").onclick = () => addCue("Sound"); $("addVoice").onclick = () => addCue("Voice");

  function download(blob, ext) {
    const a = el("a"), url = URL.createObjectURL(blob), slug = project.title.trim().replace(/[^\p{L}\p{N}_ -]+/gu, "").replace(/\s+/g, "-").slice(0, 80);
    a.href = url; a.download = (slug || "Storyboard") + ext; document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  }
  $("save").onclick = () => {
    download(new Blob([JSON.stringify(project, null, 2)], { type: "application/json" }), ".json"); say("Storyboard Download Requested.");
  };
  $("openFile").onchange = async e => {
    const file = e.target.files[0]; if (!file) return;
    try {
      if (file.size > 128 * 1024 * 1024) throw new Error("Project Too Large.");
      const next = P.cleanProject(JSON.parse(await file.text()));
      changed(); cached.clear(); project = next; selected = 0; position = Math.min(1, getScene().duration * 0.55);
      showProject(); say("Storyboard Opened.");
    } catch { say("Could Not Open This Storyboard. Choose A Valid Version One JSON File Under 128 MiB."); }
    e.target.value = "";
  };
  $("sheet").onclick = () => {
    const lines = [project.title, project.aspect + " · " + project.fps + " FPS · " + seconds(P.duration(project)), ""];
    project.scenes.forEach((s, i) => {
      const start = P.start(project, i);
      lines.push("Scene " + (i + 1) + " | " + seconds(start) + " To " + seconds(start + s.duration) + " | " + s.mode, s.title);
      if (s.body && s.mode !== "Process Diagram") lines.push(s.body);
      if (s.mode === "Process Diagram") lines.push(...s.steps);
      [...s.cues].sort((a, b) => a.at - b.at).forEach(c => lines.push(seconds(start + c.at) + " | " + c.type + " | " + (c.type === "Sound" ? c.sound : (c.text || "Voice") + (c.clip ? " (Recording Attached)" : " (Script Only)"))));
      lines.push("");
    });
    download(new Blob([lines.join("\n")], {type: "text/plain;charset=utf-8"}), "-Cue-Sheet.txt"); say("Cue Sheet Download Requested.");
  };

  function audioSystem() {
    if (audio) return;
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) throw new Error("Audio Playback Requires Web Audio.");
    audio = new AC(); master = audio.createDynamicsCompressor();
    master.threshold.value = -4; master.knee.value = 3; master.ratio.value = 8; master.connect(audio.destination);
  }
  async function bufferFor(cue) {
    audioSystem();
    const key = cue.type === "Sound" ? cue.sound : cue.clip;
    if (!key) return null;
    if (!cached.has(key)) {
      const result = (async () => {
        if (cue.type === "Sound") {
          const data = MotionSound.make(cue.sound, audio.sampleRate);
          const buffer = audio.createBuffer(1, data.length, audio.sampleRate); buffer.copyToChannel(data, 0); return buffer;
        }
        const raw = atob(cue.clip.slice(cue.clip.indexOf(",") + 1));
        const bytes = Uint8Array.from(raw, c => c.charCodeAt(0));
        return audio.decodeAudioData(bytes.buffer);
      })();
      cached.set(key, result);
      result.catch(() => cached.delete(key));
    }
    return cached.get(key);
  }
  async function cuePlan(from) {
    const plan = []; let offset = 0;
    for (const s of project.scenes) {
      for (const cue of s.cues) {
        if (offset + s.duration <= from || (!cue.clip && cue.type === "Voice") || cue.gain <= 0) continue;
        plan.push({ cue, start: offset + cue.at, end: offset + s.duration });
      }
      offset += s.duration;
    }
    return Promise.all(plan.map(async item => ({ ...item, buffer: await bufferFor(item.cue) })));
  }
  function schedule(plan, job) {
    for (const item of plan) {
      const skip = Math.max(0, job.from - item.start), wait = Math.max(0, item.start - job.from);
      const span = Math.min(item.buffer.duration, item.end - item.start) - skip;
      if (span <= 0) continue;
      const src = audio.createBufferSource(), gain = audio.createGain(), when = job.base + wait;
      const fade = Math.min(span / 2, 0.008); src.buffer = item.buffer; src.connect(gain); gain.connect(master);
      gain.gain.setValueAtTime(0, when); gain.gain.linearRampToValueAtTime(item.cue.gain, when + fade);
      gain.gain.setValueAtTime(item.cue.gain, when + span - fade); gain.gain.linearRampToValueAtTime(0, when + span);
      src.start(when, skip, span); job.sources.push([src, gain]);
    }
  }

  function halt(completed = false) {
    attempt++; preparing = false; const job = running; running = null;
    if (job) {
      cancelAnimationFrame(job.raf);
      job.sources.forEach(([s, g]) => { try { s.stop(); } catch {} s.disconnect(); g.disconnect(); });
      if (job.recorder) {
        job.keep = completed;
        if (job.recorder.state !== "inactive") job.recorder.stop();
        master.disconnect(job.destination);
        if (!completed) say("Export Interrupted. The Partial Recording Was Discarded.");
      }
      if (completed && job.kind === "review") {
        reviewed = true; say(canRecord() ? "Review Finished. Confirm Your Approval To Enable Export." : "Review Finished. This Browser Does Not Offer WebM Recording.");
      }
      if (completed && job.kind === "play") say("Playback Finished.");
    }
    $("play").textContent = "Play"; $("review").disabled = false; reviewControls();
  }
  function attachRecorder(job) {
    const mime = ["video/webm;codecs=vp9,opus", "video/webm;codecs=vp8,opus", "video/webm"].find(m => MediaRecorder.isTypeSupported(m));
    const dest = audio.createMediaStreamDestination(); job.destination = dest; master.connect(dest);
    const stream = canvas.captureStream(project.fps); dest.stream.getAudioTracks().forEach(track => stream.addTrack(track));
    job.stream = stream;
    const recorder = new MediaRecorder(stream, { mimeType: mime, videoBitsPerSecond: 9000000, audioBitsPerSecond: 192000 });
    const chunks = [];
    recorder.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
    recorder.onerror = () => { if (running === job) { halt(); say("Recording Failed. The Partial Recording Was Discarded."); } };
    recorder.onstop = () => {
      stream.getTracks().forEach(track => track.stop());
      if (job.keep && chunks.length) { download(new Blob(chunks, {type: mime}), ".webm"); say("Approved WebM Download Requested."); }
      else if (job.keep) say("Recording Ended Without A Video File.");
      if (!running) { resize(); draw(); }
    };
    job.recorder = recorder;
  }
  async function begin(kind) {
    if (kind === "export" && (!reviewed || !$("approve").checked || !canRecord())) return;
    halt(); const token = attempt, from = kind === "play" && position < P.duration(project) - 0.02 ? position : 0;
    preparing = true; reviewControls();
    if (kind === "review") invalidate();
    try {
      audioSystem(); await audio.resume(); const plan = await cuePlan(from);
      if (token !== attempt) return;
      const job = { kind, from, base: audio.currentTime + 0.06, sources: [], raf: 0, recorder: null, keep: false };
      running = job; preparing = false;
      if (kind === "export") { resize(true); position = 0; draw(); attachRecorder(job); }
      job.base = audio.currentTime + 0.04;
      schedule(plan, job);
      if (job.recorder) job.recorder.start(500);
      $("play").textContent = kind === "export" ? "Cancel Export" : "Pause"; $("review").disabled = true; reviewControls();
      say(kind === "export" ? "Recording The Approved Cut. Keep This Tab Visible." : kind === "review" ? "Reviewing The Entire Cut. Keep This Tab Visible." : "Playing.");
      function frame() {
        if (running !== job) return;
        const now = Math.max(from, from + audio.currentTime - job.base);
        setPosition(now);
        if (now >= P.duration(project)) { halt(true); return; }
        job.raf = requestAnimationFrame(frame);
      }
      frame();
    } catch {
      if (token !== attempt) return;
      const failed = running;
      halt(); if (failed?.stream) failed.stream.getTracks().forEach(track => track.stop());
      if (failed?.destination && !failed.recorder) { try { master.disconnect(failed.destination); } catch {} }
      resize(); draw(); say("Playback Or Recording Could Not Start. Check Browser Audio Support And Any Embedded Recordings.");
    }
  }
  $("play").onclick = () => { if (running || preparing) { halt(); say("Playback Stopped."); } else begin("play"); };
  $("review").onclick = () => begin("review");
  $("approve").onchange = reviewControls;
  $("export").onclick = () => begin("export");
  document.addEventListener("visibilitychange", () => {
    if (document.hidden && (running || preparing)) { halt(); say("Playback Stopped When The Tab Was Hidden."); }
  });
  showProject();
})();
