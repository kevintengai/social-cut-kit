(function (root) {
  "use strict";

  const lengths = { "Paper Tap": 0.19, "Glass Point": 0.82, "Air Sweep": 0.78, "Low Bloom": 1.46, "Twin Tick": 0.39, "Orbit Rise": 1.32, "Room Air": 4 };
  const tau = Math.PI * 2;
  const sin = (hz, time) => Math.sin(tau * hz * time);
  function make(name, rate = 48000) {
    if (!(name in lengths)) throw new Error("Unknown Sound.");
    const span = lengths[name];
    const samples = new Float32Array(Math.round(span * rate));
    let seed = 84320, smooth = 0, band = 0;
    for (let n = 0; n < samples.length; n++) {
      const t = n / rate, u = t / span;
      seed = (Math.imul(1664525, seed) + 1013904223) >>> 0;
      const noise = seed / 2147483648 - 1;
      smooth += (noise - smooth) * 0.078;
      band += (smooth - band) * 0.024;
      const attack = 1 - Math.exp(-t * 1600);
      let y = 0;
      switch (name) {
        case "Paper Tap":
          y = (0.40 * sin(184, t) + 0.38 * sin(357, t) + 0.47 * noise) * Math.exp(-t * 39) * attack;
          break;
        case "Glass Point":
          y = (0.47 * sin(733, t) * Math.exp(-5.2 * t) + 0.16 * sin(1733, t) * Math.exp(-9.5 * t) + 0.12 * sin(2228, t) * Math.exp(-12 * t)) * attack;
          break;
        case "Air Sweep":
          y = (smooth - band) * 2.3 * Math.pow(Math.sin(Math.PI * u), 2.2) * (0.28 + u * 0.85);
          break;
        case "Low Bloom":
          y = (0.48 * Math.sin(tau * (46 * t + 1.5 * (1 - Math.exp(-t * 17)))) + 0.16 * sin(94, t) * Math.exp(-5 * t)) * (1 - Math.exp(-t * 65)) * Math.exp(-3.8 * t);
          break;
        case "Twin Tick": {
          const tick = (at, hz) => at < 0 ? 0 : (0.42 * sin(hz, at) + 0.16 * sin(hz * 1.48, at)) * (1 - Math.exp(-at * 1100)) * Math.exp(-at * 39);
          y = tick(t, 896) + tick(t - 0.12, 1118);
          break;
        }
        case "Orbit Rise":
          y = (Math.sin(tau * (144 * t + 108 * t * t)) * 0.34 + Math.sin(tau * (221 * t + 95 * t * t)) * 0.19 + 0.32 * band) * Math.pow(Math.sin(Math.PI * u), 1.45);
          break;
        case "Room Air":
          y = (0.20 + 0.035 * sin(0.25, t)) * sin(66, t) + 0.095 * sin(99.25, t) + 0.045 * sin(148.5, t) * (0.75 + 0.2 * sin(0.5, t)) + 0.017 * sin(330.25, t);
          break;
      }
      const tail = name === "Room Air" ? 1 : Math.min(1, (span - t) / 0.025);
      samples[n] = Math.max(-1, Math.min(1, y * tail));
    }
    return samples;
  }

  function wav(samples, rate = 48000) {
    const data = new Uint8Array(44 + samples.length * 2), view = new DataView(data.buffer);
    const tag = (at, str) => { for (let i = 0; i < str.length; i++) data[at + i] = str.charCodeAt(i); };
    tag(0, "RIFF"); view.setUint32(4, data.length - 8, true); tag(8, "WAVE"); tag(12, "fmt ");
    view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
    view.setUint32(24, rate, true); view.setUint32(28, rate * 2, true); view.setUint16(32, 2, true);
    view.setUint16(34, 16, true); tag(36, "data"); view.setUint32(40, samples.length * 2, true);
    for (let i = 0; i < samples.length; i++) view.setInt16(44 + i * 2, Math.round(samples[i] * (samples[i] < 0 ? 32768 : 32767)), true);
    return data;
  }
  const api = { lengths, make, wav };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.MotionSound = api;
})(globalThis);
