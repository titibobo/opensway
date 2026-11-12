import os
import pandas as pd
from typing import Dict, Tuple, Any

from .data_process         import read_brainblox_csv, preprocess
from .fileformat           import Recording
from .dynamic_analysis     import dynamic_metrics
from .positional_analysis  import positional_metrics
from .frequential_analysis import frequency_metrics
from .stochastic_analysis  import stochastic_metrics
from .nonlinear_analysis   import nonlinear_metrics
from .params import Params


def analyze_recording(rec: Recording, p: Params, name: str = ""
                      ) -> Tuple[pd.DataFrame, Dict[str, Any]]:

    t, x_c, y_c, x_filt, y_filt, qc = preprocess(rec, p)

    disp  = positional_metrics(x_c, y_c)
    dyn   = dynamic_metrics(x_c, y_c, y_filt, qc, disp['pos_ellipse95_area'], p)
    freq  = frequency_metrics(x_c, y_c, p)
    stoch = stochastic_metrics(x_c, y_c, p)
    nonl  = nonlinear_metrics(x_c, y_c, p)

    metrics = {**qc, **disp, **dyn, **freq, **stoch, **nonl}
    df      = pd.DataFrame([metrics])
    df.insert(0, 'file', name)

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

    rec = read_brainblox_csv(filepath)
    return analyze_recording(rec, p, os.path.basename(filepath))
