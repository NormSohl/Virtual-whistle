// Render a control CSV with the JS port (for checking against the C++ renderer).
// node web/render-node.js control.csv out.raw   -> float32 raw, 96 kHz
const fs = require('fs');
const { VwWhistle, vwGenerationD } = require('./whistle-model.js');
const [csv, out] = process.argv.slice(2);
const rows = fs.readFileSync(csv, 'utf8').trim().split('\n').slice(1).map((l) => l.split(',').map(Number));
const w = new VwWhistle(vwGenerationD());
const sr = 96000, n = Math.floor(rows[rows.length - 1][0] * sr), y = new Float32Array(n);
let r = 0;
for (let i = 0; i < n; i++) {
  if (i % 32 === 0) {
    const t = i / sr;
    while (r + 1 < rows.length - 1 && rows[r + 1][0] <= t) r++;
    const A = rows[r], B = rows[r + 1], span = B[0] - A[0];
    const u = Math.min(1, Math.max(0, span > 0 ? (t - A[0]) / span : 0));
    for (let h = 0; h < 6; h++) w.setOpenness(h, A[1 + h] + (B[1 + h] - A[1 + h]) * u);
    w.setBreath(A[7] + (B[7] - A[7]) * u);
  }
  y[i] = w.process();
}
fs.writeFileSync(out, Buffer.from(y.buffer));
