import numpy as np
from scipy.signal import savgol_filter, find_peaks
from typing import Dict

from .params import Params


## Distances calculations
def _timedep_calc(dx:np.ndarray, dy:np.ndarray, ellipse_area:float):

    # Distances calculations per axis (cm)
    ML_length         = float(np.sum(np.abs(dx)))
    AP_length         = float(np.sum(np.abs(dy)))

    GLOBAL_length_vec = np.sqrt(dx**2 + dy**2)
    GLOBAL_length     = float(np.sum(GLOBAL_length_vec))

    # LFS (n.u.)
    lfs = GLOBAL_length/ellipse_area if ellipse_area >0 else np.nan

    return ML_length, AP_length, GLOBAL_length, lfs

## Velocities calculations per axis
def _veloc_calc(vx:np.ndarray, vy:np.ndarray):

    # Velocities calculations per axes (cm/s)
    ML_veloc          = np.abs(vx)
    AP_veloc          = np.abs(vy)
    GLOBAL_veloc      = np.sqrt(vx**2 + vy**2)

    # Mean and SD velocities (cm/s)
    ML_mean_veloc     = float(np.mean(ML_veloc))
    ML_SD_veloc       = float(np.std(ML_veloc, ddof=1))

    AP_mean_veloc     = float(np.mean(AP_veloc))
    AP_SD_veloc       = float(np.std(AP_veloc, ddof=1))

    GLOBAL_mean_veloc = float(np.mean(GLOBAL_veloc))
    GLOBAL_SD_veloc   = float(np.std(GLOBAL_veloc, ddof=1))

    return ML_mean_veloc, ML_SD_veloc,  \
            AP_mean_veloc, AP_SD_veloc, \
            GLOBAL_mean_veloc, GLOBAL_SD_veloc

## Temporal frequencies calculations
def _temporal_frequencies(x: np.ndarray, y: np.ndarray, vx: np.ndarray, vy: np.ndarray):

    ML_mean_dist        = float(np.mean(np.abs(x)))
    AP_mean_dist        = float(np.mean(np.abs(y)))
    R                   = np.sqrt(x**2 + y**2)
    mean_dist_rad       = float(np.mean(np.abs(R)))

    # Mean frequencies (Hz)
    ML_veloc            = np.abs(vx)
    ML_mean_veloc       = float(np.mean(ML_veloc))
    ML_dyn_meanfreq     = ML_mean_veloc/ML_mean_dist if ML_mean_dist >0 else np.nan

    AP_veloc            = np.abs(vy)
    AP_mean_veloc       = float(np.mean(AP_veloc))
    AP_dyn_meanfreq     = AP_mean_veloc/AP_mean_dist if AP_mean_dist >0 else np.nan
    
    GLOBAL_veloc        = np.sqrt(vx**2 + vy**2)
    GLOBAL_mean_veloc   = float(np.mean(GLOBAL_veloc))
    GLOBAL_dyn_meanfreq = GLOBAL_mean_veloc/mean_dist_rad if mean_dist_rad >0 else np.nan

    return ML_dyn_meanfreq, AP_dyn_meanfreq, GLOBAL_dyn_meanfreq

## Zero-crossings calculations
def _zero_cross_computing(v: np.ndarray) -> int:

    s = np.sign(v)
    
    for i in range(1, len(s)):
        if s[i] == 0:
            s[i] = s[i-1]

    zero_cross = int(np.sum(s[:-1] * s[1:] < 0))

    return zero_cross

## Velocity peaks calculations
def _vel_peaks_computing(v: np.ndarray):

    s = np.sign(v)

    for i in range(1, len(s)):
        if s[i] == 0:
            s[i] = s[i-1]

    cuts         = np.where(s[:-1] * s[1:] <= 0)[0]
    boundaries   = np.concatenate(([0], cuts + 1, [len(v) - 1]))

    pos_peaks, neg_peaks, abs_peaks = [], [], []

    for k in range(len(boundaries) - 1):
        start, end = boundaries[k], boundaries[k + 1]
        seg = v[start:end + 1]
        if seg.size == 0:
            continue
        max_pos = np.max(seg)
        min_neg = np.min(seg)
        if max_pos > 0:
            pos_peaks.append(max_pos)
        if min_neg < 0:
            neg_peaks.append(min_neg)
        abs_peaks.append(seg[np.argmax(np.abs(seg))])

    return float(np.mean((pos_peaks))), float(np.mean((neg_peaks))), float(np.mean((abs_peaks)))

## Advanced dynamic calculations
def _advanced_calc(x: np.ndarray, y: np.ndarray, vx:np.ndarray, vy:np.ndarray,
                  y_filt: np.ndarray, dt:float):
    
    R = np.sqrt(x**2 + y**2)
    T = (len(x)-1) * dt

    # VFY (cm.s⁻², Quijoux et al.): var(velocity norm) / mean AP position
    #   NB: depends on the (non-centered) AP position of the feet on the board
    mean_AP           = float(np.mean(y_filt))
    v_norm            = np.sqrt(vx**2 + vy**2)
    var_v_norm        = float(np.var(v_norm, ddof=0))
    vfy               = var_v_norm / mean_AP if mean_AP != 0 else np.nan

    # Sway area per second (cm²/s)
    areas             = 0.5 * np.abs(x[:-1] * y[1:] - x[1:] * y[:-1])
    sway_area_s       = float(np.sum(areas) / T)

    # Phase plane parameters (n.u.)
    sigma_x           = float(np.std(x, ddof=1))
    sigma_vx          = float(np.std(vx,  ddof=1))
    ML_phase_plane    = sigma_x + sigma_vx

    sigma_y           = float(np.std(y, ddof=1))
    sigma_vy          = float(np.std(vy,  ddof=1))
    AP_phase_plane    = sigma_y + sigma_vy

    # Mean peak interval (s)
    peaks,_           = find_peaks(R)
    peak_intervals    = np.diff(peaks) * dt
    mean_peak_s       = float(np.mean(peak_intervals))

    # Mean SD peak distance (cm)
    peak_distances    = np.abs(np.diff(R[peaks]))
    mean_SD_peak_dist = float(np.std(peak_distances, ddof=1))


    return vfy, sway_area_s, ML_phase_plane, AP_phase_plane, mean_peak_s, mean_SD_peak_dist

