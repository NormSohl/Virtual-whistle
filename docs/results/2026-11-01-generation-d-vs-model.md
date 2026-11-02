# 2026-11-01: Model vs Norm's Generation D

First comparison of the impedance model with a real, measured, recorded whistle.

## Data
- Geometry: `data/generation_d/geometry_measured.csv` (calipers).
- Recording: `data/generation_d/recordings/2026-11-01_two_octaves_diatonic.m4a`, two octaves diatonic, no cross fingerings. Norm: "whistle is sounding pretty poor".
- Pitches: `data/generation_d/pitches_measured.csv` via `analysis.pitch`. D6 (second-octave D) didn't sound cleanly and is excluded.

## How the real whistle plays (vs 12-TET, A4 = 440)
Whole whistle ~40-55 cents sharp, unevenly: F# lowest (+23 / +34), B and C# highest (+80 / +82, +91 / +70).

## Model vs measurement (`python -m acoustics.calibrate_generation_d`)
```
Uncalibrated (bore top at labium, 30 °C): mean -27.0, sd 9.7, max |err| 44.8 cents
  D5   reg 1   -11.4
  E5   reg 1   -21.5
  F#5  reg 1   -22.3
  G5   reg 1   -42.8
  A5   reg 1   -34.0
  B5   reg 1   -22.9
  C#6  reg 1   -25.1
  E6   reg 2   -27.6
  F#6  reg 2   -23.8
  G6   reg 2   -44.8
  A6   reg 2   -35.5
  B6   reg 2   -26.5
  C#7  reg 2   -12.4

Calibrated: bore top 262.8 mm from foot, window scale 0.86: mean -0.7, sd 10.5, max |err| 21.6 cents
  D5   reg 1    +9.8
  E5   reg 1    +2.0
  F#5  reg 1    +3.5
  G5   reg 1   -15.6
  A5   reg 1    -3.7
  B5   reg 1   +11.2
  C#6  reg 1   +12.2
  E6   reg 2    -6.7
  F#6  reg 2    -1.5
  G6   reg 2   -21.6
  A6   reg 2   -11.1
  B6   reg 2    -0.9
  C#7  reg 2   +13.2

Calibrated + hole 4 position free: bore top 262.9, window scale 0.89, hole 4 lower edge 77.6 mm (measured 73.75): mean -0.5, sd 6.3, max |err| 10.7 cents
  D5   reg 1    +6.0
  E5   reg 1    -2.1
  F#5  reg 1    -1.0
  G5   reg 1    +4.5
  A5   reg 1    -5.2
  B5   reg 1    +5.8
  C#6  reg 1    +5.9
  E6   reg 2   -10.4
  F#6  reg 2    -5.5
  G6   reg 2    -2.2
  A6   reg 2    -9.4
  B6   reg 2    -3.2
  C#7  reg 2   +10.7
```

## Findings
- **The model predicted the whistle's shape before seeing the recording.** Uncalibrated, it is off by a nearly constant offset (sd ~10 cents around the mean). In particular it predicted B and C# sitting ~45-60 cents above the other notes; the real whistle does exactly that. The sharp top notes are the whistle, not the model.
- **Two calibration numbers** (where the acoustic top of the bore sits, and the window inertance) bring all 13 notes within ±22 cents, sd 10.5.
- **Hole 4** is the largest remaining residual (G flat in both octaves). Letting its position float moves it from the measured 73.75 mm to 77.6 mm and drops the error to sd 6.3, max 11 cents. Either hole 4 was mis-measured (worth one more check) or something else affects G. Treat 77.6 as a hypothesis, not a measurement.
- **Overall pitch:** the uncalibrated model at 30 °C is ~27 cents flat of the real whistle; part of that is the jet (flue pipes sound above their passive resonance), absorbed into the window calibration.

## Next
1. Recheck hole 4 (lower edge to foot).
2. Record the chromatic half-hole notes and cross-fingered C natural to test the partial-hole model.
3. Breath sweeps for pitch vs blowing pressure (needed for the real-time model's jet).
4. Then phase 3: the time-domain model in C++, rendered offline, checked against these same pitches.

## Update: second take (same setup)
`recordings/2026-11-01_two_octaves_diatonic_take2.m4a`; pitches added to `pitches_measured.csv` with a `take` column. Second-octave D sounded this time (+36 cents); C#7 was unsteady and is excluded.

- **Take-to-take spread:** take 2 is 12.5 cents lower on average (softer blowing), and individual notes differ by 2-34 cents (sd 8.7). That is the noise floor of a single human-played take.
- **Calibration on both takes together:** sd 14.7 with two numbers; sd 10.9 with hole 4 free. The model now fits about as well as the player repeats.
- **Hole 4 again lands at ~78 mm** (78.1 here, 77.6 from take 1) instead of the measured 73.75. Two independent takes agree, so a re-measure of hole 4 is the most useful next check.
- Second-octave D (top hole vented) comes out ~26 cents flat in the model relative to the real whistle: the vented-octave fingering is a good target for the next round of model work.
