"""Onglet « Réglages » : paramètres d'analyse (ex-« Advanced settings » v2.3) et langue."""
from dataclasses import fields

import tkinter as tk
from tkinter import ttk, messagebox

from core.params import Params, ADVANCED_SETTINGS, RQA_MODES, RESAMPLING_MODES
from core.i18n import tr, get_language
from gui.common import save_config

LABEL_W = 30          # largeur des libellés (alignement des champs dans chaque cadre)
FIELD_W = 11          # largeur des champs ; listes déroulantes : FIELD_W - 2 (+ flèche)


def _flag(lang: str, w: int = 30, h: int = 20):
    """Petit drapeau dessiné (les émojis drapeaux ne s'affichent pas sous Windows)."""
    from PIL import Image, ImageDraw, ImageTk
    k = 4
    W, H = w * k, h * k
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    if lang == "fr":
        d.rectangle([0, 0, W // 3, H], fill="#0055A4")
        d.rectangle([2 * W // 3, 0, W, H], fill="#EF4135")
    else:
        d.rectangle([0, 0, W, H], fill="#012169")
        d.line([0, 0, W, H], fill="white", width=H // 5)
        d.line([0, H, W, 0], fill="white", width=H // 5)
        d.line([0, 0, W, H], fill="#C8102E", width=H // 15)
        d.line([0, H, W, 0], fill="#C8102E", width=H // 15)
        d.rectangle([W // 2 - H // 6, 0, W // 2 + H // 6, H], fill="white")
        d.rectangle([0, H // 2 - H // 6, W, H // 2 + H // 6], fill="white")
        d.rectangle([W // 2 - H // 10, 0, W // 2 + H // 10, H], fill="#C8102E")
        d.rectangle([0, H // 2 - H // 10, W, H // 2 + H // 10], fill="#C8102E")
    d.rectangle([0, 0, W - 1, H - 1], outline="#999999", width=k)
    return ImageTk.PhotoImage(img.resize((w, h), Image.LANCZOS))


class SettingsPanel(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=10)
        self.app      = app
        self.defaults = Params()
        self.types    = {f.name: type(getattr(self.defaults, f.name)) for f in fields(Params)}
        self.tkvars   = {}
        self._build()

    @property
    def params(self) -> Params:
        return self.app.analysis.params

    def _build(self):
        groups = []
        for group, attr, label in ADVANCED_SETTINGS:
            if group not in groups:
                groups.append(group)

        body = ttk.Frame(self)
        body.grid(row=0, column=0, sticky='nw')
        body.columnconfigure((0, 1, 2), uniform='col')       # 3 colonnes de même largeur
        frames = {}
        for k, g in enumerate(groups):
            fr = ttk.LabelFrame(body, text=tr(g), labelanchor='n', padding=(4, 2))
            fr.grid(row=k // 3, column=k % 3, sticky='nsew', padx=6, pady=4)
            frames[g] = [fr, 0]

        for group, attr, label in ADVANCED_SETTINGS:
            fr, i = frames[group]
            value = getattr(self.params, attr)
            ttk.Label(fr, text=tr(label), width=LABEL_W).grid(row=i, column=0, sticky='w',
                                                              padx=4, pady=2)
            if self.types[attr] is bool:
                var = tk.BooleanVar(value=value)
                ttk.Checkbutton(fr, variable=var).grid(row=i, column=1, sticky='w', padx=4)
            elif attr in ("rqa_mode", "resampling"):
                var = tk.StringVar(value=value)
                ttk.Combobox(fr, textvariable=var, state='readonly', width=FIELD_W - 2,
                             values=RQA_MODES if attr == "rqa_mode" else RESAMPLING_MODES
                             ).grid(row=i, column=1, sticky='w', padx=4)
            else:
                var = tk.StringVar(value=str(value))
                ttk.Entry(fr, textvariable=var, width=FIELD_W).grid(row=i, column=1, sticky='w',
                                                                    padx=4)
            self.tkvars[attr] = var
            frames[group][1] += 1

        # ---- Interface : langue ---------------------------------------------
        k = len(groups)
        fr = ttk.LabelFrame(body, text=tr("Interface"), labelanchor='n', padding=(4, 2))
        fr.grid(row=k // 3, column=k % 3, sticky='nsew', padx=6, pady=4)
        ttk.Label(fr, text=tr("Language"), width=12).grid(row=0, column=0, sticky='w',
                                                               padx=4, pady=2)
        self.var_lang = tk.StringVar(value=get_language())
        self._flags = {}
        lf = ttk.Frame(fr)
        lf.grid(row=0, column=1, sticky='w', padx=4, pady=2)
        for j, (code, name) in enumerate((("fr", "Français"), ("en", "English"))):
            try:
                self._flags[code] = _flag(code)
            except Exception:
                self._flags[code] = None
            ttk.Radiobutton(lf, text=f" {name}", image=self._flags[code], compound='left',
                            value=code, variable=self.var_lang, style='Toolbutton',
                            command=self._on_language).grid(row=0, column=j, padx=(0, 4))

        # ---- Boutons ------------------------------------------------------------
        btns = ttk.Frame(self)
        btns.grid(row=1, column=0, sticky='w', padx=6, pady=(10, 0))
        ttk.Button(btns, text=tr("Reset to defaults"), command=self.reset).grid(row=0, column=0,
                                                                               padx=(0, 4))
        ttk.Button(btns, text=tr("Apply"), command=self.apply).grid(row=0, column=1)
        self.var_msg = tk.StringVar(value=tr("Changes are applied with the « Apply » button."))
        ttk.Label(btns, textvariable=self.var_msg).grid(row=0, column=2, padx=12)

    # ------------------------------------------------------------------------
    def reset(self):
        for attr, var in self.tkvars.items():
            d = getattr(self.defaults, attr)
            var.set(d if self.types[attr] in (bool, str) else str(d))

    def _convert(self, attr, v):
        t = self.types[attr]
        if t is bool:
            return bool(v)
        if t is int:
            return int(float(str(v).replace(',', '.')))
        if t is float:
            return float(str(v).replace(',', '.'))
        return str(v)

    def apply(self):
        new = {}
        for attr, var in self.tkvars.items():
            try:
                new[attr] = self._convert(attr, var.get())
            except ValueError:
                messagebox.showerror(tr("Settings"), tr("Invalid value for '{}'.").format(attr))
                return
        p = self.params
        changed = [a for a, v in new.items() if getattr(p, a) != v]
        for attr, v in new.items():
            setattr(p, attr, v)
        ana = self.app.analysis
        ana._refresh_params()
        if changed:
            ana.cache.clear()
            ana._log(f"[Settings] changed: {', '.join(changed)} (results will be recomputed)")
            self.var_msg.set(tr("Settings applied: results will be recomputed."))
            if ana.file_tree.selection():
                ana.on_file_selected(None)
        else:
            self.var_msg.set(tr("No change."))

    def _on_language(self):
        lang = self.var_lang.get()
        if lang == get_language():
            return
        save_config(language=lang)
        if self.app.acquisition.busy_recording():
            messagebox.showinfo(tr("Language"),
                                tr("The language will change at the next start of OpenSway."))
            return
        if messagebox.askyesno(tr("Language"), tr("Restart OpenSway now to change the language?\n"
                                                  "(the board will be disconnected)")):
            self.app.request_restart()
