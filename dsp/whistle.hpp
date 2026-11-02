// virtual-whistle: real-time physical model of a six-hole whistle.
//
// Digital waveguide bore (pressure waves, both directions) split into
// segments at each tonehole. Each tonehole is a shunt-admittance scattering
// junction whose filter is derived from the same acoustics as the impedance
// model (acoustics/tmm.py): open hole = inertance, closed hole = compliance,
// partly open = both in parallel. The foot radiates as an unflanged pipe;
// the window end reflects through the window inertance; the jet is an
// STK-style delayed nonlinear feedback driven by breath pressure.
//
// Portable C++17, header-only, no heap allocation and no locks after
// construction. Same source runs offline (render/) and on the Daisy Seed3.
#pragma once

#include <array>
#include <cmath>
#include <cstdint>

namespace vw {

constexpr float kPi = 3.14159265358979323846f;

// ------------------------------------------------------------- delay line

// Power-of-two ring buffer with 3rd-order Lagrange fractional read.
template <int N>
class DelayLine {
    static_assert((N & (N - 1)) == 0, "N must be a power of two");

public:
    void clear() {
        buf_.fill(0.f);
        w_ = 0;
    }
    void write(float x) {
        buf_[w_] = x;
        w_ = (w_ + 1) & (N - 1);
    }
    // Delay in samples, measured from the most recent write; must be >= 2.
    float read(float d) const {
        if (d < 2.f) d = 2.f;
        if (d > float(N - 3)) d = float(N - 3);
        const int di = int(d);
        const float f = d - float(di);  // 0..1
        // Taps at delays di-1, di, di+1, di+2; fractional position D = f + 1 in [1, 2).
        const float D = f + 1.f;
        const float h0 = -(D - 1.f) * (D - 2.f) * (D - 3.f) / 6.f;
        const float h1 = D * (D - 2.f) * (D - 3.f) / 2.f;
        const float h2 = -D * (D - 1.f) * (D - 3.f) / 2.f;
        const float h3 = D * (D - 1.f) * (D - 2.f) / 6.f;
        return h0 * tap(di - 1) + h1 * tap(di) + h2 * tap(di + 1) + h3 * tap(di + 2);
    }

private:
    float tap(int delay) const { return buf_[(w_ - delay) & (N - 1)]; }
    std::array<float, N> buf_{};
    int w_ = 0;
};

// ------------------------------------------------------------- biquad

// Biquad designed from an analog prototype
//   H(s) = (b0 + b1 s + b2 s^2) / (a0 + a1 s + a2 s^2)
// via the bilinear transform. Coefficients can change while state is kept.
class Biquad {
public:
    void setAnalog(double b0, double b1, double b2, double a0, double a1, double a2, double fs) {
        const double K = 2.0 * fs, K2 = K * K;
        if (b2 == 0.0 && a2 == 0.0) {
            // First-order prototype: transform it as first order, otherwise the
            // biquad form adds a cancelling pole/zero pair at Nyquist that is
            // numerically marginal.
            const double A0 = a0 + a1 * K;
            nb0_ = float((b0 + b1 * K) / A0);
            nb1_ = float((b0 - b1 * K) / A0);
            nb2_ = 0.f;
            na1_ = float((a0 - a1 * K) / A0);
            na2_ = 0.f;
            return;
        }
        const double B0 = b0 + b1 * K + b2 * K2, B1 = 2 * b0 - 2 * b2 * K2, B2 = b0 - b1 * K + b2 * K2;
        const double A0 = a0 + a1 * K + a2 * K2, A1 = 2 * a0 - 2 * a2 * K2, A2 = a0 - a1 * K + a2 * K2;
        nb0_ = float(B0 / A0);
        nb1_ = float(B1 / A0);
        nb2_ = float(B2 / A0);
        na1_ = float(A1 / A0);
        na2_ = float(A2 / A0);
    }
    float process(float x) {  // transposed direct form II
        const float y = nb0_ * x + s1_;
        s1_ = nb1_ * x - na1_ * y + s2_;
        s2_ = nb2_ * x - na2_ * y;
        return y;
    }
    void reset() { s1_ = s2_ = 0.f; }

private:
    float nb0_ = 1, nb1_ = 0, nb2_ = 0, na1_ = 0, na2_ = 0;
    float s1_ = 0, s2_ = 0;
};

// One-pole DC blocker for the output.
class DcBlock {
public:
    float process(float x) {
        const float y = x - x1_ + 0.995f * y1_;
        x1_ = x;
        y1_ = y;
        return y;
    }

private:
    float x1_ = 0, y1_ = 0;
};

// ------------------------------------------------------------- geometry

constexpr int kHoles = 6;

struct Geometry {
    // Positions in metres measured from the window (top of the bore) toward the foot.
    float boreRadius = 0.0059f;
    float length = 0.2634f;  // window to foot
    std::array<float, kHoles> holePos{};     // hole centres, hole 1 nearest the window
    std::array<float, kHoles> holeRadius{};
    std::array<float, kHoles> chimney{};     // wall thickness at the hole
    float windowLength = 0.005f;             // along the axis
    float windowWidth = 0.0077f;
    float windowWall = 0.002f;
    float windowScale = 1.0f;                // calibration on the window inertance
};

struct Settings {
    float sampleRate = 96000.f;
    float tempC = 30.f;
    float dispersion = 0.991f;   // boundary-layer slowing of sound in the bore (c_eff = c * dispersion)
    float footLoss = 0.985f;     // broadband loss per foot reflection (wall losses lumped)
    float jetRatio = 2.0f;       // scales jet travel time (window length / convection speed)
    float jetReflection = 0.5f;  // how strongly the returning bore wave acts on the jet
    float jetGain = 1.0f;
    float noiseGain = 0.03f;
    int jetModel = 0;            // 0 = STK-style (default), 1 = experimental deflection/tanh
    float jetOffset = 0.15f;     // labium offset (experimental jet only)
    float jetCutoffHz = 8000.f;  // jet drive lowpass
    float maxPressurePa = 1500.f; // breath 1.0 corresponds to this mouth pressure
};

// ------------------------------------------------------------- model

class Whistle {
public:
    static constexpr int kDelayN = 4096;

