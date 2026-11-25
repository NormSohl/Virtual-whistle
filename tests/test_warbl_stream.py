"""WARBL sensor stream v3 decoder (web/warbl-stream.js) against messages packed the way the
firmware packs them (SysExBitWriter in WARBL2 warbl2_firmware/Sensor_stream.ino)."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

JS = r"""
const WS = require(process.argv[1]);
// Port of the firmware's SysExBitWriter: MSB-first, 7 bits per byte.
function pack(fields) {
  const out = []; let bitsInByte = 0;
  for (const [value, bits] of fields) {
    for (let b = bits - 1; b >= 0; b--) {
      if (bitsInByte === 0) out.push(0);
      out[out.length - 1] |= (Math.floor(value / 2 ** b) & 1) << (6 - bitsInByte);
      bitsInByte = (bitsInByte + 1) % 7;
    }
  }
  return out;
}
const msg = (type, fields) => [0xF0, 0x00, 0x03, 0x0F, 0x03, type, ...pack(fields), 0xF7];
const u16 = (v) => (v + 65536) % 65536;
const r = {};

r.example = pack([[0, 7], [0x1234, 14]]).slice(1);           // spec: 0x1234 on a 7-bit boundary is 24 34

const holes = [5, 900, 812, 700, 1023, 0, 333, 444, 555];
const frame = msg(0x01, [[16383, 14], [2097151, 21], ...holes.map((h) => [h, 10]), [9000, 14],
  [u16(-1234), 16], [u16(-32767), 16], [u16(16384), 16], [u16(32767), 16], [0b101010101, 9], [3, 7]]);
r.frameLen = frame.length;
r.frameType = WS.messageType(frame);
r.frame = WS.decodeFrame(frame);
try { WS.decodeFrame(frame.slice(0, -2).concat([0xF7])); r.truncated = 'accepted'; } catch (e) { r.truncated = 'rejected'; }

const baseline = [10, 20, 30, 40, 50, 60, 70, 80, 90];
const covered = [10, 420, 530, 640, 750, 860, 970, 1000, 900];   // absolute readings, as the firmware stores them
const info = msg(0x10, [[48, 16], ...baseline.map((v) => [v, 16]), ...covered.map((v) => [v, 16]),
  [400, 16], [2, 16], [3, 16], [2, 16], [1600, 16]]);
r.infoLen = info.length;
r.info = WS.decodeInfo(info);
r.cov = [WS.coverage(r.info, 20, 1), WS.coverage(r.info, 220, 1), WS.coverage(r.info, 2000, 1), WS.coverage(r.info, 0, 1), WS.coverage(r.info, 500, 0)];
r.pa = [WS.pressurePa(r.info, 1600), WS.pressurePa(r.info, 1600 + 2184)];

const samples = [[1000, holes], [1100, holes.map((h) => 1023 - h)], [1200, holes]];
const batch = msg(0x02, [[16383, 14], [2097100, 21], [100, 21], [3, 5],
  [u16(7), 16], [0, 16], [0, 16], [0, 16], [1, 7], ...samples.flatMap(([p, hs]) => [[p, 14], ...hs.map((h) => [h, 10])])]);
r.batchLen = batch.length;
r.batch = WS.decodeBatch(batch);

r.notOurs = [WS.messageType([0xF0, 0x7D, 0x57, 0x52, 0x01, 0, 0xF7]), WS.messageType([0xF0, 0x00, 0x03, 0x0F, 0x02, 0x01, 0xF7]),
  WS.messageType([0xF0, 0x00, 0x03, 0x0F, 0x03, 0x01, 0x80, 0xF7])];
r.cmd = [WS.config(true, false), WS.config(true, true), WS.config(false), WS.requestInfo()];
r.seq = [WS.seqStep(0, 16383), WS.seqStep(5, 5)];
r.ts = WS.tsMs(10, 2097152 - 32758);
console.log(JSON.stringify(r));
"""


def run():
    out = subprocess.run(["node", "-e", JS, str(ROOT / "web/warbl-stream.js")],
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def test_bit_packing_matches_spec_example():
    assert run()["example"] == [0x24, 0x34]


def test_usb_frame():
    r = run()
    assert r["frameLen"] == 39 and r["frameType"] == 1
    f = r["frame"]
    s = f["samples"][0]
    assert (s["seq"], s["ts"], s["pressure"]) == (16383, 2097151, 9000)
    assert s["holes"] == [5, 900, 812, 700, 1023, 0, 333, 444, 555]
    assert f["accelY"] == -1234 and f["roll"] == -180 and f["yaw"] == 180
    assert abs(f["elevation"] - 90) < 0.01
    assert (f["coveredMask"], f["flags"]) == (0b101010101, 3)
    assert r["truncated"] == "rejected"


def test_info_and_calibration():
    r = run()
    assert r["infoLen"] == 62
    i = r["info"]
    assert i["firmware"] == 48 and i["ambient"] == 1600 and i["loopMs"] == 2
    assert i["span"][1] == 400 and i["span"][0] == 1        # zero span guarded
    assert r["cov"] == [0, 0.5, 1, 0, 1]
    assert r["pa"][0] == 0 and abs(r["pa"][1] - 1000) < 1e-9


def test_ble_batch():
    r = run()
    assert r["batchLen"] == 7 + -(-(132 + 104 * 3) // 7) == 71
    b = r["batch"]
    assert [s["seq"] for s in b["samples"]] == [16383, 0, 1]
    assert [s["pressure"] for s in b["samples"]] == [1000, 1100, 1200]
    assert b["samples"][1]["holes"][4] == 0 and b["samples"][2]["holes"][1] == 900
    assert [s["ts"] for s in b["samples"]] == [2097100, 24, 100]   # 152-tick span across the wrap; midpoint estimated
    assert b["accelY"] == 7 and b["flags"] == 1 and b["coveredMask"] is None


def test_commands_and_rejects():
    r = run()
    assert r["notOurs"] == [None, None, None]
    assert r["cmd"] == [[0xF0, 0, 3, 15, 3, 0x20, 0x05, 0xF7], [0xF0, 0, 3, 15, 3, 0x20, 0x07, 0xF7],
                        [0xF0, 0, 3, 15, 3, 0x20, 0x00, 0xF7], [0xF0, 0, 3, 15, 3, 0x21, 0xF7]]
    assert r["seq"] == [1, 0]
    assert abs(r["ts"] - 1000) < 1e-9
