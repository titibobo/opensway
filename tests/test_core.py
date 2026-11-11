"""Tests du cœur d'analyse (lancés avant chaque compilation)."""
import glob
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.fileformat import read_recording, write_recording      # noqa: E402
from core.params import Params                                    # noqa: E402
from core.pipeline import run_pipeline                            # noqa: E402
from core.swarii import swarii                                    # noqa: E402

EXAMPLES = sorted(glob.glob(os.path.join(ROOT, "examples", "*.csv")))


def test_swarii_regular_signal_is_preserved():
    t = np.arange(0, 10, 0.01)
    x = np.sin(2 * np.pi * 0.3 * t)
    t_out = np.arange(0.2, 9.7, 0.04)        # hors bords (fenêtre tronquée)
    y = swarii(t, x, t_out, 0.25)
    assert np.max(np.abs(y - np.sin(2 * np.pi * 0.3 * t_out))) < 0.02


def test_swarii_bursts_do_not_bias():
    # rafale de 5 mesures identiques au même endroit : poids = durée représentée
    t = np.array([0.0, 0.1, 0.1001, 0.1002, 0.1003, 0.1004, 0.2, 0.3])
    x = np.array([0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 2.0, 3.0])
    y = swarii(t, x, np.array([0.15]), 0.25)
    assert abs(y[0] - 1.5) < 0.15


def test_brainblox_examples_still_analysed():
    assert EXAMPLES
    for f in EXAMPLES:
        df, series = run_pipeline(f, Params())
        r = df.iloc[0]
        assert r["format"] == "brainblox"
        assert r["pos_ellipse95_area"] > 0
        assert len(series["t"]) > 100


def test_opensway_roundtrip_and_axes(tmp_path):
    rec = read_recording(EXAMPLES[0])
    rows = np.column_stack([rec.t_s * 1000, rec.sensors, rec.ml, rec.ap, rec.total])
    p = tmp_path / "x.csv"
    write_recording(str(p), rows, {"sujet": "T", "yeux": "YO", "surface": "dur", "essai": 1})
    rec2 = read_recording(str(p))
    assert rec2.source_format == "opensway"
    assert rec2.meta["sujet"] == "T"
    # même convention interne : pas de double inversion
    assert np.allclose(rec2.ap, rec.ap, atol=1e-3)
    assert np.allclose(rec2.ml, rec.ml, atol=1e-3)
