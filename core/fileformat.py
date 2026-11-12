"""
Lecture / écriture des enregistrements.

Deux formats sont reconnus automatiquement :

* OpenSway (v1) -- en-tête de lignes "# clé: valeur", puis 8 colonnes séparées
  par des espaces :  t_ms TL_kg TR_kg BL_kg BR_kg cop_ml_cm cop_ap_cm total_kg
  La convention d'axes est écrite dans l'en-tête (clé "axes").

* BrainBLoX (historique) -- pas d'en-tête, mêmes 8 colonnes ; l'axe AP de
  BrainBLoX est inversé, on le redresse ici (comme le faisait BrainBloX_analysis).

En interne, tout est ramené à : ML+ = droite, AP+ = avant, t en secondes.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

FORMAT_TAG     = "OpenSway"
FORMAT_VERSION = 1
AXES_STANDARD  = "ML+ = droite, AP+ = avant"
COLUMNS        = "t_ms TL_kg TR_kg BL_kg BR_kg cop_ml_cm cop_ap_cm total_kg"

# Ordre d'écriture des métadonnées (les autres clés suivent)
META_ORDER = ["format", "logiciel", "date", "source", "sujet", "groupe", "temps",
              "yeux", "surface", "serie", "essai", "n_essais", "duree_s", "note", "axes",
              "tare_kg", "calibration", "colonnes"]


@dataclass
class Recording:
    t_s:     np.ndarray            # temps (s), départ à 0
    ml:      np.ndarray            # CoP médio-latéral (cm), + = droite
    ap:      np.ndarray            # CoP antéro-postérieur (cm), + = avant
    total:   np.ndarray            # charge totale (kg)
    sensors: np.ndarray            # (n, 4) : TL, TR, BL, BR (kg)
    meta:    dict = field(default_factory=dict)
    source_format: str = "brainblox"

    @property
    def duration(self) -> float:
        return float(self.t_s[-1] - self.t_s[0]) if len(self.t_s) > 1 else 0.0


# -----------------------------------------------------------------------------
def write_recording(path: str, rows: np.ndarray, meta: dict) -> None:
    """rows : (n, 8) dans l'ordre COLUMNS, déjà en convention standard."""
    m = dict(meta)
    m["format"]   = f"{FORMAT_TAG} v{FORMAT_VERSION}"
    m.setdefault("date", datetime.now().isoformat(timespec="seconds"))
    m["axes"]     = AXES_STANDARD
    m["colonnes"] = COLUMNS

    keys = [k for k in META_ORDER if k in m] + [k for k in m if k not in META_ORDER]
    width = max(len(k) for k in keys)
    lines = [f"# {k:<{width}} : {m[k]}" for k in keys]

    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
        for r in rows:
            f.write(f"{r[0]:.1f} {r[1]:.4f} {r[2]:.4f} {r[3]:.4f} {r[4]:.4f} "
                    f"{r[5]:.4f} {r[6]:.4f} {r[7]:.4f}\n")


def _read_header(path: str) -> dict:
    meta = {}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if not line.startswith("#"):
                break
            body = line[1:].strip()
            if ":" in body:
                k, v = body.split(":", 1)
                meta[k.strip().lower()] = v.strip()
    return meta


def read_header(path: str) -> dict:
    """Métadonnées d'un fichier OpenSway ({} pour un fichier BrainBLoX)."""
    return _read_header(path)


def _axis_signs(axes: str) -> tuple[float, float]:
    """Facteurs pour ramener à ML+ = droite, AP+ = avant."""
    a = axes.lower()
    s_ml = -1.0 if "ml+ = gauche" in a else 1.0
    s_ap = -1.0 if "ap+ = arri" in a else 1.0
    return s_ml, s_ap


def read_recording(path: str) -> Recording:
    meta = _read_header(path)
    data = np.genfromtxt(path, delimiter=None, comments="#")
    if data.ndim != 2 or data.shape[1] < 8 or len(data) < 10:
        raise ValueError("Fichier vide ou format non reconnu (8 colonnes attendues).")

    t_s     = (data[:, 0] - data[0, 0]) / 1000.0
    sensors = data[:, 1:5]
    total   = data[:, 7]

    if meta.get("format", "").startswith(FORMAT_TAG):
        s_ml, s_ap = _axis_signs(meta.get("axes", AXES_STANDARD))
        ml, ap = s_ml * data[:, 5], s_ap * data[:, 6]
        fmt = "opensway"
    else:
        # BrainBLoX : axe AP inversé -> redressement (cf. BrainBloX_analysis v2)
        ml, ap = data[:, 5], -data[:, 6]
        fmt = "brainblox"

    # Sécurité : temps strictement croissant requis pour le ré-échantillonnage
    order = np.argsort(t_s, kind="stable")
    return Recording(t_s[order], ml[order], ap[order], total[order], sensors[order],
                     meta, fmt)
