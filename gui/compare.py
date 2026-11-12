"""
Fenêtre « Comparaison » : 2 à 6 éléments (essais ou moyennes d'un sujet),
statokinésigrammes superposés, diagramme d'un descripteur (moyenne ± ET entre
essais) et tableau avec différence et rapport au premier élément.
"""
import numpy as np
import tkinter as tk
from tkinter import ttk

from matplotlib.figure import Figure
from matplotlib.patches import Ellipse
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from scipy.stats import chi2

from core.design import aggregate_metrics, MeanSD
from core.i18n import tr, metric_short
from gui.common import center_window

COLORS = ['#0e5780', '#e4572e', '#2a9d8f', '#8e44ad', '#e9a03b', '#6b6b6b']
MAX_ITEMS = len(COLORS)

FAMILIES = ['Positional Parameters', 'Dynamic Parameters', 'Spectral Analysis',
            'Stochastic & Nonlinear']

METRICS = [
    ('Positional Parameters'   , 'ML mean position     (cm) ', 'mean_ML'),
    ('Positional Parameters'   , 'AP mean position     (cm) ', 'mean_AP'),
    ('Positional Parameters'   , 'ML RMS               (cm) ', 'pos_rms_ML'),
    ('Positional Parameters'   , 'AP RMS               (cm) ', 'pos_rms_AP'),
    ('Positional Parameters'   , 'Global RMS radius    (cm) ', 'pos_rms_radius'),
    ('Positional Parameters'   , 'Planar deviation     (cm) ', 'pos_planarDev'),
    ('Positional Parameters'   , 'ML mean distance     (cm) ', 'pos_meanDist_ML'),
    ('Positional Parameters'   , 'AP mean distance     (cm) ', 'pos_meanDist_AP'),
    ('Positional Parameters'   , 'Mean radius          (cm) ', 'pos_meanDist'),
    ('Positional Parameters'   , 'ML maximal distance  (cm) ', 'pos_max_ML'),
    ('Positional Parameters'   , 'AP maximal distance  (cm) ', 'pos_max_AP'),
    ('Positional Parameters'   , 'Maximal radius       (cm) ', 'pos_max_radius'),
    ('Positional Parameters'   , 'ML range             (cm) ', 'pos_range_ML'),
    ('Positional Parameters'   , 'AP range             (cm) ', 'pos_range_AP'),
    ('Positional Parameters'   , 'AP-ML range          (cm) ', 'pos_range_AP-ML'),
    ('Positional Parameters'   , 'Range ratio           (-) ', 'pos_rangeRatio'),
    ('Positional Parameters'   , 'Sway direct° coeff.   (-) ', 'pos_swaydirCoeff'),
    ('Positional Parameters'   , '95% ellipse area    (cm²) ', 'pos_ellipse95_area'),
    ('Positional Parameters'   , 'Princ. sway direct°   (°) ', 'pos_princSwaydir'),
    ('Dynamic Parameters'      , 'ML path length       (cm) ', 'dyn_length_ML'),
    ('Dynamic Parameters'      , 'AP path length       (cm) ', 'dyn_length_AP'),
    ('Dynamic Parameters'      , 'Global path length   (cm) ', 'dyn_length_global'),
    ('Dynamic Parameters'      , 'LFS                (cm⁻¹) ', 'dyn_lfs'),
    ('Dynamic Parameters'      , 'ML mean velocity   (cm/s) ', 'dyn_meanVeloc_ML'),
    ('Dynamic Parameters'      , 'AP mean velocity   (cm/s) ', 'dyn_meanVeloc_AP'),
    ('Dynamic Parameters'      , 'Global mean vel.   (cm/s) ', 'dyn_meanVeloc_global'),
    ('Dynamic Parameters'      , 'ML 0-crossings set    (-) ', 'dyn_zeroCross_ML'),
    ('Dynamic Parameters'      , 'AP 0-crossings set    (-) ', 'dyn_zeroCross_AP'),
    ('Dynamic Parameters'      , 'ML mean frequency    (Hz) ', 'dyn_meanFreq_ML'),
    ('Dynamic Parameters'      , 'AP mean frequency    (Hz) ', 'dyn_meanFreq_AP'),
    ('Dynamic Parameters'      , 'Global mean freq.    (Hz) ', 'dyn_meanfreq_global'),
    ('Dynamic Parameters'      , 'VFY                   (-) ', 'dyn_vfy'),
    ('Dynamic Parameters'      , 'Area per second   (cm²/s) ', 'dyn_swayAreaPerS'),
    ('Dynamic Parameters'      , 'ML phase plane            ', 'dyn_phasePlane_ML'),
    ('Dynamic Parameters'      , 'AP phase plane            ', 'dyn_phasePlane_AP'),
    ('Dynamic Parameters'      , 'Fractal dimension     (-) ', 'dyn_fractalDim'),
    ('Dynamic Parameters'      , 'ML peak pos. vel.  (cm/s) ', 'dyn_mppPos_ML'),
    ('Dynamic Parameters'      , 'ML peak neg. vel.  (cm/s) ', 'dyn_mppNeg_ML'),
    ('Dynamic Parameters'      , 'ML mean peak vel.  (cm/s) ', 'dyn_mppAbs_ML'),
    ('Dynamic Parameters'      , 'AP peak pos. vel.  (cm/s) ', 'dyn_mppPos_AP'),
    ('Dynamic Parameters'      , 'AP peak neg. vel.  (cm/s) ', 'dyn_mppNeg_AP'),
    ('Dynamic Parameters'      , 'AP mean peak vel.  (cm/s) ', 'dyn_mppAbs_AP'),
    ('Dynamic Parameters'      , 'Mean SD peaks dist.  (cm) ', 'dyn_meanSdPeakDist'),
    ('Dynamic Parameters'      , "Mean peaks' interval  (s) ", 'dyn_meanPeakInterval'),
    ('Spectral Analysis'       , 'ML total power      (cm²) ', 'frq_total_power_ML'),
    ('Spectral Analysis'       , 'AP total power      (cm²) ', 'frq_total_power_AP'),
    ('Spectral Analysis'       , 'ML 50% power freq.   (Hz) ', 'frq_f50_ML'),
    ('Spectral Analysis'       , 'AP 50% power freq.   (Hz) ', 'frq_f50_AP'),
    ('Spectral Analysis'       , 'ML 95% power freq.   (Hz) ', 'frq_f95_ML'),
    ('Spectral Analysis'       , 'AP 95% power freq.   (Hz) ', 'frq_f95_AP'),
    ('Spectral Analysis'       , 'ML power mode        (Hz) ', 'frq_power_mode_ML'),
    ('Spectral Analysis'       , 'AP power mode        (Hz) ', 'frq_power_mode_AP'),
    ('Spectral Analysis'       , 'ML centroidal freq.  (Hz) ', 'frq_centroid_freq_ML'),
    ('Spectral Analysis'       , 'AP centroidal freq.  (Hz) ', 'frq_centroid_freq_AP'),
    ('Spectral Analysis'       , 'ML freq. dispersion   (-) ', 'frq_freq_disp_ML'),
    ('Spectral Analysis'       , 'AP freq. dispersion   (-) ', 'frq_freq_disp_AP'),
    ('Spectral Analysis'       , 'ML [0-0.5] Hz       (cm²) ', 'frq_energy_0_05_ML'),
    ('Spectral Analysis'       , 'AP [0-0.5] Hz       (cm²) ', 'frq_energy_0_05_AP'),
    ('Spectral Analysis'       , 'ML [0.5–2] Hz       (cm²) ', 'frq_energy_05_2_ML'),
    ('Spectral Analysis'       , 'AP [0.5–2] Hz       (cm²) ', 'frq_energy_05_2_AP'),
    ('Spectral Analysis'       , 'ML  [2–5]  Hz       (cm²) ', 'frq_energy_2_5_ML'),
    ('Spectral Analysis'       , 'AP  [2–5]  Hz       (cm²) ', 'frq_energy_2_5_AP'),
    ('Spectral Analysis'       , 'ML freq. quotient     (-) ', 'frq_freq_quotient_ML'),
    ('Spectral Analysis'       , 'AP freq. quotient     (-) ', 'frq_freq_quotient_AP'),
    ('Stochastic & Nonlinear'  , 'ML ST Hurst exp.      (-) ', 'stc_HurstShortTerm_ML'),
    ('Stochastic & Nonlinear'  , 'AP ST Hurst exp.      (-) ', 'stc_HurstShortTerm_AP'),
    ('Stochastic & Nonlinear'  , 'ML LT Hurst exp.      (-) ', 'stc_HurstLongTerm_ML'),
    ('Stochastic & Nonlinear'  , 'AP LT Hurst exp.      (-) ', 'stc_HurstLongTerm_AP'),
    ('Stochastic & Nonlinear'  , 'ML ST diffus. coeff.  (-) ', 'stc_DiffShortTerm_ML'),
    ('Stochastic & Nonlinear'  , 'AP ST diffus. coeff.  (-) ', 'stc_DiffShortTerm_AP'),
    ('Stochastic & Nonlinear'  , 'ML LT diffus. coeff.  (-) ', 'stc_DiffLongTerm_ML'),
    ('Stochastic & Nonlinear'  , 'AP LT diffus. coeff.  (-) ', 'stc_DiffLongTerm_AP'),
    ('Stochastic & Nonlinear'  , 'ML crit. time Tc      (s) ', 'stc_critTime_ML'),
    ('Stochastic & Nonlinear'  , 'AP crit. time Tc      (s) ', 'stc_critTime_AP'),
    ('Stochastic & Nonlinear'  , 'ML MSD at Tc        (cm²) ', 'stc_critMSD_ML'),
    ('Stochastic & Nonlinear'  , 'AP MSD at Tc        (cm²) ', 'stc_critMSD_AP'),
    ('Stochastic & Nonlinear'  , 'ML sample entropy     (-) ', 'nl_sampEn_ML'),
    ('Stochastic & Nonlinear'  , 'AP sample entropy     (-) ', 'nl_sampEn_AP'),
    ('Stochastic & Nonlinear'  , 'ML DFA α short-term   (-) ', 'nl_dfaAlphaShort_ML'),
    ('Stochastic & Nonlinear'  , 'AP DFA α short-term   (-) ', 'nl_dfaAlphaShort_AP'),
    ('Stochastic & Nonlinear'  , 'ML DFA α long-term    (-) ', 'nl_dfaAlphaLong_ML'),
    ('Stochastic & Nonlinear'  , 'AP DFA α long-term    (-) ', 'nl_dfaAlphaLong_AP'),
    ('Stochastic & Nonlinear'  , 'ML RQA recurrence     (%) ', 'nl_rqaRec_ML'),
    ('Stochastic & Nonlinear'  , 'AP RQA recurrence     (%) ', 'nl_rqaRec_AP'),
    ('Stochastic & Nonlinear'  , 'ML RQA determinism    (%) ', 'nl_rqaDet_ML'),
    ('Stochastic & Nonlinear'  , 'AP RQA determinism    (%) ', 'nl_rqaDet_AP'),
    ('Stochastic & Nonlinear'  , 'ML RQA max. line    (pts) ', 'nl_rqaLmax_ML'),
    ('Stochastic & Nonlinear'  , 'AP RQA max. line    (pts) ', 'nl_rqaLmax_AP'),
    ('Stochastic & Nonlinear'  , 'ML RQA line entropy   (-) ', 'nl_rqaEntr_ML'),
    ('Stochastic & Nonlinear'  , 'AP RQA line entropy   (-) ', 'nl_rqaEntr_AP'),
    ('Stochastic & Nonlinear'  , 'ML embedding dim.     (-) ', 'nl_rqaDim_ML'),
    ('Stochastic & Nonlinear'  , 'AP embedding dim.     (-) ', 'nl_rqaDim_AP'),
    ('Stochastic & Nonlinear'  , 'ML embedding delay    (s) ', 'nl_rqaDelay_ML'),
    ('Stochastic & Nonlinear'  , 'AP embedding delay    (s) ', 'nl_rqaDelay_AP'),
]


