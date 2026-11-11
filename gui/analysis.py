"""Onglet « Analyse » : reprise de BrainBloX_analysis v2.0 (mise en page inchangée)."""
import os
import traceback

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import numpy as np
import pandas as pd

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_pdf import PdfPages
from typing import List, Tuple, Dict

from core                    import plotting as pl
from core.params             import Params, load_logo
from core.params             import GUI_METRIC_LABELS, METRIC_TOOLTIPS
from core.pipeline           import run_pipeline
from core.export_pdf_report  import make_report_figures
from core.aggregate          import export_excel

from gui.common              import ToolTip, resource_path, VERSION


class AnalysisPanel(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.ui_fixed = app.ui_fixed

        self.params = Params()
        self.files:   List[str] = []
        self.results: List[pd.DataFrame] = []
        self.cache:   Dict[str, Tuple[dict, Dict[str, np.ndarray]]] = {}


        self._build_layout()

    # == GLOBAL LAYOUT =========================================================
    def _build_layout(self):

        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        def _metrics_enumeration(labels_list, var_group, subframe):
            for i, label in enumerate(labels_list):
                var = tk.StringVar(value="")
                var_group[label] = var

                label_name = ttk.Label(subframe, text=label)
                label_name.grid(row=i, column=0, sticky='w', padx=4, pady=1)

                tip = METRIC_TOOLTIPS.get(label)
                if tip:
                    ToolTip(label_name, tip)

                ttk.Label(subframe, textvariable=var, width=11, anchor='center',
                        relief='sunken').grid(row=i, column=1, sticky='w', padx=4, pady=1)

        ## =====================================================================
        ## == LEFT PANEL (CONTROLS) =====
        ## =====================================================================

        left = ttk.Frame(self, padding=10)
        left.grid(row=0, column=0, sticky='ns')

        # ==== Parameters =============
        logo = ttk.Frame(left)
        logo.grid(row=0, column=0, sticky='ew')
        logo.columnconfigure(1, weight=1)

        logo_path = resource_path("assets", "ESO_logo.png")
        try:
            self._logo_img = load_logo(logo_path, max_size=(211, 74))
            logo_lbl = ttk.Label(logo, image=self._logo_img)
        except Exception:
            logo_lbl = ttk.Label(logo, text=f"OpenSway {VERSION}",
                                 font=(self.ui_fixed.actual('family'), 14, 'bold'))
        logo_lbl.grid(row=0, column=0, sticky='w')

        ToolTip(logo_lbl,
            f"OpenSway - v{VERSION}\n"
            "ESO Paris, Research Department\n"
            "\nAll measurements and operations based on\n"
            "Quijoux et al. 2021, Physiological Reports\n"
            "doi: 10.14814/phy2.15067\n"
            "\nResampling: SWARII (Audiffren & Contal 2016,\n"
            "Sensors, doi: 10.3390/s16081208)",
            delay_ms=250
        )

        sep1 = ttk.Separator(left, orient='horizontal')
        sep1.grid(row=1, column=0, sticky='ew', pady=8)

        frm = ttk.LabelFrame(left, text="Parameters")
        frm.grid(row=2, column=0, sticky='ew')

        self.var_fs      = tk.DoubleVar(value=self.params.target_fs)
        self.var_fc      = tk.DoubleVar(value=self.params.butter_fc)
        self.var_order   = tk.IntVar(value=self.params.butter_order)
        self.var_sg      = tk.BooleanVar(value=self.params.savgol_enable)
        self.var_sg_win  = tk.DoubleVar(value=self.params.savgol_win_s)
        self.var_sg_poly = tk.IntVar(value=self.params.savgol_poly)
        self.var_segsec  = tk.DoubleVar(value=self.params.seg_seconds)
        self.var_resamp  = tk.StringVar(value=self.params.resampling)
        self.var_sw_win  = tk.DoubleVar(value=self.params.swarii_win_s)

        grid = [
            ("Resampling",         self.var_resamp),
            ("SWARII window (s)",  self.var_sw_win),
            ("Target freq. (Hz)",  self.var_fs),
            ("Lowpass freq. (Hz)", self.var_fc),
            ("Butterworth order",  self.var_order),
            ("Savitzky-Golay",     self.var_sg),
            ("SG window (s)",      self.var_sg_win),
            ("SG order",           self.var_sg_poly),
            ("Welch segment (s)",  self.var_segsec)
        ]

        for i, (label, var) in enumerate(grid):
            ttk.Label(frm, text=label).grid(row=i, column=0, sticky='w', padx=4, pady=2)
            if isinstance(var, tk.BooleanVar):
                ttk.Checkbutton(frm, variable=var).grid(row=i, column=1, sticky='w')
            elif var is self.var_resamp:
                ttk.Combobox(frm, textvariable=var, values=("swarii", "linear"),
                             state="readonly", width=6).grid(row=i, column=1, sticky='w')
            else:
                ttk.Entry(frm, textvariable=var, width=8).grid(row=i, column=1, sticky='w')


        # ==== File section =============
        sep2 = ttk.Separator(left, orient='horizontal')
        sep2.grid(row=3, column=0, sticky='ew', pady=8)

        ttk.Label(left, text="Recordings (OpenSway / BrainBloX)").grid(row=4, column=0, sticky='ew')
        ttk.Button(left, text="Add file...",            command=self.add_files).grid(row=5, column=0, sticky='ew', pady=2)
        self.file_list = tk.Listbox(left, height=8, selectmode=tk.EXTENDED)
        self.file_list.configure(font=self.ui_fixed)
        self.file_list.grid(row=6, column=0, sticky='ew', pady=4)
        self.file_list.bind("<<ListboxSelect>>", self.on_file_selected)

        ttk.Button(left, text="Empty list",             command=self.clear_files).grid(row=7, column=0, sticky='ew', pady=2)

        sep3 = ttk.Separator(left, orient='horizontal')
        sep3.grid(row=8, column=0, sticky='ew', pady=8)

        ttk.Button(left, text="Process filelist",       command=self.process_selected).grid(row=9, column=0, sticky='ew', pady=2)
        ttk.Button(left, text="Export selected report", command=self.export_report).grid(row=10, column=0, sticky='ew', pady=2)
        ttk.Button(left, text="Export all results",     command=self.export_all).grid(row=11, column=0, sticky='ew', pady=2)


        ## =====================================================================
        ## == RIGHT PANEL (DISPLAYS) =====
        ## =====================================================================

        right = ttk.Notebook(self)
        right.grid(row=0, column=1, sticky='nsew', padx=3, pady=3)

        ## ==== tab: POSITIONAL PARAMETERS =====================================
        tab_pos = ttk.Frame(right)
        right.add(tab_pos, text="Positional Parameters")

        tab_pos.rowconfigure(0, weight=0)      # stabilograms plot
        tab_pos.rowconfigure(1, weight=1)      # metrics+SKG plot
        tab_pos.columnconfigure(0, weight=0)   # metrics
        tab_pos.columnconfigure(1, weight=1)   # SKG plot

        pos_plotstab_frm = ttk.Frame(tab_pos)
        pos_plotstab_frm.grid(row=0, column=0, columnspan=2, sticky='nsew', padx=0, pady=0)

        self.fig_stab = Figure(figsize=(5, 1.2), dpi=100)
        self.ax_stab = self.fig_stab.add_subplot(1, 1, 1)
        self.canvas_stab = FigureCanvasTkAgg(self.fig_stab, master=pos_plotstab_frm)
        self.canvas_stab.get_tk_widget().pack(fill='both', expand=True)

        pos_metrics_frm = ttk.Frame(tab_pos)
        pos_metrics_frm.grid(row=1, column=0, sticky='nsw', padx=3, pady=3)

        self.pos_duration_var = tk.StringVar(value="")
        
        duration_frm = ttk.Frame(pos_metrics_frm)
        duration_frm.grid(row=0, column=0, sticky='new', padx=0, pady=(0, 3))

        ttk.Label(duration_frm, text="Duration              (s) ").grid(
            row=0, column=0, sticky='w', padx=4, pady=1)

        ttk.Label(duration_frm, textvariable=self.pos_duration_var,
                    width=11, anchor='center', relief='sunken').grid(
                            row=0, column=1, sticky='w', padx=4, pady=1)
        

        pos_metrics_subfrm_cntr = ttk.LabelFrame(pos_metrics_frm,
                        text="Center Position & Dispersion", labelanchor='n')
        pos_metrics_subfrm_cntr.grid(row=1, column=0, sticky='new', padx=0, pady=3)

        pos_metrics_subfrm_dists = ttk.LabelFrame(pos_metrics_frm,
                        text="Distances & Amplitudes", labelanchor='n')
        pos_metrics_subfrm_dists.grid(row=2, column=0, sticky='new', padx=0, pady=3)

        pos_metrics_subfrm_geom = ttk.LabelFrame(pos_metrics_frm,
                        text="Geometry & Direction", labelanchor='n')
        pos_metrics_subfrm_geom.grid(row=3, column=0, sticky='new', padx=0, pady=3)

        pos_plotskg_frm = ttk.Frame(tab_pos)
        pos_plotskg_frm.grid(row=1, column=1, sticky='nsew', padx=0, pady=0)
        pos_plotskg_frm.rowconfigure(0, weight=1)
        pos_plotskg_frm.columnconfigure(0, weight=1)

        self.fig_skg = Figure(figsize=(5, 4), dpi=100)
        self.ax_skg = self.fig_skg.add_subplot(1,1,1)
        self.canvas_skg = FigureCanvasTkAgg(self.fig_skg, master=pos_plotskg_frm)
        self.canvas_skg.get_tk_widget().pack(fill='both', expand=True)

        self.positional_vars: Dict[str, tk.StringVar] = {}

        _metrics_enumeration(GUI_METRIC_LABELS['pos_center'],    self.positional_vars, pos_metrics_subfrm_cntr)
        _metrics_enumeration(GUI_METRIC_LABELS['pos_distances'], self.positional_vars, pos_metrics_subfrm_dists)
        _metrics_enumeration(GUI_METRIC_LABELS['pos_geometry'],  self.positional_vars, pos_metrics_subfrm_geom)


        ## ==== tab: DYNAMIC PARAMETERS ========================================
        tab_dyn= ttk.Frame(right)
        right.add(tab_dyn, text="Dynamic Parameters")

        tab_dyn.columnconfigure(0, weight=0)  # metrics
        tab_dyn.columnconfigure(1, weight=1)  # plot
        tab_dyn.rowconfigure(0, weight=1)

        dyn_metrics_frm = ttk.Frame(tab_dyn)
        dyn_metrics_frm.grid(row=0, column=0, sticky='nsw', padx=3, pady=3)
      
        duration_frm = ttk.Frame(dyn_metrics_frm)
        duration_frm.grid(row=0, column=0, sticky='new', padx=0, pady=(0, 3))

        ttk.Label(duration_frm, text="Duration              (s) ").grid(
            row=0, column=0, sticky='w', padx=4, pady=1)

        ttk.Label(duration_frm, textvariable=self.pos_duration_var,
                    width=11, anchor='center', relief='sunken').grid(
                            row=0, column=1, sticky='w', padx=4, pady=1)


        dyn_metrics_subfrm_timedep = ttk.LabelFrame(dyn_metrics_frm,
                        text="Duration-dep. Metrics", labelanchor='n')
        dyn_metrics_subfrm_timedep.grid(row=1, column=0, sticky='new', padx=0, pady=3)

        dyn_metrics_subfrm_vel = ttk.LabelFrame(dyn_metrics_frm,
                        text="Velocities", labelanchor='n')
        dyn_metrics_subfrm_vel.grid(row=2, column=0, sticky='new', padx=0, pady=3)

        dyn_metrics_subfrm_freq = ttk.LabelFrame(dyn_metrics_frm,
                        text="Temporal Frequencies", labelanchor='n')
        dyn_metrics_subfrm_freq.grid(row=3, column=0, sticky='new', padx=0, pady=3)

        dyn_metrics_subfrm_adv = ttk.LabelFrame(dyn_metrics_frm,
                        text="Advanced Dynamics", labelanchor='n')
        dyn_metrics_subfrm_adv.grid(row=4, column=0, sticky='new', padx=0, pady=3)

        dyn_plot_frm = ttk.Frame(tab_dyn)
        dyn_plot_frm.grid(row=0, column=1, sticky='nsew', padx=6, pady=6)

        self.dynamic_vars: Dict[str, tk.StringVar] = {}

        _metrics_enumeration(GUI_METRIC_LABELS['dyn_timedep'],      self.dynamic_vars, dyn_metrics_subfrm_timedep)
        _metrics_enumeration(GUI_METRIC_LABELS['dyn_velocities'],   self.dynamic_vars, dyn_metrics_subfrm_vel)
        _metrics_enumeration(GUI_METRIC_LABELS['dyn_frequencies'],  self.dynamic_vars, dyn_metrics_subfrm_freq)
        _metrics_enumeration(GUI_METRIC_LABELS['dyn_advanced'],     self.dynamic_vars, dyn_metrics_subfrm_adv)


        ## ==== tab: FREQUENCY PARAMETERS ======================================
        tab_psd = ttk.Frame(right)
        right.add(tab_psd, text="Spectral Analysis")

        tab_psd.columnconfigure(0, weight=0)  # metrics
        tab_psd.columnconfigure(1, weight=1)  # plot
        tab_psd.rowconfigure(0, weight=1)
        
        psd_metrics_frm = ttk.LabelFrame(tab_psd, text="Spectral Parameters", labelanchor='n')
        psd_metrics_frm.grid(row=0, column=0, sticky='nsw', padx=3, pady=3)
        
        psd_plot_frm    = ttk.Frame(tab_psd)
        psd_plot_frm.grid(row=0, column=1, sticky='nsew', padx=6, pady=6)

        psd_metrics_subfrm_freq = ttk.LabelFrame(psd_metrics_frm, text="Frequency Metrics", labelanchor='n')
        psd_metrics_subfrm_freq.grid(row=0, column=0, sticky='new', padx=0, pady=3)

        psd_metrics_subfrm_band = ttk.LabelFrame(psd_metrics_frm, text="Band Energies", labelanchor='n')
        psd_metrics_subfrm_band.grid(row=1, column=0, sticky='new', padx=0, pady=3)

        self.fig_psd = Figure(figsize=(5, 4), dpi=100)
        gs_psd       = self.fig_psd.add_gridspec(2, 1, height_ratios=[2, 1], hspace=0.55)

        self.ax_psd  = self.fig_psd.add_subplot(gs_psd[0, 0])
        self.ax_band = self.fig_psd.add_subplot(gs_psd[1, 0], polar=True)

        self.canvas_psd = FigureCanvasTkAgg(self.fig_psd, master=psd_plot_frm)
        self.canvas_psd.get_tk_widget().pack(fill='both', expand=True)

        self.spectral_vars: Dict[str, tk.StringVar] = {}

        _metrics_enumeration(GUI_METRIC_LABELS['spec_freq'],  self.spectral_vars, psd_metrics_subfrm_freq)
        _metrics_enumeration(GUI_METRIC_LABELS['spec_bands'], self.spectral_vars, psd_metrics_subfrm_band)


        ## ==== tab: STOCHASTIC PARAMETERS =====================================
        tab_stc = ttk.Frame(right)
        right.add(tab_stc, text="Stochastic Parameters")

        tab_stc.columnconfigure(0, weight=0)  # metrics
        tab_stc.columnconfigure(1, weight=1)  # plot
        tab_stc.rowconfigure(0, weight=1)
        
        stc_metrics_frm = ttk.LabelFrame(tab_stc, text="Spectral Parameters", labelanchor='n')
        stc_metrics_frm.grid(row=0, column=0, sticky='nsw', padx=3, pady=3)
        
        stc_plot_frm = ttk.Frame(tab_stc)
        stc_plot_frm.grid(row=0, column=1, sticky='nsew', padx=6, pady=6)

        stc_metrics_subfrm_sda = ttk.LabelFrame(stc_metrics_frm, text="Stabilogram Diffusion analysis", labelanchor='n')
        stc_metrics_subfrm_sda.grid(row=0, column=0, sticky='new', padx=0, pady=3)

        stc_metrics_subfrm_crit = ttk.LabelFrame(stc_metrics_frm, text="Critical Time & MSD", labelanchor='n')
        stc_metrics_subfrm_crit.grid(row=1, column=0, sticky='new', padx=0, pady=3)

        self.stochastic_vars: Dict[str, tk.StringVar] = {}

        _metrics_enumeration(GUI_METRIC_LABELS['stc_sda'],      self.stochastic_vars, stc_metrics_subfrm_sda)
        _metrics_enumeration(GUI_METRIC_LABELS['stc_critical'], self.stochastic_vars, stc_metrics_subfrm_crit)


        ## ==== tab: LOGS =============
        tab_logs = ttk.Frame(right)
        right.add(tab_logs, text="Logs")
        self.txt_logs = tk.Text(tab_logs, height=10)
        self.txt_logs.configure(font=self.ui_fixed)
        self.txt_logs.pack(fill='both', expand=True)

    ## =========================================================================
    ## == METHODS ==============================================================
    ## =========================================================================    

    def add_files(self):
        paths = filedialog.askopenfilenames(
            title="Select OpenSway / BrainBloX recordings",
            filetypes=[("csv", "*.csv"), ("All", "*.*")]
        )
        for p in paths:
            self.add_path(p)

    def add_path(self, p: str, process: bool = False):
        """Ajoute un fichier à la liste ; `process` = l'analyser et l'afficher."""
        if p and p not in self.files:
            self.files.append(p)
            name = os.path.splitext(os.path.basename(p))[0]
            self.file_list.insert('end', name)
        if process:
            i = self.files.index(p)
            self.file_list.selection_clear(0, 'end')
            self.file_list.selection_set(i)
            self.file_list.see(i)
            self.on_file_selected(None)

    def clear_files(self):
        self.files.clear()
        self.results.clear()
        self.cache.clear()
        self.file_list.delete(0, 'end')

    def _refresh_params(self):
        self.params.target_fs     = float(self.var_fs.get())
        self.params.butter_fc     = float(self.var_fc.get())
        self.params.butter_order  = int(self.var_order.get())
        self.params.savgol_enable = bool(self.var_sg.get())
        self.params.savgol_win_s  = float(self.var_sg_win.get())
        self.params.savgol_poly   = int(self.var_sg_poly.get())
        self.params.seg_seconds   = float(self.var_segsec.get())
        self.params.fmax          = self.params.butter_fc
        self.params.resampling    = str(self.var_resamp.get())
        self.params.swarii_win_s  = float(self.var_sw_win.get())

    def process_selected(self):
        
        self._refresh_params()
        sels = self.file_list.curselection()
        
        if not sels:
            # si rien sélectionné, traiter tous
            idxs = range(self.file_list.size())
        else:
            idxs = sels

        results = []

        for i in idxs:
            path = self.files[i]          # chemin complet
            name = os.path.basename(path) # pour les titres de graph
            try:
                df, series = run_pipeline(path, self.params)
                results.append(df)

                metrics_dict = df.iloc[0].to_dict()
                # on met en cache pour un usage ultérieur
                self.cache[path] = (metrics_dict, series)

                self._update_positional_metrics(metrics_dict)
                self._update_dynamic_metrics(metrics_dict)
                self._update_spectral_metrics(metrics_dict)
                self._update_stochastic_metrics(metrics_dict)

                self._plot_series(os.path.basename(path), series, metrics_dict, self.params)

                self._log(f"[OK] {os.path.basename(path)} processed.")
            except Exception as e:
                self._log(f"[ERROR] {os.path.basename(path)}: {e}")
                self._log(traceback.format_exc())

        if results:
            self.results.append(pd.concat(results, ignore_index=True))

    def on_file_selected(self, event):
        sels = self.file_list.curselection()
        if not sels:
            return

        i = sels[0]

        if i >= len(self.files):
            return
        path = self.files[i]
        name = os.path.basename(path)

        if path in self.cache:
            metrics_dict, series = self.cache[path]
        else:
            try:
                df, series       = run_pipeline(path, self.params)
                metrics_dict     = df.iloc[0].to_dict()
                self.cache[path] = (metrics_dict, series)
            except Exception as e:
                self._log(f"[ERROR] {os.path.basename(path)} (on select): {e}")
                self._log(traceback.format_exc())
                return

        self._update_positional_metrics(metrics_dict)
        self._update_dynamic_metrics(metrics_dict)
        self._update_spectral_metrics(metrics_dict)
        self._update_stochastic_metrics(metrics_dict)
        self._plot_series(name, series, metrics_dict, self.params)

    def _plot_series(self, name: str, series: Dict[str, np.ndarray], metrics: dict, p: Params):
        t         = series['t']
        x_filt    = series['x_filt']
        y_filt    = series['y_filt']
        x         = series['x']
        y         = series['y']
        filename  = os.path.splitext(name)[0]


        # == plot: STABILOGRAM ===
        pl.plot_stabilogram(self.ax_stab, t, x, y, filename)
        self.fig_stab.subplots_adjust(left=0.08, right=0.98, bottom=0.18, top=0.88)
        self.canvas_stab.draw()

        # == plot: STATOKINESIGRAM ===
        pl.plot_statokinesigram(self.ax_skg, x_filt, y_filt, filename)
        self.fig_skg.subplots_adjust(left=0.12, right=0.98, bottom=0.12, top=0.88)
        self.canvas_skg.draw()

        # ==== plot: WELCH SPECTRUM ========
        pl.plot_welch_spectrum(self.ax_psd, x, y, p, filename)
        self.ax_psd.set_xlabel("")

        # ==== RADAR : normalized energy bands, ML vs AP ==========
        pl.plot_energy_radar(self.ax_band, metrics, filename)
        self.fig_psd.subplots_adjust(left=0.10, right=0.82, bottom=0.08, top=0.88, hspace=0.35)
        self.canvas_psd.draw()

    def export_all(self):

        if not self.files:
            messagebox.showinfo("Export Error", "No file in the list.")
            return

        if not hasattr(self, "cache"):
            self.cache = {}

        self._refresh_params()

        metrics_per_file = {}
        for path in self.files:
            name = os.path.splitext(os.path.basename(path))[0]

            if path in self.cache:
                metrics_dict, _ = self.cache[path]
            else:
                try:
                    df, series = run_pipeline(path, self.params)
                    metrics_dict = df.iloc[0].to_dict()
                    self.cache[path] = (metrics_dict, series)
                except Exception as e:
                    self._log(f"[ERROR] {os.path.basename(path)} (export all): {e}")
                    self._log(traceback.format_exc())
                    continue

            metrics_per_file[name] = metrics_dict

        if not metrics_per_file:
            messagebox.showinfo("Export Error", "No metrics available to export.")
            return

        df = pd.DataFrame(metrics_per_file)

        path = filedialog.asksaveasfilename(
            title="Export all results",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")]
        )

        if not path:
            return

        try:
            if path.lower().endswith(".csv"):
                df.to_csv(path, sep=";", index=True)
                sheets = ["Essais"]
            else:
                sheets = export_excel(path, metrics_per_file)
            self._log(f"[Export all] {os.path.basename(path)} ({', '.join(sheets)})")

        except Exception as e:
            messagebox.showerror("Export Error", str(e))
            self._log(f"[ERROR] export_all: {e}")

    def export_report(self):

        sels = self.file_list.curselection()
        if not sels:
            messagebox.showinfo("Export report", "Please select at least one file in the list.")
            return

        path_pdf = filedialog.asksaveasfilename(
            title="Export report as PDF",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")]
        )
        if not path_pdf:
            return

        self._refresh_params()

        files = [self.files[i] for i in sels if i < len(self.files)]
        if not files:
            messagebox.showinfo("Export report", "No valid file selected.")
            return

        with PdfPages(path_pdf) as pdf:
            for i in sels:
                if i >= len(self.files):
                    continue
                path = self.files[i]
                name = os.path.splitext(os.path.basename(path))[0]

                if path in getattr(self, "cache", {}):
                    metrics_dict, series = self.cache[path]
                else:
                    try:
                        df, series   = run_pipeline(path, self.params)
                        metrics_dict = df.iloc[0].to_dict()
                        if not hasattr(self, "cache"):
                            self.cache   = {}
                        self.cache[path] = (metrics_dict, series)
                    except Exception as e:
                        self._log(f"[ERROR] {os.path.basename(path)} (export report): {e}")
                        self._log(traceback.format_exc())
                        continue

                figs = make_report_figures(name, series, metrics_dict, self.params)
                for fig in figs:
                    pdf.savefig(fig)


        self._log(f"[Report] Exported PDF: {os.path.basename(path_pdf)}")

    def _log(self, msg: str):
        self.txt_logs.insert("end", msg + "\n")
        self.txt_logs.see("end")

    def _update_positional_metrics(self, metrics: dict):
        fmt = lambda v: v if isinstance(v, str) else ("" if v is None else str(v))

        self.pos_duration_var.set(str(metrics.get('duration')))

        mapping = {
            "ML mean position     (cm) ":  f"{metrics.get('mean_ML')} ±{metrics.get('std_ML')}",
            "AP mean position     (cm) ":  f"{metrics.get('mean_AP')} ±{metrics.get('std_AP')}",

            "ML RMS               (cm) ":  metrics.get('pos_rms_ML'),
            "AP RMS               (cm) ":  metrics.get('pos_rms_AP'),
            "Global RMS radius    (cm) ":  metrics.get('pos_rms_radius'),
            "Planar deviation     (cm) ":  metrics.get('pos_planarDev'),

            "ML mean distance     (cm) ":  metrics.get('pos_meanDist_ML'),
            "AP mean distance     (cm) ":  metrics.get('pos_meanDist_AP'),
            "Mean radius          (cm) ":  metrics.get('pos_meanDist'),
            "ML maximal distance  (cm) ":  metrics.get('pos_max_ML'),
            "AP maximal distance  (cm) ":  metrics.get('pos_max_AP'),
            "Maximal radius       (cm) ":  metrics.get('pos_max_radius'),
            "ML range             (cm) ":  metrics.get('pos_range_ML'),
            "AP range             (cm) ":  metrics.get('pos_range_AP'),
            "AP-ML range          (cm) ":  metrics.get('pos_range_AP-ML'),
            "Range ratio           (-) ":  metrics.get('pos_rangeRatio'),

            "Sway direct° coeff.   (-) ":  metrics.get('pos_swaydirCoeff'),
            "95% ellipse area    (cm²) ":  metrics.get('pos_ellipse95_area'),
            "Princ. sway direct°   (°) ":  metrics.get('pos_princSwaydir'),
        }
        for label, var in self.positional_vars.items():
            var.set(fmt(mapping.get(label)))

    def _update_dynamic_metrics(self, metrics: dict):
        fmt = lambda v: v if isinstance(v, str) else ("" if v is None else str(v))

        mapping = {
            "ML path length       (cm) ":  metrics.get('dyn_length_ML'),
            "AP path length       (cm) ":  metrics.get('dyn_length_AP'),
            "Global path length   (cm) ":  metrics.get('dyn_length_global'),
            "LFS                (cm⁻¹) ":  metrics.get('dyn_lfs'),

            "ML mean velocity   (cm/s) ":  f"{metrics.get('dyn_meanVeloc_ML')} ±{metrics.get('dyn_sdVeloc_ML')}",
            "AP mean velocity   (cm/s) ":  f"{metrics.get('dyn_meanVeloc_AP')} ±{metrics.get('dyn_sdVeloc_AP')}",
            "Global mean vel.   (cm/s) ":  f"{metrics.get('dyn_meanVeloc_global')} ±{metrics.get('dyn_sdVeloc_global')}",
            "ML 0-crossings set    (-) ":  metrics.get('dyn_zeroCross_ML'),
            "AP 0-crossings set    (-) ":  metrics.get('dyn_zeroCross_AP'),

            "ML mean frequency    (Hz) ":  metrics.get('dyn_meanFreq_ML'),
            "AP mean frequency    (Hz) ":  metrics.get('dyn_meanFreq_AP'),
            "Global mean freq.    (Hz) ":  metrics.get('dyn_meanfreq_global'),

            "VFY                   (-) ":  metrics.get('dyn_vfy'),
            "Area per second   (cm²/s) ":  metrics.get('dyn_swayAreaPerS'),
            "ML phase plane            ":  metrics.get('dyn_phasePlane_ML'),
            "AP phase plane            ":  metrics.get('dyn_phasePlane_AP'),
            # "Fractal dimension         ": ,
            "ML peak pos. vel.  (cm/s) ":  metrics.get('dyn_mppPos_ML'),
            "ML peak neg. vel.  (cm/s) ":  metrics.get('dyn_mppNeg_ML'),
            "ML mean peak vel.  (cm/s) ":  metrics.get('dyn_mppAbs_ML'),
            "AP peak pos. vel.  (cm/s) ":  metrics.get('dyn_mppPos_AP'),
            "AP peak neg. vel.  (cm/s) ":  metrics.get('dyn_mppNeg_AP'),
            "AP mean peak vel.  (cm/s) ":  metrics.get('dyn_mppAbs_AP'),
            "Mean SD peaks dist.  (cm) ":  metrics.get('dyn_meanSdPeakDist'),
            "Mean peaks' interval  (s) ":  metrics.get('dyn_meanPeakInterval')
        }
        for label, var in self.dynamic_vars.items():
            var.set(fmt(mapping.get(label)))

    def _update_spectral_metrics(self, metrics: dict):
        fmt3 = lambda v: "" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.3f}"
        fmt2 = lambda v: "" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.2f}"

        map_specfreq = {
            "ML total power      (cm²) ":  metrics.get('frq_total_power_ML'),
            "AP total power      (cm²) ":  metrics.get('frq_total_power_AP'),

            "ML 50% power freq.   (Hz) ":  metrics.get('frq_f50_ML'),
            "AP 50% power freq.   (Hz) ":  metrics.get('frq_f50_AP'),
            "ML 95% power freq.   (Hz) ":  metrics.get('frq_f95_ML'),
            "AP 95% power freq.   (Hz) ":  metrics.get('frq_f95_AP'),

            "ML power mode        (Hz) ":  metrics.get('frq_power_mode_ML'),
            "AP power mode        (Hz) ":  metrics.get('frq_power_mode_AP'),

            "ML centroidal freq.  (Hz) ":  metrics.get('frq_centroid_freq_ML', metrics.get('dyn_meanFreq_ML')),
            "AP centroidal freq.  (Hz) ":  metrics.get('frq_centroid_freq_AP', metrics.get('dyn_meanFreq_AP')),

            "ML freq. dispersion   (-) ":  metrics.get('frq_freq_disp_ML'),
            "AP freq. dispersion   (-) ":  metrics.get('frq_freq_disp_AP')
        }
        for label, value in map_specfreq.items():
            var = self.spectral_vars.get(label)
            if var is not None:
                var.set(fmt3(value))
        
        map_specband = {
            "ML [0-0.5] Hz       (cm²) ":  metrics.get('frq_energy_0_05_ML'),
            "AP [0-0.5] Hz       (cm²) ":  metrics.get('frq_energy_0_05_AP'),
            "ML [0.5–2] Hz       (cm²) ":  metrics.get('frq_energy_05_2_ML'),
            "AP [0.5–2] Hz       (cm²) ":  metrics.get('frq_energy_05_2_AP'),
            "ML  [2–5]  Hz       (cm²) ":  metrics.get('frq_energy_2_5_ML'),
            "AP  [2–5]  Hz       (cm²) ":  metrics.get('frq_energy_2_5_AP'),

            "ML freq. quotient     (-) ":  metrics.get('frq_freq_quotient_ML'),
            "AP freq. quotient     (-) ":  metrics.get('frq_freq_quotient_AP')
        }
        for label, value in map_specband.items():
            var = self.spectral_vars.get(label)
            if var is not None:
                var.set(fmt2(value))

    def _update_stochastic_metrics(self, metrics: dict):
        fmt3 = lambda v: "" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.3f}"
        fmt2 = lambda v: "" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.2f}"

        map_sda = {
            "ML ST Hurst exp.      (-) ":  metrics.get('stc_HurstShortTerm_ML'),
            "AP ST Hurst exp.      (-) ":  metrics.get('stc_HurstShortTerm_AP'),
            "ML LT Hurst exp.      (-) ":  metrics.get('stc_HurstLongTerm_ML'),
            "AP LT Hurst exp.      (-) ":  metrics.get('stc_HurstLongTerm_AP'),

            "ML ST diffus. coeff.  (-) ":  metrics.get('stc_DiffShortTerm_ML'),
            "AP ST diffus. coeff.  (-) ":  metrics.get('stc_DiffShortTerm_AP'),
            "ML LT diffus. coeff.  (-) ":  metrics.get('stc_DiffLongTerm_ML'),
            "AP LT diffus. coeff.  (-) ":  metrics.get('stc_DiffLongTerm_AP'),
        }

        for label, value in map_sda.items():
            var = self.stochastic_vars.get(label)
            if var is not None:
                var.set(fmt3(value))

        map_crit = {
            "Radial trans° time Tc (s) ":  metrics.get('stc_transTime_radial'),
            "Radial MSD at Tc    (cm²) ":  metrics.get('stc_MSD_radial')
        }

        for label, value in map_crit.items():
            var = self.stochastic_vars.get(label)
            if var is not None:
                var.set(fmt2(value))
