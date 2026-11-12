from typing import Dict, List, Optional, Tuple
import numpy as np

from matplotlib.figure import Figure
from datetime import date

from .params import Params
from . import plotting as pl


# === TEXT HELPERS ===
_VAL_W = 8      # value column width (wider for "mean±SD" in subject reports)

def _kv_lines(metrics: dict, items: List[Tuple[str, str, str]], fmt="{:.2f}"
              ) -> List[str]:

    out = []

    for lab, key, unit in items:
        v = metrics.get(key, None)
        if v is None or (isinstance(v, float) and np.isnan(v)):
            s = ""
        elif isinstance(v, (int, np.integer)):
            s = str(int(v))
        elif isinstance(v, (float, np.floating)):
            s = fmt.format(v) if hasattr(v, 'sd') else fmt.format(float(v))
        else:
            s = str(v)
        out.append(f"{lab:<28} {s:>{_VAL_W}} {unit}")

    return out

def _draw_textbox(ax, title: str, lines: List[str], fontsize=8):
    ax.axis("off")
    txt = (title + "\n" if title else "") + "\n".join(lines)
    ax.text(0.0, 1.0, txt, va="top", ha="left", fontsize=fontsize, family="monospace")


# ====== PAGE 1 ======
def _page1(name: str, series: Dict[str, np.ndarray], metrics: dict, p: Params,
           series_list: Optional[List[Dict[str, np.ndarray]]] = None) -> Figure:
    
    fig = Figure(figsize=(8.27, 11.69), dpi=120)  # A4 portrait
    
    gs  = fig.add_gridspec(nrows=2, ncols=2, height_ratios=[0.65, 0.35],
                            width_ratios=[1.0, 1.0],hspace=0.18, wspace=0.25)
    filename = name

    ax_pos_txt = fig.add_subplot(gs[0, 0])
    ax_skg     = fig.add_subplot(gs[0, 1])
    ax_stab    = fig.add_subplot(gs[1, :])

    # --- plots ---
    t      = series['t']
    x      = series['x']
    y      = series['y']
    x_filt = series['x_filt']
    y_filt = series['y_filt']

    if series_list:
        pl.plot_stabilogram_multi(ax_stab, series_list, filename)
    else:
        pl.plot_stabilogram(ax_stab, t, x, y, filename)
    # ax_stab.set_title(f"{filename} — Stabilogram (centered)", fontsize=10, pad=6)

    if series_list:
        pl.plot_statokinesigram_multi(ax_skg, series_list, filename)
    else:
        pl.plot_statokinesigram(ax_skg, x_filt, y_filt, filename)
    # ax_skg.set_title(f"{filename} — Statokinesigram + ellipse 95%", fontsize=10, pad=6)

#     lines.append(f"   ML mean position  = {metrics.get('mean_ML')} ± {metrics.get('SD_ML')} cm")
#     lines.append(f"   AP mean position  = {metrics.get('mean_AP')} ± {metrics.get('SD_AP')} cm")

    lines = (
        ["", "", "", "", ""] + ["POSITIONAL METRICS"]
        + ["", "Center Position & Dispersion:"] +
        _kv_lines(metrics, [
            ("  ML mean position  =",  'mean_ML',           "cm"),
            ("  AP mean position  =",  'mean_AP',           "cm"),
            ("  ML RMS            =",  'pos_rms_ML',        "cm"),
            ("  AP RMS            =",  'pos_rms_AP',        "cm"),
            ("  Global RMS radius =",  'pos_rms_radius',    "cm"),
            ("  Planar deviation  =",  'pos_planarDev',     "cm")
        ], fmt="{:.2f}")

        + ["", "Distances & Amplitudes:"] +
        _kv_lines(metrics, [
            ("  ML mean distance  =",  'pos_meanDist_ML',   "cm"),
            ("  AP mean distance  =",  'pos_meanDist_AP',   "cm"),
            ("  Mean radius       =",  'pos_meanDist',      "cm"),
            ("  ML max distance   =",  'pos_max_ML',        "cm"),
            ("  AP max distance   =",  'pos_max_AP',        "cm"),
            ("  Maximal radius    =",  'pos_max_radius',    "cm"),
            ("  ML range          =",  'pos_range_ML',      "cm"),
            ("  AP range          =",  'pos_range_AP',      "cm"),
            ("  AP-ML range       =",  'pos_range_AP-ML',   "cm"),
            ("  Range ratio       =",  'pos_rangeRatio',    "(-)")
        ], fmt="{:.2f}")

        + ["", "Geometry & Direction:"] +
        _kv_lines(metrics, [
            ("  Sway dir° coeff.  =",  'pos_swaydirCoeff',   "(-)"),
            ("  95% ellipse area  =",  'pos_ellipse95_area', "cm²"),
            ("  Princ. sway dir°  =",  'pos_princSwaydir',   "°")
        ], fmt="{:.2f}")
    )
    
    _draw_textbox(ax_pos_txt, "", lines, fontsize=9)

    fig.suptitle(f"{filename} - OpenSway stabilometric report \n   \
    {date.today()}   -   page 1/3", fontsize=12, y=0.995)
    
    fig.subplots_adjust(top=0.97, left=0.06, right=0.97, bottom=0.05)

    return fig


