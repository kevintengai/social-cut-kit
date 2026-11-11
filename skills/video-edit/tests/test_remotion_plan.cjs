// The Remotion Timing And Layout Module, Checked Without Remotion Installed.
const assert = require("node:assert/strict");
const {readFileSync} = require("node:fs");
const {join} = require("node:path");
const {test} = require("node:test");

const Cut = require("../remotion/cut-plan.cjs");

const still = (width, height) => Cut.probeSummary({format: {format_name: "png_pipe"},
  streams: [{codec_type: "video", codec_name: "png", width, height, pix_fmt: "rgb24"}]});
const clip = (extra = {}, audio = true, duration = 20) => Cut.probeSummary({format: {format_name: "mov,mp4,m4a,3gp,3g2,mj2", duration: String(duration)},
  streams: [{codec_type: "video", codec_name: "h264", width: 1920, height: 1080, pix_fmt: "yuv420p", avg_frame_rate: "30/1", ...extra},
    ...(audio ? [{codec_type: "audio", codec_name: "aac", channels: 2}] : [])]});
const wav = (duration = 10) => Cut.probeSummary({format: {format_name: "wav", duration: String(duration)},
  streams: [{codec_type: "audio", codec_name: "pcm_s16le", channels: 2}]});

function project(extra = {}) {
  return {version: 1, title: "Plan Check", canvas: {width: 1080, height: 1920, fps: 30, fit: "cover"},
    assets: {Cam: {kind: "video", path: "cam.mp4"}, Card: {kind: "image", path: "card.png"}, Tone: {kind: "audio", path: "tone.wav"}},
    shots: [{asset: "Cam", in: 1, out: 2.5}], ...extra};
}
const probes = (extra = {}) => ({Cam: clip(), Card: still(160, 100), Tone: wav(), ...extra});
const fails = (doc, pattern, sources = probes(), options) =>
  assert.throws(() => Cut.plan(doc, sources, {}, options), error => error instanceof Cut.CutError && pattern.test(error.message), String(pattern));

