// JavaScript port of dsp/whistle.hpp (physical flue jet, model 2, with radiation).
// Kept line-for-line close to the C++ so the two can be checked against each
// other (tests/test_js_port.py renders the same control script with both).
// Runs in Node (verification) and inside an AudioWorklet (web/play.html).

class VwDelay {
  constructor(n = 4096) { this.n = n; this.mask = n - 1; this.buf = new Float64Array(n); this.w = 0; }
  write(x) { this.buf[this.w] = x; this.w = (this.w + 1) & this.mask; }
  tap(d) { return this.buf[(this.w - d) & this.mask]; }
  read(d) {
    if (d < 2) d = 2;
    if (d > this.n - 3) d = this.n - 3;
    const di = Math.floor(d), D = d - di + 1;
    const h0 = -(D - 1) * (D - 2) * (D - 3) / 6, h1 = D * (D - 2) * (D - 3) / 2;
    const h2 = -D * (D - 1) * (D - 3) / 2, h3 = D * (D - 1) * (D - 2) / 6;
    return h0 * this.tap(di - 1) + h1 * this.tap(di) + h2 * this.tap(di + 1) + h3 * this.tap(di + 2);
  }
}

class VwBiquad {
  constructor() { this.b0 = 1; this.b1 = 0; this.b2 = 0; this.a1 = 0; this.a2 = 0; this.s1 = 0; this.s2 = 0; }
  setAnalog(b0, b1, b2, a0, a1, a2, fs) {
    const K = 2 * fs, K2 = K * K;
    if (b2 === 0 && a2 === 0) {
      const A0 = a0 + a1 * K;
      this.b0 = (b0 + b1 * K) / A0; this.b1 = (b0 - b1 * K) / A0; this.b2 = 0;
      this.a1 = (a0 - a1 * K) / A0; this.a2 = 0;
      return;
    }
    const B0 = b0 + b1 * K + b2 * K2, B1 = 2 * b0 - 2 * b2 * K2, B2 = b0 - b1 * K + b2 * K2;
    const A0 = a0 + a1 * K + a2 * K2, A1 = 2 * a0 - 2 * a2 * K2, A2 = a0 - a1 * K + a2 * K2;
    this.b0 = B0 / A0; this.b1 = B1 / A0; this.b2 = B2 / A0; this.a1 = A1 / A0; this.a2 = A2 / A0;
  }
  process(x) {
    const y = this.b0 * x + this.s1;
    this.s1 = this.b1 * x - this.a1 * y + this.s2;
    this.s2 = this.b2 * x - this.a2 * y;
    return y;
  }
}

// First-order filter with unity gain at DC, for distributed wall losses: y = k (x + b x1) - a y1.
class VwOnePole {
  constructor() { this.k = 1; this.b = 0; this.a = 0; this.x1 = 0; this.y1 = 0; }
  process(x) { const y = this.k * (x + this.b * this.x1) - this.a * this.y1; this.x1 = x; this.y1 = y; return y; }
}

// Fit k (1 + b z^-1) / (1 + a z^-1), k = (1 + a) / (1 + b), to the wall-loss magnitude exp(-alpha(f) len)
// with alpha = 3e-5 sqrt(f) / radius (Np/m; Fletcher & Rossing), least squares on log magnitude, 100 Hz - 8 kHz.
function vwFitWallLoss(len, radius, scale, fs) {
  const fr = []; for (let f = 100; f <= 8000; f *= 1.15) fr.push(f);
  const target = fr.map((f) => -scale * 3e-5 * Math.sqrt(f) / radius * len);
  const err = ([a, b]) => {
    if (Math.abs(a) >= 0.999 || Math.abs(b) >= 0.999) return 1e9;
    const k = (1 + a) / (1 + b); let e = 0;
    for (let i = 0; i < fr.length; i++) {
      const w = 2 * Math.PI * fr[i] / fs, c = Math.cos(w);
      const m2 = k * k * (1 + b * b + 2 * b * c) / (1 + a * a + 2 * a * c);
      const d = 0.5 * Math.log(m2) - target[i]; e += d * d;
    }
    return e;
  };
  // Nelder-Mead from a gentle high-shelf start.
  let pts = [[-0.5, -0.49], [-0.6, -0.59], [-0.5, -0.48]].map((x) => [x, err(x)]);
  for (let it = 0; it < 600; it++) {
    pts.sort((u, v) => u[1] - v[1]);
    const [best, mid, worst] = pts;
    const c = [(best[0][0] + mid[0][0]) / 2, (best[0][1] + mid[0][1]) / 2];
    const at = (t) => [c[0] + t * (worst[0][0] - c[0]), c[1] + t * (worst[0][1] - c[1])];
    const r = at(-1), er = err(r);
    if (er < best[1]) { const e2 = at(-2), ee = err(e2); pts[2] = ee < er ? [e2, ee] : [r, er]; }
    else if (er < mid[1]) pts[2] = [r, er];
    else {
      const cc = at(0.5), ec = err(cc);
      if (ec < worst[1]) pts[2] = [cc, ec];
      else pts = pts.map(([x], i) => { if (i === 0) return pts[0]; const y = [(x[0] + best[0][0]) / 2, (x[1] + best[0][1]) / 2]; return [y, err(y)]; });
    }
  }
  pts.sort((u, v) => u[1] - v[1]);
  const [a, b] = pts[0][0];
  return { k: (1 + a) / (1 + b), a, b, rms: Math.sqrt(pts[0][1] / fr.length) };
}