# ====== PAGE 2 ======
def _page2(name: str, series: Dict[str, np.ndarray], metrics: dict, p: Params,
           series_list: Optional[List[Dict[str, np.ndarray]]] = None) -> Figure:

    fig = Figure(figsize=(8.27, 11.69), dpi=120)

    gs = fig.add_gridspec(nrows=2, ncols=2, height_ratios=[0.58, 0.42],
                          width_ratios=[1.05, 1.00], hspace=0.22, wspace=0.25)

    # TOP: dynamic metrics in 2 columns
    ax_dyn_left  = fig.add_subplot(gs[0, 0])
    ax_dyn_right = fig.add_subplot(gs[0, 1])

    # BOTTOM: left text, right graphs (PSD + radar stacked)
    ax_txt_bottom = fig.add_subplot(gs[1, 0])
    gs_graphs = gs[1, 1].subgridspec(2, 1, height_ratios=[0.6, 0.4], hspace=0.30)
    ax_psd   = fig.add_subplot(gs_graphs[0, 0])
    ax_radar = fig.add_subplot(gs_graphs[1, 0], polar=True)

    filename = name
    x        = series['x']
    y        = series['y']

    # --- plots ---
    if series_list:
        pl.plot_welch_spectrum_multi(ax_psd, series_list, p, filename)
    else:
        pl.plot_welch_spectrum(ax_psd, x, y, p, filename)
    # ax_psd.set_title("PSD (Welch, Hann)", fontsize=10, pad=6)

    pl.plot_energy_radar(ax_radar, metrics, filename)
    # ax_radar.set_title("Band energy distribution (normalized)", fontsize=10, pad=10)


    dyn_left = (
        _kv_lines(metrics, [
            ("  Duration           =",  'duration',          "s")], fmt="{:.1f}"
        )

        + ["DYNAMIC METRICS"]
        + ["", "Duration-dependent Metrics:"]
        + _kv_lines(metrics, [
            ("  ML path length     =", 'dyn_length_ML',      "cm"),
            ("  AP path length     =", 'dyn_length_AP',      "cm"),
            ("  Global path len.   =", 'dyn_length_global',  "cm"),
            ("  LFS                =", 'dyn_lfs',            "cm⁻¹"),
        ], fmt="{:.2f}")

        + ["", "Velocities:"]
        + _kv_lines(metrics, [
            ("  ML mean velocity   =",  'dyn_meanVeloc_ML',     "cm/s"),
            ("  AP mean velocity   =",  'dyn_meanVeloc_AP',     "cm/s"),
            ("  Global mean vel.   =",  'dyn_meanVeloc_global', "cm/s"),
            ("  ML 0-crossings set =",  'dyn_zeroCross_ML',     ""),
            ("  AP 0-crossings set =",  'dyn_zeroCross_AP',     "")
        ], fmt="{:.2f}")

        + ["", "Temporal Frequencies:"]
        + _kv_lines(metrics, [
            ("  ML mean frequency  =",  'dyn_meanFreq_ML',      "Hz"),
            ("  AP mean frequency  =",  'dyn_meanFreq_AP',      "Hz"),
            ("  Global mean freq.  =",  'dyn_meanfreq_global',  "Hz")
        ], fmt="{:.3f}")
    )

    _draw_textbox(ax_dyn_left, "", dyn_left, fontsize=9)

