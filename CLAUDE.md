# virtual-whistle

Phase 1 of the "Virtual Renaissance recorder (WARBL physical model)" project, tracked in Norm's Claude Hub (Notion).
This file is the source of truth for project context; the hub row tracks status only.

## Goal
A physical model of a penny whistle, driven by WARBL finger-hole + breath data, that plays in tune.
The whistle is the proving ground for the full pipeline; Renaissance recorders, capped reeds, bagpipes, duduk and shehnai come later.

## Architecture
- `acoustics/` (Python): transfer-matrix impedance model + optimizer (CMA-ES / Nelder-Mead). Predicts playing pitch per fingering from geometry.
- `dsp/` (C++17): real-time model: waveguide bore, tonehole junctions, jet/edge excitation. Portable: must later compile for Daisy Seed3 (Cortex-M7).
- `render/`: offline renderer: scripted control stream (9 hole openness values 0-1 + breath pressure) -> WAV.
- `analysis/`: pitch detection (YIN), cents error per fingering, spectrograms.
- `data/`: measured geometry and recorded ground-truth pitches of Norm's real whistle(s).
- `docs/`: measuring guide, design decisions log.

## Rules
- Claude cannot hear. Never claim something is "in tune" or "sounds right" without a measured number (cents error, spectrum). Every tuning claim cites a test result.
- Ground truth comes from Norm's real whistle: caliper measurements + recordings of every fingering, both registers. See `docs/measuring.md`.
- DSP core: no heap allocation or locks in the audio path, float32, sample-rate agnostic (48/96/192 kHz), fractional delays for tuning precision.
- Same C++ DSP code runs offline and later on the Daisy; no platform code inside `dsp/`.
- Log design choices in `docs/decisions.md` with one-line reasons.
- Units: millimetres for geometry, Hz and cents for pitch, metres/second and kelvin only inside the acoustics code.

## Phases
1. Measure a real whistle (geometry + pitches) -> `data/`.
2. Impedance model reproduces the measured pitches within a few cents.
3. Real-time model rendered offline, pitch-checked automatically.
4. Optimizer: fit geometry to target charts (standard D/C whistle, then Norm's rationalized C chart with forked accidentals).
5. Live on the Mac: standalone app reading WARBL over USB MIDI (stock firmware first: hole bitmask + breath), CoreAudio out.
6. WARBL2 firmware fork with a raw-stream mode (packed SysEx, ~2 ms frames); then port DSP to Daisy Seed3.

## Where work happens
Norm prefers the Claude app interface over the command line. Phases 1-4 run in the Claude app's cloud workspace (clone, build, render, analyze, push here). Phase 5+ needs his Mac and hardware (Claude desktop app linked to the Mac).

## References
- WARBL2 firmware + Config Tool protocol: github.com/amowry/WARBL2 (`warbl2_firmware/Defines.h`, `webconfig/js/midi.js`). GPL-3.
- Prior art: STK BlowHole/Flute (Scavone, Cook), WWIDesigner, Inria OpenWInD.

## End of session
Offer to update the Claude Hub row: Status, Next step, Last touched; tag Where with the surface used.
