// The Only Place This Kit Starts FFmpeg Or FFprobe. They Are External Tools Found On PATH. The Kit Does Not Install Them.
// Every FFmpeg Run Built Here Either Measures Into The Null Sink Or Decodes Sound Into Memory. None Of Them Can Write A File.
"use strict";
const { spawnSync } = require("node:child_process");
const fs = require("node:fs"), path = require("node:path");

const RATE = 48000;
const labels = { ffmpeg: "FFmpeg", ffprobe: "FFprobe" }, variables = { ffmpeg: "MOTION_STUDIO_FFMPEG", ffprobe: "MOTION_STUDIO_FFPROBE" };

// Find A Working Tool: The Path Given On The Command Line, Then The Environment Variable, Then PATH.
function locate(name, given) {
  const chosen = given || process.env[variables[name]] || name;
  const out = spawnSync(chosen, ["-version"], { windowsHide: true, encoding: "utf8" });
  if (out.error || out.status !== 0) {
    const error = new Error((given || process.env[variables[name]] ? "No Working " + labels[name] + " Was Found At " + chosen + "." : labels[name] + " Was Not Found On PATH.") +
      " It Is An External Tool That This Kit Does Not Install. Install It Only With The User's Agreement, Which Needs The Network, Or Pass Its Path With --" + name +
      ". The Video Edit Skill's Setup Check Prints An Install Command For This Machine.");
    error.missingTool = name;
    throw error;
  }
  return chosen;
}
// FFprobe Usually Sits Beside FFmpeg. Look There When Only FFmpeg's Path Was Given.
function locateProbe(given, ffmpeg) {
  if (!given && !process.env[variables.ffprobe] && ffmpeg && /[\\/]/.test(ffmpeg)) {
    const beside = path.join(path.dirname(ffmpeg), path.basename(ffmpeg).replace(/ffmpeg/i, "ffprobe"));
    if (fs.existsSync(beside)) return locate("ffprobe", beside);
  }
  return locate("ffprobe", given);
}
// Refuse Any FFmpeg Argument List That Could Write A File. The Output Must Be The Null Sink, Or Raw Sound On Standard Output With Picture Left Out.
function assertSink(args) {
  const last = args[args.length - 1], inputs = args.filter(arg => arg === "-i").length;
  const measuring = args.slice(-3).join(" ") === "-f null -";
  const decoding = last === "pipe:1" && args.includes("-vn") && args[args.indexOf("-f", args.indexOf("-i")) + 1] === "f32le";
  if (inputs !== 1 || (!measuring && !decoding)) throw new Error("This Kit Runs FFmpeg Only To Measure Into The Null Sink Or To Decode Sound Into Memory.");
  return args;
}
function run(tool, args, input) {
  const out = spawnSync(tool, args, { input, windowsHide: true, maxBuffer: 2147483647 });
  if (out.error) throw new Error("The Tool Could Not Run: " + out.error.message);
  return { status: out.status, stdout: out.stdout, stderr: out.stderr.toString("utf8") };
}
const decodeArgs = file => assertSink(["-hide_banner", "-nostats", "-nostdin", "-i", file, "-vn", "-sn", "-dn", "-f", "f32le", "-acodec", "pcm_f32le", "-ac", "2", "-ar", String(RATE), "pipe:1"]);
const measureFileArgs = file => assertSink(["-hide_banner", "-nostats", "-nostdin", "-i", file, "-vn", "-sn", "-dn", "-af", "ebur128=peak=true:framelog=verbose", "-f", "null", "-"]);
const measureSamplesArgs = () => assertSink(["-hide_banner", "-nostats", "-f", "f32le", "-ar", String(RATE), "-ac", "2", "-i", "pipe:0", "-af", "ebur128=peak=true:framelog=verbose", "-f", "null", "-"]);

// Decode Any Sound File To Stereo Float Samples At 48 kHz, Interleaved Left Then Right. Nothing Is Written.
function decode(ffmpeg, file) {
  const out = run(ffmpeg, decodeArgs(file));
  if (out.status !== 0 || !out.stdout.length) throw new Error("FFmpeg Could Not Decode The Sound In " + file + ". " + out.stderr.trim().split("\n").pop());
  const samples = new Float32Array(Math.floor(out.stdout.length / 4));
  Buffer.from(samples.buffer).set(out.stdout.subarray(0, samples.length * 4));
  // FFmpeg Lowers A One-Channel Recording By Three Decibels When It Spreads It Over Two. A Player Does Not, So Put The Level Back.
  if (/Stream #\d+:\d+.*: Audio: .*\b\d+ Hz, (mono|1 channels)\b/.test(out.stderr)) for (let i = 0; i < samples.length; i++) samples[i] *= Math.SQRT2;
  return samples;
}
// Read The Summary The ebur128 Filter Prints: Integrated Loudness In LUFS, Loudness Range In LU, And True Peak In dBTP.
function parseLoudness(text) {
  const summary = text.slice(Math.max(0, text.lastIndexOf("Summary:")));
  const value = pattern => { const found = pattern.exec(summary); return found ? (/inf/i.test(found[1]) ? (found[1].startsWith("-") ? -Infinity : Infinity) : Number(found[1])) : null; };
  const out = { integrated: value(/\bI:\s+(-?inf|nan|-?[\d.]+)\s+LUFS/i), range: value(/\bLRA:\s+(-?inf|nan|-?[\d.]+)\s+LU/i), truePeak: value(/\bPeak:\s+(-?inf|nan|-?[\d.]+)\s+dBFS/i) };
  if (out.integrated === null || Number.isNaN(out.integrated)) throw new Error("FFmpeg Did Not Report A Loudness Summary. Check That This FFmpeg Build Includes The ebur128 Filter.");
  // The Filter Reports Minus Seventy When Nothing Rose Above Its Gate.
  out.silent = out.integrated <= -70;
  return out;
}
// Measure Stereo Float Samples In Memory, Or The Sound Of A File, Through The Null Sink.
function loudness(ffmpeg, source) {
  const out = typeof source === "string" ? run(ffmpeg, measureFileArgs(source)) : run(ffmpeg, measureSamplesArgs(), Buffer.from(source.buffer, source.byteOffset, source.byteLength));
  if (out.status !== 0) throw new Error("FFmpeg Could Not Measure The Loudness. " + out.stderr.trim().split("\n").pop());
  return parseLoudness(out.stderr);
}
// Describe A File's Streams With FFprobe. Reading Only.
function probe(ffprobe, file) {
  const out = run(ffprobe, ["-v", "error", "-show_format", "-show_streams", "-of", "json", file]);
  if (out.status !== 0) throw new Error("FFprobe Could Not Read " + file + ". " + out.stderr.trim().split("\n").pop());
  try { return JSON.parse(out.stdout.toString("utf8")); } catch { throw new Error("FFprobe Returned Something That Is Not JSON For " + file + "."); }
}
// The Time Of The Last Picture Frame, For Files That Do Not State Their Length. Reading Only.
function lastFrameTime(ffprobe, file) {
  const out = run(ffprobe, ["-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time", "-of", "csv=p=0", file]);
  if (out.status !== 0) return null;
  const times = out.stdout.toString("utf8").split(/\s+/).map(Number).filter(Number.isFinite);
  return times.length ? Math.max(...times) : null;
}
module.exports = { RATE, locate, locateProbe, assertSink, decodeArgs, measureFileArgs, measureSamplesArgs, decode, parseLoudness, loudness, probe, lastFrameTime };