    void init(const Geometry& g, const Settings& s) {
        g_ = g;
        s_ = s;
        c_ = 331.3f * std::sqrt((s.tempC + 273.15f) / 273.15f) * s.dispersion;
        rho_ = 1.2041f * 293.15f / (s.tempC + 273.15f);

        // Segment boundaries: window, hole 1..6, foot.
        float x[kHoles + 2];
        x[0] = 0.f;
        for (int i = 0; i < kHoles; ++i) x[i + 1] = g.holePos[i];
        x[kHoles + 1] = g.length;
        for (int k = 0; k < kHoles + 1; ++k) segDelay_[k] = (x[k + 1] - x[k]) / c_ * s.sampleRate;

        for (auto& d : right_) d.clear();
        for (auto& d : left_) d.clear();
        jetDelay_.clear();
        for (auto& h : holeFilt_) h.reset();
        windowFilt_.reset();
        footFilt_.reset();

        designWindow();
        designFoot();
        for (int i = 0; i < kHoles; ++i) setOpenness(i, 0.f, true);
        noise_ = 22222u;
        jetLp_ = 0.f;
        jetLpCoef_ = 1.f - std::exp(-2.f * kPi * s.jetCutoffHz / s.sampleRate);
    }

    // 0 = closed by a finger, 1 = fully open. Cheap enough to call every block.
    void setOpenness(int hole, float o, bool force = false) {
        o = o < 0.f ? 0.f : (o > 1.f ? 1.f : o);
        if (!force && std::fabs(o - open_[hole]) < 1e-4f) return;
        open_[hole] = o;
        designHole(hole);
    }

    // Breath 0..1 (fraction of maxPressurePa).
    void setBreath(float b) { breath_ = b < 0.f ? 0.f : b; }

    float process() {
        const float fs = s_.sampleRate;

        // Read every wave arriving at a boundary this sample.
        float rOut[kHoles + 1], lOut[kHoles + 1];
        for (int k = 0; k < kHoles + 1; ++k) {
            rOut[k] = right_[k].read(segDelay_[k]);
            lOut[k] = left_[k].read(segDelay_[k]);
        }

        // Window end: wave returning from the bore, reflected through the
        // window inertance, plus the jet's contribution.
        const float aTop = lOut[0];
        const float pressurePa = breath_ * s_.maxPressurePa;
        const float ujet = std::sqrt(2.f * pressurePa / rho_);           // jet speed, m/s
        const float convect = 0.5f * (ujet > 1e-3f ? ujet : 1e-3f);      // jet disturbance speed
        float jetDelaySamples = s_.jetRatio * (g_.windowLength / convect) * fs;
        jetDelaySamples = jetDelaySamples < 2.f ? 2.f : (jetDelaySamples > 2000.f ? 2000.f : jetDelaySamples);

        float jet;
        if (s_.jetModel == 0) {
            // STK-style flute jet (Cook): breath minus the returning bore wave
            // passes through the jet delay and a cubic nonlinearity. Breath sets
            // the operating point and, through jet speed, the delay.
            const float pd = breath_ * (1.f + s_.noiseGain * white()) - s_.jetReflection * aTop;
            jetDelay_.write(pd);
            float jx = jetDelay_.read(jetDelaySamples);
            jx = jx > 1.f ? 1.f : (jx < -1.f ? -1.f : jx);
            jet = s_.jetGain * (jx * jx * jx - jx);
        } else {
            // Experimental: deflection from the window flow, tanh labium split,
            // drive ~ jet speed. Not yet stable on the long fingerings.
            const float deflect = -s_.jetReflection * aTop + s_.noiseGain * white();
            jetDelay_.write(deflect);
            const float jx = jetDelay_.read(jetDelaySamples);
            jet = s_.jetGain * std::sqrt(breath_) * std::tanh(jx + s_.jetOffset);
        }
        // Jets only amplify over a limited band; one-pole lowpass on the drive.
        jetLp_ += jetLpCoef_ * (jet - jetLp_);
        jet = jetLp_;
        const float pTopOut = windowFilt_.process(aTop) + jet;
        right_[0].write(pTopOut);

        // Toneholes: shunt junction between segment k-1 and segment k.
        for (int i = 0; i < kHoles; ++i) {
            const float a = rOut[i];      // arriving from the window side
            const float b = lOut[i + 1];  // arriving from the foot side
            const float pJ = holeFilt_[i].process(a + b);
            left_[i].write(pJ - a);
            right_[i + 1].write(pJ - b);
        }

        // Foot: unflanged radiation reflectance with lumped losses.
        left_[kHoles].write(s_.footLoss * footFilt_.process(rOut[kHoles]));

        // Radiated sound ~ rate of change of window pressure.
        const float pWin = aTop + pTopOut;
        const float out = dc_.process(pWin - lastWin_);
        lastWin_ = pWin;
        return out;
    }

