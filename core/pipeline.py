import os
import pandas as pd
from typing import Dict, Tuple, Any

from .data_process         import preprocess
from .fileformat           import Recording, read_recording
from .dynamic_analysis     import dynamic_metrics
from .positional_analysis  import positional_metrics
from .frequential_analysis import frequency_metrics
from .stochastic_analysis  import stochastic_metrics
from .params import Params

# Métadonnées recopiées dans les résultats (vides pour les fichiers BrainBLoX)
META_KEYS = ["sujet", "yeux", "surface", "serie", "essai"]


def analyze_recording(rec: Recording, p: Params, name: str = ""
                      ) -> Tuple[pd.DataFrame, Dict[str, Any]]:

    t, x_c, y_c, x_filt, y_filt, qc = preprocess(rec, p)

    disp  = positional_metrics(x_c, y_c)
    dyn   = dynamic_metrics(x_c, y_c, y_filt, qc, disp['pos_ellipse95_area'], p)
    freq  = frequency_metrics(x_c, y_c, p)
    stoch = stochastic_metrics(x_c, y_c, p)

    metrics = {**qc, **disp, **dyn, **freq, **stoch}
    df      = pd.DataFrame([metrics])
    df.insert(0, 'file', name)
    for i, k in enumerate(META_KEYS, start=1):
        df.insert(i, k, rec.meta.get(k, ""))
    df.insert(len(META_KEYS) + 1, 'format', rec.source_format)

    series = {
        't':      t,
        'x':      x_c,
        'y':      y_c,
        'x_filt': x_filt,
        'y_filt': y_filt,
    }
    return df, series


def run_pipeline(filepath: str, p: Params
                 ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    rec = read_recording(filepath)
    return analyze_recording(rec, p, os.path.basename(filepath))
