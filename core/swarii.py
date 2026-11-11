"""
SWARII -- Sliding Windows Weighted Averaged Interpolation.

Audiffren J. & Contal E. (2016). Preprocessing the Nintendo Wii Board Signal to
Derive More Accurate Descriptors of Statokinesigrams. Sensors 16(8):1208.
doi:10.3390/s16081208

Chaque instant s de la grille régulière est estimé par la moyenne des mesures
situées dans la fenêtre |t - s| < Δ/2, chacune pondérée par son « intervalle de
pertinence » (de la mi-distance avec sa voisine de gauche à la mi-distance avec
sa voisine de droite, borné par la fenêtre). Des mesures arrivées en rafale ont
ainsi, ensemble, le poids de la durée qu'elles représentent.

Paramètres des auteurs : Δ = 0,25 s, fréquence cible 25 Hz (exemple publié).
Réimplémentation indépendante d'après la description de l'article.
"""
from __future__ import annotations

import numpy as np


def swarii(t: np.ndarray, x: np.ndarray, t_out: np.ndarray,
           window_s: float = 0.25) -> np.ndarray:
    t = np.asarray(t, dtype=float)
    x = np.asarray(x, dtype=float)
    half = 0.5 * window_s

    mid   = 0.5 * (t[1:] + t[:-1])
    left  = np.concatenate(([t[0]], mid))      # bord gauche de chaque mesure
    right = np.concatenate((mid, [t[-1]]))     # bord droit

    lo = np.searchsorted(t, t_out - half, side="right")
    hi = np.searchsorted(t, t_out + half, side="left")

    out = np.full(len(t_out), np.nan)
    for k, s in enumerate(t_out):
        i0, i1 = lo[k], hi[k]
        n = i1 - i0
        if n <= 0:
            continue
        if n == 1:
            out[k] = x[i0]
            continue
        l = left[i0:i1].copy()
        r = right[i0:i1].copy()
        l[0]  = max(t[0],  s - half)
        r[-1] = min(t[-1], s + half)
        w = np.clip(r - l, 0.0, None)
        sw = w.sum()
        out[k] = np.dot(x[i0:i1], w) / sw if sw > 0 else x[i0:i1].mean()

    # Fenêtres vides (trou de transmission) : interpolation linéaire de secours
    bad = ~np.isfinite(out)
    if bad.any() and (~bad).sum() >= 2:
        out[bad] = np.interp(t_out[bad], t_out[~bad], out[~bad])
    return out
