"""Éléments partagés de l'interface."""
import json
import os
import sys
from pathlib import Path

import tkinter as tk

VERSION = "1.3.4"


# -----------------------------------------------------------------------------
# Réglages mémorisés (langue…) : %APPDATA%/OpenSway/config.json ou ~/.opensway/
# -----------------------------------------------------------------------------
def _config_path() -> Path:
    base = os.environ.get("APPDATA")
    return (Path(base) / "OpenSway" if base else Path.home() / ".opensway") / "config.json"


def load_config() -> dict:
    try:
        return json.loads(_config_path().read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(**values) -> None:
    cfg = load_config()
    cfg.update(values)
    try:
        p = _config_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def center_window(win, parent=None) -> None:
    """Place une fenêtre secondaire au centre de sa fenêtre parente
    (et non dans le coin supérieur gauche de l'écran)."""
    win.withdraw()
    win.update_idletasks()
    w, h = win.winfo_reqwidth(), win.winfo_reqheight()
    if parent is not None and parent.winfo_ismapped():
        px, py = parent.winfo_rootx(), parent.winfo_rooty()
        pw, ph = parent.winfo_width(), parent.winfo_height()
    else:
        px, py = 0, 0
        pw, ph = win.winfo_screenwidth(), win.winfo_screenheight()
    x = max(0, px + (pw - w) // 2)
    y = max(0, py + (ph - h) // 3)
    win.geometry(f"+{x}+{y}")
    win.deiconify()


def resource_path(*parts: str) -> str:
    """
    Return absolute path to a resource (works in dev and in PyInstaller bundle).
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = Path(__file__).resolve().parent.parent
    return str(base.joinpath(*parts))


class ToolTip:
    def __init__(self, widget, text: str, delay_ms: int = 300, wraplength: int = 360):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self.wraplength = wraplength

        self._after_id = None
        self._tw = None

        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")

    def _on_enter(self, _evt=None):
        self._schedule()

    def _on_leave(self, _evt=None):
        self._cancel()
        self._hide()

    def _schedule(self):
        self._cancel()
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _cancel(self):
        if self._after_id is not None:
            self.widget.after_cancel(self._after_id)
            self._after_id = None

    def _show(self):
        if self._tw is not None:
            return

        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8

        self._tw = tk.Toplevel(self.widget)
        self._tw.wm_overrideredirect(True)
        self._tw.wm_geometry(f"+{x}+{y}")

        text = self.text() if callable(self.text) else self.text
        if not text:
            self._tw.destroy()
            self._tw = None
            return
        lbl = tk.Label(
            self._tw,
            text=text,
            justify="left",
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=6,
            wraplength=self.wraplength,
        )
        lbl.pack()

    def _hide(self):
        if self._tw is not None:
            self._tw.destroy()
            self._tw = None


class Blitter:
    """Redessin rapide (blitting) : le fond de la figure est mémorisé, seuls les
    éléments animés sont redessinés à chaque image (~quelques ms au lieu de ~50)."""

    def __init__(self, canvas, artists):
        self.canvas = canvas
        self.artists = list(artists)
        self.bg = None
        for a in self.artists:
            a.set_animated(True)
        canvas.mpl_connect('draw_event', self._on_draw)

    def _on_draw(self, _event):
        self.bg = self.canvas.copy_from_bbox(self.canvas.figure.bbox)
        self._draw_artists()

    def _draw_artists(self):
        fig = self.canvas.figure
        for a in self.artists:
            fig.draw_artist(a)

    def full_redraw(self):
        self.canvas.draw()

    def update(self):
        if self.bg is None:
            self.canvas.draw()
            return
        self.canvas.restore_region(self.bg)
        self._draw_artists()
        self.canvas.blit(self.canvas.figure.bbox)


class Progress:
    """
    Fenêtre de progression modale : bloque les clics sur la fenêtre principale
    pendant les traitements longs (dossiers, sujets, exports, rapports).
    Utilisation :  with Progress(parent, "Titre", total) as pr: ... pr.step("fichier")
    """
    def __init__(self, parent, title: str, total: int):
        from tkinter import ttk
        self.parent = parent.winfo_toplevel()
        self.total  = max(1, int(total))
        self.k      = 0
        self.win    = tk.Toplevel(self.parent)
        self.win.title(title)
        self.win.transient(self.parent)
        self.win.resizable(False, False)
        self.win.protocol("WM_DELETE_WINDOW", lambda: None)     # non fermable
        frm = ttk.Frame(self.win, padding=12)
        frm.pack(fill='both', expand=True)
        self.var = tk.StringVar(value="")
        ttk.Label(frm, text=title).pack(anchor='w')
        self.bar = ttk.Progressbar(frm, length=360, mode='determinate', maximum=self.total)
        self.bar.pack(fill='x', pady=6)
        ttk.Label(frm, textvariable=self.var, width=56, anchor='w').pack(anchor='w')
        center_window(self.win, self.parent)
        try:
            self.win.grab_set()
        except tk.TclError:
            pass
        self.parent.configure(cursor='watch')
        self.win.update()

    def step(self, text: str = ""):
        self.k += 1
        self.bar['value'] = min(self.k, self.total)
        self.var.set(f"{min(self.k, self.total)}/{self.total}  {text}"[:56])
        self.win.update()

    def close(self):
        try:
            self.win.grab_release()
            self.win.destroy()
        except tk.TclError:
            pass
        try:
            self.parent.configure(cursor='')
        except tk.TclError:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


class NoProgress:
    """Remplaçant silencieux (traitement court, ou progression déjà affichée)."""
    def __init__(self, widget=None):
        self.widget = widget

    def step(self, text: str = ""):
        if self.widget is not None:
            self.widget.update_idletasks()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class AutoScrollFrame(tk.Frame):
    """
    Cadre défilant vertical : son contenu (self.inner) s'affiche en entier si la
    place suffit ; sinon une barre de défilement apparaît (molette active au survol).
    Évite qu'une colonne de descripteurs soit tronquée sur un petit écran.
    """
    def __init__(self, master, **kw):
        from tkinter import ttk
        super().__init__(master, **kw)
        bg = ttk.Style(self).lookup('TFrame', 'background') or None
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0, background=bg)
        self.vsb    = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.inner  = ttk.Frame(self.canvas)
        self._win   = self.canvas.create_window(0, 0, window=self.inner, anchor='nw')
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.inner.bind('<Configure>', self._sync)
        self.canvas.bind('<Configure>', self._sync)
        self.bind('<Enter>', lambda e: self.bind_all('<MouseWheel>', self._wheel))
        self.bind('<Leave>', lambda e: self.unbind_all('<MouseWheel>'))

    def _sync(self, _e=None):
        w, h = self.inner.winfo_reqwidth(), self.inner.winfo_reqheight()
        self.canvas.configure(width=w, height=h, scrollregion=(0, 0, w, h))
        if h > self.canvas.winfo_height() + 1 and self.canvas.winfo_height() > 1:
            self.vsb.grid(row=0, column=1, sticky='ns')
        else:
            self.vsb.grid_remove()
            self.canvas.yview_moveto(0)

    def _wheel(self, e):
        if self.vsb.winfo_ismapped():
            self.canvas.yview_scroll(int(-e.delta / 120) or (-1 if e.delta > 0 else 1), 'units')
