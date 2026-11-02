# WARBL2 raw stream (firmware fork)

Branch `raw-stream` of a WARBL2 firmware fork, based on amowry/WARBL2 main (4.8.0, commit 9ae59a2). Patches in `firmware/patches/`, test build `firmware/WARBL2_firmware_4.8.0_rawstream1.uf2` (arduino-cli 1.5.2, Adafruit nRF52 core 1.7.0, board WARBL2, BMP5xx library patched to 8 MHz SPI per the WARBL2 build notes). Compiles: 245,540 bytes flash (30 %), 28,088 bytes RAM (11 %). **Not yet run on hardware.**

## Why
Stock firmware reports holes as covered/uncovered after an adaptive smoothing filter, and to the Config Tool only every 25+ ms. A physical model needs how much of each hole is covered, continuously. The optical sensors already measure that.

## Protocol
Commands, CC 106 on MIDI channel 7 (bytes `B6 6A vv`):
| Value | Meaning |
|---|---|
| 79 | Enter raw-stream mode (sends a calibration frame first) |
| 80 | Exit raw-stream mode |
| 81 | Re-send the calibration frame |

Raw stream runs alongside normal playing: notes and CCs still go out, so the WARBL keeps working with any synth. USB only.

Data frame, every main-loop pass (~2 ms on USB), 27 bytes:
`F0 7D 57 52 01 seq h0lo h0hi ... h8lo h8hi plo phi F7`
- `7D` = non-commercial SysEx ID; `57 52` = "WR".
- `seq` 0-127 increments per frame (detect drops).
- h0..h8: holes bell, R4, R3, R2, R1, L3, L2, L1, thumb. 14-bit, baseline-corrected (0 = uncovered), taken **before** the firmware's adaptive smoothing filter.
- p: `twelveBitPressure + 8192`. On BMP585 hardware twelveBitPressure = (breath − ambient) mbar × 54.6 + 400.

Calibration frame, 29 bytes:
`F0 7D 57 52 02 format version patch c0lo c0hi ... c8lo c8hi alo ahi F7`
- c0..c8: reading at full cover (toneholeCovered − toneholeBaseline). Coverage = h / c, clamp 0..1.
- a: `(sensorCalibration << 2) + 8192`, the startup pressure in twelve-bit units (ambient).

Whistle holes 1-6 map to firmware holes L1, L2, L3, R1, R2, R3 (indices 7, 6, 5, 4, 3, 2).

## Host
`web/play.html` asks for the raw stream (CC 106 = 79); if no frame arrives within 0.6 s it falls back to the stock Config Tool mode (on/off holes, ~40 Hz). Needs Web MIDI with SysEx: Chrome on the Mac works; Safari doesn't.

## Flashing
Hold button 1 while plugging the WARBL in (or double-click reset), then copy the .uf2 onto the WARBLBOOT drive. To go back, copy an official release .uf2 the same way. Note: 4.8 firmware may update the WARBL's ATmega sensor firmware on first boot (built-in upstream behaviour).

## Open questions
- Frame rate vs USB: ~13.5 kB/s of SysEx; the firmware writes without blocking, so a stalled host can drop or truncate frames. Hosts must check length and F7.
- Optical reading vs actual coverage is not linear; a per-hole curve may be needed after first tests.
- Honeywell (pre-BMP) units: pressure scale differs; host needs a gain.