test("The Module Imports Nothing", () => {
  const source = readFileSync(join(__dirname, "../remotion/cut-plan.cjs"), "utf8");
  assert.doesNotMatch(source, /\brequire\s*\(|^\s*import\s/m);
});

test("Ties Round To The Even Neighbor As Python Does", () => {
  assert.deepEqual([0.5, 1.5, 2.5, 3.5, -0.5, 2.4999, 2.5001].map(Cut.pyRound), [0, 2, 2, 4, 0, 2, 3]);
});

test("Times Snap To The Nearest Output Frame With The Timeline Rule", () => {
  // Reference Frame Numbers Computed By timeline.py For A 30 FPS Canvas.
  const expected = new Map([[0.15, 5], [2.85, 86], [3.11, 93], [1.15, 35], [0.95, 29], [7.05, 212], [0.016, 0], [0.0167, 1]]);
  for (const [seconds, frame] of expected) {
    assert.equal(Cut.frameOf(seconds, 30), frame, String(seconds));
    assert.equal(Cut.quantize(seconds, 30), frame / 30, String(seconds));
  }
  assert.equal(Cut.frameOf(1 / 48, 24), 1);
  assert.equal(Cut.frameOf(1 / 48 - 1e-9, 24), 0);
});

test("Shot Framing Matches The FFmpeg Route's Crop, Scale, And Pad", () => {
  // Reference Values Printed By timeline.framing For The Same Inputs.
  const cases = [
    [[{width: 1920, height: 1080}, 1080, 1920, "cover", 1, 0, 0], [608, 1080, 656, 0], [1080, 1920], [0, 0]],
    [[{width: 1920, height: 1080}, 1080, 1920, "contain", 1, 0, 0], [1920, 1080, 0, 0], [1080, 608], [0, 656]],
    [[{width: 1920, height: 1080}, 1080, 1920, "cover", 1.5, -0.5, 0.4], [405, 720, 379, 252], [1080, 1920], [0, 0]],
    [[{width: 160, height: 100}, 360, 640, "cover", 1.2, 0.15, 0], [47, 83, 65, 8], [360, 640], [0, 0]],
    [[{width: 3840, height: 2160, side_data_list: [{rotation: -90}]}, 1080, 1920, "cover", 1, 0, 0], [2160, 3840, 0, 0], [1080, 1920], [0, 0]],
    [[{width: 1440, height: 1080, sample_aspect_ratio: "4:3"}, 1920, 1080, "contain", 1, 0, 0], [1440, 1080, 0, 0], [1920, 1080], [0, 0]],
    [[{width: 720, height: 576, sample_aspect_ratio: "16:15"}, 1080, 1920, "contain", 2.5, 1, -1], [288, 546, 432, 0], [1080, 1920], [0, 0]],
    [[{width: 1001, height: 563}, 1080, 1080, "contain", 1, 0.3, 0.3], [1001, 563, 0, 0], [1080, 608], [0, 307]],
    [[{width: 1080, height: 1920, tags: {rotate: "270"}}, 1920, 1080, "cover", 3.7, -1, 1], [519, 292, 0, 788], [1920, 1080], [0, 0]]
  ];
  for (const [args, crop, scale, pad] of cases) {
    const geometry = Cut.framing(...args);
    assert.deepEqual([geometry.crop, geometry.scale, geometry.pad], [crop, scale, pad], JSON.stringify(args));
  }
});

test("The Layout Shows Exactly The Cropped Region Inside The Visible Box", () => {
  const layout = Cut.shotLayout(Cut.framing({width: 1920, height: 1080}, 1080, 1920, "cover", 1.5, -0.5, 0.4));
  assert.deepEqual(layout.box, {left: 0, top: 0, width: 1080, height: 1920});
  const kx = 1080 / 405, ky = 1920 / 720;
  assert.deepEqual(layout.media, {left: -379 * kx, top: -252 * ky, width: 1920 * kx, height: 1080 * ky});
  // The Crop's Right And Bottom Edges Land On The Box Edges.
  assert.ok(Math.abs(layout.media.left + (379 + 405) * kx - 1080) < 1e-9);
  assert.ok(Math.abs(layout.media.top + (252 + 720) * ky - 1920) < 1e-9);
  const letterbox = Cut.shotLayout(Cut.framing({width: 1920, height: 1080}, 1080, 1920, "contain", 1, 0, 0));
  assert.deepEqual(letterbox, {box: {left: 0, top: 656, width: 1080, height: 608}, media: {left: 0, top: 0, width: 1080, height: 608}});
});

test("An Overlay Height Follows The Asset Proportions And Is Even", () => {
  assert.equal(Cut.overlayHeight({width: 160, height: 100}, 120), 76);
  assert.equal(Cut.overlayHeight({width: 1920, height: 1080}, 400), 226);
  assert.equal(Cut.overlayHeight({width: 1920, height: 1080, side_data_list: [{rotation: -90}]}, 400), 712);
});

test("Shots Carry Handles, Speed, Frames, And The Nearest-Frame Picture Trim", () => {
  const doc = project({shots: [
    {asset: "Cam", in: 1, out: 2.5},
    {asset: "Cam", in: 4, out: 6, lead: 0.2, tail: 0.1, speed: 2, gain: 0.5, fade_in: 0.2, fade_out: 0.1, zoom: 1.5, pan_x: -0.5, pan_y: 0.4,
      brightness: 1.1, contrast: 1.2, saturation: 0.6},
    {asset: "Card", in: 0, out: 1, fit: "contain"},
    {asset: "Cam", in: 7.05, out: 8, gain: 0}
  ]});
  const plan = Cut.plan(doc, probes(), {Cam: "media/01-cam.mp4", Card: "media/02-card.png"});
  assert.deepEqual(plan.shots.map(s => [s.from, s.frames]), [[0, 45], [45, 35], [80, 30], [110, 29]]);
  assert.equal(plan.frames, 139);
  const [first, second, third, fourth] = plan.shots;
  assert.equal(first.file, "media/01-cam.mp4");
  assert.deepEqual([first.start, first.end, first.speed, first.trim], [1, 2.5, 1, 30.499]);
  assert.deepEqual(first.sound, {trim: 30, gain: 1, fadeIn: 0, fadeOut: 0});
  assert.equal(first.filter, null);
  assert.ok(Math.abs(second.start - 3.8) < 1e-12 && Math.abs(second.end - 6.1) < 1e-12);
  assert.ok(Math.abs(second.trim - (114 + 0.998)) < 1e-9);
  assert.ok(Math.abs(second.sound.trim - 114) < 1e-9);
  assert.deepEqual([second.sound.gain, second.sound.fadeIn, second.sound.fadeOut], [0.5, 0.2, 0.1]);
  assert.equal(second.filter, "brightness(1.1) contrast(1.2) saturate(0.6)");
  assert.deepEqual(second.box, {left: 0, top: 0, width: 1080, height: 1920});
  assert.equal(third.kind, "image");
  assert.equal(third.sound, null);
  assert.deepEqual(third.box, {left: 0, top: 622, width: 1080, height: 676});
  assert.equal(fourth.sound, null, "A Muted Shot Has No Sound Element");
  // Output Frame n Of A Shot Samples The Source Just Under Half A Frame Late, Scaled By Speed.
  assert.ok(Math.abs(Cut.sourceSeconds(second, 3, 30) - (3.8 + 3.499 * 2 / 30)) < 1e-12);
  assert.ok(Math.abs(Cut.sourceSeconds(second, 0, 30) * 30 - second.trim) < 1e-9);
});

test("Overlays, Audio Cues, And Captions Snap To Frames And Keep Their Order", () => {
  const doc = project({shots: [{asset: "Cam", in: 0, out: 8}],
    overlays: [{asset: "Card", at: 1, end: 1.75, x: 18, y: 54, width: 120}, {asset: "Cam", at: 0.5, end: 2.02, in: 1, x: -40, width: 400}],
    audio: [{asset: "Tone", at: 3, end: 3.11, in: 0.25, gain: 0.36}, {asset: "Cam", at: 0, end: 8, fade_in: 0.5, fade_out: 1}],
    captions: [{at: 0.15, end: 2.85, text: "First Line\nSecond Line"}, {at: 3.15, end: 5.85, text: "Top", position: "top"}]});
  const plan = Cut.plan(doc, probes());
  assert.deepEqual(plan.overlays.map(o => [o.id, o.from, o.frames, o.left, o.top, o.width, o.height, o.kind]),
    [["overlay-1", 30, 23, 18, 54, 120, 76, "image"], ["overlay-2", 15, 46, -40, 0, 400, 226, "video"]]);
  assert.equal(plan.overlays[1].trim, 30.499);
  assert.deepEqual(plan.audio.map(a => [a.from, a.frames, a.trim, a.gain, a.fadeIn, a.fadeOut]), [[90, 3, 7.5, 0.36, 0, 0], [0, 240, 0, 1, 0.5, 1]]);
  assert.deepEqual(plan.captions, [{id: "caption-1", from: 5, frames: 81, text: "First Line\nSecond Line", position: "bottom"},
    {id: "caption-2", from: 95, frames: 81, text: "Top", position: "top"}]);
});

test("Sound Level Follows Gain And Straight Fades Frame By Frame", () => {
  const sound = {gain: 0.8, fadeIn: 0.5, fadeOut: 1};
  const level = frame => Cut.levelAt(sound, frame, 90, 30);
  assert.ok(Math.abs(level(0) - 0.8 * (0.5 / 30) / 0.5) < 1e-12);
  assert.ok(Math.abs(level(7) - 0.8 * 0.5) < 1e-12);
  assert.equal(level(15), 0.8);
  assert.equal(level(59), 0.8);
  assert.ok(Math.abs(level(74) - 0.8 * (1 - (74.5 / 30 - 2))) < 1e-12);
  assert.ok(level(89) > 0 && level(89) < 0.02);
  assert.equal(Cut.levelAt({gain: 1.5, fadeIn: 0, fadeOut: 0}, 10, 90, 30), 1.5);
  for (let frame = 0; frame < 89; frame++) assert.ok(level(frame) <= 0.8 && level(frame) >= 0);
});

test("Caption Style Defaults And Pixel Layout Follow The FFmpeg Route", () => {
  // A Vertical Canvas Defaults To A Size Of 6 Percent Of Its Width And Margins That Clear The Platform's Controls.
  assert.deepEqual(Cut.captionStyle({}, 720, 1280), {font: "Arial", size: 43, color: "#FFFFFF", outline: "#101010", stroke: 3, margin: 25, top_margin: 12});
  assert.deepEqual(Cut.captionStyle({}, 360, 640), {font: "Arial", size: 22, color: "#FFFFFF", outline: "#101010", stroke: 2, margin: 25, top_margin: 12});
  assert.deepEqual(Cut.captionStyle({}, 1080, 1920), {font: "Arial", size: 65, color: "#FFFFFF", outline: "#101010", stroke: 5, margin: 25, top_margin: 12});
  // A Horizontal Or Square Canvas Keeps The Earlier Defaults.
  assert.deepEqual(Cut.captionStyle({}, 1920, 1080), {font: "Arial", size: 84, color: "#FFFFFF", outline: "#101010", stroke: 6, margin: 7, top_margin: 7});
  assert.deepEqual(Cut.captionStyle({}, 1080, 1080), {font: "Arial", size: 84, color: "#FFFFFF", outline: "#101010", stroke: 6, margin: 7, top_margin: 7});
  // An Explicit Margin Applies At Both Edges, As Before, Unless The Top Margin Is Set Too.
  assert.deepEqual(Cut.captionStyle({caption_style: {size: 61, stroke: 4, margin: 7}}, 720, 1280),
    {font: "Arial", size: 61, color: "#FFFFFF", outline: "#101010", stroke: 4, margin: 7, top_margin: 7});
  assert.equal(Cut.captionStyle({caption_style: {margin: 30, top_margin: 9}}, 1080, 1920).top_margin, 9);
  const tall = Cut.captionLayout(Cut.captionStyle({}, 1080, 1920), 1080, 1920);
  assert.deepEqual([tall.edge, tall.topEdge, tall.lineHeight], [480, 230, 65]);
  assert.throws(() => Cut.captionStyle({caption_style: {top_margin: 60}}, 1080, 1920), /Caption Top Margin Must Be A Number/);
  const style = Cut.captionStyle({caption_style: {font: "Georgia", size: 90, stroke: 6, margin: 10, color: "#FFEE00"}}, 1080, 1920);
  const look = Cut.captionLayout(style, 1080, 1920);
  assert.deepEqual([look.side, look.edge, look.lineHeight, look.stroke, look.color], [59, 192, 90, 6, "#FFEE00"]);
  assert.equal(look.topEdge, 192);
  assert.ok(Math.abs(look.fontSize - 90 * 2048 / 2327) < 1e-9);
  assert.match(look.fontFamily, /^Georgia, /);
  for (const font of Cut.FONTS) assert.ok(Cut.FONT_EM[font] > 0.8 && Cut.FONT_EM[font] < 0.92, font);
  assert.throws(() => Cut.captionStyle({caption_style: {font: "Comic Sans MS"}}, 1080, 1920), /Unsupported Caption Font Value/);
  assert.throws(() => Cut.captionStyle({caption_style: {color: "white"}}, 1080, 1920), /Six-Digit Hex Color/);
});

test("Invalid Timelines Are Refused With The Timeline's Own Messages", () => {
  fails(project({version: 2}), /Set Project Version To 1\./);
  fails(project({extra: 1}), /Unknown Project Field extra\./);
  fails(project({canvas: {width: 1081}}), /Canvas Dimensions Must Be Even\./);
  fails(project({canvas: {fps: 29.97}}), /FPS Requires A Whole Number\./);
  fails(project({shots: []}), /Add At Least One Shot\./);
  fails(project({shots: [{asset: "Cam", in: 2, out: 1}]}), /Positive Source Range/);
  fails(project({shots: [{asset: "Cam", in: 0, out: 25}]}), /Selection Extends Past The End Of cam\.mp4\./);
  fails(project({shots: [{asset: "Cam", in: 0, out: 1, speed: 5}]}), /Speed Must Be A Number Between 0\.25 And 4\./);
  fails(project({shots: [{asset: "Cam", in: 0, out: 0.01}]}), /At Least One Output Frame/);
  fails(project({shots: [{asset: "Tone", in: 0, out: 1}]}), /Invalid Asset For This Track Tone\./);
  fails(project({shots: [{asset: "Cam", in: 0, out: 1, fade_in: 0.6, fade_out: 0.6}]}), /Shot Fades Must Fit Inside Its 1 Second Length\./);
  fails(project({overlays: [{asset: "Card", at: 1, end: 9}]}), /Overlay Must Fit Inside The Timeline/);
  fails(project({audio: [{asset: "Card", at: 0, end: 1}]}), /Invalid Asset For This Track Card\./);
  fails(project({captions: [{at: 0, end: 1, text: " "}]}), /Caption Text Requires Text\./);
  fails(project({captions: [{at: 0, end: 1, text: "Hi", position: "left"}]}), /Unsupported Caption Position Value left\./);
  fails(project(), /Missing Asset cam\.mp4\./, {Card: still(160, 100), Tone: wav()});
  fails(project(), /Missing video Stream In cam\.mp4\./, probes({Cam: wav()}));
  fails(project({audio: [{asset: "Cam", at: 0, end: 1}]}), /Audio Cue Requires An Audio Stream\./, probes({Cam: clip({}, false)}));
});

test("HDR Sources Are Refused By Default And Point To The FFmpeg Render", () => {
  const hlg = probes({Cam: clip({codec_name: "hevc", pix_fmt: "yuv420p10le", color_transfer: "arib-std-b67", color_primaries: "bt2020"})});
  fails(project(), /Asset Cam Is HLG HDR, Used By Shot 1\..*FFmpeg Render.*--allow-hdr/, hlg);
  const pq = probes({Cam: clip({pix_fmt: "yuv420p10le", color_transfer: "smpte2084", color_primaries: "bt2020"})});
  fails(project({overlays: [{asset: "Cam", at: 0, end: 1}]}), /Asset Cam Is PQ HDR, Used By Shot 1, Overlay 1\./, pq);
  const dolby = probes({Cam: clip({side_data_list: [{side_data_type: "DOVI configuration record", dv_profile: 5}]})});
  fails(project(), /Dolby Vision Profile 5/, dolby);
  const plan = Cut.plan(project(), hlg, {}, {allowHdr: true});
  assert.ok(plan.warnings.some(note => /Asset Cam Is HLG HDR.*Has Not Verified HDR In Remotion/.test(note)));
  // An HDR File That No Shot Or Overlay Uses For Picture Does Not Block The Project.
  const unused = project({assets: {...project().assets, Spare: {kind: "video", path: "spare.mov"}}});
  assert.doesNotThrow(() => Cut.plan(unused, {...probes(), Spare: hlg.Cam}));
});

test("Every Difference From The FFmpeg Route Is Reported As A Warning", () => {
  const has = (plan, pattern) => assert.ok(plan.warnings.some(note => pattern.test(note)), `${pattern} Not In ${JSON.stringify(plan.warnings)}`);
  const plain = Cut.plan(project(), probes());
  assert.deepEqual(plain.warnings, []);
  const busy = Cut.plan(project({shots: [{asset: "Cam", in: 0, out: 2.04, speed: 2, gain: 1.5, fade_in: 0.005}],
    audio: [{asset: "Tone", at: 0, end: 1, gain: 2, fade_out: 0.01}], captions: [{at: 0, end: 1, text: "Words"}]}), probes());
  has(busy, /Shot 1 Plays Sound At 2× Speed\. Remotion Keeps The Pitch With Its Own Tempo Filter/);
  has(busy, /Shot 1 Is Retimed To 2×/);
  has(busy, /Shot 1 Has Gain 1\.5\./);
  has(busy, /Audio Cue 1 Has Gain 2\./);
  has(busy, /Shot 1 Has A 5 Millisecond Fade In\..*Single Step/);
  has(busy, /Audio Cue 1 Has A 10 Millisecond Fade Out\./);
  has(busy, /Shot 1 Is Rounded Up To A Whole Frame\..*17 Milliseconds/);
  has(busy, /Captions Are Drawn By Chrome In Arial/);
  const odd = Cut.plan(project({audio: [{asset: "Tone", at: 0, end: 1}]}), probes({
    Cam: Cut.probeSummary({format: {format_name: "mov,mp4,m4a,3gp,3g2,mj2", duration: "20"}, streams: [
      {codec_type: "video", codec_name: "prores", width: 1920, height: 1080, avg_frame_rate: "24000/1001", side_data_list: [{rotation: -90}]},
      {codec_type: "audio", codec_name: "pcm_s24le", channels: 6}]}),
    Tone: Cut.probeSummary({format: {format_name: "aiff", duration: "10"}, streams: [{codec_type: "audio", codec_name: "pcm_s16be", channels: 2}]})}));
  has(odd, /Asset Cam Is prores Video.*Chrome Does Not Play This Format/);
  has(odd, /Asset Cam Has A 90 Degree Display Rotation\..*Has Not Verified Rotated Clips/);
  has(odd, /Asset Cam Has 6 Audio Channels/);
  has(odd, /Asset Cam Runs At 23\.976 FPS On A 30 FPS Canvas/);
  has(odd, /Asset Tone Is pcm_s16be Audio In A aiff File/);
  const heic = Cut.plan(project({shots: [{asset: "Card", in: 0, out: 1}]}), probes({Card: Cut.probeSummary({format: {format_name: "tiff_pipe"},
    streams: [{codec_type: "video", codec_name: "tiff", width: 100, height: 100}]})}));
  has(heic, /Asset Card Is A tiff Image/);
  for (const note of [...busy.warnings, ...odd.warnings, ...heic.warnings]) assert.match(note, /\.$/);
});

test("Probe Summaries Read Rotation, Depth, And HDR Signalling", () => {
  const phone = Cut.probeSummary({format: {format_name: "mov,mp4,m4a,3gp,3g2,mj2", duration: "3.5"}, streams: [
    {codec_type: "video", codec_name: "mjpeg", disposition: {attached_pic: 1}, width: 100, height: 100},
    {codec_type: "video", codec_name: "hevc", width: 3840, height: 2160, pix_fmt: "yuv420p10le", color_transfer: "arib-std-b67",
      color_primaries: "bt2020", avg_frame_rate: "30000/1001", side_data_list: [{side_data_type: "Display Matrix", rotation: -90}]},
    {codec_type: "audio", codec_name: "aac", channels: 2}]});
  assert.equal(phone.duration, 3.5);
  assert.equal(phone.video.codec_name, "hevc");
  assert.deepEqual([phone.picture.rotation, phone.picture.hdr, phone.picture.bit_depth, phone.picture.frame_rate], [90, "hlg", 10, 29.97]);
  assert.deepEqual(phone.picture.displayed_size, [2160, 3840]);
  assert.equal(Cut.rotation({tags: {rotate: "270"}}), 270);
  assert.equal(Cut.rotation({side_data_list: [{rotation: 90}]}), 270);
  assert.equal(Cut.probeSummary({format: {duration: "N/A"}, streams: []}).duration, null);
});

test("A Working Copy Lets An HDR Source Through And Says Where Picture Color Comes From", () => {
  const phone = clip({codec_name: "hevc", pix_fmt: "yuv420p10le", color_transfer: "arib-std-b67", color_primaries: "bt2020", width: 3840, height: 2160,
    avg_frame_rate: "60000/1001", nb_frames: "1199", side_data_list: [{side_data_type: "Display Matrix", rotation: -90}]});
  const twin = (extra = {}, audio = true, duration = 20) => clip({width: 1080, height: 1920, avg_frame_rate: "60000/1001", nb_frames: "1199", ...extra}, audio, duration);
  const doc = project({assets: {...project().assets, Cam: {kind: "video", path: "cam.mov", working_copy: "cam-working.mp4"}}});
  const sources = probes({Cam: phone}), files = {Cam: "media/01-cam-working.mp4"};
  fails(project(), /Asset Cam Is HLG HDR, Used By Shot 1\..*Ask The Owner Once For A Working Copy/, sources);
  fails(doc, /Missing Working Copy cam-working\.mp4\./, sources);
  const plan = Cut.plan(doc, sources, files, {copies: {Cam: twin()}});
  const notes = plan.warnings.join(" ");
  assert.match(notes, /Asset Cam, Used By Shot 1, Plays From Its Working Copy In Remotion At 1080 By 1920\. The Original Is HLG HDR\. Picture Color In Remotion Comes From The Working Copy/);
  assert.match(notes, /Render The Master With FFmpeg From The Original\./);
  // The Gated Remotion Render Reads This Field And Refuses An HDR Project.
  assert.match(plan.reviewOnly, /Review Only Because Cam Is HDR Footage\..*FFmpeg Render From The Original Files/);
  assert.equal(Cut.plan(project(), probes(), {}).reviewOnly, undefined);
  assert.doesNotMatch(notes, /hevc Video|Display Rotation|Has Not Verified HDR|Fresh Working Copy|Shapes Differ/);
  assert.match(notes, /Asset Cam Runs At 59\.9401 FPS On A 30 FPS Canvas/);
  // Layout Still Comes From The Original's Displayed Size. The File Played Is The Working Copy.
  const shot = plan.shots[0];
  assert.deepEqual([shot.file, shot.workingCopy], ["media/01-cam-working.mp4", true]);
  assert.deepEqual(shot.box, {left: 0, top: 0, width: 1080, height: 1920});
  assert.deepEqual(shot.media, {left: 0, top: 0, width: 1080, height: 1920});
  assert.equal(shot.sound.gain, 1);
  assert.equal(Cut.plan(project(), probes()).shots[0].workingCopy, undefined);
  const has = (copy, pattern, extra = doc) => {
    const made = Cut.plan(extra, sources, files, {copies: {Cam: copy}});
    assert.ok(made.warnings.some(note => pattern.test(note)), `${pattern} Not In ${JSON.stringify(made.warnings)}`);
    return made;
  };
  has(twin({}, true, 19), /Working Copy Lasts 19\.000 Seconds And Its Original Lasts 20\.000 Seconds\./);
  has(twin({nb_frames: "1100"}), /Working Copy Has 1100 Frames And Its Original Has 1199\./);
  has(twin({width: 1920, height: 1080}), /Working Copy Is 1920 By 1080 And Its Original Displays At 2160 By 3840\. The Shapes Differ/);
  has(twin({codec_name: "hevc"}), /Asset Cam Is hevc Video/);
  const silent = has(twin({}, false), /Working Copy Has No Sound, So Its Shots Are Silent In Remotion/);
  assert.equal(silent.shots[0].sound, null);
  has(twin(), /Is Used Where tone_map Is false, But Its Working Copy Is Already Converted/, {...doc, canvas: {...doc.canvas, tone_map: false}});
  // A Working Copy That Is Itself HDR Is Refused Like Any HDR Source.
  fails(doc, /Asset Cam Is HLG HDR/, sources, {copies: {Cam: twin({pix_fmt: "yuv420p10le", color_transfer: "arib-std-b67", color_primaries: "bt2020"})}});
  const plain = project({assets: {...project().assets, Cam: {kind: "video", path: "cam.mp4", working_copy: "cam-small.mp4"}}});
  const easy = Cut.plan(plain, probes(), {}, {copies: {Cam: clip({width: 960, height: 540})}});
  assert.ok(easy.warnings.some(note => /Plays From Its Working Copy In Remotion At 960 By 540\. A Remotion Render Would Be Made From That Copy/.test(note)));
  assert.ok(!easy.warnings.some(note => /Picture Color/.test(note)));
  fails(project({assets: {...project().assets, Card: {kind: "image", path: "card.png", working_copy: "card.mp4"}}}), /Only A Video Asset Can Name A Working Copy\./);
  fails(project({assets: {...project().assets, Cam: {kind: "video", path: "cam.mp4", working_copy: " "}}}), /Working Copy Path Requires Text\./);
  fails(plain, /Missing Video Stream In cam-small\.mp4\./, probes(), {copies: {Cam: wav()}});
  for (const note of [...plan.warnings, ...easy.warnings]) assert.match(note, /\.$/);
});
