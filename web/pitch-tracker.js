// Pitch and gate tracker for MIDI out: listens to the model's own audio and reports what it is sounding.
// Not part of the acoustic model (dsp/whistle.hpp has no counterpart); it is control-layer code for the
// play page, like the breath mapping. Runs in the AudioWorklet (or the ScriptProcessor fallback) on the
// model output at the device rate, before the mute and the soft limiter.
//
// Pitch: YIN (de Cheveigne and Kawahara 2002) on a short window, once per push() (one audio block, normally
// 128 samples = 2.7 ms at 48 kHz). Window 5.3 ms holds 3 periods of the lowest note the model plays.
// Gate: on when the output is loud enough and clearly periodic; off when it falls below a lower level
// (hysteresis). While the gate is on but a frame is not periodic (fingering change, octave break) the last
// good pitch is held, so a slur stays one note instead of retriggering. The gate also closes as soon as the
// breath reaching the model falls below stopBreath (a tongue stop): the model's own tail rings 50-85 ms on
// the low notes (measured 2026-11-19), which would make every note-off late on a synth.
class VwPitchTracker {
  constructor(sampleRate, opt = {}) {
    const o = Object.assign({ fmin: 450, fmax: 3200, window: 0.0053, threshold: 0.15,
      onDb: -42, offDb: -50, onFrames: 2, stopBreath: 0.02 }, opt);
    this.sr = sampleRate;
    this.tauMin = Math.max(2, Math.floor(sampleRate / o.fmax));
    this.tauMax = Math.ceil(sampleRate / o.fmin) + 1;
    this.W = Math.round(o.window * sampleRate);
    this.N = this.W + this.tauMax + 1;
    this.x = new Float32Array(this.N);
    this.d = new Float32Array(this.tauMax + 2);
    this.th = o.threshold;
    this.onLevel = Math.pow(10, o.onDb / 20);
    this.offLevel = Math.pow(10, o.offDb / 20);
    this.onFrames = o.onFrames;
    this.stopBreath = o.stopBreath;
    this.breath = 1;
    this.count = 0;
    this.f = 0;          // last good pitch, Hz (held while the gate is on)
    this.raw = 0;        // this frame's pitch, Hz, 0 when not periodic
    this.aper = 1;       // this frame's aperiodicity (CMND at the chosen dip), 0 = perfectly periodic
    this.rms = 0;
    this.gate = false;
    this.hist = [0, 0, 0];   // last three periodic estimates, for a median
  }

  // Feed one block of audio and the breath (fraction of 1500 Pa) the model used for it; analyses the
  // latest window and updates f / gate.
  push(block, breath = 1) {
    this.breath = breath;
    const n = block.length, N = this.N, x = this.x;
    if (n >= N) x.set(block.subarray(n - N));
    else { x.copyWithin(0, n); x.set(block, N - n); }
    this.analyse();
    return this;
  }

  analyse() {
    const x = this.x, W = this.W, d = this.d, tMax = this.tauMax;
    // Newest W samples are the reference; lags look back into older samples.
    const ref = this.N - W;
    let e = 0;
    for (let j = 0; j < W; j++) { const v = x[ref + j]; e += v * v; }
    this.rms = Math.sqrt(e / W);
    if (this.rms < this.offLevel * 0.5) { this.raw = 0; this.aper = 1; this.stepGate(false); return; }
    let run = 0;
    d[0] = 1;
    for (let t = 1; t <= tMax; t++) {
      let s = 0;
      const o = ref - t;
      for (let j = 0; j < W; j++) { const v = x[ref + j] - x[o + j]; s += v * v; }
      run += s;
      d[t] = run > 0 ? s * t / run : 1;
    }
    let tau = -1;
    for (let t = this.tauMin; t < tMax; t++) {
      if (d[t] < this.th) { while (t + 1 < tMax && d[t + 1] < d[t]) t++; tau = t; break; }
    }
    if (tau < 0) {
      let best = this.tauMin;
      for (let t = this.tauMin; t < tMax; t++) if (d[t] < d[best]) best = t;
      this.aper = d[best];
      if (this.aper > 0.3) { this.raw = 0; this.stepGate(false); return; }
      tau = best;
    } else this.aper = d[tau];
    const a = d[tau - 1], b = d[tau], c = d[tau + 1], den = a - 2 * b + c;
    const shift = den !== 0 ? Math.max(-1, Math.min(1, 0.5 * (a - c) / den)) : 0;
    this.raw = this.sr / (tau + shift);
    this.stepGate(this.aper < this.th);
  }

  stepGate(periodic) {
    if (periodic) {
      const h = this.hist; h[0] = h[1]; h[1] = h[2]; h[2] = this.raw;
      const m = h[0] && h[1] ? [...h].sort((p, q) => p - q)[1] : this.raw;
      if (this.gate) this.f = m;
    }
    const blowing = this.breath >= this.stopBreath;
    if (!this.gate) {
      this.count = periodic && blowing && this.rms > this.onLevel ? this.count + 1 : 0;
      if (this.count >= this.onFrames) { this.gate = true; this.f = this.raw; }
    } else if (this.rms < this.offLevel || !blowing) {
      this.gate = false; this.count = 0; this.hist.fill(0);
    }
  }
}

if (typeof module !== 'undefined') module.exports = { VwPitchTracker };
