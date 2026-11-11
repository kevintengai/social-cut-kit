// Voice Timing: Read Word Timings, Find Spoken Phrases, And Resolve A Storyboard's Phrase Anchors.
// Pure Data In, Pure Data Out. The Same Code Serves The Timing Tool, The Checks, And The Phrase Lookup Inside Code Scenes.
(function (root) {
  "use strict";
  const round = value => Math.round(value * 1000) / 1000;
  const clock = value => (Math.round(value * 100) / 100).toFixed(2) + "s";
  const times = count => count === 1 ? "Once" : count + " Times";
  const quote = text => "“" + text + "”";

  // Reduce Text To Comparable Spoken Tokens: Lower Case, No Punctuation, No Accents, No Apostrophes.
  function tokens(text) {
    return String(text).toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "").replace(/['‘’ʼ]/g, "")
      .replace(/&/g, " and ").split(/[^\p{L}\p{N}]+/u).filter(Boolean);
  }
  function syllables(word) {
    const letters = tokens(word).join("");
    if (!letters) return 1;
    if (/^\d+$/.test(letters)) return letters.length;
    let count = (letters.match(/[aeiouy]+/g) || []).length;
    if (count > 1 && /[^aeiouyl]e$/.test(letters)) count--;
    return Math.max(1, count);
  }
  function textHash(text) {
    let h = 0x811c9dc5;
    for (let i = 0; i < text.length; i++) { h ^= text.charCodeAt(i); h = Math.imul(h, 0x01000193); }
    return (h >>> 0) / 4294967296;
  }
  function problem(code, message) {
    const error = new Error(message);
    error.code = code; error.timing = true;
    return error;
  }

  // ---------------------------------------------------------------- Reading Word Timings
  // Subtitle Text In SRT Or WebVTT Form Becomes A List Of Timed Cues.
  function parseSubtitles(text) {
    const stamp = raw => raw.replace(",", ".").split(":").reverse().reduce((sum, part, i) => sum + parseFloat(part) * Math.pow(60, i), 0);
    const timing = /(\d+(?::\d+){1,2}[.,]\d+)\s+-->\s+(\d+(?::\d+){1,2}[.,]\d+)/, cues = [];
    for (const block of String(text).replace(/^﻿/, "").replace(/\r/g, "").trim().split(/\n\s*\n/)) {
      const lines = block.split("\n"), at = lines.findIndex(line => timing.test(line));
      if (at < 0) continue;
      const match = timing.exec(lines[at]), body = lines.slice(at + 1).join(" ").replace(/<[^>]*>/g, "").replace(/\s+/g, " ").trim();
      if (body) cues.push({ start: stamp(match[1]), end: stamp(match[2]), text: body });
    }
    return cues;
  }
  // Accept The Transcribe Output Of The Video Edit Speech Tool, A Plain Word List, Recognizer Segments, Or Subtitle Text.
  // Returns { words, standIn, approximate } With Words Sorted By Start Time.
  function readWords(raw) {
    let entries, standIn = false, approximate = false;
    if (typeof raw === "string") { entries = parseSubtitles(raw); approximate = true; }
    else if (Array.isArray(raw)) entries = raw;
    else if (raw && Array.isArray(raw.segments)) entries = raw.segments.flatMap(segment => Array.isArray(segment.words) && segment.words.length ? segment.words : [segment]);
    else if (raw && Array.isArray(raw.words)) { entries = raw.words; standIn = raw.standIn === true || raw.standin === true; }
    else throw problem("words", "Word Timings Need A Word List, A Words Entry, Recognizer Segments, Or Subtitle Cues.");
    const words = [];
    for (const entry of entries) {
      const start = Number(entry && entry.start), end = Number(entry && entry.end), text = String((entry && (entry.word ?? entry.text)) ?? "").trim();
      if (!Number.isFinite(start) || !Number.isFinite(end) || start < 0 || end < start || !text)
        throw problem("words", "Every Word Timing Needs A Start, An End That Is Not Earlier, And Text.");
      const parts = text.split(/\s+/);
      if (parts.length === 1) { words.push({ start, end: Math.max(end, start + 0.01), text }); continue; }
      approximate = true;
      const weights = parts.map(part => part.length + 1), total = weights.reduce((sum, w) => sum + w, 0);
      let walked = 0;
      parts.forEach((part, i) => {
        const a = start + (end - start) * walked / total;
        walked += weights[i];
        words.push({ start: a, end: Math.max(start + (end - start) * walked / total, a + 0.01), text: part });
      });
    }
    if (!words.length) throw problem("words", "The Word Timings Are Empty.");
    words.sort((a, b) => a.start - b.start || a.end - b.end);
    return { words, standIn, approximate };
  }

  // ---------------------------------------------------------------- Finding Phrases
  // Spread Each Word Into Tokens With Film Times. `offset` Is When The Recording Starts In The Film.
  function makeIndex(words, offset = 0) {
    const list = [];
    words.forEach((word, at) => {
      const parts = tokens(word.text), total = parts.reduce((sum, part) => sum + part.length, 0);
      let walked = 0;
      for (const part of parts) {
        const start = word.start + (word.end - word.start) * walked / total;
        walked += part.length;
        list.push({ token: part, start: start + offset, end: word.start + (word.end - word.start) * walked / total + offset, word: at });
      }
    });
    return { tokens: list, words, offset };
  }
  // Every Place A Phrase Is Spoken, In Order.
  function find(index, phrase) {
    const want = tokens(phrase), list = index.tokens, out = [];
    if (!want.length) return out;
    for (let i = 0; i + want.length <= list.length; i++) {
      let same = true;
      for (let j = 0; j < want.length; j++) if (list[i + j].token !== want[j]) { same = false; break; }
      if (same) out.push({ first: i, last: i + want.length - 1, start: list[i].start, end: list[i + want.length - 1].end });
    }
    return out;
  }
  // The Closest Spoken Run To A Phrase That Was Not Found, For A Helpful Error.
  function nearest(index, phrase) {
    const want = tokens(phrase), list = index.tokens;
    let best = null;
    for (let i = 0; i < list.length; i++) {
      const span = Math.min(want.length, list.length - i);
      let hits = 0;
      for (let j = 0; j < span; j++) if (list[i + j].token === want[j]) hits++;
      if (hits && (!best || hits > best.hits)) best = { hits, at: i, span };
    }
    if (!best || best.hits < Math.max(1, Math.ceil(want.length / 2))) return null;
    return { text: list.slice(best.at, best.at + best.span).map(item => item.token).join(" "), start: list[best.at].start };
  }
  // Resolve One Anchor To A Film Time, Or Throw A Timing Problem That Names The Phrase.
  // options.span Limits An Unnumbered Phrase To One Scene. options.fromToken Takes The First Occurrence At Or After A Token.
  function resolve(index, anchor, options = {}) {
    const label = options.label || "An Anchor", all = find(index, anchor.phrase);
    if (!tokens(anchor.phrase).length) throw problem("unknown", label + " Uses A Phrase With No Words: " + quote(anchor.phrase) + ".");
    if (!all.length) {
      const near = nearest(index, anchor.phrase);
      throw problem("unknown", label + " Uses A Phrase That Is Not Spoken: " + quote(anchor.phrase) + "." +
        (near ? " The Nearest Spoken Words Are " + quote(near.text) + " At " + clock(near.start) + "." : ""));
    }
    const listed = all.slice(0, 8).map(match => clock(match.start)).join(", ") + (all.length > 8 ? ", And More" : "");
    let match;
    if (anchor.occurrence != null) {
      if (anchor.occurrence > all.length)
        throw problem("range", label + " Asks For Occurrence " + anchor.occurrence + " Of " + quote(anchor.phrase) + ", Which Is Spoken " + times(all.length) + ".");
      match = all[anchor.occurrence - 1];
    } else if (options.fromToken != null) {
      match = all.find(item => item.first >= options.fromToken);
      if (!match) throw problem("order", label + " Uses A Phrase That Is Only Spoken Before The Line Above It: " + quote(anchor.phrase) + " (At " + listed + ").");
    } else if (all.length === 1) match = all[0];
    else {
      const inside = options.span ? all.filter(item => item.start >= options.span[0] - 1e-6 && item.start < options.span[1] - 1e-6) : all;
      if (inside.length !== 1)
        throw problem("ambiguous", label + " Uses A Phrase That Is Spoken " + times(all.length) + ": " + quote(anchor.phrase) + " (At " + listed + "). Add An Occurrence Number.");
      match = inside[0];
    }
    const edge = anchor.edge || options.edge || "start";
    return { time: (edge === "end" ? match.end : match.start) + (anchor.offset || 0), match, occurrence: all.indexOf(match) + 1, count: all.length };
  }
  // The Words Of A Film Voice That Overlap A Film Time Range, As { text, start, end } In Film Time.
  function wordsBetween(voice, from, to) {
    if (!voice || !Array.isArray(voice.words)) return [];
    const offset = voice.offset || 0, out = [];
    for (const word of voice.words) {
      const start = word[0] + offset, end = word[1] + offset;
      if (end > from && start < to) out.push({ text: word[2], start, end });
    }
    return out;
  }
  // The Voice Level From 0 To 1 At A Film Time.
  function levelAt(voice, time) {
    if (!voice || !voice.levels || !voice.levels.values.length) return 0;
    const values = voice.levels.values, x = (time - (voice.offset || 0)) * voice.levels.rate;
    if (x < 0 || x > values.length - 1) return x < 0 || x >= values.length ? 0 : values[values.length - 1];
    const i = Math.floor(x), f = x - i;
    return values[i] + ((values[i + 1] ?? values[i]) - values[i]) * f;
  }

  // ---------------------------------------------------------------- Stand-In Words And Levels
  // Make Plausible Word Timings From Script Text So Building Can Start Before The Voice Exists.
  // Lines That Start With # And Text In [Square Brackets] Are Directions, Not Speech.
  function standIn(script, options = {}) {
    const pace = options.wpm ?? 150, begin = options.start ?? 0.3;
    if (!(pace >= 60 && pace <= 320)) throw problem("words", "Choose A Speaking Pace From 60 To 320 Words Per Minute.");
    const spoken = String(script).replace(/\r/g, "").split("\n").filter(line => !/^\s*(#|\/\/)/.test(line)).join("\n").replace(/\[[^\]]*\]/g, " ");
    const items = [];
    spoken.split(/\n\s*\n/).forEach(paragraph => {
      const parts = paragraph.split(/\s+/).filter(part => tokens(part).length);
      parts.forEach((part, i) => {
        const closing = part.replace(/["'”’)\]]+$/, "");
        const pause = i === parts.length - 1 ? 0.75 : /[.!?…]$/.test(closing) ? 0.42 : /[,;:—–]$/.test(closing) ? 0.18 : 0;
        items.push({ text: part, weight: syllables(part) + 0.45, pause });
      });
    });
    if (!items.length) throw problem("words", "The Script Has No Spoken Words.");
    items[items.length - 1].pause = 0;
    const total = items.length / pace * 60, pauses = items.reduce((sum, item) => sum + item.pause, 0);
    const scale = pauses > total * 0.4 ? total * 0.4 / pauses : 1, speaking = total - pauses * scale;
    const weight = items.reduce((sum, item) => sum + item.weight, 0);
    let at = begin;
    return items.map(item => {
      const span = speaking * item.weight / weight, word = { start: round(at), end: round(at + span * 0.94), text: item.text };
      at += span + item.pause * scale;
      return word;
    });
  }
  // A Plausible Mouth Level From Word Timings Alone, For Use Until Real Audio Is Measured.
  function levelsFromWords(words, rate = 30) {
    const length = Math.ceil(words[words.length - 1].end * rate) + 2, values = new Array(length).fill(0);
    words.forEach((word, n) => {
      const span = Math.max(0.01, word.end - word.start), beats = syllables(word.text), loud = 0.62 + 0.38 * textHash(word.text + "#" + n);
      for (let i = Math.max(0, Math.ceil(word.start * rate)); i <= Math.min(length - 1, Math.floor(word.end * rate)); i++) {
        const u = (i / rate - word.start) / span;
        const level = Math.pow(Math.sin(Math.PI * Math.min(1, Math.max(0, u))), 0.6) * (0.55 + 0.45 * Math.pow(Math.sin(Math.PI * beats * u), 2)) * loud;
        values[i] = Math.max(values[i], Math.round(level * 100) / 100);
      }
    });
    return values;
  }
  // A Measured Level Track From Mono Samples In The Range -1 To 1.
  function levelsFromSamples(samples, sampleRate, rate = 30) {
    const hop = sampleRate / rate, length = Math.max(1, Math.ceil(samples.length / hop)), raw = new Array(length);
    const stride = Math.max(1, Math.floor(hop / 240));
    for (let i = 0; i < length; i++) {
      let sum = 0, used = 0;
      for (let j = Math.floor(i * hop), end = Math.min(samples.length, Math.floor((i + 1) * hop)); j < end; j += stride) { sum += samples[j] * samples[j]; used++; }
      raw[i] = used ? Math.sqrt(sum / used) : 0;
    }
    const sorted = raw.slice().sort((a, b) => a - b), floor = sorted[Math.floor(length * 0.1)] || 0, top = sorted[Math.min(length - 1, Math.floor(length * 0.96))] || 0;
    const range = Math.max(1e-6, top - floor);
    return raw.map(value => Math.round(Math.pow(Math.min(1, Math.max(0, (value - floor) / range)), 0.7) * 100) / 100);
  }

  // ---------------------------------------------------------------- Retiming A Storyboard
  // Resolve Every Phrase Anchor In A Cleaned Storyboard Against Word Timings.
  // Returns { project, problems, notes, report }. Any Entry In `problems` Means The Result Must Not Be Used.
  function retime(project, source, options = {}) {
    const out = JSON.parse(JSON.stringify(project)), problems = [], notes = [], words = source.words;
    const minimumScene = 0.25, count = out.scenes.length;
    let offset = options.offset ?? (project.voice && project.voice.offset) ?? 0;
    if (options.lead != null) offset = round(options.lead - words[0].start);
    const index = makeIndex(words, offset), speechStart = words[0].start + offset, speechEnd = words[words.length - 1].end + offset;
    const attempt = action => {
      try { return action(); } catch (error) { if (!error.timing) throw error; problems.push(error.message); return null; }
    };
    const report = { scenes: [], beats: 0, cues: 0, captions: 0, manualCaptions: 0, mismatches: [], uncaptioned: [], offset, speechStart: round(speechStart), speechEnd: round(speechEnd),
      words: words.length, standIn: Boolean(source.standIn) && project.narration !== "None", approximate: Boolean(source.approximate) };
    if (project.narration === "None") report.narration = "None";

    // Scene Cuts.
    const fixed = new Array(count + 1).fill(null);
    fixed[0] = 0;
    out.scenes.forEach((scene, i) => {
      if (!scene.start) return;
      if (i === 0) { problems.push("Scene 1 Has A Start Anchor, But The First Scene Always Starts At Zero. Remove The Anchor, Or Use The Lead Option To Place The First Word."); return; }
      const hit = attempt(() => resolve(index, scene.start, { label: "Scene " + (i + 1) + " Start" }));
      if (hit) fixed[i] = hit.time;
    });
    out.scenes.forEach((scene, i) => {
      if (!scene.end) return;
      if (out.scenes[i + 1] && out.scenes[i + 1].start) { problems.push("Scene " + (i + 1) + " End And Scene " + (i + 2) + " Start Both Anchor The Same Cut. Keep One."); return; }
      const hit = attempt(() => resolve(index, scene.end, { label: "Scene " + (i + 1) + " End", edge: "end" }));
      if (hit) fixed[i + 1] = hit.time;
    });
    if (fixed[count] == null && options.tail != null) fixed[count] = speechEnd + options.tail;
    const cuts = new Array(count + 1).fill(0);
    let last = 0, ordered = true;
    for (let i = 1; i <= count; i++) {
      if (fixed[i] == null) continue;
      if (fixed[i] - fixed[last] < minimumScene * (i - last) - 1e-9) {
        ordered = false;
        problems.push(i - last === 1
          ? "Scene " + (last + 1) + " Would Last " + clock(fixed[i] - fixed[last]) + " Between Its Cuts At " + clock(fixed[last]) + " And " + clock(fixed[i]) + ". Check The Phrases And Their Occurrence Numbers."
          : "Scenes " + (last + 1) + " To " + i + " Would Share " + clock(fixed[i] - fixed[last]) + " Between Cuts At " + clock(fixed[last]) + " And " + clock(fixed[i]) + ". Check The Phrases And Their Occurrence Numbers.");
      }
      const authored = out.scenes.slice(last, i).reduce((sum, scene) => sum + scene.duration, 0);
      let walked = 0;
      for (let k = last; k < i; k++) { cuts[k] = fixed[last] + (fixed[i] - fixed[last]) * walked / authored; walked += out.scenes[k].duration; }
      cuts[i] = fixed[i]; last = i;
    }
    for (let k = last; k < count; k++) cuts[k + 1] = cuts[k] + out.scenes[k].duration;
    const starts = cuts.map(round);
    out.scenes.forEach((scene, i) => {
      const was = scene.duration, next = round(starts[i + 1] - starts[i]);
      if (ordered && (next < minimumScene || next > 600)) problems.push("Scene " + (i + 1) + " Would Last " + clock(next) + ". A Scene Lasts From 0.25 To 600 Seconds.");
      scene.duration = next;
      report.scenes.push({ scene: i + 1, title: scene.title, start: starts[i], duration: next, was, anchored: fixed[i] != null && i > 0 });
    });

    // Beats And Cues, Relative To Their Scene.
    out.scenes.forEach((scene, i) => {
      const from = starts[i], to = starts[i + 1], label = "Scene " + (i + 1);
      for (const [name, beat] of Object.entries(scene.beats || {})) {
        if (!beat.phrase) continue;
        const hit = attempt(() => resolve(index, beat, { label: label + " Beat " + name, span: [from, to] }));
        if (!hit) continue;
        beat.at = round(hit.time - from); report.beats++;
        if (hit.time < from - 0.0005 || hit.time > to + 0.0005) notes.push(label + " Beat " + name + " Falls Outside Its Scene, At " + clock(beat.at) + " In Scene Time.");
      }
      scene.cues.forEach((cue, j) => {
        const limit = scene.duration - 0.01;
        if (!cue.anchor) {
          if (cue.at > limit) { cue.at = Math.max(0, round(limit)); notes.push(label + " Cue " + (j + 1) + " Was Moved Inside Its Shorter Scene."); }
          return;
        }
        const hit = attempt(() => resolve(index, cue.anchor, { label: label + " Cue " + (j + 1), span: [from, to] }));
        if (!hit) return;
        const at = hit.time - from;
        if (at < -0.05 || at > limit + 0.05) { problems.push(label + " Cue " + (j + 1) + " Is Anchored To " + quote(cue.anchor.phrase) + ", Which Falls Outside Its Scene At " + clock(at) + " In Scene Time. Move The Cue To The Scene That Contains The Phrase."); return; }
        cue.at = round(Math.min(limit, Math.max(0, at))); report.cues++;
      });
    });

    // Captions, Matched In Order.
    if (out.captions) {
      const style = out.captions.style || {}, hold = style.hold ?? 0.3, least = style.minimum ?? 0.7, covered = new Array(index.tokens.length).fill(false);
      let fromToken = 0;
      out.captions.lines.forEach((line, i) => {
        const label = "Caption Line " + (i + 1);
        if (line.phrase == null && line.at != null) { report.manualCaptions++; return; }
        const phrase = line.phrase ?? line.text;
        const hit = attempt(() => resolve(index, { phrase, occurrence: line.occurrence }, { label, fromToken: line.occurrence ? undefined : fromToken }));
        if (!hit) return;
        const shown = line.text.split(/\s+/).filter(Boolean).map(tokens), flat = shown.flat();
        let closing = hit.match;
        if (line.until) {
          const until = attempt(() => resolve(index, { phrase: line.until }, { label: label + " Until", fromToken: hit.match.first }));
          if (!until) return;
          closing = until.match;
        } else {
          // A Short Anchor Phrase May Open A Longer Line. When The Whole Line Is Spoken From There, Time The Whole Line.
          const reach = hit.match.first + flat.length - 1;
          if (reach > closing.last && reach < index.tokens.length && flat.every((token, k) => index.tokens[hit.match.first + k].token === token))
            closing = { first: hit.match.first, last: reach, start: hit.match.start, end: index.tokens[reach].end };
        }
        const spoken = index.tokens.slice(hit.match.first, closing.last + 1);
        line.phrase = phrase; line.at = round(hit.match.start); line.end = round(closing.end + hold);
        if (flat.length === spoken.length && flat.every((token, k) => token === spoken[k].token)) {
          let k = 0;
          line.words = shown.map(parts => { const at = spoken[Math.min(k, spoken.length - 1)].start; k += parts.length; return round(at); });
        } else {
          delete line.words;
          report.mismatches.push({ line: i + 1, text: line.text, spoken: spoken.map(item => item.token).join(" "), at: line.at });
        }
        for (let k = hit.match.first; k <= closing.last; k++) covered[k] = true;
        fromToken = closing.last + 1; report.captions++;
      });
      const timed = out.captions.lines.map((line, i) => ({ line, i })).filter(item => item.line.at != null).sort((a, b) => a.line.at - b.line.at || a.i - b.i);
      timed.forEach((item, n) => {
        const line = item.line, next = timed[n + 1];
        if (next && next.line.at - line.at < 0.05) { problems.push("Caption Lines " + (item.i + 1) + " And " + (next.i + 1) + " Start Within A Twentieth Of A Second Of Each Other At " + clock(line.at) + "."); return; }
        if (line.phrase == null) {
          for (let k = 0; k < index.tokens.length; k++) if (index.tokens[k].end > line.at && index.tokens[k].start < line.end) covered[k] = true;
          return;
        }
        if (line.end - line.at < least) line.end = round(line.at + least);
        if (next && line.end > next.line.at) line.end = next.line.at;
      });
      let run = null;
      index.tokens.forEach((item, k) => {
        if (!covered[k]) { if (!run) run = { text: [], at: item.start }; run.text.push(item.token); }
        if ((covered[k] || k === index.tokens.length - 1) && run) { report.uncaptioned.push({ text: run.text.join(" "), at: round(run.at) }); run = null; }
      });
    }

    // The Film Voice Carries The Words And A Level Track So Scenes Can Follow The Speech.
    const voice = Object.assign({ gain: 1 }, out.voice, { offset: round(offset), words: words.map(word => [round(word.start), round(word.end), word.text]) });
    // Stand-In Words Mark The Film As Not Ready For Export, Unless The Storyboard Declares That It Has No Narration.
    if (report.standIn) voice.standIn = true; else delete voice.standIn;
    if (options.levels) voice.levels = { rate: options.levels.rate, values: options.levels.values };
    else voice.levels = { rate: 30, values: levelsFromWords(words, 30), estimated: true };
    out.voice = voice;
    report.duration = round(starts[count]);
    if (speechEnd > starts[count] + 0.05) notes.push("The Voice Runs To " + clock(speechEnd) + " But The Film Ends At " + clock(starts[count]) + ". Anchor The Last Scene End Or Use The Tail Option.");
    if (source.approximate) notes.push("Some Word Times Were Estimated Inside Longer Cues, So Phrase Starts Inside A Cue Are Approximate.");
    return { project: out, problems, notes, report };
  }

  const api = { tokens, syllables, parseSubtitles, readWords, makeIndex, find, nearest, resolve, wordsBetween, levelAt, standIn, levelsFromWords, levelsFromSamples, retime, clock };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.MotionTiming = api;
})(globalThis);
