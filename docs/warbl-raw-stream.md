# WARBL2 sensor stream

Since firmware 4.8 (released 2026-11-20; binary `WARBL2_firmware_4.8.1.uf2` in amowry/WARBL2 `warbl2_firmware/build/adafruit.nrf52.warbl2/`), the official WARBL2 firmware streams raw sensor data over SysEx. The play page uses it; our own firmware fork (below) is superseded and no longer read by the page.

Spec: [WARBL_sensor_stream_protocol_v3.md](https://github.com/amowry/WARBL2/blob/main/WARBL_sensor_stream_protocol_v3.md). Andrew's reference host: [WARBL_stream_monitor.html](https://warbl.xyz/WARBL_stream_monitor.html). Our decoder: `web/warbl-stream.js`, tested in `tests/test_warbl_stream.py` against messages packed the way the firmware packs them.

## What the page does
- Sends `F0 00 03 0F 03 20 05 F7` (stream on, normal MIDI kept; `07`, normal MIDI suppressed, while the page's MIDI out is on) and `F0 00 03 0F 03 21 F7` (request calibration) to the outputs named WARBL (all outputs if none is), then renews the config every second (the WARBL stops streaming 3 s after the last renewal, so closing the tab or a crash ends it by itself). Sends `... 20 00 F7` on page hide.
- Decodes USB frames (type 01, 39 bytes, ~500/s) and BLE batches (type 02); applies the newest sample per message. Takes the stream from the first MIDI input that sends it (macOS shows the WARBL twice).
- Calibration from STREAM_INFO (type 10): coverage = (raw - baseline) / (covered - baseline), clamped 0..1. Re-requested every second until it arrives.
- Pressure: Pa = (p - ambient14) / 2.184, both sensor types.
- No stream within 0.6 s (older firmware, or no SysEx permission): stops the stream requests and falls back to Config Tool mode (on/off holes, ~40 Hz).
- Health chip: samples/s, lost (sequence gaps), bad (wrong length), duplicates, longest gap by the WARBL's own 32768 Hz clock.

## Differences from our fork
| | Fork (rawstream1, 2026-11-07) | Official v3 |
|---|---|---|
| Start | CC 106 = 79 | SysEx config, renewed every second |
| ID | `7D 57 52` (non-commercial) | `00 03 0F` (registered) |
| Holes | 14-bit, baseline already subtracted | 10-bit raw, host subtracts baseline |
| Pressure | twelveBit + 8192 | 14-bit, 2.184 counts/Pa |
| Also | - | 14-bit seq, device timestamp, Y accel, roll/elevation/yaw, covered mask, flags, BLE batches |

## Spec note for Andrew
The spec says covered thresholds are "relative to baseline" and gives coverage = (raw - baseline) / coveredThreshold. In the firmware, `toneholeCovered` is an absolute reading (calibration takes the highest raw reading, then subtracts 20 % of the span as a feel offset; `Functions.ino` compares `toneholeRead - baseline` against `toneholeCovered - baseline`). So the full-cover span is covered - baseline, which is what the page uses. Worth confirming with him.

## Superseded: our firmware fork
Branch `warbl2-raw-stream` of this repo, patches in `firmware/patches/`, test build `firmware/WARBL2_firmware_4.8.0_rawstream1.uf2`. Kept for the record; flash the official 4.8.1 instead.

### Fork hardware test, 2026-11-07
Norm's WARBL2 on the Mac Studio, flashed with `rawstream1.uf2` (Terminal `cp -X` to WARBLBOOT; a Finder drag left the board in UF2 mode). `web/play.html` in Chrome, about a minute of playing:
- 502 frames/s, 0 lost (seq gaps), 0 malformed, longest gap between frames 3.6 ms (host timestamps).
- Slow half-hole slides bend pitch continuously: coverage reaches the model.
- Chrome received every frame twice (two MIDI inputs carry the same WARBL data); the page now takes raw frames from the first input that sends one and counts repeats as duplicates.
- Open: the WARBL LED keeps flashing blue irregularly after flashing; not explained yet.

## Open questions
- Optical reading vs actual coverage is not linear; a per-hole curve may be needed.
- First hardware test of the v3 stream on the play page still to do.
