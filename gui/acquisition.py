"""Onglet « Acquisition » : connexion, tare, conditions, séries d'essais, tracé temps réel."""
import os
import re
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from core.fileformat import write_recording
from core.i18n import fr
from gui.common import ToolTip, Blitter, VERSION

BOARD_W, BOARD_H = 51.0, 31.0          # dimensions extérieures (cm), pour le dessin
MIN_WEIGHT_KG    = 15.0
REFRESH_MS       = 50

EYES     = [("Yeux ouverts", "YO"), ("Yeux fermés", "YF")]
SURFACES = [("Sol dur", "dur"), ("Mousse", "mousse")]


def _safe(s: str, underscore: bool = True) -> str:
    """Nom utilisable dans un chemin. Sans « _ » pour groupe / temps, car le
    dossier « groupe_temps » est découpé sur le premier « _ » à l'analyse."""
    keep = r"[^A-Za-z0-9+_-]+" if underscore else r"[^A-Za-z0-9+-]+"
    return re.sub(keep, "-", s.strip()).strip("-")


def next_trial_index(folder: str, subject: str) -> int:
    """Premier n° d'essai libre pour ce sujet dans ce dossier (rien n'est écrasé)."""
    pat = re.compile(rf"^{re.escape(subject)}_(\d+)\.csv$", re.IGNORECASE)
    try:
        nums = [int(m.group(1)) for f in os.listdir(folder) if (m := pat.match(f))]
    except FileNotFoundError:
        nums = []
    return max(nums, default=0) + 1


