"use strict";
// Timing And Layout For A Social Cut Kit Timeline In Remotion.
// This Module Imports Nothing, So Node Tests It Without Remotion And The Generated Project Bundles The Same File.
// It Follows scripts/timeline.py And scripts/media.py Rule For Rule So Both Routes Agree On Frames And Geometry.

class CutError extends Error {}

const fail = message => { throw new CutError(message); };

// Python Rounds A Tie To The Even Neighbor. The FFmpeg Route Computes Its Geometry That Way.
function pyRound(value) {
  const floor = Math.floor(value), part = value - floor;
  if (part < 0.5) return floor;
  if (part > 0.5) return floor + 1;
  return floor % 2 === 0 ? floor : floor + 1;
}

// A Time In Seconds Snapped To The Nearest Output Frame, As timeline.py Does.
const quantize = (seconds, fps) => Math.floor(seconds * fps + 0.5) / fps;
const frameOf = (seconds, fps) => Math.floor(seconds * fps + 0.5);

const HDR_TRANSFERS = {smpte2084: "pq", "arib-std-b67": "hlg"};
const HDR_NAMES = {pq: "PQ", hlg: "HLG"};
const FONTS = ["Arial", "Georgia", "Verdana", "Tahoma", "Trebuchet MS"];
// The FFmpeg Route Sizes Caption Text So The Font's Full Ascent Plus Descent Equals The Caption Size.
// A Browser Sizes Text By Its Em Square. Each Value Is The Em Square Divided By That Font's Ascent Plus Descent.
const FONT_EM = {Arial: 2048 / 2288, Georgia: 2048 / 2327, Verdana: 2048 / 2489, Tahoma: 2048 / 2472, "Trebuchet MS": 2048 / 2378};
const FONT_STACK = {
  Arial: "Arial, Helvetica, 'Liberation Sans', sans-serif",
  Georgia: "Georgia, 'Times New Roman', serif",
  Verdana: "Verdana, 'DejaVu Sans', sans-serif",
  Tahoma: "Tahoma, Verdana, sans-serif",
  "Trebuchet MS": "'Trebuchet MS', Verdana, sans-serif"
};
// What Chrome Decodes Without Help. Anything Else Draws A Warning.
const BROWSER_VIDEO = new Set(["h264", "vp8", "vp9", "av1"]);
const BROWSER_AUDIO = new Set(["aac", "mp3", "opus", "vorbis", "flac"]);
const BROWSER_IMAGE = new Set(["png", "mjpeg", "webp", "gif", "bmp", "apng"]);
const BROWSER_CONTAINER = /mp4|mov|m4a|webm|matroska|ogg|wav|mp3|flac|image2|png_pipe|jpeg_pipe|webp_pipe|gif|bmp_pipe|apng/;

function fraction(value) {
  if (typeof value === "string" && /[:/]/.test(value)) {
    const [top, bottom] = value.split(/[:/]/, 2).map(Number);
    const result = top / bottom;
    return Number.isFinite(result) ? result : null;
  }
  const result = typeof value === "string" && value.trim() !== "" ? Number(value) : typeof value === "number" ? value : NaN;
  return Number.isFinite(result) ? result : null;
}

// Clockwise Degrees Applied For Display. FFprobe Reports The Display Matrix Counterclockwise.
function rotation(video) {
  const positive = turn => ((Math.round(turn) % 360) + 360) % 360;
  for (const side of video.side_data_list || []) {
    if (side && typeof side === "object" && "rotation" in side) {
      const turn = Number(side.rotation);
      if (!Number.isFinite(turn)) break;
      return positive(-turn);
    }
  }
  const tagged = Number((video.tags || {}).rotate ?? 0);
  return Number.isFinite(tagged) ? positive(tagged) : 0;
}

function bitDepth(video) {
  const raw = String(video.bits_per_raw_sample || "");
  if (/^\d+$/.test(raw) && Number(raw)) return Number(raw);
  const name = String(video.pix_fmt || "").toLowerCase();
  if (name.includes("f32")) return 32;
  if (name.includes("f16") || /(48|64)(le|be)?$/.test(name)) return 16;
  const match = name.startsWith("nv") ? null : name.match(/(9|1[0246])(le|be)?$/);
  return match ? Number(match[1]) : 8;
}

