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

Norm's fingering requirements:
- **Thumb hole as the octave control.** On the WARBL Norm uses the thumb as an octave switch, and it's the easy way into the second octave. Acoustically this is a register vent: a small hole that, when opened, weakens the low register so the tube jumps to the second at the same breath (the recorder thumb, the saxophone and clarinet register keys). The optimizer places and sizes it so an open thumb gives an in-tune second octave on every fingering. One vent can't be ideal for every note (saxophones use two and switch automatically); the virtual instrument can have the thumb open a vent chosen per fingering, as a keyed mechanism would. Partial thumb opening stays physical (pinching).
- **Seventh finger (R4 pinky) closes to a whole tone below the tonic.** Acoustically: the bore extends below hole 6 with a seventh hole for the pinky, open by default; closing it plays the tone below the tonic (C on a D whistle).
- Cross fingerings land on Norm's rationalized charts.
- Thumb and R4 are optional per instrument: the WARBL senses both, and each model chooses whether they act acoustically (vent, seventh hole) or are ignored, so six-hole players are unaffected.
- Open idea: a "moving" thumb vent, where the vent's effective position and size follow the fingering (keywork no real instrument could carry).

Free variables: hole positions and sizes (fingers are on the WARBL, so no hand-span limits), bore profile, jet and window parameters.

## Control output
- Continuous pitch from the model (1V/oct CV, MPE pitch), gate from the model sounding, expression channels for breath, register, brightness, finger shading.
- MIDI as MPE.
- For control-only devices, a lookup table from the acoustic model (coverage + breath -> pitch, register) instead of the audio model.

## Model generalization (needed for the above and for recorders)
- Hole count per instrument, up to the WARBL's nine sensors (thumb, L1-L3, R1-R4, bell); currently fixed at six in `dsp/whistle.hpp` and `web/whistle-model.js`.
- Page and host mapping for thumb, R4 and bell from the raw stream.

## Later
Renaissance recorders from the museum measurements; capped reeds (crumhorn, cornamuse, rauschpfeife); shawm; bagpipes; duduk; shehnai; three-hole pipe (galoubet, Norm owns a good one).
