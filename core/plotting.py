import numpy as np
from scipy.stats import chi2
from matplotlib.patches import Ellipse
from core.frequential_analysis import welch_psd



def plot_stabilogram(ax, t, x, y, filename):
    ax.clear()

    ax.plot(t, x, label="ML", lw=1.0, color= '#0e5780')
    ax.plot(t, y, label="AP", lw=1.0, color='#ff8d4d')
    ax.set_title(f"{filename} - centered stabilogram", fontsize=9, pad=14)
    # ax.set_xlabel("Time (s)")
    # ax.set_ylabel("Position (cm)")
    ax.axhline(0, color="0.7", lw=0.8)
    ax.tick_params(axis='both', which='major', labelsize=7)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)


def plot_statokinesigram(ax, x_filt, y_filt, filename):
    ax.clear()
    
    mean_ml = float(np.mean(x_filt))
    mean_ap = float(np.mean(y_filt))

    cov = np.cov(np.vstack([x_filt, y_filt]))
    c = chi2.ppf(0.95, df=2)
    eigvals, eigvecs = np.linalg.eigh(cov)
    a = np.sqrt(max(eigvals[1], 0.0) * c)
    b = np.sqrt(max(eigvals[0], 0.0) * c)
    angle = np.degrees(np.arctan2(eigvecs[1, 1], eigvecs[0, 1]))

    v_largeax = eigvecs[:,1]
    large_x_ax = np.array([mean_ml-v_largeax[0]*a, mean_ml+v_largeax[0]*a])
    large_y_ax = np.array([mean_ap-v_largeax[1]*a, mean_ap+v_largeax[1]*a])
    v_smallax = eigvecs[:,0]
    small_x_ax = np.array([mean_ml-v_smallax[0]*b, mean_ml+v_smallax[0]*b])
    small_y_ax = np.array([mean_ap-v_smallax[1]*b, mean_ap+v_smallax[1]*b])

    ell = Ellipse((mean_ml, mean_ap),
                  width=2*a, height=2*b, angle=angle,
                  facecolor='#fef86c', alpha=0.5,
                  edgecolor='#ae8964', linewidth=1.5)

    ax.plot(x_filt, y_filt, lw=0.8, color='#1688c8',
            marker="x", markersize=1, linestyle='')
    
    ax.plot(large_x_ax, large_y_ax, color='#ae8964', lw=1, linestyle='-')
    ax.plot(small_x_ax, small_y_ax, color='#ae8964', lw=1, linestyle='-')
    # ax.plot(mean_ml, mean_ap, marker="+", markersize=8, color='#ae8964', mew=2.5)

    ax.add_patch(ell)
    ax.set_title(f"{filename} - statokinesigram", fontsize=9, pad=5)
    ax.set_xlabel("ML (cm)", fontsize=8)
    ax.set_ylabel("AP (cm)", fontsize=8)
    ax.tick_params(axis='both', which='major', labelsize=7)
    ax.axhline(0, color="0.7", lw=0.8)
    ax.axvline(0, color="0.7", lw=0.8)
    ax.set_xlim(int(-12), int(12))
    ax.set_ylim(int(-10), int(4))
    ax.set_aspect('equal', adjustable='box')
    ax.grid(True, alpha=0.25)


def plot_welch_spectrum(ax, x, y, p, filename):
    ax.clear()

    f_x, Pxx_x = welch_psd(x, p)
    f_y, Pxx_y = welch_psd(y, p)

    ax.plot(f_x, Pxx_x, label="ML")
    ax.plot(f_y, Pxx_y, label="AP")
    ax.set_title(f"{filename} - PSD (Welch, Hann)", fontsize=9, pad=5)
    ax.set_xlabel("Frequency (Hz)", fontsize=8)
    ax.set_ylabel("Power density", fontsize=8)
    ax.tick_params(axis='both', which='major', labelsize=7)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.25)


def plot_energy_radar(ax, metrics, filename):
    ax.clear()

    ML_bands = np.array([
        metrics.get('frq_energy_0_05_ML', np.nan),
        metrics.get('frq_energy_05_2_ML', np.nan),
        metrics.get('frq_energy_2_5_ML',   np.nan)
        ], dtype=float)

    AP_bands = np.array([
        metrics.get('frq_energy_0_05_AP', np.nan),
        metrics.get('frq_energy_05_2_AP', np.nan),
        metrics.get('frq_energy_2_5_AP',   np.nan)
        ], dtype=float)

    labels = ["0–0.5", "0.5–2", "2–5"]

    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False)
    angles = np.concatenate([angles, [angles[0]]])  # polygone closing

    def _normalize(v):
        if not np.all(np.isfinite(v)):
            return np.full_like(v, np.nan)
        tot = np.nansum(v)
        if tot <= 0:
            return np.full_like(v, np.nan)
        return v / tot

    ML_norm = _normalize(ML_bands)
    ML_plot = np.concatenate([ML_norm, [ML_norm[0]]])
    AP_norm = _normalize(AP_bands)
    AP_plot = np.concatenate([AP_norm, [AP_norm[0]]])

    ax.set_theta_offset(np.pi / 2.0)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_yticklabels([])

    ax.plot(angles, ML_plot, label="ML", linewidth=1.2)
    ax.plot(angles, AP_plot, label="AP", linewidth=1.2, linestyle='--')
    ax.fill(angles, ML_plot, alpha=0.1)
    ax.fill(angles, AP_plot, alpha=0.05)
    ax.set_title(f"{filename} - Normalized Band Energy distribution", fontsize=9, pad=14)
    ax.tick_params(axis='both', which='major', labelsize=7)
    ax.legend(fontsize=8, loc='upper right', bbox_to_anchor=(1.2, 1.1))