#     lines.append(f"  ML mean velocity  = {metrics.get('ML_mean_veloc')} ± {metrics.get('ML_SD_veloc')} cm/s")
#     lines.append(f"  AP mean velocity  = {metrics.get('AP_mean_veloc')} ± {metrics.get('AP_SD_veloc')} cm/s")
#     lines.append(f"  Global mean vel.  = {metrics.get('GLOBAL_mean_veloc')} ± {metrics.get('GLOBAL_SD_veloc')} cm/s")

    dyn_right = (
        ["", ""]
        + ["", "Advanced Dynamics:"]
        + _kv_lines(metrics, [
            ("  VFY                =",  'dyn_vfy',             "(-)"),
            ("  Area per second    =",  'dyn_swayAreaPerS',    "cm²/s"),
            ("  ML phase plane     =",  'dyn_phasePlane_ML',   "(-)"),
            ("  AP phase plane     =",  'dyn_phasePlane_AP',   "(-)"),
            ("  Fractal dimension  =",  'dyn_fractalDim',      "(-)"),
            ("  ML peak (+) vel.   =",  'dyn_mppPos_ML',       "cm/s"),
            ("  AP peak (+) vel.   =",  'dyn_mppPos_AP',       "cm/s"),
            ("  ML peak (-) vel.   =",  'dyn_mppNeg_ML',       "cm/s"),
            ("  AP peak (-) vel.   =",  'dyn_mppNeg_AP',       "cm/s"),
            ("  ML mean peak vel.  =",  'dyn_mppAbs_ML',       "cm/s"),
            ("  AP mean peak vel.  =",  'dyn_mppAbs_AP',       "cm/s"),
            ("  Mean SD peaks dist.=",  'dyn_meanSdPeakDist',  "cm"),
            ("  Mean peaks' interv.=",  'dyn_meanPeakInterval',"s"),
        ], fmt="{:.2f}")

        + ["", "STOCHASTIC METRICS"]
        + ["", "Stabilogram Diffusion Analysis:"]
        + _kv_lines(metrics, [
            ("  ML ST Hurst exp.   =",  'stc_HurstShortTerm_ML', "(-)"),
            ("  AP ST Hurst exp.   =",  'stc_HurstShortTerm_AP', "(-)"),
            ("  ML LT Hurst exp.   =",  'stc_HurstLongTerm_ML',  "(-)"),
            ("  AP LT Hurst exp.   =",  'stc_HurstLongTerm_AP',  "(-)"),
            ("  ML ST diff. coeff. =",  'stc_DiffShortTerm_ML',  "(-)"),
            ("  AP ST diff. coeff. =",  'stc_DiffShortTerm_AP',  "(-)"),
            ("  ML LT diff. coeff. =",  'stc_DiffLongTerm_ML',   "(-)"),
            ("  AP LT diff. coeff. =",  'stc_DiffLongTerm_AP',   "(-)")
        ], fmt="{:.3f}")

        + ["", "Critical Time & MSD Tc:"]
        + _kv_lines(metrics, [
            ("  ML crit. time Tc   =",  'stc_critTime_ML',       "s"),
            ("  AP crit. time Tc   =",  'stc_critTime_AP',       "s"),
            ("  ML MSD at Tc       =",  'stc_critMSD_ML',        "cm²"),
            ("  AP MSD at Tc       =",  'stc_critMSD_AP',        "cm²")
        ], fmt="{:.3f}")
    )

    _draw_textbox(ax_dyn_right, "", dyn_right, fontsize=9)


    bottom_left = (
        ["SPECTRAL METRICS"]
        + ["", "Frequency Metrics:"]
        + _kv_lines(metrics, [
            ("  ML total power      =",  'frq_total_power_ML',   "cm²"),
            ("  AP total power      =",  'frq_total_power_AP',   "cm²"),
            ("  ML 50% power freq.  =",  'frq_f50_ML',           "Hz"),
            ("  AP 50% power freq.  =",  'frq_f50_AP',           "Hz"),
            ("  ML 95% power freq.  =",  'frq_f95_ML',           "Hz"),
            ("  AP 95% power freq.  =",  'frq_f95_AP',           "Hz"),
            ("  ML power mode       =",  'frq_power_mode_ML',    "Hz"),
            ("  AP power mode       =",  'frq_power_mode_AP',    "Hz"),
            ("  ML centroidal freq. =",  'frq_centroid_freq_ML', "Hz"),
            ("  AP centroidal freq. =",  'frq_centroid_freq_AP', "Hz"),
            ("  ML freq. dispersion =",  'frq_freq_disp_ML',     "(-)"),
            ("  AP freq. dispersion =",  'frq_freq_disp_AP',     "(-)")
        ], fmt="{:.3f}")

    + ["", "Band Energies:"]
    + _kv_lines(metrics, [
        ("  ML [0-0.5] Hz      =",  'frq_energy_0_05_ML',    "cm²"),
        ("  AP [0-0.5] Hz      =",  'frq_energy_0_05_AP',    "cm²"),
        ("  ML [0.5–2] Hz      =",  'frq_energy_05_2_ML',    "cm²"),
        ("  AP [0.5–2] Hz      =",  'frq_energy_05_2_AP',    "cm²"),
        ("  ML [2–5] Hz        =",  'frq_energy_2_5_ML',     "cm²"),
        ("  AP [2–5] Hz        =",  'frq_energy_2_5_AP',     "cm²"),
        ("  ML freq. quotient  =",  'frq_freq_quotient_ML',  "(-)"),
        ("  AP freq. quotient  =",  'frq_freq_quotient_AP',  "(-)")
    ], fmt="{:.2f}")
    )

    _draw_textbox(ax_txt_bottom, "", bottom_left, fontsize=9)


    fig.suptitle(f"{filename} - OpenSway stabilometric report \n   \
                 {date.today()} — page 2/3", fontsize=12, y=0.995)
    
    fig.subplots_adjust(top=0.96, left=0.06, right=0.96, bottom=0.05)
    
    return fig


