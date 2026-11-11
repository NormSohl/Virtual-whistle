# Plan: Copeland D and the extended whistle (agreed 2026-11-10)

Written on branch `plan-copeland-extended` so `main` stays at 595d036 until the
v0.1.0-alpha release is created. Merge into `main` (and fold into `roadmap.md` and
`decisions.md`) after that.

## Decisions (Norm, 2026-11-10)

- **Alpha frozen.** v0.1.0-alpha = play page and model at `main` 595d036 (the build at
  media.sohl.com/whistle/2026-11-10/) + firmware `warbl2-raw-stream` 1babcf4. Tags
  `v0.1.0-alpha` and `warbl2-raw-stream-v0.1.0-alpha`, GitHub pre-release with the
  firmware .zip/.hex attached. Still to do (Norm, at the Mac or on the iPad): this
  session could not create tags or releases (GitHub blocks it from the cloud proxy).
- **Stock WARBL firmware is not changed**, only the code added for the raw stream.
  The diagnostics bell-sensor gap in stock code stays as it is.
- **Bell-sensor fix** (branch `raw-stream-bell-restore`, 347a99e) compiles cleanly
  (arduino-cli, Adafruit nRF52 1.7.0, board WARBL2; +224 bytes) but needs flashing and a
  hardware test at the Mac before merging into `warbl2-raw-stream`.
- **New instrument: Copeland D** (Norm's silver Copeland whistle in D, conical bore),
  a separate instrument. Generation D is never overwritten.
- **Extended whistle** built on the Copeland physics, a separate instrument. It
  **replaces the planned "ideal whistle" on Generation D physics**; Generation D
  stays as the character model.
- **The web app supports all instruments** from now on (instrument menu; Generation
  D the default).
- **Extended whistle is in D** (matches the other instruments). Later idea: a Key
  setting that scales the geometry to transpose any whistle, with an automatic retune
  per key.
- **No lower thumb hole.** Work as if it does not exist; the Swayne chart's
  lower-thumb Eb (moved to R4 in the WARBL chart) is dropped as a remap.
- **F natural and D# (in D) are important and must be real forked fingerings**:
  acoustic cross-fingerings on the existing holes, no extra keys or switches.

## Guarantee: current work is not affected

- Each instrument has its own folder under `data/` and its own preset under
  `tune/presets/`. Generation D files are not edited.
- Engine changes must keep Generation D renders byte-identical (C++ and JS), as the
  existing tests do (`tests/test_nine_holes.py` pattern). A constant-radius bore takes
  the existing code path.
- Every public build keeps its own dated folder on media.sohl.com.

## Work, in order

1. **Lock the alpha** (above) and test the bell-sensor fix on hardware.
2. **Engine and web app**, Generation D unchanged:
   - Tuning model (`acoustics/tmm.py`): conical segment transfer matrix (today the
     bore is piecewise-cylindrical).
   - Real-time engine (`dsp/whistle.hpp`, `web/whistle-model.js`): bore radius that
     varies along the tube, with scattering where the radius changes (today one
     `boreRadius` for the whole tube).
   - Instrument registry and an instrument menu on the play page.
3. **Copeland D**: measure and record it as for Generation D (`docs/measuring.md`):
   every fingering in both registers, forked fingerings, half-holes, breath sweeps.
   New: the bore profile (inside diameter at several points: both ends by caliper,
   the middle with drill bits or rods pushed in to a stop; a short guide to be
   written), window, and the thin silver wall at the holes. Success: model pitches
   within a few cents of the recordings before any tuning by ear.
4. **Extended whistle**: Copeland physics, thumb hole as a register (octave) vent,
   a seventh hole for R4. The tuning program fits hole sizes and positions to the
   target chart below. The play page reads thumb and R4 from the raw stream.

## Target chart: Swayne fingerings in D

Source: Swayne C column of `WARBL_custom_fingerings.xlsx`, saved as
`data/charts/swayne_c_warbl.csv` (256 patterns, string order thumb L1 L2 L3 R1 R2 R3
R4, 1 = covered; values are the C chart's MIDI notes). Moved up a whole tone to D.
Thumb covered = low octave; thumb open = the same fingering an octave up (the
thumb vent's job acoustically). Below a fingering's highest open hole, the lower
fingers don't matter (half-closed rule), except where a cross-fingering is listed.

| L1..R4 (1 = closed) | Swayne C | Extended D |
|---|---|---|
| 1111111 | Bb4 | C5 (7-finger note, a whole tone below the tonic) |
| 1111110 | C5 | D5 (tonic) |
| 1111100 | D5 | E5 |
| 1111101 | Eb5 (lower-thumb remap) | dropped; candidate slot for D#5, see below |
| 1111000 | E5 | F#5 |
| 1110000 | F5 | G5 |
| 1101000 | F#5 | G#5 |
| 1100000 | G5 | A5 |
| 1010000 | Ab5 | Bb5 |
| 1000000 | A5 | B5 |
| 0100000 | Bb5 | C6 |
| 0000000 | B5 | C#6 |

Required forked fingerings (Norm: "important"), to be found by the tuning program
and shown to Norm with cents errors before they are final:

- **D#5**: start from D fingering + R4 closed (1111101). Closing a hole below an
  open one flattens only a little, so this depends on the seventh hole's size.
- **F5**: start from the E-F# area, e.g. L1-L3 + R1 closed, R2 open, R3 closed
  (1111010); today that pattern plays F#.

The search tests these and nearby patterns, picks ones in tune at normal breath that
don't disturb the other notes, and the WARBL chart is updated to match whatever is
chosen, so model and WARBL agree.
