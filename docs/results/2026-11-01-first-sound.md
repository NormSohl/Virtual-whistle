# 2026-11-01: First sound from the C++ model (phase 3 start)

`dsp/whistle.hpp` (portable C++17, header-only, no allocation in `process()`), rendered offline by `render/render.cpp` at 96 kHz, driven by `python -m render.synth scale`. Geometry: Norm's Generation D from the calibrated impedance model (bore top 263.4 mm from foot, window scale 0.92). Audio: `docs/audio/2026-11-01_synth_generation_d_scale.wav` (48 kHz/16-bit copy).

## Model
- Bore: bidirectional waveguides between the window, the six holes and the foot; 3rd-order Lagrange fractional delays; c from 30 °C air with a 0.9 % boundary-layer slowdown.
- Toneholes: shunt scattering junctions; filter from the same open-inertance / closed-compliance physics as the impedance model, partial openness in between.
- Foot: unflanged-pipe reflectance (end-correction delay + radiation lowpass) with a lumped loss.
- Window: inertance reflectance; jet: STK-style (Cook) delayed cubic nonlinearity, jet delay from breath pressure via jet speed.
- Second-octave notes are played with a tonguing kick (breath overshoot 1.5x for 30 ms) and higher breath.

## Pitch check (render vs Norm's two takes)
```
note  pattern   synth Hz    take1    take2  vs avg
D     xxxxxx       598.9    598.3    593.4    +8.9
E     xxxxxo       670.5    674.2    667.1    -0.4
F#    xxxxoo       745.4    750.0    748.0    -8.3
G     xxxooo       806.1    803.3    799.5   +10.1
A     xxoooo       896.9    905.4    904.3   -15.3
B     xooooo      1029.0   1034.6   1023.3    +0.0
C#    oooooo      1150.8   1162.6   1159.8   -15.6
D'    oxxxxx      1218.3        -   1199.5   +27.0
E'    xxxxxo       670.9   1360.1   1348.1 -1215.7
F#'   xxxxoo      1494.2   1509.1   1500.7   -12.4
G'    xxxooo      1615.0   1618.4   1614.5    -1.6
A'    xxoooo      1794.3   1817.0   1800.6   -13.9
B'    xooooo      2058.2   2081.5   2040.8    -2.4
C#'   oooooo      2299.5   2308.6        -    -6.8
in correct register: 13/14; of those mean -2.4 sd 11.7 max 27.0 cents
```
- **First octave: all seven notes within ±16 cents of the recordings**, the same size as the take-to-take spread. No retuning of the C++ model against the recordings: its geometry comes straight from the impedance-model calibration.
- **Second octave: 6 of 7 notes overblow correctly and land within ±14 cents**; vented D' is +27.
- **E' stays in the first octave.** Overblowing in this jet model is driven by the attack transient more than by steady breath pressure; steady breath sweeps rise in pitch (~+14 cents on D, matching the recordings' 10-20) but don't break to the octave. Register control is the main open problem.

## Bugs found along the way
- First-order filters transformed with the biquad bilinear formula gain a cancelling pole/zero pair at Nyquist that is numerically marginal; it produced a 48 kHz runaway. `Biquad::setAnalog` now transforms first-order prototypes as first order.
- An experimental physical jet (deflection by window flow, tanh labium split, drive ~ jet speed) is in the code as `jetModel = 1`; it overblows G and B with breath like a real whistle but won't start the long fingerings yet.

## Next
1. Register control: make the second octave follow steady breath pressure (jet model 1, or a better-calibrated jet delay), check against Norm's breath sweeps.
2. Tone: compare spectra with the recordings (needs care: the iPhone mic and room colour the recordings).
3. Real-time harness on the Mac (CoreAudio + WARBL), then the Daisy port.
