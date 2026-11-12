import numpy as np
from typing import Dict

from .params import Params



## Sample Entropy (Richman & Moorman, 2000)
def _sample_entropy(sig: np.ndarray, m: int, r: float) -> float:
    """
    SampEn(m, r) = -ln(A/B)
        B = nb of pairs of templates of length m   matching within r (Chebyshev)
        A = nb of pairs of templates of length m+1 matching within r
    Self-matches excluded; the same N-m templates are used for B and A.
    """
    N = len(sig)
    if N <= m + 1:
        return np.nan

    # Templates of length m+1 (the m first points give the m-length ones)
    idx  = np.arange(N - m)[:, None] + np.arange(m + 1)[None, :]
    tpl  = sig[idx]                                  # (N-m, m+1)

    B, A = 0, 0
    for i in range(len(tpl) - 1):
        d_m  = np.max(np.abs(tpl[i+1:, :m] - tpl[i, :m]), axis=1)
        ok_m = d_m <= r
        B   += int(np.sum(ok_m))
        A   += int(np.sum(ok_m & (np.abs(tpl[i+1:, m] - tpl[i, m]) <= r)))

    if A == 0 or B == 0:
        return np.nan                                # undefined (too few matches)

    return float(-np.log(A / B))


## Detrended Fluctuation Analysis (Peng et al., 1994)
def dfa_curve(sig: np.ndarray, p: Params):
    """
    Fluctuation function F(n) for log-spaced window sizes n (samples),
    from p.dfa_nmin to N/4. The profile is the cumulative sum of the
    centered signal; linear detrending in non-overlapping windows.
    """
    N       = len(sig)
    profile = np.cumsum(sig - np.mean(sig))
    n_max   = N // 4

    if n_max <= p.dfa_nmin:
        return np.array([]), np.array([])

    scales  = np.unique(np.round(np.logspace(np.log10(p.dfa_nmin),
                                             np.log10(n_max), 30)).astype(int))
    F       = np.empty(len(scales))

    for k, n in enumerate(scales):
        nb   = N // n
        segs = profile[:nb * n].reshape(nb, n)
        t    = np.arange(n)
        coef = np.polyfit(t, segs.T, 1)                   # (2, nb)
        fit  = np.outer(coef[0], t) + coef[1][:, None]
        F[k] = np.sqrt(np.mean((segs - fit)**2))

    return scales, F


def _dfa_alphas(sig: np.ndarray, fs: float, p: Params):

    scales, F = dfa_curve(sig, p)
    if len(scales) == 0:
        return np.nan, np.nan

    n_cross   = p.dfa_cross_s * fs
    short     = scales <= n_cross
    long_     = scales >= n_cross

    def _slope(mask):
        if np.sum(mask) < 3:
            return np.nan
        return float(np.polyfit(np.log(scales[mask]), np.log(F[mask]), 1)[0])

    return _slope(short), _slope(long_)


## Recurrence Quantification Analysis (Webber & Zbilut ; Marwan et al., 2007)
def _ami_delay(sig: np.ndarray, max_lag: int, bins: int = 16) -> int:
    """ Time delay = first local minimum of the average mutual information """
    ami = []
    for lag in range(1, max_lag + 1):
        a, b   = sig[:-lag], sig[lag:]
        pab, _, _ = np.histogram2d(a, b, bins=bins)
        pab   /= pab.sum()
        pa, pb = pab.sum(1), pab.sum(0)
        nz     = pab > 0
        ami.append(float(np.sum(pab[nz] * np.log(pab[nz] / np.outer(pa, pb)[nz]))))
        if len(ami) >= 3 and ami[-2] < ami[-3] and ami[-2] <= ami[-1]:
            return lag - 1
    return int(np.argmin(ami) + 1)


def _embed(sig: np.ndarray, m: int, tau: int) -> np.ndarray:
    n = len(sig) - (m - 1) * tau
    return np.column_stack([sig[i*tau : i*tau + n] for i in range(m)])


def _fnn_dim(sig: np.ndarray, tau: int, p: Params) -> int:
    """ Embedding dimension = first m with a false nearest neighbours rate
        below p.rqa_fnn_thr (Kennel et al., 1992 ; Rtol = 15, Atol = 2) """
    sd   = float(np.std(sig))
    best = (np.inf, p.rqa_m_max)

    for m in range(1, p.rqa_m_max):
        emb  = _embed(sig, m + 1, tau)                    # m+1 coord. available
        X, z = emb[:, :m], emb[:, m]
        D    = np.sqrt(((X[:, None, :] - X[None, :, :])**2).sum(-1))
        np.fill_diagonal(D, np.inf)
        nn   = np.argmin(D, axis=1)
        d    = D[np.arange(len(X)), nn]
        dz   = np.abs(z - z[nn])
        ok   = d > 0
        crit1 = dz[ok] / d[ok] > 15.0
        crit2 = np.sqrt(d[ok]**2 + dz[ok]**2) / sd > 2.0
        fnn  = float(np.mean(crit1 | crit2))
        if fnn < p.rqa_fnn_thr:
            return m
        if fnn < best[0]:
            best = (fnn, m)

    return best[1]


