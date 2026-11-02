// Render a control CSV with the JS port (for checking against the C++ renderer).
// node web/render-node.js control.csv out.raw [geometry.json]   -> float32 raw, 96 kHz
// control.csv: t,o1..oN,breath (N must match the geometry's hole count).
// geometry.json: the VwWhistle geometry object (metres); default: Generation D.
const fs = require('fs');
const { VwWhistle, vwGenerationD } = require('./whistle-model.js');
const [csv, out, geomPath] = process.argv.slice(2);
const lines = fs.readFileSync(csv, 'utf8').trim().split('\n');
const nh = lines[0].split(',').filter((c) => c.startsWith('o')).length;
const rows = lines.slice(1).map((l) => l.split(',').map(Number));
const g = geomPath ? JSON.parse(fs.readFileSync(geomPath, 'utf8')) : vwGenerationD();
if (g.holePos.length !== nh) { console.error(`control has ${nh} hole columns, geometry has ${g.holePos.length}`); process.exit(2); }
const w = new VwWhistle(g);
const sr = 96000, n = Math.floor(rows[rows.length - 1][0] * sr), y = new Float32Array(n);
let r = 0;
for (let i = 0; i < n; i++) {
  if (i % 32 === 0) {
    const t = i / sr;
    while (r + 1 < rows.length - 1 && rows[r + 1][0] <= t) r++;
    const A = rows[r], B = rows[r + 1], span = B[0] - A[0];
    const u = Math.min(1, Math.max(0, span > 0 ? (t - A[0]) / span : 0));
    for (let h = 0; h < nh; h++) w.setOpenness(h, A[1 + h] + (B[1 + h] - A[1 + h]) * u);
    w.setBreath(A[1 + nh] + (B[1 + nh] - A[1 + nh]) * u);
  }
  y[i] = w.process();
}
fs.writeFileSync(out, Buffer.from(y.buffer));
