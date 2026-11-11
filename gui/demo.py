"""
Mode démo pédagogique : affichage grand format pour la classe.

- CoP en direct avec traînée (longueur réglable), poids et position ;
- mesure courte (10-30 s) avec décompte et bip, analysée avec le même pipeline ;
- deux mesures gardées en A et B, superposées (tracé + ellipse 95 %) et comparées,
  avec le rapport B/A x 100 (quotient de Romberg si A = yeux ouverts, B = yeux fermés).

Rien n'est enregistré sur disque.
"""
import time

import numpy as np
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox

from matplotlib.figure import Figure
from matplotlib.patches import Rectangle, Ellipse
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from scipy.stats import chi2

from core.fileformat import Recording
from core.params import Params
from core.pipeline import analyze_recording
from gui.common import Blitter

BOARD_W, BOARD_H = 51.0, 31.0
COLORS = {"A": "#1f6fb2", "B": "#e07a1f"}
METRICS = [("Surface ellipse 95 %", "pos_ellipse95_area",   "cm²"),
           ("Longueur de trajet",   "dyn_length_global",    "cm"),
           ("Vitesse moyenne",      "dyn_meanVeloc_global", "cm/s"),
           ("Amplitude ML",         "pos_range_ML",         "cm"),
           ("Amplitude AP",         "pos_range_AP",         "cm")]


def ellipse95(x, y):
    cov = np.cov(np.vstack([x, y]))
    vals, vecs = np.linalg.eigh(cov)
    c = chi2.ppf(0.95, df=2)
    a, b = np.sqrt(max(vals[1], 0) * c), np.sqrt(max(vals[0], 0) * c)
    ang = np.degrees(np.arctan2(vecs[1, 1], vecs[0, 1]))
    return Ellipse((np.mean(x), np.mean(y)), 2 * a, 2 * b, angle=ang, fill=False, lw=2)


class DemoWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("OpenSway - Démo pédagogique")
        self.geometry("1250x760")
        self.minsize(1000, 650)
        self.fullscreen = False
        self.bind("<F11>", lambda e: self._toggle_fs())
        self.bind("<Escape>", lambda e: self._toggle_fs(False))

        # Polices nommées : l'option globale Courier 8 de l'application
        # l'emporterait sinon sur les styles.
        fams = set(tkfont.families())
        fam = next((f for f in ("Segoe UI", "Helvetica", "DejaVu Sans") if f in fams),
                   tkfont.nametofont("TkDefaultFont").actual("family"))
        self.f_huge  = tkfont.Font(self, family=fam, size=30, weight='bold')
        self.big     = tkfont.Font(self, family=fam, size=14)
        self.mid     = tkfont.Font(self, family=fam, size=12)
        self.small   = tkfont.Font(self, family=fam, size=10)
        self.f_head  = tkfont.Font(self, family=fam, size=11, weight='bold')
        st = ttk.Style(self)
        st.configure('Demo.TButton', font=self.mid, padding=(6, 4))
        st.configure('Demo.Treeview', font=self.mid, rowheight=28)
        st.configure('Demo.Treeview.Heading', font=self.f_head)
        self.state = "live"           # live | countdown | measuring
        self.t_state = 0.0
        self.last = None              # (series, metrics) de la dernière mesure
        self.kept = {}                # "A"/"B" -> (series, metrics, label)
        self._artists = []
        self._build()
        self.after(50, self._tick)

    # ---------------------------------------------------------------- UI
    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.fig = Figure(figsize=(8, 6), dpi=100)
        self.ax = self.fig.add_subplot(1, 1, 1)
        ax = self.ax
        ax.add_patch(Rectangle((-BOARD_W / 2, -BOARD_H / 2), BOARD_W, BOARD_H,
                               facecolor='#f4f4f4', edgecolor='0.6', lw=1.5))
        ax.axhline(0, color='0.85', lw=1)
        ax.axvline(0, color='0.85', lw=1)
        self.ln_trail, = ax.plot([], [], lw=1.5, color='#444444', alpha=0.6)
        self.ln_dot,   = ax.plot([], [], 'o', ms=16, color='#d62828')
        self.txt_big = ax.text(0, 0, "", ha='center', va='center', fontsize=90,
                               color='#d62828', alpha=0.8, fontweight='bold')
        self.zoom = tk.StringVar(value="Zoom ×2")
        self._apply_zoom()
        ax.set_aspect('equal', adjustable='box')
        ax.set_xlabel("gauche  ←  ML (cm)  →  droite", fontsize=12)
        ax.set_ylabel("arrière  ←  AP (cm)  →  avant", fontsize=12)
        ax.tick_params(labelsize=10)
        self.fig.subplots_adjust(left=0.10, right=0.98, bottom=0.08, top=0.97)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky='nsew')
        self.blit = Blitter(self.canvas, [self.ln_trail, self.ln_dot, self.txt_big])

        side = ttk.Frame(self, padding=12)
        side.grid(row=0, column=1, sticky='ns')

        self.var_w  = tk.StringVar(value="- kg")
        self.var_xy = tk.StringVar(value="ML -   AP -")
        bg = ttk.Style(self).lookup('TFrame', 'background')
        tk.Label(side, textvariable=self.var_w, font=self.f_huge,
                 bg=bg).pack(anchor='w')
        tk.Label(side, textvariable=self.var_xy, font=self.mid, bg=bg).pack(anchor='w',
                                                                            pady=(0, 10))

        f = ttk.Frame(side)
        f.pack(fill='x', pady=4)
        ttk.Label(f, text="Traînée (s)", font=self.mid).pack(side='left')
        self.var_trail = tk.DoubleVar(value=5.0)
        ttk.Scale(f, from_=1, to=30, variable=self.var_trail).pack(side='left', fill='x',
                                                                   expand=True, padx=6)
        f = ttk.Frame(side)
        f.pack(fill='x', pady=4)
        ttk.Label(f, text="Vue", font=self.mid).pack(side='left')
        cb = ttk.Combobox(f, textvariable=self.zoom, state='readonly', width=16, font=self.mid,
                          values=("Planche entière", "Zoom ×2", "Zoom ×4"))
        cb.pack(side='left', padx=6)
        cb.bind("<<ComboboxSelected>>", lambda e: self._apply_zoom())

        ttk.Separator(side).pack(fill='x', pady=10)
        f = ttk.Frame(side)
        f.pack(fill='x')
        ttk.Label(f, text="Mesure (s)", font=self.mid).pack(side='left')
        self.var_dur = tk.StringVar(value="20")
        ttk.Combobox(f, textvariable=self.var_dur, values=("10", "20", "30"), width=4,
                     state='readonly', font=self.mid).pack(side='left', padx=6)
        self.btn_meas = ttk.Button(side, text="● Mesurer", command=self.measure,
                                   style='Demo.TButton')
        self.btn_meas.pack(fill='x', pady=(6, 2))
        self.var_info = tk.StringVar(value="")
        ttk.Label(side, textvariable=self.var_info, font=self.mid, wraplength=300).pack(
            anchor='w', pady=2)

        f = ttk.Frame(side)
        f.pack(fill='x', pady=(8, 2))
        self.var_lab = {"A": tk.StringVar(value="Yeux ouverts"),
                        "B": tk.StringVar(value="Yeux fermés")}
        for i, k in enumerate("AB"):
            ttk.Button(f, text=f"Garder en {k}", style='Demo.TButton',
                       command=lambda k=k: self.keep(k)).grid(row=i, column=0, sticky='ew', pady=2)
            ttk.Entry(f, textvariable=self.var_lab[k], width=14, font=self.mid).grid(
                row=i, column=1, sticky='ew', padx=6, pady=2)
            tk.Label(f, text="■", fg=COLORS[k], font=self.big,
                     bg=ttk.Style(self).lookup('TFrame', 'background')).grid(row=i, column=2)
        ttk.Button(side, text="Effacer A et B", command=self.clear,
                   style='Demo.TButton').pack(fill='x', pady=(4, 10))

        self.table = ttk.Treeview(side, columns=("A", "B", "r"), height=len(METRICS),
                                  selectmode='none', style='Demo.Treeview')
        self.table.heading("#0", text="Descripteur")
        self.table.heading("A", text="A")
        self.table.heading("B", text="B")
        self.table.heading("r", text="B/A ×100")
        self.table.column("#0", width=230)
        for c in ("A", "B", "r"):
            self.table.column(c, width=110, anchor='e')
        for lab, key, unit in METRICS:
            self.table.insert("", "end", iid=key, text=f"{lab} ({unit})", values=("", "", ""))
        self.table.pack(fill='x')
        ttk.Label(side, text="B/A ×100 = quotient de Romberg\nsi A = yeux ouverts, B = yeux fermés.",
                  font=self.small).pack(anchor='w', pady=(4, 0))

        ttk.Label(side, text="F11 : plein écran", font=self.small).pack(side='bottom',
                                                                             anchor='w')

    def _apply_zoom(self):
        k = {"Planche entière": 1, "Zoom ×2": 2, "Zoom ×4": 4}[self.zoom.get()]
        cx, cy = 0.0, 0.0
        r = self.app.board.reader
        if k > 1 and r is not None:
            w = r.window(2.0)
            if w:
                a = np.array(w)
                cx, cy = float(np.mean(a[:, 5])), float(np.mean(a[:, 6]))
        self.ax.set_xlim(cx - (BOARD_W / 2 + 1) / k, cx + (BOARD_W / 2 + 1) / k)
        self.ax.set_ylim(cy - (BOARD_H / 2 + 1) / k, cy + (BOARD_H / 2 + 1) / k)
        self.txt_big.set_position((cx, cy))
        if hasattr(self, "blit"):
            self.blit.full_redraw()

    def _toggle_fs(self, value=None):
        self.fullscreen = (not self.fullscreen) if value is None else value
        self.attributes("-fullscreen", self.fullscreen)

    # ------------------------------------------------------------- mesure
    def measure(self):
        r = self.app.board.reader
        if r is None:
            messagebox.showinfo("Démo", "Connecte d'abord la planche ou le simulateur "
                                        "(onglet Acquisition).", parent=self)
            return
        if r.recording or self.app.acquisition.busy_recording():
            messagebox.showinfo("Démo", "Un enregistrement est déjà en cours.", parent=self)
            return
        self.dur = float(self.var_dur.get())
        self.state = "countdown"
        self.t_state = time.monotonic()
        self.btn_meas.configure(state='disabled')

    def _finish(self):
        rows = self.app.board.reader.stop_recording()
        self.app.bell()
        self.state = "live"
        self.txt_big.set_text("")
        self.btn_meas.configure(state='normal')
        if len(rows) < 50:
            self.var_info.set("Mesure vide : vérifier la planche.")
            return
        rec = Recording(rows[:, 0] / 1000.0, rows[:, 5], rows[:, 6], rows[:, 7],
                        rows[:, 1:5], {}, "opensway")
        try:
            df, series = analyze_recording(rec, Params(), "demo")
        except Exception as e:
            self.var_info.set(f"Analyse impossible : {e}")
            return
        m = df.iloc[0].to_dict()
        self.last = (series, m)
        self.var_info.set(f"Ellipse {m['pos_ellipse95_area']:.1f} cm²  ·  "
                          f"vitesse {m['dyn_meanVeloc_global']:.2f} cm/s\n"
                          f"→ « Garder en A » ou « en B »")

    def keep(self, k):
        if self.last is None:
            self.var_info.set("Fais d'abord une mesure.")
            return
        self.kept[k] = self.last
        self._redraw_kept()

    def clear(self):
        self.kept.clear()
        self._redraw_kept()

    def _redraw_kept(self):
        for art in self._artists:
            art.remove()
        self._artists = []
        for k, (series, m) in self.kept.items():
            x, y = series['x_filt'], series['y_filt']
            ln, = self.ax.plot(x, y, lw=1.0, color=COLORS[k], alpha=0.8)
            el = ellipse95(x, y)
            el.set_edgecolor(COLORS[k])
            self.ax.add_patch(el)
            self._artists += [ln, el]
        for lab, key, unit in METRICS:
            va = self.kept.get("A", (None, {}))[1].get(key)
            vb = self.kept.get("B", (None, {}))[1].get(key)
            ratio = f"{100 * vb / va:.0f}" if va and vb else ""
            self.table.item(key, values=("" if va is None else f"{va:.2f}",
                                         "" if vb is None else f"{vb:.2f}", ratio))
        self.table.heading("A", text=self.var_lab["A"].get()[:14] or "A")
        self.table.heading("B", text=self.var_lab["B"].get()[:14] or "B")
        self.blit.full_redraw()

    # -------------------------------------------------------------- boucle
    def _tick(self):
        if not self.winfo_exists():
            return
        try:
            self._update()
        finally:
            self.after(50, self._tick)

    def _update(self):
        r = self.app.board.reader
        if r is None:
            self.var_w.set("- kg")
            return
        el = time.monotonic() - self.t_state
        if self.state == "countdown":
            rem = 3 - el
            self.txt_big.set_text(str(int(np.ceil(rem))) if rem > 0 else "")
            if rem <= 0:
                r.start_recording()
                self.app.bell()
                self.state = "measuring"
                self.t_state = time.monotonic()
        elif self.state == "measuring":
            t = r.recording_elapsed()
            self.var_info.set(f"Mesure : {t:4.1f} / {self.dur:g} s")
            if t >= self.dur:
                self._finish()

        trail_s = float(self.var_trail.get())
        if self.state == "measuring":
            trail_s = max(trail_s, r.recording_elapsed())
        w = r.window(trail_s)
        if not w:
            return
        a = np.array(w)
        loaded = a[:, 7] > 15
        self.var_w.set(f"{a[-12:, 7].mean():5.1f} kg")
        self.ln_trail.set_data(a[loaded, 5], a[loaded, 6])
        if a[-1, 7] > 15:
            self.ln_dot.set_data([a[-1, 5]], [a[-1, 6]])
            self.var_xy.set(f"ML {a[-1, 5]:+5.1f} cm   AP {a[-1, 6]:+5.1f} cm")
        else:
            self.ln_dot.set_data([], [])
            self.var_xy.set("Personne sur la planche")
        self.blit.update()