class AcquisitionPanel(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        self.state = "idle"          # idle | countdown | recording | pause | wait
        self.t_state = 0.0
        self.trial = 0
        self.series_id = ""
        self.series_dir = ""
        self._count = 0
        self._build()
        self.after(REFRESH_MS, self._tick)

    # ================================================================ LAYOUT
    def _build(self):
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        left = ttk.Frame(self, padding=10)
        left.grid(row=0, column=0, sticky='ns')
        left.columnconfigure(0, weight=1)
        LW = 16                              # largeur des libellés (alignement)

        # ---- Planche -------------------------------------------------------
        frm = ttk.LabelFrame(left, text=fr("Planche"))
        frm.grid(row=0, column=0, sticky='ew')
        frm.columnconfigure(1, weight=1)

        self.var_source = tk.StringVar(value="wbb")
        src = ttk.Frame(frm)
        src.grid(row=0, column=0, columnspan=2, sticky='w', padx=4, pady=2)
        ttk.Radiobutton(src, text="Wii Balance Board", value="wbb",
                        variable=self.var_source).pack(side='left')
        ttk.Radiobutton(src, text=fr("Simulateur"), value="sim",
                        variable=self.var_source).pack(side='left', padx=(8, 0))

        btns = ttk.Frame(frm)
        btns.grid(row=1, column=0, columnspan=2, sticky='ew', padx=4, pady=2)
        btns.columnconfigure((0, 1, 2), weight=1, uniform='b')
        self.btn_connect = ttk.Button(btns, text=fr("Connecter"), command=self.connect)
        self.btn_connect.grid(row=0, column=0, sticky='ew', padx=(0, 2))
        self.btn_tare = ttk.Button(btns, text=fr("Tare"), command=self.tare, state='disabled')
        self.btn_tare.grid(row=0, column=1, sticky='ew', padx=2)
        self.btn_disc = ttk.Button(btns, text=fr("Déconnecter"), command=self.disconnect,
                                   state='disabled')
        self.btn_disc.grid(row=0, column=2, sticky='ew', padx=(2, 0))
        ToolTip(self.btn_tare, fr("Mise à zéro des 4 capteurs, planche VIDE.\n"
                                  "À refaire si la planche a été déplacée."))

        self.var_status = tk.StringVar(value=fr("Non connectée"))
        self.var_batt   = tk.StringVar(value="-")
        self.var_weight = tk.StringVar(value="-")
        self.var_tare   = tk.StringVar(value=fr("non faite"))
        self._tare_done = False
        for i, (lab, var) in enumerate([("Statut", self.var_status),
                                        ("Batterie", self.var_batt),
                                        ("Charge", self.var_weight),
                                        ("Tare", self.var_tare)], start=2):
            ttk.Label(frm, text=fr(lab), width=LW).grid(row=i, column=0, sticky='w', padx=4, pady=1)
            ttk.Label(frm, textvariable=var, width=22, anchor='w').grid(
                row=i, column=1, sticky='w', padx=4, pady=1)

        # ---- Sujet & conditions -------------------------------------------
        frm = ttk.LabelFrame(left, text=fr("Sujet & conditions"))
        frm.grid(row=1, column=0, sticky='ew', pady=(8, 0))
        self.var_subject = tk.StringVar()
        self.var_group   = tk.StringVar()
        self.var_time    = tk.StringVar()
        self.var_eyes    = tk.StringVar(value="YO")
        self.var_surface = tk.StringVar(value="dur")
        self.var_note    = tk.StringVar()

        entries = [("Sujet (code)", self.var_subject,
                    "Code pseudonyme du sujet (ex. S012).\nÉviter nom / prénom : il figure "
                    "dans le nom du fichier."),
                   ("Groupe",       self.var_group,
                    "Facultatif (ex. ttt, sim). Avec le temps, donne le dossier\n"
                    "« groupe_temps », reconnu à l'analyse comme dans la v2.3."),
                   ("Temps",        self.var_time,
                    "Facultatif (ex. AV, AP, T0, T1).")]
        for r, (lab, var, tip) in enumerate(entries):
            ttk.Label(frm, text=fr(lab), width=LW).grid(row=r, column=0, sticky='w', padx=4, pady=2)
            e = ttk.Entry(frm, textvariable=var, width=22)
            e.grid(row=r, column=1, sticky='w', padx=4, pady=2)
            ToolTip(e, fr(tip))

        for r, (lab, var, opts) in enumerate([("Yeux", self.var_eyes, EYES),
                                              ("Surface", self.var_surface, SURFACES)], start=3):
            ttk.Label(frm, text=fr(lab), width=LW).grid(row=r, column=0, sticky='w', padx=4, pady=2)
            f = ttk.Frame(frm)
            f.grid(row=r, column=1, sticky='w', padx=4, pady=2)
            for j, (txt, val) in enumerate(opts):
                ttk.Radiobutton(f, text=fr(txt), value=val, variable=var,
                                command=self._sync_simulator).grid(row=0, column=j, sticky='w',
                                                                   padx=(0, 8))

        ttk.Label(frm, text=fr("Note"), width=LW).grid(row=5, column=0, sticky='w', padx=4, pady=2)
        ttk.Entry(frm, textvariable=self.var_note, width=22).grid(row=5, column=1, sticky='w',
                                                                  padx=4, pady=2)

        # ---- Protocole -----------------------------------------------------
        frm = ttk.LabelFrame(left, text=fr("Protocole"))
        frm.grid(row=2, column=0, sticky='ew', pady=(8, 0))
        self.var_dur    = tk.StringVar(value="60")
        self.var_ntrial = tk.IntVar(value=3)
        self.var_pause  = tk.StringVar(value="30")
        self.var_wait   = tk.BooleanVar(value=False)
        self.var_cd     = tk.StringVar(value="3")

        rows = [("Durée (s)",          ttk.Entry(frm, textvariable=self.var_dur, width=6)),
                ("Nombre d'essais",    ttk.Spinbox(frm, from_=1, to=10, width=5,
                                                   textvariable=self.var_ntrial)),
                ("Pause (s)",          ttk.Entry(frm, textvariable=self.var_pause, width=6)),
                ("Décompte (s)",       ttk.Entry(frm, textvariable=self.var_cd, width=6))]
        for r, (lab, w) in enumerate(rows):
            ttk.Label(frm, text=fr(lab), width=LW).grid(row=r, column=0, sticky='w', padx=4, pady=2)
            w.grid(row=r, column=1, sticky='w', padx=4, pady=2)
        cb = ttk.Checkbutton(frm, text=fr("Attendre ma validation entre essais"),
                             variable=self.var_wait)
        cb.grid(row=4, column=0, columnspan=2, sticky='w', padx=4, pady=2)
        ToolTip(cb, fr("Si coché, l'essai suivant ne démarre qu'au clic sur « Essai suivant »\n"
                       "(sinon il démarre automatiquement après la pause)."))
        ToolTip(rows[0][1], fr("60 s par défaut : au moins 60 s pour l'entropie d'échantillon\n"
                               "(Montesinos et al., 2018) ; 90 s pour la fiabilité des\n"
                               "paramètres classiques (Ruhe et al., 2010)."))
        ToolTip(rows[1][1], fr("3 essais par défaut : moyenner 3 à 5 répétitions\n"
                               "(Ruhe et al., 2010)."))

        # ---- Dossier -------------------------------------------------------
        frm = ttk.LabelFrame(left, text=fr("Dossier d'enregistrement"))
        frm.grid(row=3, column=0, sticky='ew', pady=(8, 0))
        frm.columnconfigure(0, weight=1)
        self.out_dir = str(Path.home() / "Documents" / "OpenSway")
        self.var_dir = tk.StringVar(value=self._short(self.out_dir))
        ttk.Label(frm, textvariable=self.var_dir, width=30, anchor='w').grid(
            row=0, column=0, sticky='ew', padx=4, pady=2)
        ttk.Button(frm, text="…", width=3, command=self.choose_dir).grid(
            row=0, column=1, sticky='e', padx=4, pady=2)

        # ---- Commandes -----------------------------------------------------
        cmd = ttk.Frame(left)
        cmd.grid(row=4, column=0, sticky='ew', pady=(10, 0))
        cmd.columnconfigure((0, 1), weight=1, uniform='c')
        self.btn_start = ttk.Button(cmd, text="▶ " + fr("Démarrer"), style='Big.TButton',
                                    command=self.start_series)
        self.btn_start.grid(row=0, column=0, sticky='ew', padx=(0, 2))
        self.btn_stop = ttk.Button(cmd, text="■ " + fr("Arrêter"), style='Big.TButton',
                                   command=self.stop_series, state='disabled')
        self.btn_stop.grid(row=0, column=1, sticky='ew', padx=(2, 0))
        self.btn_next = ttk.Button(cmd, text=fr("Essai suivant") + " ▶", command=self.next_trial,
                                   state='disabled')
        self.btn_next.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(4, 0))

        self.var_progress = tk.StringVar(value="")
        ttk.Label(left, textvariable=self.var_progress, anchor='w').grid(
            row=5, column=0, sticky='ew', pady=(6, 0))

        # ---- Tracés temps réel --------------------------------------------
        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky='nsew', padx=3, pady=3)
        self.fig = Figure(figsize=(7, 5), dpi=100)
        gs = self.fig.add_gridspec(2, 2, width_ratios=[1.25, 1], hspace=0.35, wspace=0.25)
        self.ax_cop = self.fig.add_subplot(gs[:, 0])
        self.ax_ml  = self.fig.add_subplot(gs[0, 1])
        self.ax_ap  = self.fig.add_subplot(gs[1, 1], sharex=self.ax_ml)
        self._init_plots()
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
        self.blit = Blitter(self.canvas, [self.ln_trail, self.ln_dot, self.txt_big,
                                          self.ln_ml, self.ln_ap])
        self._last_full = 0.0

        self.var_statusline = tk.StringVar(value="")
        ttk.Label(right, textvariable=self.var_statusline, anchor='w').pack(fill='x')

    def _init_plots(self):
        ax = self.ax_cop
        ax.add_patch(Rectangle((-BOARD_W / 2, -BOARD_H / 2), BOARD_W, BOARD_H,
                               facecolor='#f4f4f4', edgecolor='0.6', lw=1))
        ax.axhline(0, color='0.8', lw=0.8)
        ax.axvline(0, color='0.8', lw=0.8)
        self.ln_trail, = ax.plot([], [], lw=0.8, color='#1688c8', alpha=0.7)
        self.ln_dot,   = ax.plot([], [], 'o', ms=9, color='#e4572e')
        ax.set_xlim(-BOARD_W / 2 - 1, BOARD_W / 2 + 1)
        ax.set_ylim(-BOARD_H / 2 - 1, BOARD_H / 2 + 1)
        ax.set_aspect('equal', adjustable='box')
        ax.set_xlabel(fr("ML (cm)   gauche ← → droite"), fontsize=8)
        ax.set_ylabel(fr("AP (cm)   arrière ← → avant"), fontsize=8)
        ax.tick_params(labelsize=7)
        ax.set_title(fr("Centre de pression (temps réel)"), fontsize=9)
        self.txt_big = ax.text(0, 0, "", ha='center', va='center', fontsize=40,
                               color='#e4572e', alpha=0.85, fontweight='bold')

        for a, lab, col in ((self.ax_ml, "ML (cm)", '#0e5780'), (self.ax_ap, "AP (cm)", '#ff8d4d')):
            a.set_ylabel(lab, fontsize=8)
            a.tick_params(labelsize=7)
            a.grid(True, alpha=0.25)
        self.ln_ml, = self.ax_ml.plot([], [], lw=1, color='#0e5780')
        self.ln_ap, = self.ax_ap.plot([], [], lw=1, color='#ff8d4d')
        self.ax_ml.set_title(fr("10 dernières secondes"), fontsize=9)
        self.ax_ap.set_xlabel(fr("Temps (s)"), fontsize=8)
        self.fig.subplots_adjust(left=0.08, right=0.98, bottom=0.10, top=0.93)

    @staticmethod
    def _short(p: str, n: int = 30) -> str:
        return p if len(p) <= n else "…" + p[-(n - 1):]

    def set_status_line(self, msg: str):
        self.var_statusline.set(msg.splitlines()[-1] if msg else "")

    # ============================================================ CONNEXION
    def connect(self):
        self.btn_connect.configure(state='disabled')
        self.var_status.set(fr("Connexion…"))
        self.app.board.connect(self.var_source.get(), self._on_connect)

    def _on_connect(self, status, msg):
        if status == "ok":
            self._connected_ui(msg)
            return
        if status == "not_found" and self.var_source.get() == "wbb":
            if messagebox.askokcancel(
                    fr("Planche non trouvée"),
                    fr("La planche n'est pas connectée.\n\n"
                       "Appuie sur le bouton rouge SYNC (sous le capot des piles) :\n"
                       "la LED clignote. Puis clique sur OK.\n\n"
                       "(Si la planche a déjà été appairée sur ce PC, le bouton POWER\n"
                       "peut suffire : appuie dessus puis clique sur Annuler et réessaie.)")):
                self.var_status.set(fr("Appairage…"))
                self.app.log(fr("[BT] Appairage en cours (20-40 s)…"))
                self.app.board.pair_and_connect(self._on_connect_after_pair)
                return
        self.var_status.set(fr("Non connectée"))
        self.btn_connect.configure(state='normal')
        self.app.log(f"[Connexion] {msg}")
        if status == "error":
            messagebox.showerror(fr("Connexion"), msg)

    def _on_connect_after_pair(self, status, msg):
        if status == "ok":
            self._connected_ui(msg)
        else:
            self.var_status.set(fr("Non connectée"))
            self.btn_connect.configure(state='normal')
            self.app.log(f"[Connexion] {msg}")
            messagebox.showwarning(fr("Connexion"),
                                   msg + "\n\n" + fr("Réessaie : bouton SYNC puis Connecter."))

    def _connected_ui(self, msg):
        dev = self.app.board.device
        self.var_status.set(fr(dev.name))
        self.var_tare.set(fr("non faite"))
        self._tare_done = False
        self.btn_connect.configure(state='disabled')
        self.btn_disc.configure(state='normal')
        self.btn_tare.configure(state='normal')
        self._count = 0
        self._sync_simulator()
        self.app.log(f"[Connexion] {msg}")
        if dev.cal:
            self.app.log(f"[Connexion] {fr('Calibration usine')} : {dev.cal}")
        if messagebox.askyesno(fr("Tare"), fr("Faire la tare maintenant ?\n(planche vide)")):
            self.tare()

    def disconnect(self):
        if self.busy_recording():
            return
        self.app.board.disconnect()
        self.var_status.set(fr("Non connectée"))
        self.var_batt.set("-")
        self.var_weight.set("-")
        self.btn_connect.configure(state='normal')
        self.btn_disc.configure(state='disabled')
        self.btn_tare.configure(state='disabled')

    def _sync_simulator(self):
        dev = self.app.board.device
        if self.app.board.is_simulator:
            k = 1.0 if self.var_eyes.get() == "YO" else 1.6
            k *= 1.0 if self.var_surface.get() == "dur" else 1.7
            dev.instability = k

    # ================================================================= TARE
    def tare(self):
        r = self.app.board.reader
        if r is None or self.busy_recording():
            return
        if not messagebox.askokcancel(fr("Tare"), fr("Personne sur la planche ?\n"
                                                    "Clique sur OK, la tare dure 2 s.")):
            return
        self.btn_tare.configure(state='disabled')
        r.start_tare()
        self.var_tare.set(fr("en cours…"))

        def done():
            n = r.finish_tare()
            self.btn_tare.configure(state='normal')
            self._tare_done = bool(n)
            self.var_tare.set(f"{fr('faite')} ({datetime.now():%H:%M})" if n else fr("échec"))
            self.app.log(f"[Tare] {n} {fr('mesures')}, offsets kg (TL TR BL BR) = "
                         + " ".join(f"{v:+.3f}" for v in r.tare))
        self.after(2000, done)

    # ============================================================ PROTOCOLE
    def busy_recording(self) -> bool:
        return self.state in ("countdown", "recording", "pause", "wait")

    def choose_dir(self):
        d = filedialog.askdirectory(initialdir=self.out_dir, title=fr("Dossier d'enregistrement"))
        if d:
            self.out_dir = d
            self.var_dir.set(self._short(d))

    def start_series(self):
        r = self.app.board.reader
        if r is None:
            messagebox.showinfo(fr("Démarrer"), fr("Connecte d'abord la planche (ou le simulateur)."))
            return
        subj = self.var_subject.get().strip()
        if not subj:
            messagebox.showinfo(fr("Démarrer"), fr("Renseigne le code du sujet."))
            return
        try:
            self.dur    = float(str(self.var_dur.get()).replace(',', '.'))
            self.ntrial = int(self.var_ntrial.get())
            self.pause  = float(str(self.var_pause.get()).replace(',', '.'))
            self.cd     = int(float(self.var_cd.get()))
            assert self.dur >= 5 and self.ntrial >= 1 and self.pause >= 0 and self.cd >= 0
        except Exception:
            messagebox.showerror(fr("Démarrer"), fr("Paramètres du protocole invalides "
                                                    "(durée ≥ 5 s, essais ≥ 1)."))
            return
        if not self._tare_done:
            if not messagebox.askyesno(fr("Démarrer"), fr("La tare n'a pas été faite. Continuer ?")):
                return
        if self._current_weight() < MIN_WEIGHT_KG:
            if not messagebox.askyesno(fr("Démarrer"), fr("Personne ne semble être sur la planche.\n"
                                                          "Démarrer quand même ?")):
                return
        # Rangement (convention v2.3) : <dossier>/<groupe_temps>/<YO-dur>/<sujet>_<n>.csv
        grp, tps = _safe(self.var_group.get(), False), _safe(self.var_time.get(), False)
        parts = [self.out_dir]
        if grp or tps:
            parts.append(f"{grp}_{tps}")
        parts.append(f"{self.var_eyes.get()}-{self.var_surface.get()}")
        self.series_dir = os.path.join(*parts)
        self.subject    = _safe(subj) or "S"
        self.first_idx  = next_trial_index(self.series_dir, self.subject)
        self.series_id  = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.trial = 1
        self._set_state("countdown")
        self.btn_start.configure(state='disabled')
        self.btn_stop.configure(state='normal')
        self.btn_disc.configure(state='disabled')
        self.btn_tare.configure(state='disabled')
        self.app.log(f"[{fr('Série')}] {subj} {grp} {tps} {self.var_eyes.get()} "
                     f"{self.var_surface.get()} : {self.ntrial} × {self.dur:g} s")

    def stop_series(self):
        r = self.app.board.reader
        if self.state == "recording" and r is not None:
            r.stop_recording()
            self.app.log(f"[{fr('Série')}] {fr('Essai')} {self.trial} "
                         f"{fr('interrompu (non enregistré).')}")
        self._end_series(fr("Série arrêtée."))

    def next_trial(self):
        if self.state == "wait":
            self._set_state("countdown")

    def _end_series(self, msg):
        self._set_state("idle")
        self.txt_big.set_text("")
        self.var_progress.set(msg)
        self.btn_start.configure(state='normal')
        self.btn_stop.configure(state='disabled')
        self.btn_next.configure(state='disabled')
        if self.app.board.connected:
            self.btn_disc.configure(state='normal')
            self.btn_tare.configure(state='normal')

    def _set_state(self, s):
        self.state = s
        self.t_state = time.monotonic()
        self.btn_next.configure(state='normal' if s == "wait" else 'disabled')

    def _finish_trial(self):
        r = self.app.board.reader
        rows = r.stop_recording()
        self.app.bell()
        if len(rows) < 50:
            self.app.log(fr("[Série] Essai vide ou trop court : vérifier la connexion."))
            self._end_series(fr("Erreur : essai vide."))
            return
        eyes, surf = self.var_eyes.get(), self.var_surface.get()
        idx   = self.first_idx + self.trial - 1
        path  = os.path.join(self.series_dir, f"{self.subject}_{idx}.csv")
        dev = self.app.board.device
        meta = {
            "logiciel": f"OpenSway {VERSION}",
            "source":   dev.name,
            "sujet":    self.subject,
            "groupe":   _safe(self.var_group.get(), False),
            "temps":    _safe(self.var_time.get(), False),
            "yeux":     eyes,
            "surface":  surf,
            "serie":    self.series_id,
            "essai":    idx,
            "n_essais": self.ntrial,
            "duree_s":  f"{self.dur:g}",
            "note":     self.var_note.get().strip(),
            "tare_kg":  " ".join(f"{v:.3f}" for v in r.tare) + "  (TL TR BL BR)",
        }
        if dev.cal:
            meta["calibration"] = str(dev.cal) + "  (TR BR TL BL ; 0/17/34 kg)"
        try:
            write_recording(path, rows, meta)
        except Exception as e:
            msg = fr("Impossible d'écrire le fichier :")
            messagebox.showerror(fr("Enregistrement"), f"{msg}\n{e}")
            self._end_series(fr("Erreur d'écriture."))
            return
        fs = (len(rows) - 1) / (rows[-1, 0] / 1000) if rows[-1, 0] > 0 else 0
        self.app.log(f"[{fr('Essai')} {self.trial}/{self.ntrial}] {len(rows)} {fr('mesures')} "
                     f"({fs:.0f}/s), {rows[:, 7].mean():.1f} kg -> {path}")
        self.app.analysis.add_path(path, process=True)

        if self.trial >= self.ntrial:
            self._end_series(f"{fr('Série terminée')} : {self.ntrial} × -> {self.series_dir}")
            return
        self.trial += 1
        self._set_state("wait" if self.var_wait.get() else "pause")

    # ========================================================== TEMPS RÉEL
    def _current_weight(self) -> float:
        r = self.app.board.reader
        if r is None:
            return 0.0
        w = r.window(0.5)
        return float(np.mean([x[7] for x in w])) if w else 0.0

    def _tick(self):
        try:
            self._update_protocol()
            self._update_plots()
        finally:
            self.after(REFRESH_MS, self._tick)

    def _update_protocol(self):
        board = self.app.board
        r = board.reader
        if board.device is not None and r is not None and not r.is_alive():
            err = r.error
            self.app.log(f"[Connexion] {fr('Planche perdue')} : {err}")
            if self.state == "recording":
                r.stop_recording()
            board.disconnect()
            self.disconnect()
            self._end_series(fr("Connexion perdue."))
            messagebox.showwarning(fr("Connexion"), fr("La planche s'est déconnectée.\n"
                                                       "Vérifie les piles puis reconnecte."))
            return

        el = time.monotonic() - self.t_state
        if self.state == "countdown":
            rem = self.cd - el
            self.txt_big.set_text(str(int(np.ceil(rem))) if rem > 0 else "")
            self.var_progress.set(f"{fr('Essai')} {self.trial}/{self.ntrial} : "
                                  f"{fr('départ dans')} {max(rem, 0):.0f} s")
            if rem <= 0:
                r.start_recording()
                self.app.bell()
                self._set_state("recording")
        elif self.state == "recording":
            t = r.recording_elapsed()
            self.var_progress.set(f"{fr('Essai')} {self.trial}/{self.ntrial} : "
                                  f"{t:5.1f} / {self.dur:g} s")
            if t >= self.dur:
                self._finish_trial()
        elif self.state == "pause":
            rem = self.pause - el
            self.txt_big.set_text("")
            self.var_progress.set(f"Pause : {fr('essai')} {self.trial}/{self.ntrial} "
                                  f"{fr('dans')} {rem:.0f} s")
            if rem <= 0:
                self._set_state("countdown")
        elif self.state == "wait":
            ready = fr("Prêt pour l'essai")
            self.var_progress.set(f"{ready} {self.trial}/{self.ntrial} : "
                                  f"{fr('clique sur « Essai suivant »')}")

    def _update_plots(self):
        r = self.app.board.reader
        if r is None:
            return
        if self.app.board.device is not None:
            b = self.app.board.device.battery_percent()
            self.var_batt.set("-" if b is None else f"~{b} %")
        win = r.window(10.0)
        if not win:
            return
        a = np.array(win)
        w = a[-12:, 7].mean()
        self.var_weight.set(f"{w:.1f} kg")

        if self.state == "recording":
            t0 = a[-1, 0] - r.recording_elapsed()
            tr = a[a[:, 0] >= t0]
        else:
            tr = a[a[:, 0] >= a[-1, 0] - 3.0]
        loaded = tr[:, 7] > MIN_WEIGHT_KG
        self.ln_trail.set_data(tr[loaded, 5], tr[loaded, 6])
        if a[-1, 7] > MIN_WEIGHT_KG:
            self.ln_dot.set_data([a[-1, 5]], [a[-1, 6]])
        else:
            self.ln_dot.set_data([], [])

        t = a[:, 0] - a[-1, 0]
        self.ln_ml.set_data(t, a[:, 5])
        self.ln_ap.set_data(t, a[:, 6])

        # Échelles : recalculées seulement si le signal sort du cadre, ou toutes
        # les 3 s pour resserrer (un redessin complet coûte ~50 ms).
        rescale = time.monotonic() - self._last_full > 3.0
        lims = []
        for ax, col in ((self.ax_ml, 5), (self.ax_ap, 6)):
            v = a[:, col]
            lo, hi = float(np.min(v)), float(np.max(v))
            c, h = 0.5 * (lo + hi), max(1.0, 0.6 * (hi - lo))
            y0, y1 = ax.get_ylim()
            if lo < y0 or hi > y1:
                rescale = True
            lims.append((ax, c - h, c + h))
        if rescale:
            self.ax_ml.set_xlim(-10, 0)
            for ax, y0, y1 in lims:
                ax.set_ylim(y0, y1)
            self._last_full = time.monotonic()
            self.blit.full_redraw()
        else:
            self.blit.update()