class VwDc {
  constructor() { this.x1 = 0; this.y1 = 0; }
  process(x) { const y = x - this.x1 + 0.995 * this.y1; this.x1 = x; this.y1 = y; return y; }
}

const VW_DEFAULT_SETTINGS = {
  sampleRate: 96000, tempC: 30, dispersion: 0.991, footLoss: 1.0, radiation: true,
  jetRatio: 1.0, jetReflection: 1.0, jetGain: -100, noiseGain: 0.002, jetOffset: 0.1,
  jetStrouhal: 0.2, jetLpOrder: 2, maxPressurePa: 1500, jetDelayRise: 0.003,
  wallLoss: 0,   // viscothermal wall losses along the bore: 0 off (Generation D as calibrated), 1 physical strength
  wallReleaseOnly: false,   // experiment: apply wall losses only while breath is ~0 (note tails), not while playing
};

const VW_MAX_HOLES = 9;
// Closed-hole leak, rad/s: where the hole filter's slow pole stops as the hole closes (time constant ~1 s),
// stable in float32 and far below audio frequencies; a matching zero cancels it when fully closed.
const VW_HOLE_LEAK = 1.0;

class VwWhistle {
  // g: {boreRadius, length, holePos[n], holeRadius[n], chimney[n], windowLength, windowWidth, windowWall, windowScale} (metres)
  // n = holePos.length, up to 9 (VW_MAX_HOLES), holes in bore order from the window.
  constructor(g, s = {}) {
    this.g = g;
    this.s = Object.assign({}, VW_DEFAULT_SETTINGS, s);
    const S = this.s;
    this.c = 331.3 * Math.sqrt((S.tempC + 273.15) / 273.15) * S.dispersion;
    this.rho = 1.2041 * 293.15 / (S.tempC + 273.15);
    this.nh = Math.min(VW_MAX_HOLES, g.holePos.length);
    const x = [0, ...g.holePos.slice(0, this.nh), g.length];
    this.segDelay = []; this.right = []; this.left = [];
    for (let k = 0; k < this.nh + 1; k++) {
      this.segDelay.push((x[k + 1] - x[k]) / this.c * S.sampleRate);
      this.right.push(new VwDelay()); this.left.push(new VwDelay());
    }
    this.jetDelay = new VwDelay();
    this.holeFilt = Array.from({ length: this.nh }, () => new VwBiquad());
    this.open = new Float64Array(this.nh);
    this.windowFilt = new VwBiquad(); this.footFilt = new VwBiquad();
    this.dc = new VwDc(); this.vWinDc = new VwDc();
    this.leakDc = 0;
    this.breath = 0; this.lastWin = 0; this.jetLp = 0; this.jetLp2 = 0; this.jetLpCoef = 0;
    this.lastTopOut = 0; this.lastSplit = 0; this.lastBreathForLp = -1; this.jdSmooth = 2000;
    this.noise = 22222 >>> 0;
    this.rOut = new Float64Array(this.nh + 1); this.lOut = new Float64Array(this.nh + 1);
    this.segLen = []; for (let k = 0; k < this.nh + 1; k++) this.segLen.push(x[k + 1] - x[k]);
    this.wallR = Array.from({ length: this.nh + 1 }, () => new VwOnePole());
    this.wallL = Array.from({ length: this.nh + 1 }, () => new VwOnePole());
    this.setWallLoss(S.wallLoss);
    this.designWindow(); this.designFoot();
    for (let i = 0; i < this.nh; i++) this.setOpenness(i, 0, true);
  }

  setOpenness(i, o, force = false) {
    if (i < 0 || i >= this.nh) return;
    o = Math.min(1, Math.max(0, o));
    if (!force && Math.abs(o - this.open[i]) < 1e-4) return;
    this.open[i] = o;
    this.designHole(i);
  }

  setBreath(b) { this.breath = b < 0 ? 0 : b; }

