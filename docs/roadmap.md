# Roadmap

## Now
- WARBL raw stream on hardware: fork, flash, test with `web/play.html` in Chrome (see [warbl-raw-stream.md](warbl-raw-stream.md)).

## Ideal whistle (playability-optimized)
The Generation D model stays as is, a character model. Alongside it, an "ideal whistle" with the same physics and a geometry the optimizer picks for playability instead of fidelity to a real instrument.

Optimization targets:
- Every fingering and register in tune: no sharp B/C#, no octave stretch; cross fingerings land on Norm's rationalized charts.
- Wide, overlapping register windows at similar pressures for all notes, so the octave break sits consistently.
- Pitch steady with breath; any pitch-vs-breath slope is a chosen parameter, not inherited.
- Easy, even starts; even tone and loudness across the range.
- Half-holes: coverage maps smoothly and evenly to pitch on every hole.

Free variables: hole positions and sizes (fingers are on the WARBL, so no hand-span limits), bore profile, jet and window parameters.

## Control output
- Continuous pitch from the model (1V/oct CV, MPE pitch), gate from the model sounding, expression channels for breath, register, brightness, finger shading.
- MIDI as MPE.
- For control-only devices, a lookup table from the acoustic model (coverage + breath -> pitch, register) instead of the audio model.

## Later
Renaissance recorders from the museum measurements; capped reeds (crumhorn, cornamuse, rauschpfeife); shawm; bagpipes; duduk; shehnai; three-hole pipe (galoubet, Norm owns a good one).
