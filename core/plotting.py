import numpy as np
from scipy.stats import chi2
from matplotlib.patches import Ellipse
from matplotlib.ticker  import NullFormatter
from core.frequential_analysis import welch_psd
from core.nonlinear_analysis   import dfa_curve, recurrence_matrix
from core.stochastic_analysis  import sda_fit
from .i18n import tr, get_language



def plot_stabilogram(ax, t, x, y, filename):
    ax.clear()

    ax.plot(t, x, label="ML", lw=1.0, color= '#0e5780')
    ax.plot(t, y, label="AP", lw=1.0, color='#ff8d4d')
    ax.set_title(f"{filename} - {tr('centered stabilogram')}", fontsize=9, pad=14)
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
    ax.set_title(f"{filename} - {tr('statokinesigram')}", fontsize=9, pad=5)
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
    ax.set_title(f"{filename} - DSP (Welch, Hann)" if get_language() == "fr" else f"{filename} - PSD (Welch, Hann)", fontsize=9, pad=5)
    ax.set_xlabel(tr("Frequency (Hz)"), fontsize=8)
    ax.set_ylabel(tr("Power density"), fontsize=8)
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
    ax.set_title(f"{filename} - {tr('Normalized Band Energy distribution')}", fontsize=9, pad=14)
    ax.tick_params(axis='both', which='major', labelsize=7)
    ax.legend(fontsize=8, loc='upper right', bbox_to_anchor=(1.2, 1.1))


def plot_sda(ax, x, y, p, filename):
    ax.clear()

    fs = p.target_fs

    for sig, lab, col in ((x, "ML", '#0e5780'), (y, "AP", '#ff8d4d')):
        dt, msd, (a_s, b_s), (a_l, b_l) = sda_fit(sig, fs, p)
        ax.loglog(dt, msd, lw=1.0, label=lab, color=col)
        if np.all(np.isfinite([a_s, b_s, a_l, b_l])) and a_s != a_l:
            tc = float(np.clip(np.exp((b_l - b_s) / (a_s - a_l)), dt[0], dt[-1]))
            d_s, d_l = dt[dt <= 2 * tc], dt[dt >= tc / 2]
            ax.loglog(d_s, np.exp(b_s) * d_s**a_s, lw=0.8, linestyle='--', color=col)
            ax.loglog(d_l, np.exp(b_l) * d_l**a_l, lw=0.8, linestyle=':',  color=col)
            ax.plot(tc, np.exp(a_s * np.log(tc) + b_s), marker='o',
                    markersize=4, color=col)

    ax.set_title(f"{filename} - {tr('Stabilogram diffusion plot')}", fontsize=9, pad=5)
    ax.set_xlabel("Δt (s)", fontsize=8)
    ax.set_ylabel("MSD (cm²)", fontsize=8)
    ax.tick_params(axis='both', which='major', labelsize=7)
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.legend(fontsize=8)
    ax.grid(True, which='both', alpha=0.25)


def plot_dfa(ax, x, y, p, filename):
    ax.clear()

    fs = p.target_fs

    for sig, lab, col in ((x, "ML", '#0e5780'), (y, "AP", '#ff8d4d')):
        n, F = dfa_curve(sig, p)
        if len(n) == 0:
            continue
        ax.loglog(n / fs, F, marker='o', markersize=2.5, lw=0.8, label=lab, color=col)

    ax.axvline(p.dfa_cross_s, color="0.6", lw=0.8, linestyle='--')
    ax.set_title(f"{filename} - {tr('DFA fluctuation function')}", fontsize=9, pad=5)
    ax.set_xlabel(tr("Window size (s)"), fontsize=8)
    ax.set_ylabel("F(n) (cm)", fontsize=8)
    ax.tick_params(axis='both', which='major', labelsize=7)
    ax.legend(fontsize=8)
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.grid(True, which='both', alpha=0.25)


def plot_recurrence(ax, sig, p, filename, axis_name="AP"):
    ax.clear()

    fs = p.target_fs
    R, m, tau, w = recurrence_matrix(sig, fs, p)
    R  = R | R.T                                          # symmetric display
    T  = len(R) / fs

    ax.imshow(R, cmap='Greys', origin='lower', interpolation='nearest',
              extent=(0, T, 0, T))
    ax.set_title(f"{filename} - {axis_name} {tr('recurrence plot')} (m={m}, τ={tau/fs:.2f} s)",
                 fontsize=9, pad=5)
    ax.set_xlabel(tr("Time (s)"), fontsize=8)
    ax.set_ylabel(tr("Time (s)"), fontsize=8)
    ax.tick_params(axis='both', which='major', labelsize=7)


# =============================================================================
# SUBJECT MODE: repeated trials overlaid (one series dict per trial)
# =============================================================================

TRIAL_COLORS = ['#1688c8', '#ff8d4d', '#4daf4a', '#984ea3', '#e41a1c', '#a65628']


def _ellipse95(x, y):
    cov = np.cov(np.vstack([x, y]))
    c   = chi2.ppf(0.95, df=2)
    eigvals, eigvecs = np.linalg.eigh(cov)
    a   = np.sqrt(max(eigvals[1], 0.0) * c)
    b   = np.sqrt(max(eigvals[0], 0.0) * c)
    ang = np.degrees(np.arctan2(eigvecs[1, 1], eigvecs[0, 1]))
    return float(np.mean(x)), float(np.mean(y)), a, b, ang