  // Wall-loss strength: 0 off, 1 physical (alpha = 3e-5 sqrt(f) / radius). Can change while playing.
  setWallLoss(scale, releaseOnly = this.s.wallReleaseOnly) {
    this.s.wallReleaseOnly = !!releaseOnly;
    if (this.wallMix === undefined) this.wallMix = 0;
    this.wallScale = scale > 0 ? scale : 0;
    this.wallFit = [];
    if (!this.wallScale) return;
    for (let k = 0; k < this.nh + 1; k++) {
      const f = vwFitWallLoss(this.segLen[k], this.g.boreRadius, this.wallScale, this.s.sampleRate);
      for (const flt of [this.wallR[k], this.wallL[k]]) { flt.k = f.k; flt.a = f.a; flt.b = f.b; }
      this.wallFit.push(f);
    }
  }

  white() {
    let n = this.noise;
    n ^= n << 13; n >>>= 0;
    n ^= n >>> 17;
    n ^= n << 5; n >>>= 0;
    this.noise = n;
    return n * (2 / 4294967295) - 1;
  }

  process() {
    const S = this.s, g = this.g, fs = S.sampleRate;
    for (let k = 0; k < this.nh + 1; k++) {
      this.rOut[k] = this.right[k].read(this.segDelay[k]);
      this.lOut[k] = this.left[k].read(this.segDelay[k]);
    }
    if (this.wallScale) {
      // Release-only mode crossfades the losses in over ~10 ms once breath is ~0, and out as soon as it returns.
      let m = 1;
      if (S.wallReleaseOnly) {
        const target = this.breath < 0.01 ? 1 : 0, step = 1 / (0.01 * S.sampleRate);
        this.wallMix += Math.max(-step, Math.min(step, target - this.wallMix));
        m = this.wallMix;
      }
      for (let k = 0; k < this.nh + 1; k++) {
        const r = this.wallR[k].process(this.rOut[k]), l = this.wallL[k].process(this.lOut[k]);
        this.rOut[k] += m * (r - this.rOut[k]);
        this.lOut[k] += m * (l - this.lOut[k]);
      }
    }
    const aTop = this.lOut[0];
    const pressurePa = this.breath * S.maxPressurePa;
    const ujet = Math.sqrt(2 * pressurePa / this.rho);
    const convect = 0.4 * (ujet > 1e-3 ? ujet : 1e-3);
    let jd = S.jetRatio * (g.windowLength / convect) * fs;
    jd = jd < 2 ? 2 : (jd > 2000 ? 2000 : jd);
    if (jd > this.jdSmooth + S.jetDelayRise) jd = this.jdSmooth + S.jetDelayRise;   // see C++
    this.jdSmooth = jd;

    const u = ujet > 0.5 ? ujet : 0.5;
    const vWin = this.vWinDc.process(this.lastTopOut - aTop);
    this.jetDelay.write(S.jetReflection * vWin / u + S.noiseGain * this.white());
    const F = Math.tanh(this.jetDelay.read(jd) + S.jetOffset);
    let jet = S.jetGain * ujet * (F - this.lastSplit);
    this.lastSplit = F;

    if (S.jetStrouhal > 0 && this.breath !== this.lastBreathForLp) {
      const fc = S.jetStrouhal * u / g.windowLength;
      this.jetLpCoef = 1 - Math.exp(-2 * Math.PI * Math.min(fc, 0.45 * fs) / fs);
      this.lastBreathForLp = this.breath;
    }
    this.jetLp += this.jetLpCoef * (jet - this.jetLp);
    this.jetLp2 += this.jetLpCoef * (this.jetLp - this.jetLp2);
    jet = S.jetLpOrder >= 2 ? this.jetLp2 : this.jetLp;

    let w = this.windowFilt.process(aTop);
    this.leakDc += 0.0002 * (w - this.leakDc);
    w -= 0.0002 * this.leakDc;
    const pTopOut = w + jet;
    this.right[0].write(pTopOut);
    this.lastTopOut = pTopOut;

    for (let i = 0; i < this.nh; i++) {
      const a = this.rOut[i], b = this.lOut[i + 1];
      const pJ = this.holeFilt[i].process(a + b);
      this.left[i].write(pJ - a);
      this.right[i + 1].write(pJ - b);
    }
    this.left[this.nh].write(S.footLoss * this.footFilt.process(this.rOut[this.nh]));

    const pWin = aTop + pTopOut;
    const out = this.dc.process(pWin - this.lastWin);
    this.lastWin = pWin;
    return out;
  }

