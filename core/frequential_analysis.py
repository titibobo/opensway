import numpy as np
from scipy.signal import welch
from typing import Dict

from .params import Params


def _safe_welch(sig: np.ndarray, fs: float, fmax: float, seg_seconds: float):

    N = len(sig)

    if N < 16:
        return np.array([0.0]), np.array([np.nan])
    
    nper  = int(round(seg_seconds * fs))
    nper  = max(64, min(N, nper))
    nover = nper // 2

    f, Pxx = welch(sig, fs=fs, window="hann",
                   nperseg=nper, noverlap=nover,
                   detrend=False, scaling="density", average="mean")
    
    if fmax is not None:
        mask   = f <= min(fmax, 0.5*fs)
        f, Pxx = f[mask], Pxx[mask]

    return f, Pxx

# Public function creation (for import in other py scripts)
def welch_psd(sig: np.ndarray, p: Params):
    return _safe_welch(sig, p.target_fs, p.fmax, p.seg_seconds)


def _spectral_features(f: np.ndarray, Pxx: np.ndarray) -> Dict[str, float]:

    # Total power = PSD integral (cm²)
    total_power = float(np.trapezoid(Pxx, f))

    # Power mode (maximmal PSD frequency)
    idx_max     = int(np.nanargmax(Pxx))
    power_mode  = float(f[idx_max])

    # Spectral moments M1, M2
    M1 = float(np.trapezoid(f * Pxx, f))
    M2 = float(np.trapezoid((f**2) * Pxx, f))

    centroid  = M1 / total_power                  # CENTROIDAL FREQ
    freq_disp = np.nan
    if M2 > 0:
        # Quijoux :  1 - (M1²) / (M2 * total_power)    (n.u.)
        freq_disp = 1.0 - (M1**2) / (M2 * total_power)

    # CDF for 50%, 80%, 95% power frequencies
    incr  = (Pxx[:-1] + Pxx[1:]) * 0.5 * np.diff(f)
    cdf   = np.concatenate([[0.0], np.cumsum(incr)])
    total = float(cdf[-1])


    def _percentile(alpha: float) -> float:
        target = alpha * total
        idx    = int(np.clip(np.searchsorted(cdf, target) - 1, 0, len(f)-2))

        x0, x1 = cdf[idx], cdf[idx+1]
        y0, y1 = f[idx],   f[idx+1]
        ratio  = 0.0 if x1 == x0 else (target - x0) / (x1 - x0)

        return float(y0 + ratio * (y1 - y0))

    f50 = _percentile(0.5)   # 50% power freq.
    f80 = _percentile(0.8)
    f95 = _percentile(0.95)  # 95% power freq.


    # Band energies (cm²) – Quijoux : 0–0.5, 0.5–2, >2
    def _band_energy(fmin, fmax):
        mask = (f >= fmin) & (f <= fmax)
        if not np.any(mask):
            return 0.0
        return float(np.trapezoid(Pxx[mask], f[mask]))

    E_0_0p5 = _band_energy(0.0, 0.5)
    E_0p5_2 = _band_energy(0.5, 2.0)
    E_2_5   = _band_energy(2.0, 5.0)

    denom = E_0_0p5 + E_0p5_2
    freq_quotient = float(E_2_5 / denom)

    return {
        'total_power':   round(total_power, 3),
        'power_mode':    round(power_mode, 3),
        'centroid_freq': round(centroid, 3),
        'f50':           round(f50, 3),
        'f80':           round(f80, 3),
        'f95':           round(f95, 3),
        'freq_disp':     round(freq_disp, 3),
        'E_0_0p5':       round(E_0_0p5, 3),
        'E_0p5_2':       round(E_0p5_2, 3),
        'E_2_5':         round(E_2_5, 3),
        'freq_quotient': round(freq_quotient, 2)
    }


## MAIN FUNCTION: Frequential metrics
def frequency_metrics(x: np.ndarray, y: np.ndarray, p: Params) -> Dict[str, float]:

    fs         = p.target_fs
    
    f_x, Pxx_x = _safe_welch(x, fs, p.fmax, p.seg_seconds)
    feat_x     = _spectral_features(f_x, Pxx_x)

    f_y, Pxx_y = _safe_welch(y, fs, p.fmax, p.seg_seconds)
    feat_y     = _spectral_features(f_y, Pxx_y)

    return {
        # Total powers
        'frq_total_power_ML':    feat_x['total_power'],
        'frq_total_power_AP':    feat_y['total_power'],
        # Power modes
        'frq_power_mode_ML':     feat_x['power_mode'],
        'frq_power_mode_AP':     feat_y['power_mode'],
        # Percentiles, centroid, quotient
        'frq_f50_ML':            feat_x['f50'],
        'frq_f50_AP':            feat_y['f50'],
        'frq_f95_ML':            feat_x['f95'],
        'frq_f95_AP':            feat_y['f95'],
        'frq_centroid_freq_ML':  feat_x['centroid_freq'],
        'frq_centroid_freq_AP':  feat_y['centroid_freq'],
        'frq_freq_disp_ML':      feat_x['freq_disp'],
        'frq_freq_disp_AP':      feat_y['freq_disp'],
        # Band energies
        'frq_energy_0_05_ML':    feat_x['E_0_0p5'],
        'frq_energy_0_05_AP':    feat_y['E_0_0p5'],
        'frq_energy_05_2_ML':    feat_x['E_0p5_2'],
        'frq_energy_05_2_AP':    feat_y['E_0p5_2'],
        'frq_energy_2_5_ML':     feat_x['E_2_5'],
        'frq_energy_2_5_AP':     feat_y['E_2_5'],
        'frq_freq_quotient_ML':  feat_x['freq_quotient'],
        'frq_freq_quotient_AP':  feat_y['freq_quotient']
    }