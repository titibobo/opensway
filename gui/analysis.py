"""Onglet « Analyse » : reprise de BrainBloX_analysis v2.3 (mise en page inchangée)."""
import os
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

import numpy as np
import pandas as pd

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.backends.backend_pdf import PdfPages
from typing import List, Tuple, Dict

from core                    import plotting as pl
from core.params             import Params
from core.params             import load_logo
from core.params             import GUI_METRIC_LABELS
from core.params             import ADVANCED_SETTINGS, RQA_MODES, RESAMPLING_MODES
from core.pipeline           import run_pipeline
from core.export_pdf_report  import make_report_figures, make_subject_report
from core.design             import parse_name, folder_factors, aggregate_metrics, with_trial_sd
from core.design             import time_order_key, describe_file
from core.design             import build_tables, settings_table, write_results
from core.fileformat         import read_header
from core.i18n               import tr, metric_label, metric_tooltip, get_language, LANGUAGES

from gui.common              import ToolTip, resource_path, center_window, save_config, VERSION

from dataclasses import fields


class AnalysisPanel(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app      = app
        self.ui_fixed = app.ui_fixed
        self.style    = app.style

        self.params = Params()
        self.files:   List[str] = []
        self.results: List[pd.DataFrame] = []
        self.cache:   Dict[str, Tuple[dict, Dict[str, np.ndarray]]] = {}

        self.iid2path: Dict[str, str] = {}      # file row id -> full path
        self.design:   Dict[str, List[str]] = {}  # file row id -> [name, subject, trial, f1, f2, cond]
        self.unit2fids: Dict[str, List[str]] = {} # subject row id -> file row ids
        self._iid_count    = 0
        self.factor_names  = [tr("Group"), tr("Time")]  # renamable (click on header)


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

                label_name = ttk.Label(subframe, text=metric_label(label))
                label_name.grid(row=i, column=0, sticky='w', padx=4, pady=1)

                tip = metric_tooltip(label)
                if tip:
                    ToolTip(label_name, tip)

                ttk.Label(subframe, textvariable=var, width=13, anchor='center',
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

        # ==== File section =============
        left.rowconfigure(5, weight=1)

        ttk.Label(left, text=tr("Recordings (OpenSway / BrainBloX)")).grid(row=2, column=0, sticky='ew')

        btn_frm = ttk.Frame(left)
        btn_frm.grid(row=3, column=0, sticky='ew', pady=2)
        btn_frm.columnconfigure(0, weight=1)
        btn_frm.columnconfigure(1, weight=1)
        ttk.Button(btn_frm, text=tr("Add files..."),   command=self.add_files).grid(row=0, column=0, sticky='ew', padx=(0, 1))
        ttk.Button(btn_frm, text=tr("Add folder..."),  command=self.add_folder).grid(row=0, column=1, sticky='ew', padx=(1, 0))

        self.view_mode = tk.StringVar(value='files')
        view_frm = ttk.Frame(left)
        view_frm.grid(row=4, column=0, sticky='ew', pady=(4, 0))
        ttk.Label(view_frm, text=tr("View:")).grid(row=0, column=0, sticky='w')
        ttk.Radiobutton(view_frm, text=tr("Files"),    value='files',    variable=self.view_mode,
                        command=self._refresh_tree).grid(row=0, column=1, sticky='w', padx=4)
        ttk.Radiobutton(view_frm, text=tr("Subjects"), value='subjects', variable=self.view_mode,
                        command=self._refresh_tree).grid(row=0, column=2, sticky='w', padx=4)

        tree_frm = ttk.Frame(left)
        tree_frm.grid(row=5, column=0, sticky='nsew', pady=4)
        tree_frm.rowconfigure(0, weight=1)
        tree_frm.columnconfigure(0, weight=1)

        self.style.configure('Treeview', font=self.ui_fixed, rowheight=16)
        self.style.configure('Treeview.Heading', font=self.ui_fixed)

        cols = ('file', 'subject', 'trial', 'f1', 'f2', 'cond')
        self.file_tree = ttk.Treeview(tree_frm, columns=cols, show='headings',
                                      selectmode='extended', height=14)
        heads  = (tr("File"), tr("Subject"), "N°", self.factor_names[0], self.factor_names[1],
                  tr("Cond."))
        widths = (90, 50, 24, 48, 38, 62)
        for c, h, w in zip(cols, heads, widths):
            self.file_tree.column(c, width=w, minwidth=20, stretch=(c == 'file'), anchor='w')
            self.file_tree.heading(c, text=h, anchor='w')
        self.file_tree.heading('f1', command=lambda: self._rename_factor(0))
        self.file_tree.heading('f2', command=lambda: self._rename_factor(1))

        tree_sb = ttk.Scrollbar(tree_frm, orient='vertical', command=self.file_tree.yview)
        self.file_tree.configure(yscrollcommand=tree_sb.set)
        self.file_tree.grid(row=0, column=0, sticky='nsew')
        tree_sb.grid(row=0, column=1, sticky='ns')

        self.file_tree.bind("<<TreeviewSelect>>", self.on_file_selected)
        self.file_tree.bind("<Double-1>",         self._edit_cell)

        edit_frm = ttk.Frame(left)
        edit_frm.grid(row=6, column=0, sticky='ew', pady=2)
        edit_frm.columnconfigure(0, weight=1)
        edit_frm.columnconfigure(1, weight=1)
        btn_edit = ttk.Button(edit_frm, text=tr("Edit selection..."), command=self.open_edit_selection)
        btn_edit.grid(row=0, column=0, sticky='ew', padx=(0, 1))
        ttk.Button(edit_frm, text=tr("Empty list"), command=self.clear_files).grid(row=0, column=1, sticky='ew', padx=(1, 0))
        ToolTip(btn_edit, tr(
            "Set Subject / factors for the selected files (empty field = unchanged),\n"
            "and rename the factors. A single cell can also be edited by double-click.\n"
            "\nSubject and trial n° are read from file names (ID_1 or ID_n°1),\n"
            "factors from the parent folder name (group_time),\n"
            "eyes and surface from an OpenSway condition folder (YO-dur)."),
            delay_ms=250
        )

        sep3 = ttk.Separator(left, orient='horizontal')
        sep3.grid(row=7, column=0, sticky='ew', pady=8)

        ttk.Button(left, text=tr("Advanced settings..."),   command=self.open_settings).grid(row=8, column=0, sticky='ew', pady=2)
        ttk.Button(left, text=tr("Process filelist"),       command=self.process_selected).grid(row=9, column=0, sticky='ew', pady=2)
        ttk.Button(left, text=tr("Compare..."),             command=self.open_compare).grid(row=10, column=0, sticky='ew', pady=2)
        ttk.Button(left, text=tr("Export selected report"), command=self.export_report).grid(row=11, column=0, sticky='ew', pady=2)
        ttk.Button(left, text=tr("Export all results"),     command=self.export_all).grid(row=12, column=0, sticky='ew', pady=2)


        ## =====================================================================
        ## == RIGHT PANEL (DISPLAYS) =====
        ## =====================================================================

        right = ttk.Notebook(self)
        right.grid(row=0, column=1, sticky='nsew', padx=3, pady=3)

        ## ==== tab: POSITIONAL PARAMETERS =====================================
        tab_pos = ttk.Frame(right)
        right.add(tab_pos, text=tr("Positional Parameters"))

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

        ttk.Label(duration_frm, text=metric_label("Duration              (s) ")).grid(
            row=0, column=0, sticky='w', padx=4, pady=1)

        ttk.Label(duration_frm, textvariable=self.pos_duration_var,
                    width=13, anchor='center', relief='sunken').grid(
                            row=0, column=1, sticky='w', padx=4, pady=1)
        

        pos_metrics_subfrm_cntr = ttk.LabelFrame(pos_metrics_frm,
                        text=tr("Center Position & Dispersion"), labelanchor='n')
        pos_metrics_subfrm_cntr.grid(row=1, column=0, sticky='new', padx=0, pady=3)

        pos_metrics_subfrm_dists = ttk.LabelFrame(pos_metrics_frm,
                        text=tr("Distances & Amplitudes"), labelanchor='n')
        pos_metrics_subfrm_dists.grid(row=2, column=0, sticky='new', padx=0, pady=3)

        pos_metrics_subfrm_geom = ttk.LabelFrame(pos_metrics_frm,
                        text=tr("Geometry & Direction"), labelanchor='n')
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
        right.add(tab_dyn, text=tr("Dynamic Parameters"))

        tab_dyn.columnconfigure(0, weight=0)  # metrics
        tab_dyn.columnconfigure(1, weight=1)  # plot
        tab_dyn.rowconfigure(0, weight=1)

        dyn_metrics_frm = ttk.Frame(tab_dyn)
        dyn_metrics_frm.grid(row=0, column=0, sticky='nsw', padx=3, pady=3)
      
        duration_frm = ttk.Frame(dyn_metrics_frm)
        duration_frm.grid(row=0, column=0, sticky='new', padx=0, pady=(0, 3))

        ttk.Label(duration_frm, text=metric_label("Duration              (s) ")).grid(
            row=0, column=0, sticky='w', padx=4, pady=1)

        ttk.Label(duration_frm, textvariable=self.pos_duration_var,
                    width=13, anchor='center', relief='sunken').grid(
                            row=0, column=1, sticky='w', padx=4, pady=1)


        dyn_metrics_subfrm_timedep = ttk.LabelFrame(dyn_metrics_frm,
                        text=tr("Duration-dep. Metrics"), labelanchor='n')
        dyn_metrics_subfrm_timedep.grid(row=1, column=0, sticky='new', padx=0, pady=3)

        dyn_metrics_subfrm_vel = ttk.LabelFrame(dyn_metrics_frm,
                        text=tr("Velocities"), labelanchor='n')
        dyn_metrics_subfrm_vel.grid(row=2, column=0, sticky='new', padx=0, pady=3)

        dyn_metrics_subfrm_freq = ttk.LabelFrame(dyn_metrics_frm,
                        text=tr("Temporal Frequencies"), labelanchor='n')
        dyn_metrics_subfrm_freq.grid(row=3, column=0, sticky='new', padx=0, pady=3)

        dyn_metrics_subfrm_adv = ttk.LabelFrame(dyn_metrics_frm,
                        text=tr("Advanced Dynamics"), labelanchor='n')
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
        right.add(tab_psd, text=tr("Spectral Analysis"))

        tab_psd.columnconfigure(0, weight=0)  # metrics
        tab_psd.columnconfigure(1, weight=1)  # plot
        tab_psd.rowconfigure(0, weight=1)
        
        psd_metrics_frm = ttk.LabelFrame(tab_psd, text=tr("Spectral Parameters"), labelanchor='n')
        psd_metrics_frm.grid(row=0, column=0, sticky='nsw', padx=3, pady=3)
        
        psd_plot_frm    = ttk.Frame(tab_psd)
        psd_plot_frm.grid(row=0, column=1, sticky='nsew', padx=6, pady=6)

        psd_metrics_subfrm_freq = ttk.LabelFrame(psd_metrics_frm, text=tr("Frequency Metrics"), labelanchor='n')
        psd_metrics_subfrm_freq.grid(row=0, column=0, sticky='new', padx=0, pady=3)

        psd_metrics_subfrm_band = ttk.LabelFrame(psd_metrics_frm, text=tr("Band Energies"), labelanchor='n')
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


        ## ==== tab: STOCHASTIC & NONLINEAR PARAMETERS =========================
        tab_stc = ttk.Frame(right)
        right.add(tab_stc, text=tr("Stochastic & Nonlinear"))

        tab_stc.columnconfigure(0, weight=0)  # stochastic metrics
        tab_stc.columnconfigure(1, weight=0)  # nonlinear metrics
        tab_stc.columnconfigure(2, weight=1)  # plots
        tab_stc.rowconfigure(0, weight=1)

        stc_metrics_frm = ttk.LabelFrame(tab_stc, text=tr("Stochastic Parameters"), labelanchor='n')
        stc_metrics_frm.grid(row=0, column=0, sticky='nsw', padx=3, pady=3)

        nl_metrics_frm = ttk.LabelFrame(tab_stc, text=tr("Nonlinear Parameters"), labelanchor='n')
        nl_metrics_frm.grid(row=0, column=1, sticky='nsw', padx=3, pady=3)

        stc_plot_frm = ttk.Frame(tab_stc)
        stc_plot_frm.grid(row=0, column=2, sticky='nsew', padx=3, pady=3)

        stc_metrics_subfrm_sda = ttk.LabelFrame(stc_metrics_frm, text=tr("Stabilogram Diffusion analysis"), labelanchor='n')
        stc_metrics_subfrm_sda.grid(row=0, column=0, sticky='new', padx=0, pady=3)

        stc_metrics_subfrm_crit = ttk.LabelFrame(stc_metrics_frm, text=tr("Critical Time & MSD"), labelanchor='n')
        stc_metrics_subfrm_crit.grid(row=1, column=0, sticky='new', padx=0, pady=3)

        nl_metrics_subfrm_ent = ttk.LabelFrame(nl_metrics_frm, text=tr("Sample Entropy"), labelanchor='n')
        nl_metrics_subfrm_ent.grid(row=0, column=0, sticky='new', padx=0, pady=3)

        nl_metrics_subfrm_dfa = ttk.LabelFrame(nl_metrics_frm, text=tr("Detrended Fluctuation Analysis"), labelanchor='n')
        nl_metrics_subfrm_dfa.grid(row=1, column=0, sticky='new', padx=0, pady=3)

        nl_metrics_subfrm_rqa = ttk.LabelFrame(nl_metrics_frm, text=tr("Recurrence Quantification"), labelanchor='n')
        nl_metrics_subfrm_rqa.grid(row=2, column=0, sticky='new', padx=0, pady=3)

        nl_metrics_subfrm_emb = ttk.LabelFrame(nl_metrics_frm, text=tr("RQA Embedding"), labelanchor='n')
        nl_metrics_subfrm_emb.grid(row=3, column=0, sticky='new', padx=0, pady=3)

        self.fig_nl  = Figure(figsize=(3.5, 6), dpi=100)
        gs_nl        = self.fig_nl.add_gridspec(3, 1, height_ratios=[1, 1, 1.25], hspace=0.55)

        self.ax_sda  = self.fig_nl.add_subplot(gs_nl[0, 0])
        self.ax_dfa  = self.fig_nl.add_subplot(gs_nl[1, 0])
        self.ax_rp   = self.fig_nl.add_subplot(gs_nl[2, 0])

        self.canvas_nl = FigureCanvasTkAgg(self.fig_nl, master=stc_plot_frm)
        self.canvas_nl.get_tk_widget().pack(fill='both', expand=True)

        self.stochastic_vars: Dict[str, tk.StringVar] = {}
        self.nonlinear_vars:  Dict[str, tk.StringVar] = {}

        _metrics_enumeration(GUI_METRIC_LABELS['stc_sda'],      self.stochastic_vars, stc_metrics_subfrm_sda)
        _metrics_enumeration(GUI_METRIC_LABELS['stc_critical'], self.stochastic_vars, stc_metrics_subfrm_crit)

        _metrics_enumeration(GUI_METRIC_LABELS['nl_entropy'],   self.nonlinear_vars,  nl_metrics_subfrm_ent)
        _metrics_enumeration(GUI_METRIC_LABELS['nl_dfa'],       self.nonlinear_vars,  nl_metrics_subfrm_dfa)
        _metrics_enumeration(GUI_METRIC_LABELS['nl_rqa'],       self.nonlinear_vars,  nl_metrics_subfrm_rqa)
        _metrics_enumeration(GUI_METRIC_LABELS['nl_embedding'], self.nonlinear_vars,  nl_metrics_subfrm_emb)


        ## ==== tab: LOGS =============
        tab_logs = ttk.Frame(right)
        right.add(tab_logs, text=tr("Logs"))
        self.txt_logs = tk.Text(tab_logs, height=10)
        self.txt_logs.configure(font=self.ui_fixed)
        self.txt_logs.pack(fill='both', expand=True)

    ## =========================================================================
    ## == METHODS ==============================================================
    ## =========================================================================    

    def _insert_file(self, p: str):
        if not p or p in self.files:
            return False
        self.files.append(p)
        try:
            meta = read_header(p)
        except Exception:
            meta = {}
        d    = describe_file(p, meta)
        cond = "-".join(x for x in (d['eyes'], d['surface']) if x)
        name = os.path.splitext(os.path.basename(p))[0]
        fid  = f"f{self._iid_count}"
        self._iid_count += 1
        self.iid2path[fid] = p
        self.design[fid]   = [name, d['subject'], d['trial'], d['f1'], d['f2'], cond]
        return bool(d['f1'] or d['f2'])

    def add_path(self, p: str, process: bool = False):
        """ Fichier enregistré par l'onglet Acquisition : ajout, puis analyse et affichage """
        self.view_mode.set('files')
        self._insert_file(p)
        self._refresh_tree()
        fid = next((f for f, q in self.iid2path.items() if q == p), None)
        if fid and process:
            self.file_tree.selection_set(fid)
            self.file_tree.see(fid)
            self.on_file_selected(None)

    def add_files(self):
        paths = filedialog.askopenfilenames(
            title=tr("Select OpenSway / BrainBloX recordings"),
            filetypes=[("csv", "*.csv"), ("All", "*.*")]
        )
        n_fact = sum(self._insert_file(p) for p in paths)
        self._refresh_tree()
        if paths:
            self._log(f"[Add files] {len(paths)} file(s), factors read for {n_fact}")

    def add_folder(self):
        root = filedialog.askdirectory(title=tr("Select a folder (csv files, sub-folders: group_time)"))
        if not root:
            return
        paths  = sorted(str(f) for f in Path(root).rglob("*.csv"))
        n_fact = sum(self._insert_file(p) for p in paths)
        self._refresh_tree()
        self._log(f"[Add folder] {len(paths)} csv file(s) in {os.path.basename(root)}, "
                  f"factors read for {n_fact}")

    def clear_files(self):
        self.files.clear()
        self.results.clear()
        self.cache.clear()
        self.iid2path.clear()
        self.design.clear()
        self.unit2fids.clear()
        self.file_tree.delete(*self.file_tree.get_children())

    # == File table: Files / Subjects views ====================================
    def _refresh_tree(self):
        tree = self.file_tree
        tree.delete(*tree.get_children())

        if self.view_mode.get() == 'files':
            tree.configure(displaycolumns=('file', 'subject', 'trial', 'f1', 'f2', 'cond'))
            tree.heading('trial', text="N°")
            tree.column('subject', width=50)
            for fid, vals in self.design.items():
                tree.insert('', 'end', iid=fid, values=vals)
        else:
            tree.configure(displaycolumns=('subject', 'trial', 'f1', 'f2', 'cond'))
            tree.heading('trial', text="n")
            tree.column('subject', width=140)
            self.unit2fids.clear()
            for k, (key, fids) in enumerate(self._units().items()):
                iid = f"s{k}"
                self.unit2fids[iid] = fids
                tree.insert('', 'end', iid=iid, values=("", key[0], len(fids), key[1], key[2], key[3]))

    def _units(self) -> Dict[Tuple[str, str, str, str], List[str]]:
        """ (subject, f1, f2, cond) -> file row ids, in list order """
        units: Dict[Tuple[str, str, str, str], List[str]] = {}
        for fid, (_, subject, _, f1, f2, cond) in self.design.items():
            units.setdefault((subject, f1, f2, cond), []).append(fid)
        return units

    @staticmethod
    def _unit_label(*parts: str) -> str:
        return " ".join(x for x in parts if x)

    def _selected_paths(self) -> List[str]:
        sel  = set(self.file_tree.selection())
        rows = [i for i in self.file_tree.get_children() if i in sel]
        if self.view_mode.get() == 'files':
            return [self.iid2path[i] for i in rows]
        return [self.iid2path[f] for i in rows for f in self.unit2fids.get(i, [])]

    def _all_paths(self) -> List[str]:
        return [self.iid2path[f] for f in self.design]

    # == File table editing ====================================================
    def _rename_factor(self, k: int):
        name = simpledialog.askstring(tr("Rename factor"),
                                      tr("New name for '{}':").format(self.factor_names[k]),
                                      initialvalue=self.factor_names[k], parent=self)
        if not name or not name.strip():
            return
        name = name.strip()
        if name in ("File", "Subject", "Trial", tr("File"), tr("Subject"), self.factor_names[1 - k]):
            messagebox.showinfo(tr("Rename factor"), tr("'{}' is already used.").format(name))
            return
        self.factor_names[k] = name
        self.file_tree.heading(('f1', 'f2')[k], text=name)

    def _edit_cell(self, event):
        tree = self.file_tree
        if self.view_mode.get() != 'files':
            return
        if tree.identify_region(event.x, event.y) != 'cell':
            return
        col = tree.identify_column(event.x)          # '#1' ... '#5'
        row = tree.identify_row(event.y)
        if not row or col == '#1':                   # file name not editable
            return

        col_id = ('file', 'subject', 'trial', 'f1', 'f2', 'cond')[int(col[1:]) - 1]
        bbox   = tree.bbox(row, col)
        if not bbox:
            return
        x, y, w, h = bbox

        entry = ttk.Entry(tree)
        entry.insert(0, tree.set(row, col_id))
        entry.select_range(0, 'end')
        entry.place(x=x, y=y, width=max(w, 60), height=h)
        entry.focus_set()

        sel     = tree.selection()
        targets = sel if row in sel else (row,)

        def _commit(_evt=None):
            value = entry.get().strip()
            idx   = ('file', 'subject', 'trial', 'f1', 'f2', 'cond').index(col_id)
            for iid in targets:
                tree.set(iid, col_id, value)
                self.design[iid][idx] = value
            entry.destroy()

        entry.bind("<Return>",   _commit)
        entry.bind("<FocusOut>", _commit)
        entry.bind("<Escape>",   lambda _e: entry.destroy())

    def open_edit_selection(self):
        if self.view_mode.get() != 'files':
            messagebox.showinfo(tr("Edit selection"), tr("Switch to the 'Files' view to edit the design."))
            return

        sel = self.file_tree.selection()

        win = tk.Toplevel(self)
        win.title(tr("Edit selection"))
        win.transient(self)
        win.resizable(False, False)

        frm_val = ttk.LabelFrame(win, text=tr("Values for the {} selected file(s)").format(len(sel)), labelanchor='n')
        frm_val.grid(row=0, column=0, sticky='ew', padx=6, pady=4)
        frm_fac = ttk.LabelFrame(win, text=tr("Factor names"), labelanchor='n')
        frm_fac.grid(row=1, column=0, sticky='ew', padx=6, pady=4)

        v_subj = tk.StringVar()
        v_f1   = tk.StringVar()
        v_f2   = tk.StringVar()
        v_cond = tk.StringVar()
        n_f1   = tk.StringVar(value=self.factor_names[0])
        n_f2   = tk.StringVar(value=self.factor_names[1])

        for i, (lab, var) in enumerate(((tr("Subject"), v_subj),
                                        (self.factor_names[0], v_f1),
                                        (self.factor_names[1], v_f2),
                                        (tr("Condition"), v_cond))):
            ttk.Label(frm_val, text=lab).grid(row=i, column=0, sticky='w', padx=4, pady=2)
            ttk.Entry(frm_val, textvariable=var, width=16).grid(row=i, column=1, sticky='w', padx=4)
        ttk.Label(frm_val, text=tr("(empty field = unchanged)")).grid(row=4, column=0, columnspan=2, sticky='w', padx=4)
        if not sel:
            ttk.Label(frm_val, text=tr("No file selected: only factor names can be changed."),
                      foreground='#ae4c00').grid(row=5, column=0, columnspan=2, sticky='w', padx=4)

        for i, (lab, var) in enumerate(((tr("Factor 1"), n_f1), (tr("Factor 2"), n_f2))):
            ttk.Label(frm_fac, text=lab).grid(row=i, column=0, sticky='w', padx=4, pady=2)
            ttk.Entry(frm_fac, textvariable=var, width=16).grid(row=i, column=1, sticky='w', padx=4)

        def _apply():
            names = [n_f1.get().strip() or self.factor_names[0],
                     n_f2.get().strip() or self.factor_names[1]]
            if names[0] == names[1] or set(names) & {"File", "Subject", "Trial",
                                                    tr("File"), tr("Subject")}:
                messagebox.showerror(tr("Edit selection"),
                                     tr("Factor names must differ from each other\n"
                                        "and from 'File', 'Subject', 'Trial'."), parent=win)
                return
            self.factor_names = names
            self.file_tree.heading('f1', text=names[0])
            self.file_tree.heading('f2', text=names[1])

            for idx, var in ((1, v_subj), (3, v_f1), (4, v_f2), (5, v_cond)):
                value = var.get().strip()
                if not value:
                    continue
                for fid in sel:
                    if fid in self.design:
                        self.design[fid][idx] = value
            self._refresh_tree()
            for fid in sel:
                if self.file_tree.exists(fid):
                    self.file_tree.selection_add(fid)
            win.destroy()

        btns = ttk.Frame(win)
        btns.grid(row=2, column=0, sticky='e', padx=6, pady=6)
        ttk.Button(btns, text=tr("Cancel"), command=win.destroy).grid(row=0, column=0, padx=2)
        ttk.Button(btns, text=tr("OK"),     command=_apply).grid(row=0, column=1, padx=2)

        center_window(win, self.winfo_toplevel())
        try:
            win.grab_set()
        except tk.TclError:
            pass

    # == Advanced settings =====================================================
    def open_settings(self):
        win = tk.Toplevel(self)
        win.title(tr("Advanced settings"))
        win.transient(self)
        win.resizable(False, False)

        defaults = Params()
        types    = {f.name: type(getattr(defaults, f.name)) for f in fields(Params)}
        tkvars: Dict[str, tk.Variable] = {}
        frames: Dict[str, ttk.LabelFrame] = {}
        rows:   Dict[str, int] = {}

        for group, attr, label in ADVANCED_SETTINGS:
            if group not in frames:
                k  = len(frames)
                fr = ttk.LabelFrame(win, text=tr(group), labelanchor='n')
                fr.grid(row=k // 2, column=k % 2, sticky='new', padx=6, pady=4)
                frames[group], rows[group] = fr, 0
            fr, i = frames[group], rows[group]
            value = getattr(self.params, attr)

            ttk.Label(fr, text=tr(label)).grid(row=i, column=0, sticky='w', padx=4, pady=2)
            if types[attr] is bool:
                var = tk.BooleanVar(value=value)
                ttk.Checkbutton(fr, variable=var).grid(row=i, column=1, sticky='w', padx=4)
            elif attr in ("rqa_mode", "resampling"):
                var = tk.StringVar(value=value)
                ttk.Combobox(fr, textvariable=var, state='readonly', width=12,
                             values=RQA_MODES if attr == "rqa_mode" else RESAMPLING_MODES
                             ).grid(row=i, column=1, sticky='w', padx=4)
            else:
                var = tk.StringVar(value=str(value))
                ttk.Entry(fr, textvariable=var, width=8).grid(row=i, column=1, sticky='w', padx=4)
            tkvars[attr]  = var
            rows[group]  += 1

        # Interface : langue (appliquée au prochain démarrage)
        k  = len(frames)
        fr = ttk.LabelFrame(win, text=tr("Interface"), labelanchor='n')
        fr.grid(row=k // 2, column=k % 2, sticky='new', padx=6, pady=4)
        frames["Interface"] = fr
        lang_var = tk.StringVar(value=get_language())
        ttk.Label(fr, text=tr("Language")).grid(row=0, column=0, sticky='w', padx=4, pady=2)
        ttk.Combobox(fr, textvariable=lang_var, values=LANGUAGES, state='readonly',
                     width=12).grid(row=0, column=1, sticky='w', padx=4)

        def _reset():
            for attr, var in tkvars.items():
                d = getattr(defaults, attr)
                var.set(d if types[attr] in (bool, str) else str(d))

        def _convert(attr: str, v):
            t = types[attr]
            if t is bool:
                return bool(v)
            if t is int:
                return int(float(v))
            if t is float:
                return float(v)
            return str(v)

        def _apply():
            new = {}
            for attr, var in tkvars.items():
                try:
                    new[attr] = _convert(attr, var.get())
                except ValueError:
                    messagebox.showerror(tr("Advanced settings"), tr("Invalid value for '{}'.").format(attr), parent=win)
                    return
            changed = [a for a, v in new.items() if getattr(self.params, a) != v]
            for attr, v in new.items():
                setattr(self.params, attr, v)
            self._refresh_params()
            if changed:
                self.cache.clear()
                self._log(f"[Settings] changed: {', '.join(changed)} (results will be recomputed)")
            if lang_var.get() != get_language():
                save_config(language=lang_var.get())
                messagebox.showinfo(tr("Language"),
                                    tr("The language will change at the next start of OpenSway."),
                                    parent=win)
            win.destroy()

        btns = ttk.Frame(win)
        btns.grid(row=(len(frames) + 1) // 2, column=0, columnspan=2, sticky='e', padx=6, pady=6)
        ttk.Button(btns, text=tr("Reset to defaults"), command=_reset).grid(row=0, column=0, padx=2)
        ttk.Button(btns, text=tr("Cancel"),            command=win.destroy).grid(row=0, column=1, padx=2)
        ttk.Button(btns, text=tr("OK"),                command=_apply).grid(row=0, column=2, padx=2)

        center_window(win, self.winfo_toplevel())
        try:
            win.grab_set()
        except tk.TclError:
            pass

    def _refresh_params(self):
        self.params.fmax = self.params.butter_fc

    # == Processing ============================================================
    def _get_results(self, path: str, context: str = ""):
        if path in self.cache:
            return self.cache[path]
        try:
            df, series       = run_pipeline(path, self.params)
            metrics_dict     = df.iloc[0].to_dict()
            self.cache[path] = (metrics_dict, series)
            return self.cache[path]
        except Exception as e:
            self._log(f"[ERROR] {os.path.basename(path)}{context}: {e}")
            self._log(traceback.format_exc())
            return None

    def _show_results(self, path: str, metrics_dict: dict, series: Dict[str, np.ndarray]):
        self._update_positional_metrics(metrics_dict)
        self._update_dynamic_metrics(metrics_dict)
        self._update_spectral_metrics(metrics_dict)
        self._update_stochastic_metrics(metrics_dict)
        self._update_nonlinear_metrics(metrics_dict)
        self._plot_series(os.path.basename(path), series, metrics_dict, self.params)

    def process_selected(self):

        self._refresh_params()

        # si rien sélectionné, traiter tous
        paths = self._selected_paths() or self._all_paths()

        results, last = [], None

        for k, path in enumerate(paths, 1):
            self.cache.pop(path, None)                 # forced recomputation
            res = self._get_results(path)
            if res is not None:
                results.append(pd.DataFrame([res[0]]))
                last = (path, res)
                self._log(f"[OK] ({k}/{len(paths)}) {os.path.basename(path)} processed.")
            self.update_idletasks()

        # displays: selected subject, or last processed file (faster on large lists)
        sel = self.file_tree.selection()
        if self.view_mode.get() == 'subjects' and sel:
            self._show_unit(sel[0])
        elif last is not None:
            path, (metrics_dict, series) = last
            self._show_results(path, metrics_dict, series)

        if results:
            self.results.append(pd.concat(results, ignore_index=True))

    def on_file_selected(self, event):
        sel = self.file_tree.selection()
        if not sel:
            return
        if self.view_mode.get() == 'subjects':
            self._show_unit(sel[0])
            return
        path = self.iid2path.get(sel[0])
        if path is None:
            return

        res = self._get_results(path, " (on select)")
        if res is None:
            return
        metrics_dict, series = res
        self._show_results(path, metrics_dict, series)

    def _unit_data(self, fids: List[str]):
        """ Trials of a subject row: (series list, metrics list) of the valid files """
        series_list, metrics_list = [], []
        for fid in fids:
            res = self._get_results(self.iid2path[fid], " (subject)")
            if res is not None:
                metrics_list.append(res[0])
                series_list.append(res[1])
            self.update_idletasks()
        return series_list, metrics_list

    def _show_unit(self, uid: str):
        fids = self.unit2fids.get(uid)
        if not fids:
            return
        _, subject, _, f1, f2, cond = self.design[fids[0]]
        series_list, metrics_list = self._unit_data(fids)
        if not series_list:
            return

        agg  = aggregate_metrics(metrics_list)
        name = self._unit_label(subject, f1, f2, cond) + f" ({tr('mean of {}').format(len(series_list))})"

        disp = with_trial_sd(agg)
        self._update_positional_metrics(disp)
        self._update_dynamic_metrics(disp)
        self._update_spectral_metrics(agg)
        self._update_stochastic_metrics(agg)
        self._update_nonlinear_metrics(agg)
        self._plot_subject(name, series_list, agg, self.params)

    def _plot_subject(self, name: str, series_list: List[Dict[str, np.ndarray]], metrics: dict, p: Params):

        # == plot: STABILOGRAMS + STATOKINESIGRAMS (trials overlaid) ===
        pl.plot_stabilogram_multi(self.ax_stab, series_list, name)
        self.fig_stab.subplots_adjust(left=0.08, right=0.98, bottom=0.18, top=0.88)
        self.canvas_stab.draw()

        pl.plot_statokinesigram_multi(self.ax_skg, series_list, name)
        self.fig_skg.subplots_adjust(left=0.12, right=0.98, bottom=0.12, top=0.88)
        self.canvas_skg.draw()

        # ==== WELCH SPECTRA + RADAR (mean band energies) ========
        pl.plot_welch_spectrum_multi(self.ax_psd, series_list, p, name)
        self.ax_psd.set_xlabel("")
        pl.plot_energy_radar(self.ax_band, metrics, name)
        self.fig_psd.subplots_adjust(left=0.10, right=0.82, bottom=0.08, top=0.88, hspace=0.35)
        self.canvas_psd.draw()

        # ==== STOCHASTIC & NONLINEAR : SDA + DFA (overlaid) + recurrence plot (trial 1) ===
        pl.plot_sda_multi(self.ax_sda, series_list, p, name)
        pl.plot_dfa_multi(self.ax_dfa, series_list, p, name)
        pl.plot_recurrence(self.ax_rp, series_list[0]['y'], p, name + f" {tr('trial')} 1", "AP")
        self.fig_nl.subplots_adjust(left=0.18, right=0.96, bottom=0.07, top=0.95)
        self.canvas_nl.draw()

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

        # ==== STOCHASTIC & NONLINEAR : SDA + DFA + AP recurrence plot ==========
        pl.plot_sda(self.ax_sda, x, y, p, filename)
        pl.plot_dfa(self.ax_dfa, x, y, p, filename)
        pl.plot_recurrence(self.ax_rp, y, p, filename, "AP")
        self.fig_nl.subplots_adjust(left=0.18, right=0.96, bottom=0.07, top=0.95)
        self.canvas_nl.draw()

    def export_all(self):

        paths = self._all_paths()
        if not paths:
            messagebox.showinfo(tr("Export Error"), tr("No file in the list."))
            return

        self._refresh_params()

        rows = []
        for fid, (name, subject, trial, f1, f2, cond) in self.design.items():
            path = self.iid2path[fid]
            res  = self._get_results(path, " (export all)")
            if res is None:
                continue
            eyes, _, surface = cond.partition("-")
            rows.append({'file': name, 'subject': subject, 'trial': trial,
                         'f1': f1, 'f2': f2, 'eyes': eyes, 'surface': surface,
                         'metrics': res[0]})
            self.update_idletasks()

        if not rows:
            messagebox.showinfo(tr("Export Error"), tr("No metrics available to export."))
            return

        means, trials = build_tables(rows, self.factor_names)
        settings      = settings_table(self.params, VERSION)

        path = filedialog.asksaveasfilename(
            title=tr("Export all results"),
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")]
        )

        if not path:
            return

        try:
            written = write_results(path, means, trials, settings)
            self._log(f"[Export all] {len(trials)} trial(s), {len(means)} mean(s) -> "
                      + ", ".join(os.path.basename(w) for w in written))

        except Exception as e:
            messagebox.showerror(tr("Export Error"), str(e))
            self._log(f"[ERROR] export_all: {e}")

    def export_report(self):

        if self.view_mode.get() == 'subjects':
            self.export_subject_report()
            return

        files = self._selected_paths()
        if not files:
            messagebox.showinfo(tr("Export report"), tr("Please select at least one file in the list."))
            return

        path_pdf = filedialog.asksaveasfilename(
            title=tr("Export report as PDF"),
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")]
        )
        if not path_pdf:
            return

        self._refresh_params()

        with PdfPages(path_pdf) as pdf:
            for path in files:
                name = os.path.splitext(os.path.basename(path))[0]

                res = self._get_results(path, " (export report)")
                if res is None:
                    continue
                metrics_dict, series = res

                figs = make_report_figures(name, series, metrics_dict, self.params)
                for fig in figs:
                    pdf.savefig(fig)


        self._log(f"[Report] Exported PDF: {os.path.basename(path_pdf)}")

    def export_subject_report(self):
        """ One patient report per selected Subject x factor 1, all levels of factor 2 """

        sel = [i for i in self.file_tree.get_children() if i in set(self.file_tree.selection())]
        if not sel:
            messagebox.showinfo(tr("Export report"), tr("Please select at least one subject in the list."))
            return

        path_pdf = filedialog.asksaveasfilename(
            title=tr("Export patient report as PDF"),
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")]
        )
        if not path_pdf:
            return

        self._refresh_params()

        units   = self._units()
        targets: List[Tuple[str, str, str]] = []
        for uid in sel:
            _, subject, _, f1, _, cond = self.design[self.unit2fids[uid][0]]
            if (subject, f1, cond) not in targets:
                targets.append((subject, f1, cond))

        with PdfPages(path_pdf) as pdf:
            for subject, f1, cond in targets:
                levels = []
                for (s_, g_, lvl, c_), fids in units.items():
                    if (s_, g_, c_) != (subject, f1, cond):
                        continue
                    series_list, metrics_list = self._unit_data(fids)
                    if series_list:
                        levels.append((lvl, series_list, aggregate_metrics(metrics_list)))
                if not levels:
                    continue
                levels.sort(key=lambda lv: time_order_key(lv[0]))
                figs = make_subject_report(self._unit_label(subject, f1, cond),
                                           self.factor_names[1], levels, self.params)
                for fig in figs:
                    pdf.savefig(fig)
                self._log(f"[Report] {self._unit_label(subject, f1, cond)}: {len(levels)} condition(s)")

        self._log(f"[Report] Exported patient PDF: {os.path.basename(path_pdf)}")

    def open_compare(self):
        from gui.compare import CompareWindow
        w = getattr(self, "_compare", None)
        if w is not None and w.winfo_exists():
            w.refresh_items()
            w.lift()
            return
        self._compare = CompareWindow(self)

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
            "Fractal dimension     (-) ":  metrics.get('dyn_fractalDim'),
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
            "ML crit. time Tc      (s) ":  metrics.get('stc_critTime_ML'),
            "AP crit. time Tc      (s) ":  metrics.get('stc_critTime_AP'),
            "ML MSD at Tc        (cm²) ":  metrics.get('stc_critMSD_ML'),
            "AP MSD at Tc        (cm²) ":  metrics.get('stc_critMSD_AP')
        }

        for label, value in map_crit.items():
            var = self.stochastic_vars.get(label)
            if var is not None:
                var.set(fmt2(value))

    def _update_nonlinear_metrics(self, metrics: dict):
        fmt3 = lambda v: "" if v is None or (isinstance(v, float) and np.isnan(v)) else f"{v:.3f}"
        fmt  = lambda v: "" if v is None or (isinstance(v, float) and np.isnan(v)) else str(v)

        map_ent = {
            "ML sample entropy     (-) ":  metrics.get('nl_sampEn_ML'),
            "AP sample entropy     (-) ":  metrics.get('nl_sampEn_AP'),

            "ML DFA α short-term   (-) ":  metrics.get('nl_dfaAlphaShort_ML'),
            "AP DFA α short-term   (-) ":  metrics.get('nl_dfaAlphaShort_AP'),
            "ML DFA α long-term    (-) ":  metrics.get('nl_dfaAlphaLong_ML'),
            "AP DFA α long-term    (-) ":  metrics.get('nl_dfaAlphaLong_AP'),

            "ML RQA line entropy   (-) ":  metrics.get('nl_rqaEntr_ML'),
            "AP RQA line entropy   (-) ":  metrics.get('nl_rqaEntr_AP')
        }

        for label, value in map_ent.items():
            var = self.nonlinear_vars.get(label)
            if var is not None:
                var.set(fmt3(value))

        map_rqa = {
            "ML RQA recurrence     (%) ":  metrics.get('nl_rqaRec_ML'),
            "AP RQA recurrence     (%) ":  metrics.get('nl_rqaRec_AP'),
            "ML RQA determinism    (%) ":  metrics.get('nl_rqaDet_ML'),
            "AP RQA determinism    (%) ":  metrics.get('nl_rqaDet_AP'),
            "ML RQA max. line    (pts) ":  metrics.get('nl_rqaLmax_ML'),
            "AP RQA max. line    (pts) ":  metrics.get('nl_rqaLmax_AP'),

            "ML embedding dim.     (-) ":  metrics.get('nl_rqaDim_ML'),
            "AP embedding dim.     (-) ":  metrics.get('nl_rqaDim_AP'),
            "ML embedding delay    (s) ":  metrics.get('nl_rqaDelay_ML'),
            "AP embedding delay    (s) ":  metrics.get('nl_rqaDelay_AP')
        }

        for label, value in map_rqa.items():
            var = self.nonlinear_vars.get(label)
            if var is not None:
                var.set(fmt(value))