FR = {
    "Comparison":                   "Comparaison",
    "Items":                        "Éléments",
    "Type":                         "Type",
    "Mean":                         "Moy.",
    "Trial":                        "Essai",
    "Compare":                      "Comparer",
    "Select 2 to {} items (Ctrl+click). The first one is the reference.":
        "Sélectionner 2 à {} éléments (Ctrl+clic). Le premier sert de référence.",
    "Family":                       "Famille",
    "All":                          "Tous",
    "Descriptor":                   "Descripteur",
    "Diff. (last - first)":         "Écart (dern. - 1er)",
    "last / first (%)":             "dern. / 1er (%)",
    "Copy table":                   "Copier le tableau",
    "Table copied (paste it into Excel).": "Tableau copié (à coller dans Excel).",
    "Click a row to plot the descriptor.": "Cliquer une ligne pour tracer le descripteur.",
    "Mean ± SD between trials":     "Moyenne ± ET entre essais",
}


def _t(s: str) -> str:
    from core.i18n import get_language
    return FR.get(s, s) if get_language() == "fr" else tr(s)


def _num(v):
    try:
        f = float(v)
        return f if np.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _fmt(v) -> str:
    if isinstance(v, MeanSD):
        return str(v)
    f = _num(v)
    if f is None:
        return ""
    a = abs(f)
    d = 3 if a < 1 else 2 if a < 100 else 1
    return f"{f:.{d}f}"


