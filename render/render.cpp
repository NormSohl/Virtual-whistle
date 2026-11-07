// Offline renderer: config + control script -> mono 32-bit float WAV.
//
//   render config.txt control.csv out.wav
//
// config.txt: key = value lines (see keys below). Lengths in millimetres.
// control.csv: header "t,o1,...,oN,breath" then rows (N = number of o columns,
// up to 9, and must match num_holes); values are linearly interpolated between rows. o = hole openness 0 (closed) .. 1 (open),
// breath 0..1 of max mouth pressure.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <map>
#include <sstream>
#include <string>
#include <vector>

#include "../dsp/whistle.hpp"

namespace {

std::map<std::string, double> readConfig(const char* path) {
    std::map<std::string, double> m;
    std::ifstream f(path);
    std::string line;
    while (std::getline(f, line)) {
        auto hash = line.find('#');
        if (hash != std::string::npos) line = line.substr(0, hash);
        auto eq = line.find('=');
        if (eq == std::string::npos) continue;
        std::string k = line.substr(0, eq), v = line.substr(eq + 1);
        auto trim = [](std::string& s) {
            s.erase(0, s.find_first_not_of(" \t\r"));
            s.erase(s.find_last_not_of(" \t\r") + 1);
        };
        trim(k);
        trim(v);
        if (!k.empty()) m[k] = std::atof(v.c_str());
    }
    return m;
}

struct Row {
    double t;
    float o[vw::kMaxHoles];
    float breath;
};

std::vector<Row> readControl(const char* path, int& nCols) {
    std::vector<Row> rows;
    std::ifstream f(path);
    std::string line;
    std::getline(f, line);  // header: count the o columns
    nCols = 0;
    {
        std::stringstream hs(line);
        std::string cell;
        while (std::getline(hs, cell, ','))
            if (!cell.empty() && cell[0] == 'o') ++nCols;
    }
    if (nCols > vw::kMaxHoles) nCols = vw::kMaxHoles;
    while (std::getline(f, line)) {
        if (line.empty()) continue;
        std::stringstream ss(line);
        std::string cell;
        Row r{};
        std::getline(ss, cell, ',');
        r.t = std::atof(cell.c_str());
        for (int i = 0; i < nCols; ++i) {
            std::getline(ss, cell, ',');
            r.o[i] = float(std::atof(cell.c_str()));
        }
        std::getline(ss, cell, ',');
        r.breath = float(std::atof(cell.c_str()));
        rows.push_back(r);
    }
    return rows;
}

void writeWav(const char* path, const std::vector<float>& x, int sr) {
    FILE* f = std::fopen(path, "wb");
    if (!f) {
        std::perror(path);
        std::exit(1);
    }
    const uint32_t dataBytes = uint32_t(x.size() * 4);
    auto u32 = [&](uint32_t v) { std::fwrite(&v, 4, 1, f); };
    auto u16 = [&](uint16_t v) { std::fwrite(&v, 2, 1, f); };
    std::fwrite("RIFF", 1, 4, f);
    u32(36 + dataBytes);
    std::fwrite("WAVEfmt ", 1, 8, f);
    u32(16);
    u16(3);  // IEEE float
    u16(1);
    u32(uint32_t(sr));
    u32(uint32_t(sr) * 4);
    u16(4);
    u16(32);
    std::fwrite("data", 1, 4, f);
    u32(dataBytes);
    std::fwrite(x.data(), 4, x.size(), f);
    std::fclose(f);
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 4) {
        std::fprintf(stderr, "usage: %s config.txt control.csv out.wav\n", argv[0]);
        return 2;
    }
    auto cfg = readConfig(argv[1]);
    auto get = [&](const char* k, double def) { return cfg.count(k) ? cfg[k] : def; };
    const double mm = 1e-3;