  designHole(i) {
    const o = this.open[i], g = this.g, c = this.c, fs = this.s.sampleRate;
    const a = g.boreRadius, b = g.holeRadius[i], t = g.chimney[i];
    const Sb = Math.PI * a * a, Sh = Math.PI * b * b;
    const ti = (br) => { const d = br / a; return br * (0.82 - 0.193 * d - 1.09 * d * d + 1.27 * d ** 3 - 0.71 * d ** 4); };
    const tauC = (Sh / Sb) * (t + ti(b)) / c;
    // One filter form from open to fully closed (see C++ designHole): below the leak level the slow pole
    // stops at s = -VW_HOLE_LEAK and a zero moves from s = 0 to meet it, so a closed hole is the old
    // closed response (pole and zero cancel) and nothing switches.
    const oo = o <= 1e-4 ? 0 : o;
    const bo = b * Math.sqrt(oo), So = Math.PI * bo * bo;
    const A = So / Sb, tauI = (t + ti(bo)) / c, tauR = 0.61 * bo / c;
    const t1 = tauI + tauR, t2 = tauI * tauR;
    const leak = 2 * t1 * VW_HOLE_LEAK;
    const a0 = Math.max(A, leak), b0 = Math.max(0, leak - A);
    this.holeFilt[i].setAnalog(b0, 2 * t1, 2 * t2, a0, 2 * t1 + A * tauR, 2 * t2 + (1 - oo) * tauC * t1, fs);
  }

  designWindow() {
    const g = this.g, c = this.c, fs = this.s.sampleRate;
    const Sb = Math.PI * g.boreRadius ** 2, Sw = g.windowLength * g.windowWidth;
    const rw = Math.sqrt(Sw / Math.PI);
    const le = g.windowScale * (g.windowWall + 1.7 * rw);
    const B = Sb / Sw, tauWr = 0.61 * rw / c, tauWi = le / c - tauWr;
    const w1 = tauWi + tauWr, w2 = tauWi * tauWr;
    this.windowFilt.setAnalog(-1, B * w1 - tauWr, B * w2, 1, B * w1 + tauWr, B * w2, fs);
  }

  designFoot() {
    const a = this.g.boreRadius, c = this.c;
    const tl = a / c, tauA = 0.1133 * a / c;
    this.footFilt.setAnalog(-1, tauA, 0, 1, tauA + tl, tauA * tl, this.s.sampleRate);
  }
}

// Norm's Generation D, from the calibrated impedance model (render/synth.py generation_d_config).
function vwGenerationD() {
  const top = 263.4, edge = [144.65, 123.6, 100.65, 79.5, 60.15, 35.0], dia = [4.45, 5.8, 5.1, 4.75, 6.0, 6.0];
  return {
    boreRadius: 11.8 / 2 / 1000, length: top / 1000,
    holePos: edge.map((e, i) => (top - (e + dia[i] / 2)) / 1000),
    holeRadius: dia.map((d) => d / 2 / 1000),
    chimney: dia.map(() => 0.4 / 1000),
    windowLength: 5.0 / 1000, windowWidth: 7.7 / 1000, windowWall: 2.0 / 1000, windowScale: 0.92,
  };
}

// Presets. generationD: as calibrated 2026-11-01 (VW_DEFAULT_SETTINGS). generationDWall: wall losses with the
// jet and tuning refitted (tune/fit_wall.py run 6, 2026-11-07) against the same scale test plus Norm's breath
// sweeps, release rate, note balance and tongued starts; see docs/results/2026-11-07-wall-loss-refit.md.
// rawGain: output scaling that matches its loudness to Generation D's (raw output ~38 dB lower).
const VW_PRESETS = {
  generationD: { settings: {}, rawGain: 1 },
  generationDWall: { settings: {
    dispersion: 0.996712,
    jetRatio: 0.838098,
    jetGain: -12.5645,
    jetOffset: 0.209474,
    jetStrouhal: 0.07977,
    wallLoss: 0.833295
  }, rawGain: 83 },
};

// Build a whistle for a page mode: 'off' Generation D, 'release' Generation D with wall losses only in
// note tails, 'retuned' the generationDWall preset.
function vwMakeVariant(mode, sampleRate) {
  const p = mode === 'retuned' ? VW_PRESETS.generationDWall : VW_PRESETS.generationD;
  const w = new VwWhistle(vwGenerationD(), Object.assign({ sampleRate }, p.settings));
  if (mode === 'release') w.setWallLoss(1, true);
  return { w, rawGain: p.rawGain };
}

if (typeof module !== 'undefined') module.exports = { VwWhistle, vwGenerationD, VW_DEFAULT_SETTINGS, VW_MAX_HOLES, VW_HOLE_LEAK, vwFitWallLoss, VW_PRESETS, vwMakeVariant };
