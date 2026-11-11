"""
Moyennage des essais répétés, par sujet × yeux × surface.

Ne s'applique qu'aux fichiers OpenSway qui portent ces métadonnées ; les
autres fichiers restent dans la feuille « Essais » mais ne sont pas moyennés.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

GROUP_KEYS = ["sujet", "yeux", "surface"]
NON_METRIC = {"file", "sujet", "yeux", "surface", "serie", "essai", "format"}

# Quotient de Romberg (YF / YO x 100) sur quelques descripteurs usuels
ROMBERG_KEYS = {
    "pos_ellipse95_area":   "Surface ellipse 95 %",
    "dyn_length_global":    "Longueur de trajet",
    "dyn_meanVeloc_global": "Vitesse moyenne",
}


def summarize(metrics_by_file: dict[str, dict]):
    """-> (essais, moyennes, ecarts_types, romberg) ; DataFrames avec les
    descripteurs en lignes (même orientation que l'export historique)."""
    trials = pd.DataFrame(metrics_by_file).T          # lignes = fichiers
    essais = trials.T

    if trials.empty or not set(GROUP_KEYS) <= set(trials.columns):
        return essais, None, None, None
    tagged = trials[trials["sujet"].astype(str).str.len() > 0]
    if tagged.empty:
        return essais, None, None, None

    metric_cols = [c for c in tagged.columns if c not in NON_METRIC]
    num = tagged[metric_cols].apply(pd.to_numeric, errors="coerce")
    num = num.loc[:, num.notna().any()]
    keys = tagged[GROUP_KEYS].astype(str)

    grouped = num.groupby([keys[k] for k in GROUP_KEYS])
    means, sds, counts = grouped.mean(), grouped.std(ddof=1), grouped.size()

    def _label(idx):
        s, y, f = idx
        return f"{s} | {y} | {f} (n={counts[idx]})"

    moyennes = means.round(4)
    moyennes.index = [_label(i) for i in means.index]
    ecarts = sds.round(4)
    ecarts.index = [_label(i) for i in sds.index]

    # Romberg : pour chaque sujet x surface ayant YO et YF
    rows = []
    for (s, f), sub in means.groupby(level=[0, 2]):
        eyes = sub.index.get_level_values(1)
        if "YO" in eyes and "YF" in eyes:
            yo = sub.xs("YO", level=1).iloc[0]
            yf = sub.xs("YF", level=1).iloc[0]
            row = {"sujet": s, "surface": f}
            for k, lab in ROMBERG_KEYS.items():
                if k in yo and yo[k] and np.isfinite(yo[k]):
                    row[lab] = round(100.0 * yf[k] / yo[k], 1)
            rows.append(row)
    romberg = pd.DataFrame(rows) if rows else None

    return essais, moyennes.T, ecarts.T, romberg


def export_excel(path: str, metrics_by_file: dict[str, dict]) -> list[str]:
    essais, moyennes, ecarts, romberg = summarize(metrics_by_file)
    sheets = ["Essais"]
    with pd.ExcelWriter(path) as xw:
        essais.to_excel(xw, sheet_name="Essais")
        if moyennes is not None:
            moyennes.to_excel(xw, sheet_name="Moyennes")
            ecarts.to_excel(xw, sheet_name="Ecarts-types")
            sheets += ["Moyennes", "Ecarts-types"]
        if romberg is not None:
            romberg.to_excel(xw, sheet_name="Romberg (YF÷YO×100)", index=False)
            sheets.append("Romberg")
    return sheets
