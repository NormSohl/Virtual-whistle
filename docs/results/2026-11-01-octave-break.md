# 2026-11-01: Octave break from steady breath (physical jet)

Follow-up to [first sound](2026-11-01-first-sound.md). Norm: the tonguing burst used to kick the second octave was the least authentic part. Goal: the octave break should come from steady blowing pressure, like a real whistle.

## Change: physical flue jet (`jetModel = 2`, now the default)
After Verge, Fabre and Hirschberg:
- The acoustic flow through the window deflects the jet; receptivity ~ v / U.
- The deflection convects to the labium in tau = W / (0.4 U), W = window length 5 mm, U = sqrt(2 p / rho).
- The labium splits the jet (tanh profile, small offset for edge misalignment); the injected flow acts as a dipole pressure source ~ dQ/dt.
- The jet only amplifies over a band that scales with jet speed (Strouhal): a two-pole lowpass at 0.2 U / W. Without it, slow jets drove high modes; with it, soft blowing stays low.
- Breath therefore sets the jet delay and bandwidth, and the register follows steady pressure. No attack kick.

Bugs on the way: the jet source sign sets which register a given delay favours; the first try had registers inverted (fundamental at high pressure). Flipping the source sign gave the physical order.

## Register map (steady, tongued notes, breath 0.05-1.25 x 1500 Pa in steps of 0.05; digit = register, `.` = silent)
```
D   1111222222213333333333444  dB: -45 -19 -18 -10 -11 -16 -6
E   2111112222222222333333333  dB: -39 -29 -9 -10 -10 -8 -12
F#  3111111122222222222222333  dB: -47 -32 -20 -7 -7 -14 -10
G   .111111112222222222222222  dB: -64 -34 -43 -11 -6 -7 -12
A   .211111111122222222222222  dB: -116 -39 -37 -18 -9 -6 -6
B   .222111111111122222222222  dB: -70 -46 -34 -41 -15 -9 -6
C#  ..22111111111111122222222  dB: -70 -54 -30 -29 -45 -12 -6
D2  2.....222222.............  dB: -40 -33 -18 -21 -9 -6 -6
levels: 0.05 0.25 0.45 0.65 0.85 1.05 1.25 (every 4th column)
```
As on a real whistle: the first register needs more breath as the fingering shortens (D from 0.05, C# from ~0.25), and each note breaks to the second register at a higher pressure the shorter the tube. Vented D (oxxxxx) sounds D6 from 0.3 to 0.55. Weak spots: very soft blowing on the short fingerings (A, B, C#) speaks the second register instead of staying silent or first.

## Scale with per-note breath, no kick (`python -m render.synth scale`)
Breath per note = middle of its register range (`render/synth.py` BREATH table: 0.10 for low D rising to 1.10 for C#').
```
note  pattern  breath  synth Hz    take1    take2  vs avg level dB
D     xxxxxx     0.10     598.6    598.3    593.4    +8.0    -72.3
E     xxxxxo     0.17     670.3    674.2    667.1    -0.8    -61.2
F#    xxxxoo     0.25     745.3    750.0    748.0    -8.5    -52.8
G     xxxooo     0.28     805.6    803.3    799.5    +9.2    -52.2
A     xxoooo     0.35     896.7    905.4    904.3   -15.6    -47.6
B     xooooo     0.47    1028.8   1034.6   1023.3    -0.3    -41.3
C#    oooooo     0.55    1149.9   1162.6   1159.8   -16.9    -35.0
D'    oxxxxx     0.45    1212.1        -   1199.5   +18.1    -47.8
E'    xxxxxo     0.50    1342.4   1360.1   1348.1   -15.0    -43.7
F#'   xxxxoo     0.75    1495.3   1509.1   1500.7   -11.1    -36.0
G'    xxxooo     0.85    1615.0   1618.4   1614.5    -1.6    -29.8
A'    xxoooo     0.90    1794.0   1817.0   1800.6   -14.2    -23.4
B'    xooooo     1.00    2058.2   2081.5   2040.8    -2.5    -16.7
C#'   oooooo     1.10    2299.4   2308.6        -    -6.9    -10.8
in correct register: 14/14; of those mean -4.2 sd 10.1 max 18.1 cents; level spread 61 dB (raw)
```
- **All 14 notes in the right register, within ±18 cents of Norm's recordings** (mean -4, sd 10), without any attack burst.
- **Levels are badly unbalanced: 61 dB from low D to C#'.** The model has almost no losses where the sound leaves through open holes (pure inertance, no radiation resistance) and no distributed wall loss, so short fingerings ring with very high Q. A real whistle's second octave is louder than its low D, but by roughly 10-20 dB, not 60.
- Tried and parked: per-segment wall loss and a vortex-shedding loss at the window both compress the level range only a little and pull the pitch sharp (G +80 to +130 cents), because the jet then works further from resonance. Needs a better-founded loss model rather than knobs.

## Listening copy
`docs/audio/2026-11-01_synth_generation_d_scale_v2_levelled.wav`: each note scaled to equal loudness after rendering, so the raw 61 dB spread doesn't bury the low notes. **The levelling is a listening aid, not the model.**

## Next
1. Losses that are physically grounded: radiation resistance at open holes and window, frequency-dependent wall loss; then re-check pitch and register map.
2. Soft-blowing behaviour on short fingerings.
3. Tone: Norm wants a better instrument than the cheap whistle, not a copy. Levers: windway/labium geometry (jet offset, Strouhal band), bore and hole sizes from the optimizer.