// Displayed Geometry, Bit Depth, And Color Signalling For One Picture Stream.
function pictureInfo(video) {
  if (!video) return null;
  const turn = rotation(video), width = video.width, height = video.height;
  let shown = null;
  if (Number.isInteger(width) && Number.isInteger(height)) {
    const sar = fraction(video.sample_aspect_ratio) || 1;
    shown = [Math.max(1, pyRound(width * sar)), height];
    if (pyRound(turn / 90) % 2) shown.reverse();
  }
  const named = key => typeof video[key] === "string" && video[key] !== "" && video[key] !== "unknown" ? video[key] : "unspecified";
  const transfer = named("color_transfer");
  let dolby = null;
  for (const side of video.side_data_list || []) {
    const kind = String((side && side.side_data_type) || "").toLowerCase();
    if (kind.includes("dovi") || kind.includes("dolby vision")) dolby = {profile: side.dv_profile ?? null};
  }
  const rate = fraction(video.avg_frame_rate) || fraction(video.r_frame_rate);
  return {codec: video.codec_name ?? null, pixel_format: video.pix_fmt ?? null, bit_depth: bitDepth(video),
    coded_size: [width, height], displayed_size: shown, rotation: turn, frame_rate: rate ? Math.round(rate * 10000) / 10000 : null,
    color_transfer: transfer, color_primaries: named("color_primaries"), hdr: HDR_TRANSFERS[transfer] || null, dolby_vision: dolby};
}

// The Parts Of An FFprobe Report That The Plan Needs. Pass The Parsed JSON From -show_format -show_streams.
function probeSummary(data) {
  const streams = data.streams || [];
  const video = streams.find(s => s.codec_type === "video" && !(s.disposition || {}).attached_pic) || null;
  const audio = streams.find(s => s.codec_type === "audio") || null;
  const length = (data.format || {}).duration;
  const duration = length && length !== "N/A" && Number.isFinite(Number(length)) ? Number(length) : null;
  return {duration, video, audio, format: (data.format || {}).format_name || "", picture: pictureInfo(video)};
}

function number(value, name, minimum = 0, maximum = 86400) {
  if (typeof value !== "number" || !Number.isFinite(value) || value < minimum || value > maximum)
    fail(`${name} Must Be A Number Between ${minimum} And ${maximum}.`);
  return value;
}
function integer(value, name, minimum, maximum) {
  if (!Number.isInteger(value)) fail(`${name} Requires A Whole Number.`);
  return number(value, name, minimum, maximum);
}
function fields(item, allowed, name) {
  if (!item || typeof item !== "object" || Array.isArray(item)) fail(`${name} Requires An Object.`);
  const known = new Set(allowed.split(" "));
  const unknown = Object.keys(item).filter(key => !known.has(key)).sort();
  if (unknown.length) fail(`Unknown ${name} Field ${unknown[0]}.`);
}
function word(value, name) {
  if (typeof value !== "string" || !value.trim()) fail(`${name} Requires Text.`);
  return value;
}
function choice(value, options, name) {
  if (!options.includes(value)) fail(`Unsupported ${name} Value ${value}.`);
  return value;
}
function flag(value, name) {
  if (typeof value !== "boolean") fail(`${name} Requires true Or false.`);
  return value;
}
function collection(doc, key) {
  const items = doc[key] ?? [];
  if (!Array.isArray(items) || !items.every(x => x && typeof x === "object" && !Array.isArray(x))) fail(`${key} Requires A List Of Objects.`);
  return items;
}

// The Same Crop, Scale, And Pad That The FFmpeg Route Applies To A Shot.
function framing(video, w, h, fit, zoom, panX, panY) {
  let sw = video.width ?? w, sh = video.height ?? h;
  const ratio = /^(\d+):(\d+)$/.exec(video.sample_aspect_ratio || "1:1");
  let sar = ratio && Number(ratio[1]) && Number(ratio[2]) ? Number(ratio[1]) / Number(ratio[2]) : 1;
  // The Decoder Turns A Rotated Clip Upright Before Any Framing.
  if (pyRound(rotation(video) / 90) % 2) [sw, sh, sar] = [sh, sw, 1 / sar];
  const scale = (fit === "cover" ? Math.max : Math.min)(w / (sw * sar), h / sh) * zoom;
  const drawW = sw * sar * scale, drawH = sh * scale;
  const anchorX = (panX + 1) / 2, anchorY = (panY + 1) / 2;
  const cropW = Math.min(sw, Math.max(1, pyRound(sw * w / drawW))), cropH = Math.min(sh, Math.max(1, pyRound(sh * h / drawH)));
  const visibleW = Math.min(w, Math.max(2, 2 * pyRound(drawW / 2))), visibleH = Math.min(h, Math.max(2, 2 * pyRound(drawH / 2)));
  return {source: [sw, sh],
    crop: [cropW, cropH, pyRound((sw - cropW) * anchorX), pyRound((sh - cropH) * anchorY)],
    scale: [visibleW, visibleH],
    pad: [pyRound((w - visibleW) * anchorX), pyRound((h - visibleH) * anchorY)]};
}

