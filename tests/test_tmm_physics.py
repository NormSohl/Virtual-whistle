"""Physics sanity checks for the transfer-matrix model against textbook results."""
import numpy as np
import pytest

from acoustics.tmm import (Air, Bore, Hole, Window, bore_input_impedance, cylinder,
                           playing_frequencies, radiation_unflanged)

AIR = Air(25.0)


def cents(a, b):
    return 1200 * np.log2(a / b)


def first_min_freq(Z, f):
    m = np.abs(Z)
    i = next(i for i in range(1, len(f) - 1) if m[i] < m[i - 1] and m[i] <= m[i + 1])
    return f[i]


def first_max_freq(Z, f):
    m = np.abs(Z)
    i = next(i for i in range(1, len(f) - 1) if m[i] > m[i - 1] and m[i] >= m[i + 1])
    return f[i]


def test_lossless_limit_matches_quarter_wave_closed_pipe():
    """Pipe driven at one end, unflanged at the other: impedance maxima at c/4(L+dL) (odd)."""
    r, L = 0.006, 0.25
    f = np.arange(100.0, 1200.0, 0.05)
    om = 2 * np.pi * f
    M = cylinder(om, r, L, AIR)
    ZL = radiation_unflanged(om, r, AIR)
    Zin = (M[0, 0] * ZL + M[0, 1]) / (M[1, 0] * ZL + M[1, 1])
    f_lossless = AIR.c / (4 * (L + 0.6133 * r))
    # Boundary-layer dispersion slows sound in a narrow tube. Benade's independent
    # approximation: v = c (1 - 1.65e-3 / (r sqrt(f))), r in m. A 12 mm bore at ~340 Hz
    # is ~25 cents flat of the lossless formula; the model must agree with Benade.
    f_benade = f_lossless * (1 - 1.65e-3 / (r * np.sqrt(f_lossless)))
    f_model = first_max_freq(Zin, f)
    assert abs(cents(f_model, f_benade)) < 3
    assert -35 < cents(f_model, f_lossless) < -15


def test_open_open_pipe_harmonic_series():
    """Whistle tube with no holes and a bore-sized 'window': near-harmonic registers."""
    r, L = 0.006, 0.28
    bore = Bore(L, [(0.0, r)])
    # Window of the same area as the bore, negligible wall: behaves like an open end.
    w = Window(length=np.sqrt(np.pi) * r, width=np.sqrt(np.pi) * r, wall=0.0,
               corr_scale=0.6133 / 1.7)
    fs = playing_frequencies(bore, [], [], w, AIR, n_registers=3)
    f_lossless = AIR.c / (2 * (L + 2 * 0.6133 * r))
    f_benade = f_lossless * (1 - 1.65e-3 / (r * np.sqrt(f_lossless)))
    assert abs(cents(fs[0], f_benade)) < 5
    assert fs[1] / fs[0] == pytest.approx(2.0, rel=0.01)
    assert fs[2] / fs[0] == pytest.approx(3.0, rel=0.02)


def _tube():
    bore = Bore(0.30, [(0.0, 0.006)])
    window = Window(length=0.006, width=0.009, wall=0.002)
    return bore, window


def test_opening_a_hole_raises_pitch_and_larger_hole_raises_more():
    bore, window = _tube()
    f_none = playing_frequencies(bore, [], [], window, AIR, n_registers=1)[0]
    small = playing_frequencies(bore, [Hole(0.22, 0.002, 0.001)], [1.0], window, AIR, n_registers=1)[0]
    large = playing_frequencies(bore, [Hole(0.22, 0.004, 0.001)], [1.0], window, AIR, n_registers=1)[0]
    assert f_none < small < large


def test_closed_hole_slightly_lowers_pitch():
    bore, window = _tube()
    f_none = playing_frequencies(bore, [], [], window, AIR, n_registers=1)[0]
    f_closed = playing_frequencies(bore, [Hole(0.22, 0.003, 0.0015)], [0.0], window, AIR, n_registers=1)[0]
    assert f_closed < f_none
    assert cents(f_none, f_closed) < 15          # small effect


def test_large_open_hole_acts_like_cutting_the_pipe():
    bore, window = _tube()
    x = 0.20
    with_hole = playing_frequencies(bore, [Hole(x, 0.0055, 0.0005)], [1.0], window, AIR, n_registers=1)[0]
    cut = playing_frequencies(Bore(x, [(0.0, 0.006)]), [], [], window, AIR, n_registers=1)[0]
    # A hole nearly bore-sized behaves close to a pipe cut at the hole, slightly flatter.
    assert -120 < cents(with_hole, cut) < 0


def test_half_hole_lies_between_closed_and_open():
    bore, window = _tube()
    h = [Hole(0.22, 0.003, 0.001)]
    fc = playing_frequencies(bore, h, [0.0], window, AIR, n_registers=1)[0]
    fh = playing_frequencies(bore, h, [0.5], window, AIR, n_registers=1)[0]
    fo = playing_frequencies(bore, h, [1.0], window, AIR, n_registers=1)[0]
    assert fc < fh < fo


def test_warmer_air_raises_pitch_about_3_cents_per_degree():
    bore, window = _tube()
    f20 = playing_frequencies(bore, [], [], window, Air(20.0), n_registers=1)[0]
    f30 = playing_frequencies(bore, [], [], window, Air(30.0), n_registers=1)[0]
    assert 25 < cents(f30, f20) < 35
