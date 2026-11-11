import numpy as np
from typing import Dict

from .params import Params



def _sda_for_signal(sig: np.ndarray, fs: float) -> Dict[str, float]:
    N = len(sig)

    # MSD(tau)
    max_lag = int(min(N // 4, fs * 5))  # jusqu'à ≈5 s
    taus    = np.arange(1, max_lag + 1)
    msd     = np.empty_like(taus, dtype=float)

    for k, tau in enumerate(taus):
        d      = sig[tau:] - sig[:-tau]
        msd[k] = np.mean(d**2)

    def _fit_segment(tau_mask):
        mask = tau_mask & np.isfinite(msd) & (msd > 0)
        if np.sum(mask) < 2:
            return np.nan, np.nan
        dt = taus[mask] / fs
        X  = np.log(dt)
        Y  = np.log(msd[mask])
        a, b = np.polyfit(X, Y, 1)    # log(MSD) ~ a log(t) + b
        H = a / 2.0
        D = np.exp(b)                 # MSD ≈ D t^(2H)
        return float(D), float(H)

    # short-term ≤ 1 s, long-term ≥ 1.5 s (exemple Quijoux-like)
    short_mask = (taus / fs) <= 1.0
    long_mask  = (taus / fs) >= 1.5

    D_short, H_short = _fit_segment(short_mask)
    D_long,  H_long  = _fit_segment(long_mask)

    Tc, MSDc = np.nan, np.nan
    if np.all(np.isfinite([D_short, H_short, D_long, H_long])):
        denom = 2.0 * (H_long - H_short)
        if denom != 0 and D_short > 0 and D_long > 0:
            Tc = (D_short / D_long) ** (1.0 / denom)
            if Tc > 0:
                MSDc = D_short * (Tc ** (2.0 * H_short))

    return {
        'H_short':  round(H_short, 3),
        'H_long':   round(H_long, 3),
        'D_short':  round(D_short, 3),
        'D_long':   round(D_long, 3),
        'Tc':       round(Tc, 2),    # s
        'MSDc':     round(MSDc, 2)   # cm²
    }


def stochastic_metrics(x: np.ndarray, y: np.ndarray, p: Params) -> Dict[str, float]:
    fs = p.target_fs

    sda_ML = _sda_for_signal(x, fs)
    sda_AP = _sda_for_signal(y, fs)

    R      = np.sqrt(x**2 + y**2)
    sda_R  = _sda_for_signal(R, fs)

    return {
        'stc_HurstShortTerm_ML':  sda_ML['H_short'],
        'stc_HurstShortTerm_AP':  sda_AP['H_short'],
        'stc_HurstLongTerm_ML':   sda_ML['H_long'],
        'stc_HurstLongTerm_AP':   sda_AP['H_long'],

        'stc_DiffShortTerm_ML':   sda_ML['D_short'],
        'stc_DiffShortTerm_AP':   sda_AP['D_short'],
        'stc_DiffLongTerm_ML':    sda_ML['D_long'],
        'stc_DiffLongTerm_AP':    sda_AP['D_long'],

        # Radial – global transition times
        'stc_transTime_radial':   sda_R['Tc'],
        'stc_MSD_radial':         sda_R['MSDc']
    }