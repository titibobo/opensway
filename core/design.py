import os
import re
from dataclasses import asdict
from datetime import date
from typing import Dict, List, Tuple

import pandas as pd

from .params import Params


# Trial suffix: "IDPATIENT_1" (OpenSway), "IDPATIENT_n°1" (v2.3 ; also "_n1", "_no1", "_n°01")
TRIAL_RE = re.compile(r'^(?P<subject>.+?)_(?:n(?:°|o)?\s*)?(?P<trial>\d+)$', re.IGNORECASE)

# Condition folder written by OpenSway: "YO-dur", "YF-mousse" (eyes - surface)
COND_RE  = re.compile(r'^(?P<eyes>YO|YF)(?:[-_](?P<surface>[A-Za-zÀ-ÿ]+))?$', re.IGNORECASE)


## Subject & trial from the file name
def parse_name(path: str) -> Tuple[str, str]:

    stem = os.path.splitext(os.path.basename(path))[0]
    m    = TRIAL_RE.match(stem)

    if m:
        return m.group('subject'), str(int(m.group('trial')))

    return stem, ""


## Factors from the parent folder name ("sim+dt_AV" -> "sim+dt", "AV")
#   only when the folder name contains a "_" ; editable afterwards in the GUI.
#   An OpenSway condition folder ("YO-dur") is skipped: factors are then read
#   from the folder above ("ttt_AV/YO-dur/S012_1.csv").
def folder_factors(path: str) -> Tuple[str, str]:

    parent = os.path.dirname(os.path.abspath(path))
    folder = os.path.basename(parent)
    if COND_RE.match(folder):
        folder = os.path.basename(os.path.dirname(parent))
    if '_' not in folder:
        return "", ""

    f1, f2 = folder.split('_', 1)

    return f1, f2


## Eyes / surface from the parent folder name ("YF-mousse" -> "YF", "mousse")
def folder_condition(path: str) -> Tuple[str, str]:

    folder = os.path.basename(os.path.dirname(os.path.abspath(path)))
    m      = COND_RE.match(folder)
    if not m:
        return "", ""

    return m.group('eyes').upper(), (m.group('surface') or "")


## Design of one file: OpenSway header first, then file / folder names
def describe_file(path: str, meta: Dict = None) -> Dict[str, str]:

    meta           = meta or {}
    subject, trial = parse_name(path)
    f1, f2         = folder_factors(path)
    eyes, surface  = folder_condition(path)

    return {
        'subject': meta.get('sujet')   or subject,
        'trial':   str(meta.get('essai') or trial),
        'f1':      meta.get('groupe')  or f1,
        'f2':      meta.get('temps')   or f2,
        'eyes':    meta.get('yeux')    or eyes,
        'surface': meta.get('surface') or surface,
    }


## Export column name of a factor ("Groupe" -> "group", "Time point" -> "time_point")
_DEFAULT_FACTORS = {'groupe': 'group', 'temps': 'time'}

def export_name(name: str) -> str:
    slug = re.sub(r'[^0-9a-z]+', '_', name.strip().lower()).strip('_') or 'factor'
    return _DEFAULT_FACTORS.get(slug, slug)


## Mean of repeated trials, displayed as "mean±SD"
class MeanSD(float):
    """
    Float holding the mean of the trials, with the SD (ddof=1) and n.
        str(v)          -> "mean±SD"  (adaptive decimals)
        f"{v:.2f}"      -> "mean±SD"  (given format)
        f"{v}"          -> "mean"     (used in "value ±within-trial SD" displays)
    """
    def __new__(cls, mean: float, sd: float, n: int):
        obj    = float.__new__(cls, mean)
        obj.sd = sd
        obj.n  = n
        return obj

    def _dec(self) -> int:
        a = abs(float(self))
        return 3 if a < 1 else 2 if a < 100 else 1 if a < 1000 else 0

    def _with_sd(self) -> bool:
        return self.n > 1 and self.sd == self.sd          # sd not NaN

    def __str__(self) -> str:
        d = self._dec()
        m = f"{float(self):.{d}f}"
        return f"{m}±{self.sd:.{d}f}" if self._with_sd() else m

    def __format__(self, spec: str) -> str:
        if not spec:
            return f"{float(self):.{self._dec()}f}"
        m = format(float(self), spec)
        return f"{m}±{format(self.sd, spec)}" if self._with_sd() else m