# ====== PAGE 3 ======
def _page3(name: str, series: Dict[str, np.ndarray], metrics: dict, p: Params,
           series_list: Optional[List[Dict[str, np.ndarray]]] = None) -> Figure:

    fig = Figure(figsize=(8.27, 11.69), dpi=120)

    gs = fig.add_gridspec(nrows=2, ncols=2, height_ratios=[0.5, 0.5],
                          width_ratios=[1.0, 1.0], hspace=0.22, wspace=0.30)

    ax_txt   = fig.add_subplot(gs[0, 0])
    ax_dfa   = fig.add_subplot(gs[0, 1])
    ax_rp_ml = fig.add_subplot(gs[1, 0])
    ax_rp_ap = fig.add_subplot(gs[1, 1])

    filename = name
    x        = series['x']
    y        = series['y']

    # --- plots ---
    if series_list:
        pl.plot_dfa_multi(ax_dfa, series_list, p, filename)
        pl.plot_recurrence(ax_rp_ml, x, p, filename + " trial 1", "ML")
        pl.plot_recurrence(ax_rp_ap, y, p, filename + " trial 1", "AP")
    else:
        pl.plot_dfa(ax_dfa, x, y, p, filename)
        pl.plot_recurrence(ax_rp_ml, x, p, filename, "ML")
        pl.plot_recurrence(ax_rp_ap, y, p, filename, "AP")

    lines = (
        ["NONLINEAR METRICS"]
        + ["", f"Sample Entropy (m={p.sampen_m}, r={p.sampen_r} SD):"]
        + _kv_lines(metrics, [
            ("  ML sample entropy  =",  'nl_sampEn_ML',        "(-)"),
            ("  AP sample entropy  =",  'nl_sampEn_AP',        "(-)")
        ], fmt="{:.3f}")

        + ["", f"Detrended Fluctuation Analysis (crossover {p.dfa_cross_s} s):"]
        + _kv_lines(metrics, [
            ("  ML DFA α short     =",  'nl_dfaAlphaShort_ML', "(-)"),
            ("  AP DFA α short     =",  'nl_dfaAlphaShort_AP', "(-)"),
            ("  ML DFA α long      =",  'nl_dfaAlphaLong_ML',  "(-)"),
            ("  AP DFA α long      =",  'nl_dfaAlphaLong_AP',  "(-)")
        ], fmt="{:.3f}")

        + ["", "Recurrence Quantification " + (f"(fixed radius {p.rqa_radius} x mean dist.):"
                    if p.rqa_mode == "fixed_radius" else f"(fixed RR {100*p.rqa_rec_rate:.0f}%):")]
        + _kv_lines(metrics, [
            ("  ML recurrence      =",  'nl_rqaRec_ML',        "%"),
            ("  AP recurrence      =",  'nl_rqaRec_AP',        "%"),
            ("  ML determinism     =",  'nl_rqaDet_ML',        "%"),
            ("  AP determinism     =",  'nl_rqaDet_AP',        "%"),
            ("  ML max. line       =",  'nl_rqaLmax_ML',       "pts"),
            ("  AP max. line       =",  'nl_rqaLmax_AP',       "pts"),
            ("  ML line entropy    =",  'nl_rqaEntr_ML',       "(-)"),
            ("  AP line entropy    =",  'nl_rqaEntr_AP',       "(-)")
        ], fmt="{:.2f}")

        + ["", "RQA Embedding:"]
        + _kv_lines(metrics, [
            ("  ML dimension m     =",  'nl_rqaDim_ML',        ""),
            ("  AP dimension m     =",  'nl_rqaDim_AP',        ""),
            ("  ML delay τ         =",  'nl_rqaDelay_ML',      "s"),
            ("  AP delay τ         =",  'nl_rqaDelay_AP',      "s")
        ], fmt="{:.2f}")
    )

    _draw_textbox(ax_txt, "", lines, fontsize=9)


    fig.suptitle(f"{filename} - OpenSway stabilometric report \n   \
                 {date.today()} — page 3/3", fontsize=12, y=0.995)

    fig.subplots_adjust(top=0.93, left=0.08, right=0.96, bottom=0.05)

    return fig