class CompareWindow(tk.Toplevel):
    def __init__(self, panel):
        super().__init__(panel.winfo_toplevel())
        self.panel = panel
        self.title(f"OpenSway - {_t('Comparison')}")
        self.geometry("1180x720")
        self.minsize(980, 600)
        self.items = {}            # iid -> (kind, label, fids)
        self.data  = []            # [(label, color, series_list, metrics)]
        self.sel_key = 'pos_ellipse95_area'
        self._build()
        self.refresh_items()
        center_window(self, panel.winfo_toplevel())

    # ------------------------------------------------------------------ UI
    def _build(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left = ttk.Frame(self, padding=8)
        left.grid(row=0, column=0, sticky='ns')
        left.rowconfigure(1, weight=1)
        ttk.Label(left, text=_t("Select 2 to {} items (Ctrl+click). The first one is the reference.")
                  .format(MAX_ITEMS), wraplength=290, justify='left').grid(row=0, column=0, sticky='w')
        self.tree_items = ttk.Treeview(left, columns=('type', 'label'), show='headings',
                                       selectmode='extended', height=24)
        self.tree_items.heading('type',  text=_t("Type"),  anchor='w')
        self.tree_items.heading('label', text=_t("Items"), anchor='w')
        self.tree_items.column('type',  width=44, stretch=False, anchor='w')
        self.tree_items.column('label', width=250, anchor='w')
        sb = ttk.Scrollbar(left, orient='vertical', command=self.tree_items.yview)
        self.tree_items.configure(yscrollcommand=sb.set)
        self.tree_items.grid(row=1, column=0, sticky='nsew', pady=4)
        sb.grid(row=1, column=1, sticky='ns', pady=4)
        ttk.Button(left, text=_t("Compare") + " ▶", command=self.compare).grid(
            row=2, column=0, columnspan=2, sticky='ew')

        right = ttk.Frame(self, padding=(0, 8, 8, 8))
        right.grid(row=0, column=1, sticky='nsew')
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=3)
        right.rowconfigure(2, weight=2)

        self.fig = Figure(figsize=(8, 3.6), dpi=100)
        gs = self.fig.add_gridspec(1, 2, width_ratios=[1.2, 1], wspace=0.3)
        self.ax_skg = self.fig.add_subplot(gs[0, 0])
        self.ax_bar = self.fig.add_subplot(gs[0, 1])
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky='nsew')

        bar = ttk.Frame(right)
        bar.grid(row=1, column=0, sticky='ew', pady=(6, 2))
        ttk.Label(bar, text=_t("Family")).pack(side='left')
        self.var_fam = tk.StringVar(value=_t("All"))
        cb = ttk.Combobox(bar, textvariable=self.var_fam, state='readonly', width=30,
                          values=[_t("All")] + [tr(f) for f in FAMILIES])
        cb.pack(side='left', padx=6)
        cb.bind("<<ComboboxSelected>>", lambda e: self._fill_table())
        ttk.Label(bar, text=_t("Click a row to plot the descriptor.")).pack(side='left', padx=12)
        ttk.Button(bar, text=_t("Copy table"), command=self.copy_table).pack(side='right')

        tf = ttk.Frame(right)
        tf.grid(row=2, column=0, sticky='nsew')
        tf.rowconfigure(0, weight=1)
        tf.columnconfigure(0, weight=1)
        self.table = ttk.Treeview(tf, show='headings', selectmode='browse')
        sb2 = ttk.Scrollbar(tf, orient='vertical', command=self.table.yview)
        self.table.configure(yscrollcommand=sb2.set)
        self.table.grid(row=0, column=0, sticky='nsew')
        sb2.grid(row=0, column=1, sticky='ns')
        self.table.bind("<<TreeviewSelect>>", self._on_row)

        self.var_msg = tk.StringVar(value="")
        ttk.Label(right, textvariable=self.var_msg, anchor='w').grid(row=3, column=0, sticky='ew')

    # --------------------------------------------------------------- items
    def refresh_items(self):
        p = self.panel
        t = self.tree_items
        t.delete(*t.get_children())
        self.items.clear()
        k = 0
        for key, fids in p._units().items():
            if len(fids) < 2:
                continue
            label = p._unit_label(*key) + f" (n={len(fids)})"
            iid = f"u{k}"; k += 1
            self.items[iid] = ('mean', label, fids)
            t.insert('', 'end', iid=iid, values=(_t("Mean"), label))
        for fid, row in p.design.items():
            name, subject, trial, f1, f2, cond = row
            label = p._unit_label(subject, f1, f2, cond) + (f" n°{trial}" if trial else f" ({name})")
            iid = f"t{fid}"
            self.items[iid] = ('trial', label, [fid])
            t.insert('', 'end', iid=iid, values=(_t("Trial"), label))

    # ------------------------------------------------------------- compare
    def compare(self):
        sel = [i for i in self.tree_items.get_children() if i in set(self.tree_items.selection())]
        if len(sel) < 2:
            self.var_msg.set(_t("Select 2 to {} items (Ctrl+click). The first one is the reference.")
                             .format(MAX_ITEMS))
            return
        sel = sel[:MAX_ITEMS]
        self.data = []
        self.config(cursor='watch'); self.update_idletasks()
        try:
            for k, iid in enumerate(sel):
                kind, label, fids = self.items[iid]
                series, metrics = self.panel._unit_data(fids)
                if not series:
                    continue
                m = aggregate_metrics(metrics) if kind == 'mean' else metrics[0]
                self.data.append((label, COLORS[k], series, m))
        finally:
            self.config(cursor='')
        self.var_msg.set("")
        self._draw_skg()
        self._fill_table()
        self._draw_bar()

    def _draw_skg(self):
        ax = self.ax_skg
        ax.clear()
        c = chi2.ppf(0.95, df=2)
        for label, col, series, _ in self.data:
            for s in series:
                x, y = s['x_filt'], s['y_filt']
                ax.plot(x, y, color=col, lw=0.5, alpha=0.45)
                cov = np.cov(np.vstack([x, y]))
                vals, vecs = np.linalg.eigh(cov)
                a, b = np.sqrt(max(vals[1], 0) * c), np.sqrt(max(vals[0], 0) * c)
                ang = np.degrees(np.arctan2(vecs[1, 1], vecs[0, 1]))
                ax.add_patch(Ellipse((np.mean(x), np.mean(y)), 2 * a, 2 * b, angle=ang,
                                     facecolor=col, alpha=0.10, edgecolor=col, lw=1.0))
            ax.plot([], [], color=col, lw=2, label=f"{chr(65 + len(ax.get_legend_handles_labels()[0]))} : {label}")
        ax.set_title(tr("statokinesigrams"), fontsize=9)
        ax.set_xlabel("ML (cm)", fontsize=8)
        ax.set_ylabel("AP (cm)", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.axhline(0, color='0.8', lw=0.8)
        ax.axvline(0, color='0.8', lw=0.8)
        ax.set_aspect('equal', adjustable='datalim')
        ax.legend(fontsize=7, loc='best', frameon=False)

    def _draw_bar(self):
        ax = self.ax_bar
        ax.clear()
        lab = next((l for f, l, k in METRICS if k == self.sel_key), self.sel_key)
        names, means, sds, cols = [], [], [], []
        for label, col, _, m in self.data:
            v = m.get(self.sel_key)
            names.append(label)
            means.append(_num(v) or 0.0)
            sd = getattr(v, 'sd', np.nan)
            sds.append(sd if np.isfinite(sd) else 0.0)
            cols.append(col)
        x = np.arange(len(names))
        ax.bar(x, means, yerr=sds, color=cols, alpha=0.8, capsize=4)
        ax.set_xticks(x)
        ax.set_xticklabels([chr(65 + i) for i in range(len(names))], fontsize=8)
        ax.set_title(metric_short(lab), fontsize=9)
        ax.tick_params(labelsize=7)
        ax.grid(True, axis='y', alpha=0.3)
        if any(sds):
            ax.set_xlabel(_t("Mean ± SD between trials"), fontsize=7)
        self.fig.subplots_adjust(left=0.07, right=0.98, bottom=0.14, top=0.90)
        self.canvas.draw_idle()

    # --------------------------------------------------------------- table
    def _fill_table(self):
        t = self.table
        t.delete(*t.get_children())
        n = len(self.data)
        if n == 0:
            return
        cols = ['desc'] + [f"i{k}" for k in range(n)] + ['delta', 'ratio']
        t.configure(columns=cols)
        t.heading('desc', text=_t("Descriptor"), anchor='w')
        t.column('desc', width=230, stretch=False, anchor='w')
        for k, (label, *_r) in enumerate(self.data):
            t.heading(f"i{k}", text=chr(65 + k), anchor='e')
            t.column(f"i{k}", width=120, anchor='e')
        t.heading('delta', text=_t("Diff. (last - first)"), anchor='e')
        t.heading('ratio', text=_t("last / first (%)"), anchor='e')
        t.column('delta', width=120, anchor='e')
        t.column('ratio', width=120, anchor='e')

        fam = self.var_fam.get()
        for f, lab, key in METRICS:
            if fam != _t("All") and tr(f) != fam:
                continue
            vals = [m.get(key) for *_r, m in self.data]
            first, last = _num(vals[0]), _num(vals[-1])
            delta = _fmt(last - first) if first is not None and last is not None else ""
            ratio = (f"{100 * last / first:.0f}" if first not in (None, 0) and last is not None
                     else "")
            t.insert('', 'end', iid=key,
                     values=[metric_short(lab)] + [_fmt(v) for v in vals] + [delta, ratio])

    def _on_row(self, _e):
        sel = self.table.selection()
        if sel and self.data:
            self.sel_key = sel[0]
            self._draw_bar()

    def copy_table(self):
        t = self.table
        cols = t['columns']
        if not cols:
            return
        lines = ["\t".join(t.heading(c)['text'] for c in cols)]
        for iid in t.get_children():
            lines.append("\t".join(str(v) for v in t.item(iid)['values']))
        self.clipboard_clear()
        self.clipboard_append("\n".join(lines))
        self.var_msg.set(_t("Table copied (paste it into Excel)."))