def aggregate_metrics(metrics_list: List[Dict]) -> Dict:
    """ Mean ± SD of the numeric metrics of several trials (MeanSD values) """
    out = {'n_trials': len(metrics_list)}
    if not metrics_list:
        return out

    for k in metrics_list[0]:
        vals = [m.get(k) for m in metrics_list]
        try:
            arr = pd.to_numeric(pd.Series(vals), errors='raise').astype(float).to_numpy()
        except (ValueError, TypeError):
            continue
        n   = int((arr == arr).sum())
        if n == 0:
            out[k] = float('nan')
            continue
        mean = float(pd.Series(arr).mean())
        sd   = float(pd.Series(arr).std(ddof=1)) if n > 1 else float('nan')
        out[k] = MeanSD(mean, sd, n)

    return out


## Results tables
def build_tables(rows: List[Dict], factor_names: List[str]
                 ) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    rows: one dict per file -> 'file', 'subject', 'trial', 'f1', 'f2',
          'eyes', 'surface', 'metrics'
    Returns (means, trials):
        trials = one row per file (design columns + metrics)
        means  = one row per subject x factors x condition, mean of the trials + n_trials
    Column names: English, lower case, underscores.
    """
    f1_name, f2_name = (export_name(n) for n in factor_names)

    records = []
    for r in rows:
        rec = {
            'file':     r['file'],
            'subject':  r['subject'],
            f1_name:    r['f1'],
            f2_name:    r['f2'],
            'eyes':     r.get('eyes', ""),
            'surface':  r.get('surface', ""),
            'trial':    r['trial'],
        }
        rec.update({k: v for k, v in r['metrics'].items() if k != 'file'})
        records.append(rec)

    trials  = pd.DataFrame(records)

    keys    = ['subject', f1_name, f2_name, 'eyes', 'surface']
    numeric = [c for c in trials.columns
               if c not in keys + ['file', 'trial']
               and pd.api.types.is_numeric_dtype(trials[c])]

    grp     = trials.groupby(keys, sort=False, dropna=False)
    means   = grp[numeric].mean().round(4)
    means.insert(0, 'n_trials', grp.size())
    means   = means.reset_index()

    return means, trials


def settings_table(p: Params, version: str) -> pd.DataFrame:

    rows = [('software', f"OpenSway {version}"),
            ('date',     str(date.today()))]
    rows += [(k, v) for k, v in asdict(p).items()]

    return pd.DataFrame(rows, columns=['parameter', 'value'])


def write_results(path: str, means: pd.DataFrame, trials: pd.DataFrame,
                  settings: pd.DataFrame) -> List[str]:
    """ xlsx: sheets Means, Trials, Settings ; csv: means + *_trials.csv """

    if path.lower().endswith(".csv"):
        stem = os.path.splitext(path)[0]
        means.to_csv(path, sep=";", decimal=",", index=False)
        trials.to_csv(stem + "_trials.csv", sep=";", decimal=",", index=False)
        return [path, stem + "_trials.csv"]

    with pd.ExcelWriter(path) as xw:
        means.to_excel(xw,    sheet_name="Means",    index=False)
        trials.to_excel(xw,   sheet_name="Trials",   index=False)
        settings.to_excel(xw, sheet_name="Settings", index=False)

    return [path]


# "value ±SD" GUI fields: in subject mode, show the SD between trials
#   (instead of the mean within-trial SD)
_PAIRED_SD = (('mean_ML', 'std_ML'), ('mean_AP', 'std_AP'),
              ('dyn_meanVeloc_ML',     'dyn_sdVeloc_ML'),
              ('dyn_meanVeloc_AP',     'dyn_sdVeloc_AP'),
              ('dyn_meanVeloc_global', 'dyn_sdVeloc_global'))

def with_trial_sd(agg: Dict) -> Dict:
    out = dict(agg)
    for k_mean, k_sd in _PAIRED_SD:
        v = agg.get(k_mean)
        if isinstance(v, MeanSD) and v._with_sd():
            out[k_sd] = f"{v.sd:.{v._dec()}f}"
    return out


# Chronological order of the levels of the 2nd factor (comparison Δ = last - first)
_TIME_ORDER = [("av", "ap"), ("avant", "apres"), ("avant", "après"),
               ("pre", "post"), ("before", "after"), ("baseline", "follow-up")]

def time_order_key(level: str):
    """ Sort key: known pairs (AV < AP, pre < post...), then natural order (T0 < T1 < T10) """
    low = level.strip().lower()
    for pair in _TIME_ORDER:
        if low in pair:
            return (0, pair.index(low), "")
    parts = re.split(r'(\d+)', low)
    return (1, 0, tuple(int(x) if x.isdigit() else x for x in parts))
