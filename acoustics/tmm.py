"""Transfer-matrix (impedance) model of a whistle.

Plane-wave acoustics in the frequency domain. The bore is a chain of
cylindrical segments with visco-thermal losses (Keefe 1984); toneholes are
symmetric T-networks with shunt and series impedances (after Keefe 1990 and
Dalmont et al. 2002); the foot radiates as an unflanged pipe. The window
(mouth) end is an open side opening represented by an inertance plus
radiation resistance.

Units inside this module: SI (metres, seconds, kg). Geometry objects in
`whistle.py` are in millimetres and converted here.

Playing frequencies of a flue instrument are taken at the minima of the
impedance seen by the jet at the window, i.e. where Im(Z_window + Z_bore) = 0
with |Z| small. The jet's own small pitch shift is not modelled; it is
absorbed by calibration against measurements.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import brentq


# ---------------------------------------------------------------- air

@dataclass(frozen=True)
class Air:
    temp_c: float = 25.0

    @property
    def T(self) -> float:
        return self.temp_c + 273.15

    @property
    def c(self) -> float:                     # speed of sound, m/s (dry air)
        return 331.3 * np.sqrt(self.T / 273.15)

    @property
    def rho(self) -> float:                   # density, kg/m^3
        return 1.2041 * 293.15 / self.T

    @property
    def eta(self) -> float:                   # shear viscosity, Pa s (Sutherland)
        return 1.846e-5 * (self.T / 300.0) ** 0.7


# ---------------------------------------------------------------- elements

Matrix = np.ndarray   # shape (2, 2, nfreq), complex


def _identity(n: int) -> Matrix:
    m = np.zeros((2, 2, n), dtype=complex)
    m[0, 0] = m[1, 1] = 1.0
    return m


def _mul(a: Matrix, b: Matrix) -> Matrix:
    return np.einsum("ijf,jkf->ikf", a, b)


def cylinder(omega: np.ndarray, radius: float, length: float, air: Air) -> Matrix:
    """Lossy cylindrical segment (Keefe 1984 large-radius approximations)."""
    S = np.pi * radius ** 2
    rv = radius * np.sqrt(air.rho * omega / air.eta)
    Z0 = air.rho * air.c / S
    Zc = Z0 * (1 + 0.369 / rv - 1j * (0.369 / rv + 1.149 / rv ** 2 + 0.303 / rv ** 3))
    Gamma = (omega / air.c) * (1.045 / rv + 1.080 / rv ** 2 + 0.750 / rv ** 3
                               + 1j * (1 + 1.045 / rv))
    gl = Gamma * length
    m = np.empty((2, 2, len(omega)), dtype=complex)
    m[0, 0] = np.cosh(gl)
    m[0, 1] = Zc * np.sinh(gl)
    m[1, 0] = np.sinh(gl) / Zc
    m[1, 1] = np.cosh(gl)
    return m


def _inner_end_correction(b: float, delta: float) -> float:
    """Inner (matching volume) end correction of a side hole, Dalmont et al. 2002."""
    return b * (0.82 - 0.193 * delta - 1.09 * delta ** 2 + 1.27 * delta ** 3 - 0.71 * delta ** 4)


def tonehole(omega: np.ndarray, bore_radius: float, hole_radius: float, chimney: float,
             openness: float, air: Air) -> Matrix:
    """Side tonehole as a symmetric T-network.

    openness: 1 = fully open, 0 = closed by a finger, in between = partially
    covered (approximation: the open part is a hole of reduced area in
    parallel with the covered remainder acting as a closed hole).
    """
    k = omega / air.c
    a, b, t = bore_radius, hole_radius, chimney
    delta = b / a
    Sb = np.pi * b ** 2
    Zh = air.rho * air.c / Sb
    ti = _inner_end_correction(b, delta)

    # Closed hole: short closed chimney -> compliance (cotangent of effective height).
    Ys_closed = 1j * np.tan(k * (t + ti)) / Zh

    def Ys_open(br: float) -> np.ndarray:
        """Admittance of an open hole of radius br (same chimney)."""
        d = br / a
        Sbr = np.pi * br ** 2
        Zbr = air.rho * air.c / Sbr
        te = t + _inner_end_correction(br, d) + 0.61 * br       # radiation end correction ~ unflanged
        Zs = Zbr * (1j * k * te + 0.25 * (k * br) ** 2)        # inertance + radiation resistance
        return 1.0 / Zs

    s = float(np.clip(openness, 0.0, 1.0))
    if s >= 1.0:
        Ys = Ys_open(b)
        ta = -0.28 * b * delta ** 2                              # series length correction, open
    elif s <= 0.0:
        Ys = Ys_closed
        ta = -0.47 * b * delta ** 4 / (np.tanh(1.84 * t / b) + 0.62 * delta ** 2 + 0.64 * delta)
    else:
        Ys = (1 - s) * Ys_closed + Ys_open(b * np.sqrt(s))
        ta = -0.28 * b * delta ** 2 * s
    Za = 1j * k * (air.rho * air.c / (np.pi * a ** 2)) * ta
    Zs = 1.0 / Ys

    m = np.empty((2, 2, len(omega)), dtype=complex)
    m[0, 0] = 1 + Za / (2 * Zs)
    m[0, 1] = Za * (1 + Za / (4 * Zs))
    m[1, 0] = 1.0 / Zs
    m[1, 1] = 1 + Za / (2 * Zs)
    return m


def radiation_unflanged(omega: np.ndarray, radius: float, air: Air) -> np.ndarray:
    """Low-frequency radiation impedance of an unflanged pipe (Levine & Schwinger)."""
    k = omega / air.c
    ka = k * radius
    Z0 = air.rho * air.c / (np.pi * radius ** 2)
    return Z0 * (0.25 * ka ** 2 + 1j * 0.6133 * ka)


# ---------------------------------------------------------------- whistle

@dataclass
class Hole:
    position: float     # m from the top of the bore (block face)
    radius: float       # m
    chimney: float      # m (wall thickness at the hole)


@dataclass
class Bore:
    """Piecewise-cylindrical bore: list of (start_position_m, radius_m), ending at length."""
    length: float
    sections: list[tuple[float, float]]

    def radius_at(self, x: float) -> float:
        r = self.sections[0][1]
        for start, radius in self.sections:
            if x >= start:
                r = radius
        return r


@dataclass
class Window:
    length: float       # along the axis, m
    width: float        # across, m
    wall: float         # wall/labium thickness, m
    corr_scale: float = 1.0   # calibration factor on the window inertance


def bore_input_impedance(omega: np.ndarray, bore: Bore, holes: list[Hole],
                         openness: list[float], air: Air) -> np.ndarray:
    """Input impedance at the top of the bore (window position)."""
    # Breakpoints: section starts and hole positions, in order from the top.
    if len(holes) != len(openness):
        raise ValueError(f"{len(holes)} holes but {len(openness)} openness values")
    hole_at = {h.position: (h, s) for h, s in zip(holes, openness)}
    if len(hole_at) != len(holes):
        # Two holes at one position share a dictionary key and one would be dropped without a word.
        raise ValueError("two holes at the same position: offset one slightly (e.g. a thumb hole opposite hole 1)")
    if any(not 0.0 < h.position <= bore.length for h in holes):
        raise ValueError("hole position outside the bore")
    events = sorted({0.0, bore.length, *[s for s, _ in bore.sections if 0 < s < bore.length],
                     *[h.position for h in holes]})
    M = _identity(len(omega))
    for x0, x1 in zip(events[:-1], events[1:]):
        if x0 in hole_at and x0 > 0:
            h, s = hole_at[x0]
            M = _mul(M, tonehole(omega, bore.radius_at(x0), h.radius, h.chimney, s, air))
        if x1 > x0:
            M = _mul(M, cylinder(omega, bore.radius_at(0.5 * (x0 + x1)), x1 - x0, air))
    if bore.length in hole_at:
        h, s = hole_at[bore.length]
        M = _mul(M, tonehole(omega, bore.radius_at(bore.length), h.radius, h.chimney, s, air))
    ZL = radiation_unflanged(omega, bore.radius_at(bore.length), air)
    return (M[0, 0] * ZL + M[0, 1]) / (M[1, 0] * ZL + M[1, 1])


def window_impedance(omega: np.ndarray, window: Window, air: Air) -> np.ndarray:
    """Window as a short open side duct: inertance + radiation resistance.

    Effective length = wall + end corrections of an equivalent circular
    opening on each side; `corr_scale` is the calibration knob.
    """
    k = omega / air.c
    Sw = window.length * window.width
    rw = np.sqrt(Sw / np.pi)
    le = window.corr_scale * (window.wall + 1.7 * rw)
    Zw0 = air.rho * air.c / Sw
    return Zw0 * (1j * k * le + 0.25 * (k * rw) ** 2)


def playing_frequencies(bore: Bore, holes: list[Hole], openness: list[float], window: Window,
                        air: Air = Air(), fmin: float = 200.0, fmax: float = 6000.0,
                        n_registers: int = 3, df: float = 2.0) -> list[float]:
    """Frequencies (Hz) of the first n impedance minima seen by the jet."""

    def Ztot(f):
        om = 2 * np.pi * np.atleast_1d(np.asarray(f, dtype=float))
        return bore_input_impedance(om, bore, holes, openness, air) + window_impedance(om, window, air)

    f = np.arange(fmin, fmax, df)
    Z = Ztot(f)
    mag = np.abs(Z)
    out: list[float] = []
    for i in range(1, len(f) - 1):
        if mag[i] < mag[i - 1] and mag[i] <= mag[i + 1]:
            # Refine on Im(Z) zero crossing (negative -> positive through a minimum).
            lo, hi = f[i - 1], f[i + 1]
            g = lambda x: float(np.imag(Ztot(x))[0])
            try:
                if g(lo) * g(hi) < 0:
                    out.append(brentq(g, lo, hi, xtol=1e-6))
                else:
                    out.append(float(f[i]))
            except ValueError:
                out.append(float(f[i]))
            if len(out) >= n_registers:
                break
    return out