    vw::Geometry g;
    g.boreRadius = float(get("bore_diameter", 11.8) / 2 * mm);
    g.length = float(get("length", 263.4) * mm);
    g.numHoles = int(get("num_holes", 6));
    for (int i = 0; i < g.numHoles && i < vw::kMaxHoles; ++i) {
        char key[32];
        std::snprintf(key, sizeof key, "hole%d_pos", i + 1);
        g.holePos[i] = float(get(key, 0) * mm);
        std::snprintf(key, sizeof key, "hole%d_dia", i + 1);
        g.holeRadius[i] = float(get(key, 6) / 2 * mm);
        std::snprintf(key, sizeof key, "hole%d_wall", i + 1);
        g.chimney[i] = float(get(key, 0.4) * mm);
    }
    g.windowLength = float(get("window_length", 5.0) * mm);
    g.windowWidth = float(get("window_width", 7.7) * mm);
    g.windowWall = float(get("window_wall", 2.0) * mm);
    g.windowScale = float(get("window_scale", 1.0));

    vw::Settings s;
    s.sampleRate = float(get("sample_rate", 96000));
    s.tempC = float(get("temp_c", 30));
    s.dispersion = float(get("dispersion", s.dispersion));
    s.footLoss = float(get("foot_loss", s.footLoss));
    s.jetRatio = float(get("jet_ratio", s.jetRatio));
    s.jetReflection = float(get("jet_reflection", s.jetReflection));
    s.jetGain = float(get("jet_gain", s.jetGain));
    s.noiseGain = float(get("noise_gain", s.noiseGain));
    s.jetOffset = float(get("jet_offset", s.jetOffset));
    s.jetModel = int(get("jet_model", s.jetModel));
    s.jetStrouhal = float(get("jet_strouhal", s.jetStrouhal));
    s.jetLpOrder = int(get("jet_lp_order", s.jetLpOrder));
    s.lossRefHz = float(get("loss_ref_hz", s.lossRefHz));
    s.vortexLoss = float(get("vortex_loss", s.vortexLoss));
    s.levelComp = float(get("level_comp", s.levelComp));
    s.radiation = get("radiation", 1) != 0;
    s.jetDelayRise = float(get("jet_delay_rise", s.jetDelayRise));
    s.jetCutoffHz = float(get("jet_cutoff_hz", s.jetCutoffHz));
    s.maxPressurePa = float(get("max_pressure_pa", s.maxPressurePa));

    int nCols = 0;
    auto rows = readControl(argv[2], nCols);
    if (nCols != g.numHoles) {
        std::fprintf(stderr, "control file has %d hole columns, config has num_holes = %d\n", nCols, g.numHoles);
        return 2;
    }
    if (rows.size() < 2) {
        std::fprintf(stderr, "control file needs at least two rows\n");
        return 2;
    }

    static vw::Whistle w;  // large: keep off the stack
    w.init(g, s);

    const int sr = int(s.sampleRate);
    const double dur = rows.back().t;
    const size_t n = size_t(dur * sr);
    std::vector<float> out(n);
    const int block = 32;  // control-rate updates, like a real-time callback
    size_t r = 0;
    // Breath at control rate (every 32 samples); hole openness every sample, because a hole's filter
    // changes fastest in the last per cent of closing and coarse steps there click (2026-11-07).
    for (size_t i = 0; i < n; ++i) {
        const double t = double(i) / sr;
        while (r + 1 < rows.size() - 1 && rows[r + 1].t <= t) ++r;
        const Row& A = rows[r];
        const Row& B = rows[r + 1];
        const double span = B.t - A.t;
        const float u = span > 0 ? float((t - A.t) / span) : 0.f;
        const float uc = u < 0 ? 0 : (u > 1 ? 1 : u);
        for (int h = 0; h < nCols; ++h) w.setOpenness(h, A.o[h] + (B.o[h] - A.o[h]) * uc);
        if (i % block == 0) w.setBreath(A.breath + (B.breath - A.breath) * uc);
        out[i] = w.process();
    }
    // Normalize peak to -3 dBFS so files are comfortable to listen to.
    float peak = 1e-9f;
    for (float v : out) peak = std::fabs(v) > peak ? std::fabs(v) : peak;
    const float gain = 0.707f / peak;
    for (float& v : out) v *= gain;
    writeWav(argv[3], out, sr);
    std::fprintf(stderr, "wrote %s: %.2f s at %d Hz, c_eff %.1f m/s, peak before normalise %.3g\n", argv[3], dur, sr,
                 w.speedOfSound(), peak);
    return 0;
}
