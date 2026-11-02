"""Pitch tool self-tests on synthetic whistle-like tones with known pitch."""
import numpy as np
import pytest

from analysis.pitch import held_notes, midi_to_hz, pitch_track

SR = 48000


def tone(f, dur, sr=SR, harmonics=(1.0, 0.3, 0.15, 0.05), noise=0.02, vibrato_cents=0.0, seed=0):
    """Breathy harmonic tone, roughly whistle-like."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(dur * sr)) / sr
    inst = f * 2 ** (vibrato_cents / 1200 * np.sin(2 * np.pi * 5.0 * t))
    phase = 2 * np.pi * np.cumsum(inst) / sr
    x = sum(a * np.sin((k + 1) * phase) for k, a in enumerate(harmonics))
    env = np.minimum(1, np.minimum(t / 0.05, (dur - t) / 0.05))
    return 0.3 * x * env + noise * rng.standard_normal(len(t))


def silence(dur, sr=SR):
    return np.zeros(int(dur * sr))


@pytest.mark.parametrize("f", [587.33, 659.26, 880.0, 1108.73, 1174.66, 2217.46])
def test_single_note_within_one_cent(f):
    x = tone(f, 1.5)
    notes = held_notes(pitch_track(x, SR))
    assert len(notes) == 1
    assert abs(1200 * np.log2(notes[0].hz / f)) < 1.0


def test_detuned_note_reports_cents():
    f = midi_to_hz(74) * 2 ** (17 / 1200)          # D5 + 17 cents
    notes = held_notes(pitch_track(tone(f, 1.5), SR))
    assert notes[0].nearest == "D5"
    assert notes[0].cents_off == pytest.approx(17, abs=1.0)


def test_sequence_of_notes_separated_by_silence():
    freqs = [midi_to_hz(m) for m in (74, 76, 78, 79, 81, 83, 85, 86)]
    x = np.concatenate([np.concatenate([tone(f, 1.0, seed=i), silence(0.3)]) for i, f in enumerate(freqs)])
    notes = held_notes(pitch_track(x, SR))
    assert [n.nearest_midi for n in notes] == [74, 76, 78, 79, 81, 83, 85, 86]
    assert all(abs(n.cents_off) < 1.5 for n in notes)


def test_vibrato_median_is_centre_pitch():
    f = 880.0
    notes = held_notes(pitch_track(tone(f, 2.0, vibrato_cents=15), SR))
    assert len(notes) == 1
    assert abs(1200 * np.log2(notes[0].hz / f)) < 2.0


def test_short_blips_ignored():
    x = np.concatenate([tone(880, 0.15), silence(0.3), tone(987.77, 1.0)])
    notes = held_notes(pitch_track(x, SR))
    assert [n.nearest for n in notes] == ["B5"]