def recurrence_matrix(sig: np.ndarray, fs: float, p: Params):
    """ Returns the recurrence matrix (upper triangle), the embedding
        parameters (m, tau) and the Theiler window w (samples) """
    z     = (sig - np.mean(sig)) / np.std(sig)
    tau   = _ami_delay(z, max_lag=int(2 * fs))
    m     = _fnn_dim(z, tau, p)
    emb   = _embed(z, m, tau)

    # Theiler window w: pairs closer than w samples in time are excluded
    #   (temporally correlated neighbours, Marwan 2011) ; w = (m-1).tau
    w     = max(1, (m - 1) * tau)

    D     = np.sqrt(((emb[:, None, :] - emb[None, :, :])**2).sum(-1))
    iu    = np.triu_indices(len(emb), k=w)

    # Radius: fixed recurrence rate (default, van den Hoorn et al., 2020)
    #         or fixed fraction of the mean distance between points
    if p.rqa_mode == "fixed_radius":
        eps = p.rqa_radius * float(np.mean(D[iu]))
    else:
        eps = float(np.quantile(D[iu], p.rqa_rec_rate))

    R     = np.triu(D <= eps, k=w)                        # upper triangle only

    return R, m, tau, w


def _diag_lines(R: np.ndarray, lmin: int, w: int) -> np.ndarray:
    """ Lengths of the diagonal lines (upper triangle, Theiler window excluded) """
    lengths = []
    for k in range(w, len(R)):
        d    = np.concatenate(([0], np.diagonal(R, k).astype(int), [0]))
        edge = np.diff(d)
        L    = np.where(edge == -1)[0] - np.where(edge == 1)[0]
        lengths.extend(L[L >= lmin])
    return np.asarray(lengths, dtype=int)


def _rqa(sig: np.ndarray, fs: float, p: Params) -> Dict[str, float]:

    R, m, tau, w = recurrence_matrix(sig, fs, p)

    n_rec   = int(np.sum(R))
    n_pairs = int(np.sum(np.triu(np.ones_like(R, dtype=bool), k=w)))
    rec     = 100.0 * n_rec / n_pairs if n_pairs > 0 else np.nan
    lines   = _diag_lines(R, p.rqa_lmin, w)

    det     = 100.0 * lines.sum() / n_rec if n_rec > 0 else np.nan
    lmax    = int(lines.max()) if lines.size else 0

    if lines.size:
        _, cnt = np.unique(lines, return_counts=True)
        pl     = cnt / cnt.sum()
        entr   = max(0.0, float(-np.sum(pl * np.log(pl))))
    else:
        entr   = np.nan

    return {'rec': rec, 'det': det, 'lmax': lmax, 'entr': entr, 'm': m, 'tau_s': tau / fs}


## MAIN FUNCTION: Nonlinear metrics
def nonlinear_metrics(x_c: np.ndarray, y_c: np.ndarray, p: Params) -> Dict[str, float]:

    m = int(p.sampen_m)

    # Signal analysed: COP increments (stationary) or COP positions
    if p.sampen_increments:
        sx, sy = np.diff(x_c), np.diff(y_c)
    else:
        sx, sy = x_c, y_c

    # Tolerance r relative to the SD of the analysed signal
    r_x    = p.sampen_r * float(np.std(sx, ddof=1))
    r_y    = p.sampen_r * float(np.std(sy, ddof=1))

    ML_sampen = _sample_entropy(sx, m, r_x)
    AP_sampen = _sample_entropy(sy, m, r_y)

    # DFA on COP positions
    fs = p.target_fs
    ML_dfa_s, ML_dfa_l = _dfa_alphas(x_c, fs, p)
    AP_dfa_s, AP_dfa_l = _dfa_alphas(y_c, fs, p)

    # RQA on COP positions, per axis
    rqa_ML = _rqa(x_c, fs, p)
    rqa_AP = _rqa(y_c, fs, p)

    return {
        # Sample entropy
        'nl_sampEn_ML':           round(ML_sampen,3),
        'nl_sampEn_AP':           round(AP_sampen,3),
        # DFA scaling exponents
        'nl_dfaAlphaShort_ML':    round(ML_dfa_s,3),
        'nl_dfaAlphaShort_AP':    round(AP_dfa_s,3),
        'nl_dfaAlphaLong_ML':     round(ML_dfa_l,3),
        'nl_dfaAlphaLong_AP':     round(AP_dfa_l,3),
        # RQA
        'nl_rqaRec_ML':           round(rqa_ML['rec'],2),
        'nl_rqaRec_AP':           round(rqa_AP['rec'],2),
        'nl_rqaDet_ML':           round(rqa_ML['det'],2),
        'nl_rqaDet_AP':           round(rqa_AP['det'],2),
        'nl_rqaLmax_ML':          rqa_ML['lmax'],
        'nl_rqaLmax_AP':          rqa_AP['lmax'],
        'nl_rqaEntr_ML':          round(rqa_ML['entr'],3),
        'nl_rqaEntr_AP':          round(rqa_AP['entr'],3),
        'nl_rqaDim_ML':           rqa_ML['m'],
        'nl_rqaDim_AP':           rqa_AP['m'],
        'nl_rqaDelay_ML':         round(rqa_ML['tau_s'],2),
        'nl_rqaDelay_AP':         round(rqa_AP['tau_s'],2)
    }