# MAIN FUNCTION: Generate Complete Report
def make_report_figures(name: str, series: Dict[str, np.ndarray],
                        metrics: dict, p: Params,
                        series_list: Optional[List[Dict[str, np.ndarray]]] = None
                        ) -> List[Figure]:
    global _VAL_W
    _VAL_W = 13 if series_list else 8
    try:
        return [
            _page1(name, series, metrics, p, series_list),
            _page2(name, series, metrics, p, series_list),
            _page3(name, series, metrics, p, series_list)
        ]
    finally:
        _VAL_W = 8


# ====== SUBJECT REPORT: comparison page ======
COMPARE_ITEMS = [
    ("Duration",              'duration',             "s",     "{:.1f}"),
    ("95% ellipse area",      'pos_ellipse95_area',   "cm²",   "{:.2f}"),
    ("Global RMS radius",     'pos_rms_radius',       "cm",    "{:.2f}"),
    ("ML range",              'pos_range_ML',         "cm",    "{:.2f}"),
    ("AP range",              'pos_range_AP',         "cm",    "{:.2f}"),
    ("Global path length",    'dyn_length_global',    "cm",    "{:.1f}"),
    ("ML mean velocity",      'dyn_meanVeloc_ML',     "cm/s",  "{:.2f}"),
    ("AP mean velocity",      'dyn_meanVeloc_AP',     "cm/s",  "{:.2f}"),
    ("Global mean vel.",      'dyn_meanVeloc_global', "cm/s",  "{:.2f}"),
    ("ML 50% power freq.",    'frq_f50_ML',           "Hz",    "{:.3f}"),
    ("AP 50% power freq.",    'frq_f50_AP',           "Hz",    "{:.3f}"),
    ("ML ST Hurst exp.",      'stc_HurstShortTerm_ML',"(-)",   "{:.3f}"),
    ("AP ST Hurst exp.",      'stc_HurstShortTerm_AP',"(-)",   "{:.3f}"),
    ("ML sample entropy",     'nl_sampEn_ML',         "(-)",   "{:.3f}"),
    ("AP sample entropy",     'nl_sampEn_AP',         "(-)",   "{:.3f}"),
    ("ML DFA α short",        'nl_dfaAlphaShort_ML',  "(-)",   "{:.3f}"),
    ("AP DFA α short",        'nl_dfaAlphaShort_AP',  "(-)",   "{:.3f}"),
    ("ML RQA determinism",    'nl_rqaDet_ML',         "%",     "{:.1f}"),
    ("AP RQA determinism",    'nl_rqaDet_AP',         "%",     "{:.1f}"),
]


