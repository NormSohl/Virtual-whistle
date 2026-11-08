// Render a control CSV with the JS port (for checking against the C++ renderer).
// node web/render-node.js control.csv out.raw [geometry.json] [settings.json]   -> float32 raw, 96 kHz
// control.csv: t,o1..oN,breath (N must match the geometry's hole count).
// geometry.json: the VwWhistle geometry object (metres); default: Generation D ('-' for the default).
// settings.json: VwWhistle settings overrides (e.g. a preset); default: VW_DEFAULT_SETTINGS.
const fs = require('fs');
const { VwWhistle, vwGenerationD } = require('./whistle-model.js');
const [csv, out, geomPath, setPath] = process.argv.slice(2);
const lines = fs.readFileSync(csv, 'utf8').trim().split('\n');
const nh = lines[0].split(',').filter((c) => c.startsWith('o')).length;
const rows = lines.slice(1).map((l) => l.split(',').map(Number));
const g = geomPath && geomPath !== '-' ? JSON.parse(fs.readFileSync(geomPath, 'utf8')) : vwGenerationD();
if (g.holePos.length !== nh) { console.error(`control has ${nh} hole columns, geometry has ${g.holePos.length}`); process.exit(2); }
const w = new VwWhistle(g, setPath ? JSON.parse(fs.readFileSync(setPath, 'utf8')) : {});
const sr = 96000, n = Math.floor(rows[rows.length - 1][0] * sr), y = new Float32Array(n);
let r = 0;
// Same schedule as render/render.cpp: hole openness every sample, breath every 32 samples.
for (let i = 0; i < n; i++) {
  const t = i / sr;
  while (r + 1 < rows.length - 1 && rows[r + 1][0] <= t) r++;
  const A = rows[r], B = rows[r + 1], span = B[0] - A[0];
  const u = Math.fround(Math.min(1, Math.max(0, span > 0 ? (t - A[0]) / span : 0)));
  // float32 arithmetic like the C++ renderer, so per-sample updates cross setOpenness's 1e-4 skip
  // threshold on the same samples.
  const F = Math.fround;
  for (let h = 0; h < nh; h++) { const a = F(A[1 + h]), b = F(B[1 + h]); w.setOpenness(h, F(a + F(F(b - a) * u))); }
  if (i % 32 === 0) w.setBreath(A[1 + nh] + (B[1 + nh] - A[1 + nh]) * u);
  y[i] = w.process();
}
fs.writeFileSync(out, Buffer.from(y.buffer));