    float speedOfSound() const { return c_; }

private:
    void designHole(int i) {
        // Junction transfer pJ/(a+b) = 1 / (1 + Ys/(2 Y0)), Ys from open/closed parts.
        const double o = open_[i];
        const double a = g_.boreRadius, b = g_.holeRadius[i], t = g_.chimney[i];
        const double Sb = kPi * a * a, Sh = kPi * b * b;
        const double delta = b / a;
        auto ti = [&](double br) {
            const double d = br / a;
            return br * (0.82 - 0.193 * d - 1.09 * d * d + 1.27 * d * d * d - 0.71 * d * d * d * d);
        };
        const double tauC = (Sh / Sb) * (t + ti(b)) / c_;  // closed: Ys/Y0 = s tauC
        (void)delta;
        if (o <= 1e-4) {
            holeFilt_[i].setAnalog(1, 0, 0, 1, tauC / 2.0, 0, s_.sampleRate);
            return;
        }
        const double bo = b * std::sqrt(o);
        const double So = kPi * bo * bo;
        const double te = t + ti(bo) + 0.61 * bo;
        const double tauO = (Sb / So) * te / c_;            // open part: Zs/Z0 = s tauO
        // H = 2 s tauO / (o' + 2 s tauO + (1-o) s^2 tauC tauO), with o' = 1 (open part already scaled by area)
        const double closedPart = (1.0 - o) * tauC * tauO;
        holeFilt_[i].setAnalog(0, 2 * tauO, 0, 1, 2 * tauO, closedPart, s_.sampleRate);
    }

    void designWindow() {
        // Top end reflectance R = (Zw - Z0)/(Zw + Z0), Zw/Z0 = s tauW.
        const double Sb = kPi * g_.boreRadius * g_.boreRadius;
        const double Sw = g_.windowLength * g_.windowWidth;
        const double rw = std::sqrt(Sw / kPi);
        const double le = g_.windowScale * (g_.windowWall + 1.7 * rw);
        const double tauW = (Sb / Sw) * le / c_;
        windowFilt_.setAnalog(-1, tauW, 0, 1, tauW, 0, s_.sampleRate);
    }

    void designFoot() {
        // Unflanged pipe reflectance, low-frequency fit:
        //   |R| ~ 1 - (ka)^2/2  -> one-pole lowpass with time constant a/c
        //   phase ~ end correction 0.6133 a -> round-trip delay 1.2266 a/c, split between
        //   the lowpass (a/c) and a first-order allpass (2 tauA).
        const double a = g_.boreRadius;
        const double tl = a / c_;
        const double tauA = 0.1133 * a / c_;
        // R = -(1 - s tauA) / ((1 + s tauA)(1 + s tl))
        footFilt_.setAnalog(-1, tauA, 0, 1, tauA + tl, tauA * tl, s_.sampleRate);
    }

    float white() {  // xorshift, -1..1
        noise_ ^= noise_ << 13;
        noise_ ^= noise_ >> 17;
        noise_ ^= noise_ << 5;
        return float(noise_) * (2.f / 4294967295.f) - 1.f;
    }

    Geometry g_;
    Settings s_;
    float c_ = 343.f, rho_ = 1.2f;
    std::array<DelayLine<kDelayN>, kHoles + 1> right_{}, left_{};
    std::array<float, kHoles + 1> segDelay_{};
    std::array<Biquad, kHoles> holeFilt_{};
    std::array<float, kHoles> open_{};
    Biquad windowFilt_, footFilt_;
    DelayLine<kDelayN> jetDelay_;
    DcBlock dc_;
    float breath_ = 0.f, lastWin_ = 0.f;
    float jetLp_ = 0.f, jetLpCoef_ = 0.f;
    uint32_t noise_ = 22222u;
};

}  // namespace vw
