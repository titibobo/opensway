import numpy as np
from typing import Dict, Any

from scipy.stats import chi2
from scipy.spatial import ConvexHull


## Root Mean Squares per axis
def _rms_calc(x:np.ndarray, y:np.ndarray):

    R = np.sqrt(x**2 + y**2)

    # RMS per axis (cm)
    ML_rms      = float(np.sqrt(np.mean(x**2)))
    AP_rms      = float(np.sqrt(np.mean(y**2)))
    rms_radius  = float(np.sqrt(np.mean(R**2)))

    # Planar deviation (cm)
    planar_dev  = np.sqrt( np.std(x, ddof=1)**2 + np.std(y, ddof=1)**2 )

    return ML_rms, AP_rms, rms_radius, planar_dev

## Distances
def _dist_calc(x:np.ndarray, y:np.ndarray):
    R = np.sqrt(x**2 + y**2)

    # Mean distances per axis (cm)
    ML_mean_dist  = float(np.mean(np.abs(x)))
    AP_mean_dist  = float(np.mean(np.abs(y)))
    mean_dist     = float(np.mean(np.abs(R)))

    # Maximal distances per axis (cm)
    ML_max        = float(np.max(np.abs(x)))
    AP_max        = float(np.max(np.abs(y)))
    max_radius    = float(np.max(np.abs(R)))

    return ML_mean_dist, AP_mean_dist, mean_dist, ML_max, AP_max, max_radius

## Amplitudes
def _range_calc(x:np.ndarray, y:np.ndarray):

    # Amplitude per axis (cm)
    ML_range    = float(np.max(x) - np.min(x))
    AP_range    = float(np.max(y) - np.min(y))
    range_ratio = float(ML_range/AP_range) if AP_range != 0 else np.nan

    # AP-ML amplitude (cm)
    pts      = np.column_stack((x,y))
    hull     = ConvexHull(pts)
    hull_pts = pts[hull.vertices]
    max_d    = 0.0
    for i in range(len(hull_pts)):
        for j in range(i+1, len(hull_pts)):
            dx = hull_pts[i,0] - hull_pts[j,0]
            dy = hull_pts[i,1] - hull_pts[j,1]
            d  = np.sqrt(dx**2 + dy**2)
            if d > max_d:
                max_d = d
    APML_range = float(max_d)

    return ML_range, AP_range, range_ratio, APML_range

## 95% confidence ellipse calculation
def _ellipse_calc(x:np.ndarray, y:np.ndarray):

    cov              = np.cov(np.vstack([x, y]))
    var_x, var_y     = float(cov[0,0]), float(cov[1,1])
    cov_xy           = float(cov[0,1])
    c                = chi2.ppf(0.95, df=2)   # khi² thresh.val. ≈5.991 for df=2 at 95%
    eigvals, eigvecs = np.linalg.eigh(cov)
    
    # 95% confidence ellipse semi-axes
    a   = float(np.sqrt(max(eigvals[1], 0.0) * c))    # large axis = sqrt(λ1*c)
    b   = float(np.sqrt(max(eigvals[0], 0.0) * c))    # small axis = sqrt(λ2*c)

    # Elliptic area at 95% confidence
    ellipse95_area = float(np.pi * a * b)

    # Elliptic orientation (angle of the large axis /ML axis, in °)
        # v1 = proper vector associated with λ1:
    v1             = eigvecs[:, 1]                     # [vx, vy]
    theta_rad      = float(np.arctan2(v1[1], v1[0]))   # angle inside [-π, π]
    theta_deg      = float(np.degrees(theta_rad))

    # Coefficient of sway direction (n.u.)
    ML_rms         = float(np.sqrt(np.mean(x**2)))
    AP_rms         = float(np.sqrt(np.mean(y**2)))
    swaydir_coeff  = cov_xy/(ML_rms * AP_rms)

    # Principal sway direction (°)
    norm_v         = float(np.sqrt(v1[0]**2 + v1[1]**2))
    princ_swaydir  = float(np.degrees(np.arccos(np.abs(v1[0]/norm_v))))

    return ellipse95_area, a, b, theta_deg, swaydir_coeff, princ_swaydir
    

## MAIN FUNCTION: Positional metrics
def positional_metrics(x_c: np.ndarray, y_c: np.ndarray) -> Dict[str, float]:

    ML_rms, AP_rms, rms_radius, planar_dev = _rms_calc(x_c,y_c)

    ML_mean_dist, AP_mean_dist, mean_dist, ML_max, AP_max, max_radius = _dist_calc(x_c,y_c)

    ML_range, AP_range, range_ratio, APML_range = _range_calc(x_c,y_c)

    ellipse95_area, a, b, theta_deg, swaydir_coeff, princ_swaydir = _ellipse_calc(x_c,y_c)

    return {
        # RMS & dispersion
        'pos_rms_ML':           round(ML_rms,2),
        'pos_rms_AP':           round(AP_rms,2),
        'pos_rms_radius':       round(rms_radius,2),
        'pos_planarDev':        round(planar_dev,2),
        # Mean/Max distances
        'pos_meanDist_ML':      round(ML_mean_dist,2),
        'pos_meanDist_AP':      round(AP_mean_dist,2),
        'pos_meanDist':         round(mean_dist,2),
        'pos_max_ML':           round(ML_max,2),
        'pos_max_AP':           round(AP_max,2),
        'pos_max_radius':       round(max_radius,2),
        # Range
        'pos_range_ML':         round(ML_range,2),
        'pos_range_AP':         round(AP_range,2),
        'pos_range_AP-ML':      round(APML_range,2),
        'pos_rangeRatio':       round(range_ratio,2),
        # Ellipse 95%
        'pos_ellipse95_area':   round(ellipse95_area,3),
        'pos_ellipse95_a':      a,
        'pos_ellipse95_b':      b,
        'pos_ellipse95_theta':  theta_deg,
        # Direction
        'pos_swaydirCoeff':     round(swaydir_coeff,3),
        'pos_princSwaydir':     round(princ_swaydir,1)
    }