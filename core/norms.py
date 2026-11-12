"""
Valeurs de référence (normes) pour signaler les résultats inhabituels.

Fichier .xlsx ou .csv (séparateur ; ou ,) avec au minimum les colonnes
  metric  (clé de résultat, ex. pos_ellipse95_area), mean, sd
et, en option :
  eyes (YO / YF), surface (dur / mousse), n, source, label.

Une ligne sans eyes / surface vaut pour toutes les conditions ; une ligne
propre à la condition de l'élément affiché est préférée.
Le score z = (valeur - mean) / sd est comparé à deux seuils (réglages).
"""
from __future__ import annotations

import math
import os

import pandas as pd

from .metric_keys import METRICS

COLUMNS = ["metric", "label", "eyes", "surface", "mean", "sd", "n", "source"]


class Norms:
    def __init__(self, df: pd.DataFrame, path: str = ""):
        self.df = df
        self.path = path
        self._index = {}
        for _, r in df.iterrows():
            self._index.setdefault(str(r["metric"]).strip(), []).append(r)

    def __len__(self):
        return len(self._index)

    @property
    def name(self) -> str:
        return os.path.basename(self.path) if self.path else ""

    @classmethod
    def load(cls, path: str) -> "Norms":
        if path.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(path)
        else:
            df = pd.read_csv(path, sep=None, engine="python")
        df.columns = [str(c).strip().lower() for c in df.columns]
        missing = {"metric", "mean", "sd"} - set(df.columns)
        if missing:
            raise ValueError(f"Colonnes manquantes : {', '.join(sorted(missing))}")
        for c in ("eyes", "surface"):
            if c not in df.columns:
                df[c] = ""
            df[c] = df[c].fillna("").astype(str).str.strip()
        df["mean"] = pd.to_numeric(df["mean"], errors="coerce")
        df["sd"]   = pd.to_numeric(df["sd"], errors="coerce")
        df = df[df["mean"].notna() & (df["sd"] > 0)]
        return cls(df, path)

    def ref(self, key: str, eyes: str = "", surface: str = ""):
        """Ligne de référence la plus spécifique pour cette condition."""
        rows = self._index.get(key)
        if not rows:
            return None
        def score(r):
            e, s = r["eyes"], r["surface"]
            if (e and e.upper() != eyes.upper()) or (s and s.lower() != surface.lower()):
                return -1
            return bool(e) + bool(s)
        best = max(rows, key=score)
        return best if score(best) >= 0 else None

    def z(self, key: str, value, eyes: str = "", surface: str = ""):
        r = self.ref(key, eyes, surface)
        try:
            v = float(value)
        except (TypeError, ValueError):
            return None, None
        if r is None or not math.isfinite(v):
            return None, None
        return (v - r["mean"]) / r["sd"], r


def write_template(path: str, labels=None) -> None:
    """Modèle à remplir : une ligne par descripteur, mean / sd vides."""
    from .i18n import metric_short
    rows = [{"metric": key, "label": metric_short(label), "eyes": "", "surface": "",
             "mean": None, "sd": None, "n": None, "source": ""}
            for _f, label, key in METRICS]
    df = pd.DataFrame(rows, columns=COLUMNS)
    if path.lower().endswith(".csv"):
        df.to_csv(path, sep=";", index=False)
    else:
        df.to_excel(path, index=False)