// Canvas Pixels For A Shot: A Clipping Box, And The Whole Upright Picture Placed Inside It.
function shotLayout(geometry) {
  const [sw, sh] = geometry.source, [cropW, cropH, cropX, cropY] = geometry.crop;
  const [boxW, boxH] = geometry.scale, [left, top] = geometry.pad;
  const kx = boxW / cropW, ky = boxH / cropH;
  return {box: {left, top, width: boxW, height: boxH},
    media: {left: 0 - cropX * kx, top: 0 - cropY * ky, width: sw * kx, height: sh * ky}};
}

// FFmpeg Scales An Overlay To Its Width And Rounds The Height To An Even Number.
function overlayHeight(video, width) {
  let sw = video.width, sh = video.height;
  if (!sw || !sh) return width;
  if (pyRound(rotation(video) / 90) % 2) [sw, sh] = [sh, sw];
  return Math.max(2, Math.round(width * sh / (sw * 2)) * 2);
}

// Caption Defaults For A Vertical Canvas, Where The Platform Draws Its Own Controls Over The Video. They Match timeline.py.
const VERTICAL_CAPTIONS = {size: 0.06, margin: 25, top_margin: 12};
const HORIZONTAL_MARGIN = 7;

function captionStyle(doc, w, h) {
  const style = doc.caption_style ?? {};
  fields(style, "font size color outline stroke margin top_margin", "Caption Style");
  const font = choice(style.font ?? "Arial", FONTS, "Caption Font");
  const color = (key, fallback) => {
    const value = style[key] ?? fallback;
    if (typeof value !== "string" || !/^#[0-9a-fA-F]{6}$/.test(value)) fail(`${key} Requires A Six-Digit Hex Color.`);
    return value;
  };
  const tall = h > w;
  const usual = tall ? pyRound(w * VERTICAL_CAPTIONS.size) : pyRound(Math.min(h * 0.078, w * 0.085));
  const size = integer(style.size ?? Math.max(12, usual), "Caption Size", 4, 1024);
  const margin = number(style.margin ?? (tall ? VERTICAL_CAPTIONS.margin : HORIZONTAL_MARGIN), "Caption Margin", 0, 45);
  // A Timeline That Sets Its Own Margin Keeps One Margin For Both Edges, As Before.
  const above = style.margin !== undefined && style.margin !== null ? margin : tall ? VERTICAL_CAPTIONS.top_margin : HORIZONTAL_MARGIN;
  return {font, size, color: color("color", "#FFFFFF"), outline: color("outline", "#101010"),
    stroke: number(style.stroke ?? Math.max(1, pyRound(size * 0.07)), "Caption Stroke", 0, 96),
    margin, top_margin: number(style.top_margin ?? above, "Caption Top Margin", 0, 45)};
}

// Caption Measurements In Canvas Pixels, Matching The Margins And Text Height Of The FFmpeg Route.
function captionLayout(style, w, h) {
  return {fontFamily: FONT_STACK[style.font], fontSize: style.size * FONT_EM[style.font], lineHeight: style.size,
    side: pyRound(w * 0.055), edge: pyRound(h * style.margin / 100),
    topEdge: pyRound(h * (style.top_margin ?? style.margin) / 100), stroke: style.stroke,
    color: style.color, outline: style.outline};
}

// Linear Gain For One Output Frame Of A Shot Or Cue, With Its Straight Fades. The Frame Is Counted From Its Own Start.
function levelAt(sound, frame, frames, fps) {
  const t = (frame + 0.5) / fps, length = frames / fps, clamp = x => Math.max(0, Math.min(1, x));
  let gain = sound.gain;
  if (sound.fadeIn > 0) gain *= clamp(t / sound.fadeIn);
  if (sound.fadeOut > 0) gain *= clamp(1 - (t - Math.max(0, length - sound.fadeOut)) / sound.fadeOut);
  return gain;
}

// FFmpeg Places Each Source Frame On The Output Frame Nearest Its Retimed Time, And A Frame Exactly Halfway Goes To
// The Later One. Sampling The Source Just Under Half An Output Frame Late Selects The Same Frame.
const NEAREST = 0.499;
// Source Seconds Shown On One Output Frame Of A Shot Or Overlay.
function sourceSeconds(row, frame, fps) {
  return row.start + (frame + NEAREST) * (row.speed ?? 1) / fps;
}
// The Trim Remotion Needs, In Output Frames, So The Picture At Frame Zero Is sourceSeconds(row, 0).
function pictureTrim(row, fps) {
  return row.start * fps + NEAREST * (row.speed ?? 1);
}

function colorFilter(shot) {
  if (shot.brightness === 1 && shot.contrast === 1 && shot.saturation === 1) return null;
  return `brightness(${shot.brightness}) contrast(${shot.contrast}) saturate(${shot.saturation})`;
}

// Validate A Timeline The Way timeline.py Does And Return Its Model In Seconds. probes Maps Each Asset
// Name To A probeSummary Result. A Missing Entry Means The File Was Not Found. copies Maps The Name Of Each
// Asset That Has A Working Copy To The probeSummary Result Of That Copy.
function model(doc, probes, copies = {}) {
  fields(doc, "version title canvas assets shots overlays captions audio caption_style", "Project");
  if (!Number.isInteger(doc.version) || doc.version !== 1) fail("Set Project Version To 1.");
  const title = word(doc.title, "Title");
  const canvas = doc.canvas ?? {};
  fields(canvas, "width height fps fit tone_map", "Canvas");
  const w = integer(canvas.width ?? 1080, "Width", 16, 8192), h = integer(canvas.height ?? 1920, "Height", 16, 8192);
  if (w % 2 || h % 2) fail("Canvas Dimensions Must Be Even.");
  const fps = integer(canvas.fps ?? 30, "FPS", 1, 120);
  const fit = choice(canvas.fit ?? "contain", ["contain", "cover"], "Fit");
  const toneDefault = flag(canvas.tone_map ?? true, "Canvas Tone Map");
  if (!doc.assets || typeof doc.assets !== "object" || Array.isArray(doc.assets)) fail("Assets Requires A Named Object.");
  const assets = {}, uses = {};
  for (const [key, obj] of Object.entries(doc.assets)) {
    word(key, "Asset Name");
    fields(obj, "path kind working_copy", "Asset");
    const file = word(obj.path, "Asset Path");
    const meta = probes[key];
    if (!meta) fail(`Missing Asset ${file}.`);
    const kind = choice(obj.kind, ["video", "image", "audio"], "Asset Kind");
    if (!(kind === "audio" ? meta.audio : meta.video)) fail(`Missing ${kind} Stream In ${file}.`);
    assets[key] = {...meta, path: file, kind};
    if (obj.working_copy !== undefined) {
      // The Original Supplies Geometry And Timing. The Working Copy Supplies What Remotion Plays.
      if (kind !== "video") fail("Only A Video Asset Can Name A Working Copy.");
      const twin = word(obj.working_copy, "Working Copy Path");
      if (!copies[key]) fail(`Missing Working Copy ${twin}.`);
      if (!copies[key].video) fail(`Missing Video Stream In ${twin}.`);
      assets[key].working = {...copies[key], path: twin};
    }
  }
  const asset = (item, kinds) => {
    const key = word(item.asset, "Asset");
    if (!Object.prototype.hasOwnProperty.call(assets, key) || !kinds.includes(assets[key].kind)) fail(`Invalid Asset For This Track ${key}.`);
    return assets[key];
  };
  const placed = (row, item, key, label, tone) => {
    row.tone_map = tone;
    (uses[key] = uses[key] || []).push(label);
    return row;
  };
  const within = (end, item) => {
    if (item.kind !== "image" && item.duration !== null && end > item.duration + 0.001) fail(`Selection Extends Past The End Of ${item.path}.`);
  };
  const faded = (row, obj, length, label) => {
    const rise = number(obj.fade_in ?? 0, `${label} Fade In`, 0, 60), fall = number(obj.fade_out ?? 0, `${label} Fade Out`, 0, 60);
    if (rise + fall > length + 1e-9) fail(`${label} Fades Must Fit Inside Its ${Number(length.toPrecision(6))} Second Length.`);
    row.fade_in = rise; row.fade_out = fall;
    return row;
  };
  const shots = [];
  let total = 0;
  for (const obj of collection(doc, "shots")) {
    fields(obj, "asset in out lead tail speed gain fit zoom pan_x pan_y brightness contrast saturation tone_map fade_in fade_out", "Shot");
    const a = asset(obj, ["video", "image"]);
    const start = number(obj.in ?? 0, "Shot In") - number(obj.lead ?? 0, "Lead");
    const end = number(obj.out, "Shot Out") + number(obj.tail ?? 0, "Tail");
    if (start < 0 || end <= start || obj.out <= (obj.in ?? 0)) fail("Shot Bounds And Handles Must Form A Positive Source Range.");
    within(end, a);
    const speed = number(obj.speed ?? 1, "Speed", 0.25, 4);
    const duration = quantize((end - start) / speed, fps);
    if (duration <= 0) fail("Shot Requires At Least One Output Frame.");
    const shotFit = choice(obj.fit ?? fit, ["contain", "cover"], "Fit");
    const zoom = number(obj.zoom ?? 1, "Zoom", 1, 4), panX = number(obj.pan_x ?? 0, "Pan X", -1, 1), panY = number(obj.pan_y ?? 0, "Pan Y", -1, 1);
    const tone = flag(obj.tone_map ?? toneDefault, "Shot Tone Map");
    const shot = {asset: obj.asset, start, end, at: total, duration, speed, gain: number(obj.gain ?? 1, "Gain", 0, 4), fit: shotFit,
      zoom, pan_x: panX, pan_y: panY, geometry: framing(a.video, w, h, shotFit, zoom, panX, panY),
      brightness: number(obj.brightness ?? 1, "Brightness", 0, 3), contrast: number(obj.contrast ?? 1, "Contrast", 0, 3),
      saturation: number(obj.saturation ?? 1, "Saturation", 0, 2)};
    shots.push(placed(faded(shot, obj, duration, "Shot"), a, obj.asset, `Shot ${shots.length + 1}`, tone));
    total = quantize(total + duration, fps);
  }
  if (!shots.length) fail("Add At Least One Shot.");
  const span = (obj, label) => {
    const at = quantize(number(obj.at ?? 0, `${label} Start`), fps), end = quantize(number(obj.end, `${label} End`), fps);
    if (end <= at || end > total) fail(`${label} Must Fit Inside The Timeline And Last At Least One Frame.`);
    return [at, end];
  };
  const overlays = [], audio = [], captions = [];
  for (const obj of collection(doc, "overlays")) {
    fields(obj, "asset at end in x y width tone_map", "Overlay");
    const a = asset(obj, ["video", "image"]);
    const [at, end] = span(obj, "Overlay");
    const start = number(obj.in ?? 0, "Overlay Source In");
    within(start + end - at, a);
    const tone = flag(obj.tone_map ?? toneDefault, "Overlay Tone Map");
    const width = integer(obj.width ?? w, "Overlay Width", 2, w * 4);
    const overlay = {asset: obj.asset, at, end, start, x: integer(obj.x ?? 0, "Overlay X", -w, w), y: integer(obj.y ?? 0, "Overlay Y", -h, h),
      width, height: overlayHeight(a.video, width)};
    overlays.push(placed(overlay, a, obj.asset, `Overlay ${overlays.length + 1}`, tone));
  }
  for (const obj of collection(doc, "audio")) {
    fields(obj, "asset at end in gain fade_in fade_out", "Audio");
    const a = asset(obj, ["audio", "video"]);
    if (!a.audio) fail("Audio Cue Requires An Audio Stream.");
    const [at, end] = span(obj, "Audio Cue");
    const start = number(obj.in ?? 0, "Audio Source In");
    within(start + end - at, a);
    audio.push(faded({asset: obj.asset, at, end, start, gain: number(obj.gain ?? 1, "Gain", 0, 4)}, obj, end - at, "Audio Cue"));
  }
  for (const obj of collection(doc, "captions")) {
    fields(obj, "at end text position", "Caption");
    const [at, end] = span(obj, "Caption");
    captions.push({at, end, text: word(obj.text, "Caption Text"),
      position: choice(obj.position ?? "bottom", ["top", "center", "bottom"], "Caption Position")});
  }
  return {title, width: w, height: h, fps, duration: total, assets, uses, shots, overlays, captions, audio, caption_style: captionStyle(doc, w, h)};
}

const HDR_REFUSAL = "The Remotion Route Does Not Apply The Kit's Single HDR Conversion, So Its Colors Would Not Match " +
  "The Checked Stills. To Review In Remotion, Ask The Owner Once For A Working Copy, Make It With The Working Copy Command, " +
  "And Name It In The Asset's working_copy Field. Deliver This Edit Through The FFmpeg Render, Or Prepare With " +
  "--allow-hdr To Review It In Remotion With Remotion's Own Conversion.";

// Everything In The Timeline That Remotion Reproduces Differently From The FFmpeg Route, In Plain Sentences.
function limits(m, options = {}) {
  const notes = [], fps = m.fps, list = names => names.join(", ");
  const soundful = shot => m.assets[shot.asset].kind !== "image" && m.assets[shot.asset].audio && shot.gain > 0;
  for (const [key, places] of Object.entries(m.uses)) {
    const info = m.assets[key].picture || {}, dolby = info.dolby_vision || {};
    const working = m.assets[key].working, twin = working ? working.picture || {} : null;
    if (working && !twin.hdr) {
      // A Working Copy Already Carries The Kit's Conversion And Is Stored Upright, So Nothing Here Is Refused.
      const size = twin.displayed_size ? `${twin.displayed_size[0]} By ${twin.displayed_size[1]}` : "Its Own Size";
      const color = info.hdr ? `The Original Is ${HDR_NAMES[info.hdr]} HDR. Picture Color In Remotion Comes From The Working Copy, ` +
        "Which Already Carries The Kit's Single Conversion To Standard Dynamic Range. " : "";
      notes.push(`Asset ${key}, Used By ${list(places)}, Plays From Its Working Copy In Remotion At ${size}. ${color}` +
        "A Remotion Render Would Be Made From That Copy, Not From The Original. Render The Master With FFmpeg From The Original.");
      const first = m.assets[key].duration, second = working.duration, rate = info.frame_rate || 30;
      if (first !== null && second !== null && Math.abs(first - second) > Math.max(0.05, 1 / rate))
        notes.push(`Asset ${key} Working Copy Lasts ${second.toFixed(3)} Seconds And Its Original Lasts ${first.toFixed(3)} Seconds. ` +
          "Review Timing May Not Match The Render. Make A Fresh Working Copy.");
      const count = video => /^\d+$/.test(String((video || {}).nb_frames ?? "")) ? Number(video.nb_frames) : null;
      const a = count(m.assets[key].video), b = count(working.video);
      if (a !== null && b !== null && Math.abs(a - b) > 1)
        notes.push(`Asset ${key} Working Copy Has ${b} Frames And Its Original Has ${a}. Frames Seen In Review May Not Be The Frames Rendered. ` +
          "Make A Fresh Working Copy.");
      const shown = info.displayed_size, seen = twin.displayed_size;
      if (shown && seen && Math.abs(shown[0] / shown[1] - seen[0] / seen[1]) > 0.01 * shown[0] / shown[1])
        notes.push(`Asset ${key} Working Copy Is ${seen[0]} By ${seen[1]} And Its Original Displays At ${shown[0]} By ${shown[1]}. ` +
          "The Shapes Differ, So Framing In Remotion Will Not Match The Render.");
      if (twin.rotation) notes.push(`Asset ${key} Working Copy Carries A ${twin.rotation} Degree Display Rotation. A Working Copy Must Be Stored Upright.`);
      if (info.hdr && [...m.shots, ...m.overlays].some(row => row.asset === key && !row.tone_map))
        notes.push(`Asset ${key} Is Used Where tone_map Is false, But Its Working Copy Is Already Converted. Remotion Shows The Converted Picture ` +
          "And The FFmpeg Render Passes The Original Through Unconverted.");
      if (m.assets[key].audio && !working.audio && (m.shots.some(s => s.asset === key && s.gain > 0) || m.audio.some(c => c.asset === key)))
        notes.push(`Asset ${key} Working Copy Has No Sound, So Its Shots Are Silent In Remotion. Make A Fresh Working Copy.`);
      continue;
    }
    if (info.hdr || dolby.profile === 5 || (twin && twin.hdr)) {
      const label = info.hdr ? `${HDR_NAMES[info.hdr]} HDR` : twin && twin.hdr ? `Given A Working Copy That Is Itself ${HDR_NAMES[twin.hdr]} HDR` : "Dolby Vision Profile 5";
      if (!options.allowHdr) fail(`Asset ${key} Is ${label}, Used By ${list(places)}. ${HDR_REFUSAL}`);
      notes.push(`Asset ${key} Is ${label}, Used By ${list(places)}. Remotion Converts It With Its Own Tone Mapping When ` +
        "It Renders, And Remotion Studio Shows The Browser's Conversion. Neither Matches The Kit's Conversion Or Its Stills. " +
        "This Kit Has Not Verified HDR In Remotion. Use The FFmpeg Render For Delivery.");
    } else if (info.color_primaries === "bt2020") {
      notes.push(`Asset ${key} Has bt2020 Primaries Without A PQ Or HLG Transfer. Remotion And The Browser May Show Its Colors Differently From The FFmpeg Route.`);
    }
    const turn = info.rotation || 0;
    if (turn % 90) notes.push(`Asset ${key} Has A ${turn} Degree Display Rotation. Only Right-Angle Rotations Are Framed Correctly.`);
    else if (turn) notes.push(`Asset ${key} Has A ${turn} Degree Display Rotation. The Layout Assumes Remotion Shows It Upright. ` +
      "This Kit Has Not Verified Rotated Clips In Remotion, So Check Its Framing In Remotion Studio.");
  }
  const used = new Set([...m.shots, ...m.overlays, ...m.audio].map(row => row.asset));
  for (const key of used) {
    // Format Checks Describe The File Remotion Plays, Which Is The Working Copy When One Is Named.
    const a = m.assets[key].working ? {...m.assets[key], ...m.assets[key].working, kind: m.assets[key].kind, picture: m.assets[key].picture} : m.assets[key];
    const video = a.video, audio = a.audio;
    const container = BROWSER_CONTAINER.test(a.format);
    if (a.kind === "image") {
      if (!BROWSER_IMAGE.has(video.codec_name)) notes.push(`Asset ${key} Is A ${video.codec_name} Image. Chrome May Not Decode It, ` +
        "And Remotion Draws Images Through Chrome In Both Studio And The Render. Convert It To PNG Or JPEG.");
      continue;
    }
    if (a.kind === "video" && (!BROWSER_VIDEO.has(video.codec_name) || !container)) {
      const note = video.codec_name === "hevc" ? "Chrome Plays HEVC Only With Hardware Support" : "Chrome Does Not Play This Format";
      notes.push(`Asset ${key} Is ${video.codec_name} Video In A ${a.format} File. ${note}, So Remotion Studio May Show ` +
        "No Picture For It. The Render Decodes Frames With Remotion's Own FFmpeg And Is Not Limited To Browser Formats. " +
        "For Review In Studio, Use An H.264 MP4 Copy Or The Kit's Browser Editor And Stills.");
    }
    if (audio && a.kind === "audio" && !(BROWSER_AUDIO.has(audio.codec_name) || /^pcm_/.test(audio.codec_name || "")) || (a.kind === "audio" && !container))
      notes.push(`Asset ${key} Is ${audio.codec_name} Audio In A ${a.format} File. Chrome May Not Play It In Remotion Studio. Use WAV, MP3, Or AAC.`);
    if (audio && audio.channels > 2 && (a.kind === "audio" || m.shots.some(s => s.asset === key && soundful(s)) || m.audio.some(c => c.asset === key)))
      notes.push(`Asset ${key} Has ${audio.channels} Audio Channels. Remotion's Stereo Downmix May Differ From The FFmpeg Route.`);
    const rate = (a.picture || {}).frame_rate;
    if (a.kind === "video" && rate && Math.abs(rate - fps) > 0.01 && [...m.shots, ...m.overlays].some(row => row.asset === key))
      notes.push(`Asset ${key} Runs At ${rate} FPS On A ${fps} FPS Canvas. Each Route Picks The Nearest Source Frame, ` +
        "And The Two May Choose Neighboring Source Frames On Some Output Frames.");
  }
  m.shots.forEach((shot, i) => {
    const label = `Shot ${i + 1}`;
    if (shot.speed !== 1 && soundful(shot))
      notes.push(`${label} Plays Sound At ${shot.speed}× Speed. Remotion Keeps The Pitch With Its Own Tempo Filter When It Renders, ` +
        "And The Browser Keeps The Pitch In Remotion Studio. Both Can Sound Different From The FFmpeg Route. Listen To This Shot Before Approval.");
    if (shot.speed !== 1 && m.assets[shot.asset].kind === "video")
      notes.push(`${label} Is Retimed To ${shot.speed}×. On Some Output Frames Remotion May Show The Source Frame Next To The One The FFmpeg Route Shows.`);
    if (shot.gain > 1 && soundful(shot))
      notes.push(`${label} Has Gain ${shot.gain}. Remotion Studio Plays Media No Louder Than Its Recorded Level, So The Boost Is Heard Only In The Render.`);
    if (soundful(shot) && Math.abs((shot.end - shot.start) / shot.speed - shot.duration) > 1e-9 && (shot.end - shot.start) / shot.speed < shot.duration)
      notes.push(`${label} Is Rounded Up To A Whole Frame. The FFmpeg Route Fills The Last Fraction Of A Frame With Silence. Remotion Plays Up To ` +
        `${Math.round(500 / fps)} Milliseconds Of Source Sound Past The Out Point There.`);
  });
  m.audio.forEach((cue, i) => {
    if (cue.gain > 1) notes.push(`Audio Cue ${i + 1} Has Gain ${cue.gain}. Remotion Studio Plays Media No Louder Than Its Recorded Level, So The Boost Is Heard Only In The Render.`);
  });
  const stepped = (row, label) => {
    for (const [name, value] of [["Fade In", row.fade_in], ["Fade Out", row.fade_out]])
      if (value > 0 && value < 2 / fps) notes.push(`${label} Has A ${Math.round(value * 1000)} Millisecond ${name}. Remotion Changes Level Once Per Frame, ` +
        "So A Fade Shorter Than Two Frames Becomes A Single Step. The FFmpeg Route Fades Sample By Sample.");
  };
  m.shots.forEach((shot, i) => { if (soundful(shot)) stepped(shot, `Shot ${i + 1}`); });
  m.audio.forEach((cue, i) => stepped(cue, `Audio Cue ${i + 1}`));
  if (m.captions.length)
    notes.push(`Captions Are Drawn By Chrome In ${m.caption_style.font} From The Fonts Installed On This Computer. Line Breaks, Letter Shapes, ` +
      "And Outline Corners Can Differ Slightly From The FFmpeg Route, And A Missing Font Falls Back Without A Message.");
  return notes;
}

// The Remotion Cut: Every Time In Whole Output Frames, Every Position In Canvas Pixels.
// files Maps Each Asset Name To Its Path Under The Project's public Folder.
function plan(doc, probes, files = {}, options = {}) {
  const m = model(doc, probes, options.copies || {}), fps = m.fps, f = seconds => frameOf(seconds, fps);
  const warnings = limits(m, options);
  // An HDR Original Is Only Reviewed Here. Its Master Comes From The FFmpeg Render Of The Original.
  const hdrKeys = Object.keys(m.uses).filter(key => {
    const info = m.assets[key].picture || {}, dolby = info.dolby_vision || {};
    return Boolean(info.hdr) || dolby.profile === 5;
  });
  const reviewOnly = hdrKeys.length
    ? `This Project Is For Review Only Because ${hdrKeys.join(", ")} Is HDR Footage. ` +
      "Render The Master With The Kit's FFmpeg Render From The Original Files After The Owner Approves."
    : null;
  const file = key => files[key] ?? null;
  const shots = m.shots.map((shot, i) => {
    const a = m.assets[shot.asset], frames = f(shot.duration);
    const voiced = Boolean(a.audio && a.kind !== "image" && shot.gain && (!a.working || a.working.audio));
    return {id: `shot-${i + 1}`, asset: shot.asset, kind: a.kind, file: file(shot.asset), from: f(shot.at), frames,
      start: shot.start, end: shot.end, speed: shot.speed, trim: pictureTrim(shot, fps), toneMapped: shot.tone_map,
      ...(a.working ? {workingCopy: true} : {}), ...shotLayout(shot.geometry), filter: colorFilter(shot),
      sound: voiced ? {trim: shot.start * fps, gain: shot.gain, fadeIn: shot.fade_in, fadeOut: shot.fade_out} : null};
  });
  const overlays = m.overlays.map((row, i) => ({id: `overlay-${i + 1}`, asset: row.asset, kind: m.assets[row.asset].kind, file: file(row.asset),
    from: f(row.at), frames: f(row.end) - f(row.at), start: row.start, trim: pictureTrim(row, fps), toneMapped: row.tone_map,
    left: row.x, top: row.y, width: row.width, height: row.height}));
  const audio = m.audio.map((row, i) => ({id: `audio-${i + 1}`, asset: row.asset, file: file(row.asset), from: f(row.at), frames: f(row.end) - f(row.at),
    start: row.start, trim: row.start * fps, gain: row.gain, fadeIn: row.fade_in, fadeOut: row.fade_out}));
  const captions = m.captions.map((row, i) => ({id: `caption-${i + 1}`, from: f(row.at), frames: f(row.end) - f(row.at), text: row.text, position: row.position}));
  return {title: m.title, width: m.width, height: m.height, fps, frames: f(m.duration), captionStyle: m.caption_style,
    shots, overlays, audio, captions, warnings, ...(reviewOnly ? {reviewOnly} : {})};
}

module.exports = {CutError, pyRound, quantize, frameOf, fraction, rotation, pictureInfo, probeSummary, framing, shotLayout, overlayHeight,
  captionStyle, captionLayout, levelAt, sourceSeconds, pictureTrim, colorFilter, model, limits, plan, FONTS, FONT_EM, HDR_REFUSAL};