def plot_stabilogram_multi(ax, series_list, filename):
    ax.clear()

    for k, s in enumerate(series_list):
        alpha = 1.0 if k == 0 else 0.45
        ax.plot(s['t'], s['x'], lw=0.8, color='#0e5780', alpha=alpha, label="ML" if k == 0 else None)
        ax.plot(s['t'], s['y'], lw=0.8, color='#ff8d4d', alpha=alpha, label="AP" if k == 0 else None)

    ax.set_title(f"{filename} - {tr('centered stabilograms')} ({len(series_list)} {tr('trials')})", fontsize=9, pad=14)
    ax.axhline(0, color="0.7", lw=0.8)
    ax.tick_params(axis='both', which='major', labelsize=7)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)


def plot_statokinesigram_multi(ax, series_list, filename, labels=None):
    ax.clear()

    for k, s in enumerate(series_list):
        col  = TRIAL_COLORS[k % len(TRIAL_COLORS)]
        lab  = labels[k] if labels else f"{tr('trial')} {k+1}"
        x, y = s['x_filt'], s['y_filt']
        ax.plot(x, y, color=col, marker="x", markersize=1, linestyle='', alpha=0.6)
        mx, my, a, b, ang = _ellipse95(x, y)
        ax.add_patch(Ellipse((mx, my), width=2*a, height=2*b, angle=ang,
                             facecolor=col, alpha=0.15, edgecolor=col, linewidth=1.2))
        ax.plot([], [], color=col, lw=1.5, label=lab)

    ax.set_title(f"{filename} - {tr('statokinesigrams')}", fontsize=9, pad=5)
    ax.set_xlabel("ML (cm)", fontsize=8)
    ax.set_ylabel("AP (cm)", fontsize=8)
    ax.tick_params(axis='both', which='major', labelsize=7)
    ax.axhline(0, color="0.7", lw=0.8)
    ax.axvline(0, color="0.7", lw=0.8)
    ax.set_xlim(int(-12), int(12))
    ax.set_ylim(int(-10), int(4))
    ax.set_aspect('equal', adjustable='box')
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7, loc='lower right')


def plot_welch_spectrum_multi(ax, series_list, p, filename):
    ax.clear()

    for axis, lab, col in (('x', "ML", '#1f77b4'), ('y', "AP", '#ff7f0e')):
        f0, P = None, []
        for s in series_list:
            f, Pxx = welch_psd(s[axis], p)
            if f0 is None:
                f0 = f
            P.append(np.interp(f0, f, Pxx))
            ax.plot(f, Pxx, lw=0.5, alpha=0.35, color=col)
        ax.plot(f0, np.mean(P, axis=0), lw=1.4, color=col, label=f"{lab} ({tr('mean')})")

    ax.set_title(f"{filename} - {'DSP' if get_language() == 'fr' else 'PSD'} (Welch, Hann), {len(series_list)} {tr('trials')}", fontsize=9, pad=5)
    ax.set_xlabel(tr("Frequency (Hz)"), fontsize=8)
    ax.set_ylabel(tr("Power density"), fontsize=8)
    ax.tick_params(axis='both', which='major', labelsize=7)
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.25)


def plot_sda_multi(ax, series_list, p, filename):
    ax.clear()

    fs = p.target_fs

    for axis, lab, col in (('x', "ML", '#0e5780'), ('y', "AP", '#ff8d4d')):
        curves = []
        for s in series_list:
            dt, msd, _, _ = sda_fit(s[axis], fs, p)
            ax.loglog(dt, msd, lw=0.5, alpha=0.35, color=col)
            curves.append((dt, msd))
        n = min(len(c[0]) for c in curves)
        ax.loglog(curves[0][0][:n], np.mean([c[1][:n] for c in curves], axis=0),
                  lw=1.4, color=col, label=f"{lab} ({tr('mean')})")

    ax.set_title(f"{filename} - {tr('Stabilogram diffusion plot')}", fontsize=9, pad=5)
    ax.set_xlabel("Δt (s)", fontsize=8)
    ax.set_ylabel("MSD (cm²)", fontsize=8)
    ax.tick_params(axis='both', which='major', labelsize=7)
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.legend(fontsize=8)
    ax.grid(True, which='both', alpha=0.25)


def plot_dfa_multi(ax, series_list, p, filename):
    ax.clear()

    fs = p.target_fs

    for axis, lab, col in (('x', "ML", '#0e5780'), ('y', "AP", '#ff8d4d')):
        curves = []
        for s in series_list:
            n, F = dfa_curve(s[axis], p)
            if len(n) == 0:
                continue
            ax.loglog(n / fs, F, lw=0.5, alpha=0.35, color=col)
            curves.append(dict(zip(n, F)))
        if not curves:
            continue
        common = sorted(set.intersection(*(set(c) for c in curves)))
        if common:
            ax.loglog(np.array(common) / fs, [np.mean([c[k] for c in curves]) for k in common],
                      marker='o', markersize=2.5, lw=1.2, color=col, label=f"{lab} ({tr('mean')})")

    ax.axvline(p.dfa_cross_s, color="0.6", lw=0.8, linestyle='--')
    ax.set_title(f"{filename} - {tr('DFA fluctuation function')}", fontsize=9, pad=5)
    ax.set_xlabel(tr("Window size (s)"), fontsize=8)
    ax.set_ylabel("F(n) (cm)", fontsize=8)
    ax.tick_params(axis='both', which='major', labelsize=7)
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.legend(fontsize=8)
    ax.grid(True, which='both', alpha=0.25)