## Fractal dimension (Quijoux et al., 3.3.7)
def _fractal_dim(N: int, GLOBAL_length: float, ellipse_area: float):

    # d = diameter of the circle of same area as the 95% ellipse (cm)
    d  = np.sqrt(4.0 * ellipse_area / np.pi) if ellipse_area > 0 else np.nan

    # FD = log(N) / log(N.d/L)   (n.u.)
    fd = np.log(N) / np.log(N * d / GLOBAL_length) if GLOBAL_length > 0 else np.nan

    return float(fd)


## MAIN FUNCTION: Dynamic metrics
def dynamic_metrics(x_c: np.ndarray, y_c: np.ndarray, y_filt: np.ndarray,
                    qc: Dict[str, float], ellipse_area: float, p: Params
                ) -> Dict[str, float]:

    fs = p.target_fs
    dt = 1.0 / fs
    T = (len(x_c)-1) * dt
    window = int(round(0.5*fs))

    x, y = x_c, y_c

    if p.savgol_enable:
        win = int(round(p.savgol_win_s * fs))
        if win % 2 == 0:
            win += 1
        win = max(5, win)
        x   = savgol_filter(x_c, win, p.savgol_poly, mode='interp')
        y   = savgol_filter(y_c, win, p.savgol_poly, mode='interp')

    dx, dy  = np.diff(x), np.diff(y)
    vx, vy  = dx/dt, dy/dt


    ML_length, AP_length, GLOBAL_length, lfs = _timedep_calc(dx, dy, ellipse_area)

    ML_mean_veloc, ML_SD_veloc, \
        AP_mean_veloc, AP_SD_veloc, \
        GLOBAL_mean_veloc, GLOBAL_SD_veloc \
        = _veloc_calc(vx, vy)
    
    ML_zero_cross = _zero_cross_computing(vx)
    AP_zero_cross = _zero_cross_computing(vy)

    ML_dyn_meanfreq, AP_dyn_meanfreq, GLOBAL_dyn_meanfreq = _temporal_frequencies(x, y, vx, vy)

    ML_mpp_pos, ML_mpp_neg, ML_mpp_abs = _vel_peaks_computing(vx)
    AP_mpp_pos, AP_mpp_neg, AP_mpp_abs = _vel_peaks_computing(vy)

    vfy, sway_area_s, ML_phase_plane, AP_phase_plane, \
        mean_peak_s, mean_SD_peak_dist = _advanced_calc(x, y, vx, vy, y_filt, dt)

    fractal_dim = _fractal_dim(len(x), GLOBAL_length, ellipse_area)

    return {
        # Duration-dependant metrics
        'dyn_length_ML':          round(ML_length,2),
        'dyn_length_AP':          round(AP_length,2),
        'dyn_length_global':      round(GLOBAL_length,2),
        'dyn_lfs':                round(lfs,3),
        # Velocities
        'dyn_meanVeloc_ML':       round(ML_mean_veloc,2),
        'dyn_sdVeloc_ML':         round(ML_SD_veloc,3),
        'dyn_meanVeloc_AP':       round(AP_mean_veloc,2),
        'dyn_sdVeloc_AP':         round(AP_SD_veloc,3),
        'dyn_meanVeloc_global':   round(GLOBAL_mean_veloc,2),
        'dyn_sdVeloc_global':     round(GLOBAL_SD_veloc,3),
        'dyn_zeroCross_ML':       int(ML_zero_cross),
        'dyn_zeroCross_AP':       int(AP_zero_cross),
        # Temporal frequencies
        'dyn_meanFreq_ML':        round(ML_dyn_meanfreq,3),
        'dyn_meanFreq_AP':        round(AP_dyn_meanfreq,3),
        'dyn_meanfreq_global':    round(GLOBAL_dyn_meanfreq,3),
        # Advanced dynamic parameters
        'dyn_vfy':                round(vfy,3),
        'dyn_swayAreaPerS':       round(sway_area_s,3),
        'dyn_phasePlane_ML':      round(ML_phase_plane,3),
        'dyn_phasePlane_AP':      round(AP_phase_plane,3),
        'dyn_fractalDim':         round(fractal_dim,3),
        'dyn_mppPos_ML':          round(ML_mpp_pos,2),
        'dyn_mppNeg_ML':          round(ML_mpp_neg,2),
        'dyn_mppAbs_ML':          round(ML_mpp_abs,2),
        'dyn_mppPos_AP':          round(AP_mpp_pos,2),
        'dyn_mppNeg_AP':          round(AP_mpp_neg,2),
        'dyn_mppAbs_AP':          round(AP_mpp_abs,2),
        'dyn_meanSdPeakDist':     round(mean_SD_peak_dist,2),
        'dyn_meanPeakInterval':   round(mean_peak_s,3)
    }