def _page_compare(unit_name: str, factor_name: str,
                  levels: List[Tuple[str, List[Dict[str, np.ndarray]], dict]],
                  p: Params) -> Figure:

    fig = Figure(figsize=(8.27, 11.69), dpi=120)
    nb  = min(len(levels), 3)
    gs  = fig.add_gridspec(nrows=2, ncols=nb, height_ratios=[0.40, 0.60],
                           hspace=0.12, wspace=0.25)

    ax_txt = fig.add_subplot(gs[0, :])

    names  = [lv[0] or "(none)" for lv in levels]
    w      = 14
    header = f"{'':<22}" + "".join(f"{n:>{w}}" for n in names) + f"{'Δ last-first':>15}{'Δ%':>8}"
    lines  = [f"COMPARISON BY {factor_name.upper()}  (mean±SD of the trials)", "",
              header,
              f"{'n trials':<22}" + "".join(f"{lv[2].get('n_trials', 0):>{w}}" for lv in levels),
              ""]

    for lab, key, unit, fmt in COMPARE_ITEMS:
        vals = [lv[2].get(key) for lv in levels]
        cells = []
        for v in vals:
            if v is None or (isinstance(v, float) and np.isnan(v)):
                cells.append(f"{'':>{w}}")
            else:
                cells.append(f"{fmt.format(v):>{w}}")
        d_txt, dp_txt = "", ""
        v0, v1 = vals[0], vals[-1]
        if all(isinstance(v, float) and not np.isnan(v) for v in (v0, v1)):
            d      = float(v1) - float(v0)
            d_txt  = fmt.format(d)
            dp_txt = f"{100 * d / float(v0):+.0f}%" if float(v0) != 0 else ""
        lab_u = lab + (' ' + unit if unit.startswith('(') else ' (' + unit + ')')
        lines.append(f"{lab_u:<22}" + "".join(cells)
                     + f"{d_txt:>15}{dp_txt:>8}")

    _draw_textbox(ax_txt, "", lines, fontsize=8)

    for k, (lvl, series_list, _) in enumerate(levels[:nb]):
        ax = fig.add_subplot(gs[1, k])
        pl.plot_statokinesigram_multi(ax, series_list, f"{unit_name} {lvl}".strip())

    fig.suptitle(f"{unit_name} - OpenSway patient report \n   \
                 {date.today()} — comparison", fontsize=12, y=0.995)
    fig.subplots_adjust(top=0.95, left=0.05, right=0.97, bottom=0.05)

    return fig


# MAIN FUNCTION: Generate Subject (patient) Report
def make_subject_report(unit_name: str, factor_name: str,
                        levels: List[Tuple[str, List[Dict[str, np.ndarray]], dict]],
                        p: Params) -> List[Figure]:
    """
    levels: one tuple per condition (level of the 2nd factor, e.g. AV / AP):
            (level name, list of trial series, aggregated metrics mean±SD)
    """
    figs = []
    if len(levels) >= 2:
        figs.append(_page_compare(unit_name, factor_name, levels, p))

    for lvl, series_list, agg in levels:
        name = f"{unit_name} {lvl}".strip() + f" (mean of {agg.get('n_trials', len(series_list))})"
        figs += make_report_figures(name, series_list[0], agg, p, series_list)

    return figs


#     fig = Figure(figsize=(8.27, 11.69), dpi=100)  # proche A4
#     gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.1])

#     txt = "\n".join(lines)
#     ax_txt.text(0.0, 1.0, txt, va='top', ha='left', fontsize=8,
#                 family="monospace")