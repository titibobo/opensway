import numpy as np
from typing import Dict

from .params import Params



def sda_fit(sig: np.ndarray, fs: float, p: Params):
    """
    Returns the diffusion curve (dt, MSD) and the short/long-term
    log-log fits (slope a, intercept b): dt_all, msd, (a_s, b_s), (a_l, b_l)
    """
    N = len(sig)

    # MSD(tau), per axis, for 1/fs <= tau <= T/3 (Quijoux et al., Def. 5)
    max_lag = int(N // 3)
    taus    = np.arange(1, max_lag + 1)
    msd     = np.empty_like(taus, dtype=float)

    for k, tau in enumerate(taus):
        d      = sig[tau:] - sig[:-tau]
        msd[k] = np.mean(d**2)

    dt_all = taus / fs
    valid  = np.isfinite(msd) & (msd > 0)

    def _fit_segment(tau_mask):
        mask = tau_mask & valid
        if np.sum(mask) < 3:
            return np.nan, np.nan, np.inf
        X  = np.log(dt_all[mask])
        Y  = np.log(msd[mask])
        a, b = np.polyfit(X, Y, 1)    # log(MSD) ~ a log(t) + b
        sse  = float(np.sum((Y - (a*X + b))**2))
        return float(a), float(b), sse

    # Breakpoint search inside [sda_tmin ; sda_tmax] s:
    #   short-term fit on [1/fs ; tc], long-term fit on [tc ; T/3],
    #   tc chosen to minimise the total squared error of both log-log fits
    cand   = dt_all[(dt_all >= p.sda_tmin) & (dt_all <= p.sda_tmax)]
    best   = (np.inf, np.nan, np.nan, np.nan, np.nan)

    for tc in cand:
        a_s, b_s, sse_s = _fit_segment(dt_all <= tc)
        a_l, b_l, sse_l = _fit_segment(dt_all >= tc)
        if sse_s + sse_l < best[0]:
            best = (sse_s + sse_l, a_s, b_s, a_l, b_l)

    _, a_s, b_s, a_l, b_l = best

    return dt_all, msd, (a_s, b_s), (a_l, b_l)


def _sda_for_signal(sig: np.ndarray, fs: float, p: Params) -> Dict[str, float]:

    dt_all, msd, (a_s, b_s), (a_l, b_l) = sda_fit(sig, fs, p)

    # MSD ≈ D t^(2H)  ->  H = slope/2 ; D = exp(intercept)   (cm².s^-2H)
    H_short, D_short = a_s / 2.0, np.exp(b_s)
    H_long,  D_long  = a_l / 2.0, np.exp(b_l)

    # Critical point = intersection of both log-log fits, bounded to [1/fs ; T/3]
    Tc, MSDc = np.nan, np.nan
    if np.all(np.isfinite([a_s, b_s, a_l, b_l])) and a_s != a_l:
        log_tc = (b_l - b_s) / (a_s - a_l)
        Tc     = float(np.clip(np.exp(log_tc), dt_all[0], dt_all[-1]))
        MSDc   = float(np.exp(a_s * np.log(Tc) + b_s))

    return {
        'H_short':  round(H_short, 3),
        'H_long':   round(H_long, 3),
        'D_short':  round(D_short, 3),
        'D_long':   round(D_long, 3),
        'Tc':       round(Tc, 2),    # s
        'MSDc':     round(MSDc, 3)   # cm²
    }


def stochastic_metrics(x: np.ndarray, y: np.ndarray, p: Params) -> Dict[str, float]:
    fs = p.target_fs

    sda_ML = _sda_for_signal(x, fs, p)
    sda_AP = _sda_for_signal(y, fs, p)

    return {
        'stc_HurstShortTerm_ML':  sda_ML['H_short'],
        'stc_HurstShortTerm_AP':  sda_AP['H_short'],
        'stc_HurstLongTerm_ML':   sda_ML['H_long'],
        'stc_HurstLongTerm_AP':   sda_AP['H_long'],

        'stc_DiffShortTerm_ML':   sda_ML['D_short'],
        'stc_DiffShortTerm_AP':   sda_AP['D_short'],
        'stc_DiffLongTerm_ML':    sda_ML['D_long'],
        'stc_DiffLongTerm_AP':    sda_AP['D_long'],

        # Critical times & MSD, per axis (Quijoux et al.)
        'stc_critTime_ML':        sda_ML['Tc'],
        'stc_critTime_AP':        sda_AP['Tc'],
        'stc_critMSD_ML':         sda_ML['MSDc'],
        'stc_critMSD_AP':         sda_AP['MSDc']
    }
