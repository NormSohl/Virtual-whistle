// WARBL sensor streaming protocol v3 (official WARBL2 firmware 4.8+), host side.
// Spec: github.com/amowry/WARBL2/blob/main/WARBL_sensor_stream_protocol_v3.md
// Pure functions, no DOM: the play page inlines this file, tests load it in node.
// Messages: F0 00 03 0F 03 <type> <payload packed MSB-first into 7-bit bytes> F7.
const WarblStream = (() => {
  const HEADER = [0xF0, 0x00, 0x03, 0x0F, 0x03];
  const FRAME = 0x01, BATCH = 0x02, INFO = 0x10, CONFIG = 0x20, REQUEST_INFO = 0x21;
  const FRAME_LEN = 39, INFO_LEN = 62;
  const SEQ_MOD = 16384, TS_MOD = 2097152, TS_HZ = 32768;
  const PA_PER_COUNT = 1 / 2.184;            // pressure: both sensors, nominal 2.184 counts per Pa

  // Commands (host -> WARBL). Bit 0 streams, bit 1 suppresses notes/CCs, bit 2 legacy keepalive.
  const config = (on, suppress) => [...HEADER, CONFIG, on ? (0x05 | (suppress ? 0x02 : 0)) : 0x00, 0xF7];
  const requestInfo = () => [...HEADER, REQUEST_INFO, 0xF7];

  function reader(d) {                       // d: whole message incl. F0 ... F7
    let pos = 0; const n = (d.length - 7) * 7;
    const get = (bits) => {
      if (pos + bits > n) throw new Error('truncated');
      let v = 0;
      for (let i = 0; i < bits; i++, pos++) v = v * 2 + ((d[6 + Math.floor(pos / 7)] >> (6 - pos % 7)) & 1);
      return v;
    };
    return { get, s16: () => { const v = get(16); return v >= 32768 ? v - 65536 : v; } };
  }

  // Our message? Returns its type, or null. Data bytes must all be 7-bit.
  function messageType(d) {
    if (d.length < 7 || d[0] !== 0xF0 || d[d.length - 1] !== 0xF7) return null;
    if (d[1] !== 0x00 || d[2] !== 0x03 || d[3] !== 0x0F || d[4] !== 0x03) return null;
    for (let i = 1; i < d.length - 1; i++) if (d[i] & 0x80) return null;
    return d[5];
  }

  const angle = (v) => v * 180 / 32767;

  // USB frame: one sample. Throws on a wrong length (truncated or merged message).
  function decodeFrame(d) {
    if (d.length !== FRAME_LEN) throw new Error('frame length ' + d.length);
    const r = reader(d);
    const seq = r.get(14), ts = r.get(21);
    const holes = Array.from({ length: 9 }, () => r.get(10));
    const pressure = r.get(14);
    const accelY = r.s16(), roll = angle(r.s16()), elevation = angle(r.s16()), yaw = angle(r.s16());
    const coveredMask = r.get(9), flags = r.get(7);
    return { samples: [{ seq, ts, holes, pressure }], accelY, roll, elevation, yaw, coveredMask, flags };
  }

  // BLE batch: 1-16 samples, oldest first; timestamps between first and last are estimates.
  function decodeBatch(d) {
    const r = reader(d);
    const seq0 = r.get(14), ts0 = r.get(21), ts1 = r.get(21), count = r.get(5);
    const accelY = r.s16(), roll = angle(r.s16()), elevation = angle(r.s16()), yaw = angle(r.s16());
    const flags = r.get(7);
    if (count < 1 || count > 16) throw new Error('batch count ' + count);
    if (d.length !== 7 + Math.ceil((132 + 104 * count) / 7)) throw new Error('batch length ' + d.length);
    const span = (ts1 - ts0 + TS_MOD) % TS_MOD;
    const samples = [];
    for (let i = 0; i < count; i++) {
      const pressure = r.get(14);            // pressure before holes in a batch
      const holes = Array.from({ length: 9 }, () => r.get(10));
      samples.push({ seq: (seq0 + i) % SEQ_MOD, ts: (ts0 + (count === 1 ? 0 : Math.round(span * i / (count - 1)))) % TS_MOD, holes, pressure });
    }
    return { samples, accelY, roll, elevation, yaw, coveredMask: null, flags };
  }

  // Calibration. Firmware stores toneholeCovered as an absolute reading (like the baseline), so the
  // full-cover span is covered - baseline. (The v3 spec's "relative to baseline" note disagrees with
  // the firmware; see docs/warbl-raw-stream.md.)
  function decodeInfo(d) {
    if (d.length !== INFO_LEN) throw new Error('info length ' + d.length);
    const r = reader(d);
    const firmware = r.get(16);
    const baseline = Array.from({ length: 9 }, () => r.get(16));
    const covered = Array.from({ length: 9 }, () => r.get(16));
    const legacyCalibration = r.get(16), accelRange = r.get(16), gyroRange = r.get(16);
    const loopMs = r.get(16), ambient = r.get(16);
    const span = covered.map((c, i) => Math.max(1, c - baseline[i]));
    return { firmware, baseline, covered, span, legacyCalibration, accelRange, gyroRange, loopMs, ambient };
  }

  // 0 open .. 1 fully covered, for firmware hole index i.
  const coverage = (info, raw, i) => Math.max(0, Math.min(1, (raw - info.baseline[i]) / info.span[i]));
  const pressurePa = (info, p) => (p - info.ambient) * PA_PER_COUNT;
  const seqStep = (cur, prev) => (cur - prev + SEQ_MOD) % SEQ_MOD;
  const tsMs = (cur, prev) => ((cur - prev + TS_MOD) % TS_MOD) * 1000 / TS_HZ;

  return { FRAME, BATCH, INFO, config, requestInfo, messageType, decodeFrame, decodeBatch, decodeInfo, coverage, pressurePa, seqStep, tsMs };
})();
if (typeof module !== 'undefined') module.exports = WarblStream;
