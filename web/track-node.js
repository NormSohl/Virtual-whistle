// MIDI-out tracker check (tests/test_pitch_tracker.py): node web/track-node.js <repo> tongued|slur <outdir>
// Offline check of the MIDI-out tracker: play the two-octave scale (page engine settings: release-only wall
// losses, 2x oversampling, 0.0006 gain, 15 ms fingers / 8 ms breath ramps), track it in 128-sample blocks,
// write the model audio (48 kHz float) and the tracker's per-block output for comparison with analysis.pitch.
const fs = require('fs');
const path = process.argv[2], outDir = process.argv[4] || '.';
const { vwMakeVariant } = require(path + '/web/whistle-model.js');
const { VwPitchTracker } = require(path + '/web/pitch-tracker.js');
const sr = 48000, factor = 2, B = 128;
const v = vwMakeVariant('release', sr * factor), w = v.w, gain = 0.0006 * v.rawGain;
const tr = new VwPitchTracker(sr);
const F = { D: 'xxxxxx', E: 'xxxxxo', 'F#': 'xxxxoo', G: 'xxxooo', A: 'xxoooo', B: 'xooooo', 'C#': 'oooooo', D2: 'oxxxxx' };
const BR = { D: 0.10, E: 0.15, 'F#': 0.17, G: 0.17, A: 0.22, B: 0.30, 'C#': 0.32, "D'": 0.42, "E'": 0.42, "F#'": 0.55, "G'": 0.60, "A'": 0.75, "B'": 0.85, "C#'": 0.90 };
const plan = [];
for (const n of ['D', 'E', 'F#', 'G', 'A', 'B', 'C#']) plan.push([n, F[n], BR[n]]);
plan.push(["D'", F.D2, BR["D'"]]);
for (const n of ['E', 'F#', 'G', 'A', 'B', 'C#']) plan.push([n + "'", F[n], BR[n + "'"]]);
const mode = process.argv[3] || 'tongued';   // tongued: breath off between notes; slur: breath held
const seg = []; let t = 0;
for (const [name, pat, b] of plan) {
  seg.push({ name, holes: [...pat].map((c) => (c === 'x' ? 0 : 1)), b, t0: t, t1: t + 0.6 });
  t += 0.6 + (mode === 'tongued' ? 0.25 : 0);
}
const total = t + 0.3, nb = Math.ceil(total * sr / B);
const audio = new Float32Array(nb * B), log = [];
const cH = [0, 0, 0, 0, 0, 0]; let cB = 0;
const fStep = 1 / (0.015 * sr * factor);
for (let k = 0; k < nb; k++) {
  const tb = k * B / sr;
  const s = seg.find((s) => tb >= s.t0 && tb < s.t1) || (mode === 'slur' ? null : null);
  const tH = s ? s.holes : (seg.find((q) => q.t0 > tb) || seg[seg.length - 1]).holes;
  const tBr = s ? s.b : 0;
  const db = tBr - cB, bs = B / (0.008 * sr) * Math.max(0.3, db > 0 ? tBr : cB);
  cB += Math.abs(db) <= bs ? db : Math.sign(db) * bs; w.setBreath(cB);
  const blk = new Float32Array(B);
  for (let i = 0; i < B; i++) {
    let acc = 0;
    for (let j = 0; j < factor; j++) {
      for (let h = 0; h < 6; h++) { const d = tH[h] - cH[h]; if (d !== 0) { cH[h] += Math.abs(d) <= fStep ? d : Math.sign(d) * fStep; w.setOpenness(h, cH[h]); } }
      acc += w.process();
    }
    blk[i] = gain * acc / factor;
  }
  audio.set(blk, k * B);
  tr.push(blk, cB);
  log.push([tb + B / sr, tr.gate ? 1 : 0, tr.f, tr.raw, tr.aper, tr.rms, s ? s.name : '-'].join(','));
}
fs.writeFileSync(outDir + '/scale_' + mode + '.f32', Buffer.from(audio.buffer));
fs.writeFileSync(outDir + '/scale_' + mode + '.csv', 't,gate,f,raw,aper,rms,seg\n' + log.join('\n') + '\n');
fs.writeFileSync(outDir + '/scale_' + mode + '.json', JSON.stringify(seg));

