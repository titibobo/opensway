import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass


try:
    from PIL import Image, ImageTk
    PIL_OK = True
except Exception:
    PIL_OK = False
    Image = None
    ImageTk = None


class ToolTip:
    """Simple hover tooltip for a Tk widget."""
    def __init__(self, widget, text: str, delay_ms: int = 400):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self._after_id = None
        self._tip = None

        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")

    def _on_enter(self, _event=None):
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _on_leave(self, _event=None):
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None
        self._hide()

    def _show(self):
        if self._tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8

        self._tip = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        lbl = ttk.Label(
            tw,
            text=self.text,
            padding=(8, 5),
            justify="left"
        )
        # small tooltip styling
        lbl.configure(background="#ffffe0")  # light yellow
        lbl.pack()

    def _hide(self):
        if self._tip:
            self._tip.destroy()
            self._tip = None

def load_logo(path: str, max_size=(32, 32)):
    """
    Returns a Tk PhotoImage (needs a Tk root already).
    Uses Pillow if available to support PNG and resizing.
    """
    if PIL_OK:
        img = Image.open(path)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(img)

    # Fallback: Tk can load GIF/PGM/PPM without Pillow
    return tk.PhotoImage(file=path)

# -----------------------------------------------------------------------------

@dataclass
class Params:
    
    target_fs:    float   = 25.0             # 25 Hz (Quijoux et al.)
    resampling:   str     = "swarii"         # "swarii" (Audiffren & Contal, 2016) or "linear" (v2.3)
    swarii_win_s: float   = 0.25             # SWARII window (s) (Audiffren & Contal, 2016)
    butter_order: int     = 4                # 4 (Quijoux et al.)
    butter_fc:    float   = 10.0             # 10 Hz (Quijoux et al.)

    savgol_enable: bool   = True
    savgol_win_s:  float  = 0.5
    savgol_poly:   int    = 2

    fmax:          float  = 10.0
    seg_seconds:   float  = 8.0
    units:         str    = "cm"  # interne pipeline

    sda_tmin:      float  = 0.3   # SDA breakpoint search, lower bound (s) (Quijoux et al.)
    sda_tmax:      float  = 2.5   # SDA breakpoint search, upper bound (s) (Quijoux et al.)

    sampen_m:          int   = 2      # embedding dimension
    sampen_r:          float = 0.2    # tolerance, x SD of the analysed signal
    sampen_increments: bool  = True   # SampEn on COP increments (True) or positions

    dfa_nmin:      int    = 4     # DFA smallest window (samples)
    dfa_cross_s:   float  = 1.0   # DFA short/long-term crossover (s)

    rqa_mode:      str    = "fixed_rr"  # "fixed_rr" or "fixed_radius"
    rqa_rec_rate:  float  = 0.05  # fixed recurrence rate (van den Hoorn et al., 2020)
    rqa_radius:    float  = 0.27  # fixed radius, x mean distance (van den Hoorn et al., 2020)
    rqa_lmin:      int    = 2     # RQA minimal diagonal line length (samples)
    rqa_fnn_thr:   float  = 0.01  # FNN rate below which the embedding dim. is kept
    rqa_m_max:     int    = 10    # RQA maximal embedding dimension


    @property
    def target_p(self) -> float:
        return 1.0 / self.target_fs


# -----------------------------------------------------------------------------
# GUI advanced settings (dialog), grouped: (group, Params attribute, label)
# -----------------------------------------------------------------------------

ADVANCED_SETTINGS = [
    ("Preprocessing",   "resampling",        "Resampling method"),
    ("Preprocessing",   "swarii_win_s",      "SWARII window (s)"),
    ("Preprocessing",   "target_fs",         "Target frequency (Hz)"),
    ("Preprocessing",   "butter_fc",         "Lowpass cutoff (Hz)"),
    ("Preprocessing",   "butter_order",      "Butterworth order"),

    ("Dynamic",         "savgol_enable",     "Savitzky-Golay smoothing"),
    ("Dynamic",         "savgol_win_s",      "SG window (s)"),
    ("Dynamic",         "savgol_poly",       "SG polynomial order"),

    ("Spectral",        "seg_seconds",       "Welch segment (s)"),

    ("Stochastic",      "sda_tmin",          "SDA breakpoint min (s)"),
    ("Stochastic",      "sda_tmax",          "SDA breakpoint max (s)"),

    ("Sample Entropy",  "sampen_m",          "Embedding dimension m"),
    ("Sample Entropy",  "sampen_r",          "Tolerance r (x SD)"),
    ("Sample Entropy",  "sampen_increments", "On COP increments"),

    ("DFA",             "dfa_nmin",          "Smallest window (samples)"),
    ("DFA",             "dfa_cross_s",       "Short/long crossover (s)"),

    ("RQA",             "rqa_mode",          "Radius mode"),
    ("RQA",             "rqa_rec_rate",      "Fixed recurrence rate (0-1)"),
    ("RQA",             "rqa_radius",        "Fixed radius (x mean dist.)"),
    ("RQA",             "rqa_lmin",          "Min. diagonal line (pts)"),
    ("RQA",             "rqa_fnn_thr",       "FNN threshold (0-1)"),
    ("RQA",             "rqa_m_max",         "Max. embedding dimension"),
]

RQA_MODES        = ("fixed_rr", "fixed_radius")
RESAMPLING_MODES = ("swarii", "linear")


# -----------------------------------------------------------------------------
# GUI metric labels (grouped by tab / section)
# -----------------------------------------------------------------------------

GUI_METRIC_LABELS = {
    # === POSITIONAL ==========================================================
    "pos_center": [
        "ML mean position     (cm) ",
        "AP mean position     (cm) ",
        "ML RMS               (cm) ",
        "AP RMS               (cm) ",
        "Global RMS radius    (cm) ",
        "Planar deviation     (cm) ",
    ],

    "pos_distances": [
        "ML mean distance     (cm) ",
        "AP mean distance     (cm) ",
        "Mean radius          (cm) ",
        "ML maximal distance  (cm) ",
        "AP maximal distance  (cm) ",
        "Maximal radius       (cm) ",
        "ML range             (cm) ",
        "AP range             (cm) ",
        "AP-ML range          (cm) ",
        "Range ratio           (-) ",
    ],

    "pos_geometry": [
        "Sway direct° coeff.   (-) ",
        "95% ellipse area    (cm²) ",
        "Princ. sway direct°   (°) ",
    ],

    # === DYNAMIC =============================================================
    "dyn_timedep": [
        "ML path length       (cm) ",
        "AP path length       (cm) ",
        "Global path length   (cm) ",
        "LFS                (cm⁻¹) ",
    ],

    "dyn_velocities": [
        "ML mean velocity   (cm/s) ",
        "AP mean velocity   (cm/s) ",
        "Global mean vel.   (cm/s) ",
        "ML 0-crossings set    (-) ",
        "AP 0-crossings set    (-) ",
    ],

    "dyn_frequencies": [
        "ML mean frequency    (Hz) ",
        "AP mean frequency    (Hz) ",
        "Global mean freq.    (Hz) ",
    ],

    "dyn_advanced": [
        "VFY                   (-) ",
        "Area per second   (cm²/s) ",
        "ML phase plane            ",
        "AP phase plane            ",
        "Fractal dimension     (-) ",
        "ML peak pos. vel.  (cm/s) ",
        "ML peak neg. vel.  (cm/s) ",
        "ML mean peak vel.  (cm/s) ",
        "AP peak pos. vel.  (cm/s) ",
        "AP peak neg. vel.  (cm/s) ",
        "AP mean peak vel.  (cm/s) ",
        "Mean SD peaks dist.  (cm) ",
        "Mean peaks' interval  (s) ",
    ],

    # === SPECTRAL ============================================================
    "spec_freq": [
        "ML total power      (cm²) ",
        "AP total power      (cm²) ",
        "ML 50% power freq.   (Hz) ",
        "AP 50% power freq.   (Hz) ",
        "ML 95% power freq.   (Hz) ",
        "AP 95% power freq.   (Hz) ",
        "ML power mode        (Hz) ",
        "AP power mode        (Hz) ",
        "ML centroidal freq.  (Hz) ",
        "AP centroidal freq.  (Hz) ",
        "ML freq. dispersion   (-) ",
        "AP freq. dispersion   (-) ",
    ],

    "spec_bands": [
        "ML [0-0.5] Hz       (cm²) ",
        "AP [0-0.5] Hz       (cm²) ",
        "ML [0.5–2] Hz       (cm²) ",
        "AP [0.5–2] Hz       (cm²) ",
        "ML  [2–5]  Hz       (cm²) ",
        "AP  [2–5]  Hz       (cm²) ",
        "ML freq. quotient     (-) ",
        "AP freq. quotient     (-) ",
    ],

    # === STOCHASTIC ==========================================================
    "stc_sda": [
        "ML ST Hurst exp.      (-) ",
        "AP ST Hurst exp.      (-) ",
        "ML LT Hurst exp.      (-) ",
        "AP LT Hurst exp.      (-) ",
        "ML ST diffus. coeff.  (-) ",
        "AP ST diffus. coeff.  (-) ",
        "ML LT diffus. coeff.  (-) ",
        "AP LT diffus. coeff.  (-) ",
    ],

    "stc_critical": [
        "ML crit. time Tc      (s) ",
        "AP crit. time Tc      (s) ",
        "ML MSD at Tc        (cm²) ",
        "AP MSD at Tc        (cm²) ",
    ],

    # === NONLINEAR ===========================================================
    "nl_entropy": [
        "ML sample entropy     (-) ",
        "AP sample entropy     (-) ",
    ],

    "nl_dfa": [
        "ML DFA α short-term   (-) ",
        "AP DFA α short-term   (-) ",
        "ML DFA α long-term    (-) ",
        "AP DFA α long-term    (-) ",
    ],

    "nl_rqa": [
        "ML RQA recurrence     (%) ",
        "AP RQA recurrence     (%) ",
        "ML RQA determinism    (%) ",
        "AP RQA determinism    (%) ",
        "ML RQA max. line    (pts) ",
        "AP RQA max. line    (pts) ",
        "ML RQA line entropy   (-) ",
        "AP RQA line entropy   (-) ",
    ],

    "nl_embedding": [
        "ML embedding dim.     (-) ",
        "AP embedding dim.     (-) ",
        "ML embedding delay    (s) ",
        "AP embedding delay    (s) ",
    ],
}


# -----------------------------------------------------------------------------
# Tooltips (English) for GUI metric labels
# Keys MUST match the label strings used in main_gui.py
# -----------------------------------------------------------------------------

METRIC_TOOLTIPS: dict[str, str] = {
    # --- POS / Center Position & Dispersion ---
    "ML mean position     (cm) ": "Mean ML position (cm) after centering. Shows average lateral bias.",
    "AP mean position     (cm) ": "Mean AP position (cm) after centering. Shows average antero-posterior bias.",
    "ML RMS               (cm) ": "Root Mean Square of ML displacement (cm). Dispersion around the center.",
    "AP RMS               (cm) ": "Root Mean Square of AP displacement (cm). Dispersion around the center.",
    "Global RMS radius    (cm) ": "RMS of the radial distance sqrt(ML^2 + AP^2) (cm). Overall dispersion.",
    "Planar deviation     (cm) ": "2D dispersion computed from ML and AP standard deviations (cm).",

    # --- POS / Distances & Amplitudes ---
    "ML mean distance     (cm) ": "Mean absolute ML distance from the center (cm).",
    "AP mean distance     (cm) ": "Mean absolute AP distance from the center (cm).",
    "Mean radius          (cm) ": "Mean absolute radial distance from the center (cm).",
    "ML maximal distance  (cm) ": "Maximum absolute ML distance from the center (cm).",
    "AP maximal distance  (cm) ": "Maximum absolute AP distance from the center (cm).",
    "Maximal radius       (cm) ": "Maximum radial distance from the center (cm).",
    "ML range             (cm) ": "ML peak-to-peak amplitude (max - min) (cm).",
    "AP range             (cm) ": "AP peak-to-peak amplitude (max - min) (cm).",
    "AP-ML range          (cm) ": "Maximal 2D distance within the convex hull of points (cm).",
    "Range ratio           (-) ": "Range ratio = ML range / AP range (dimensionless).",

    # --- POS / Geometry & Direction ---
    "Sway direct° coeff.   (-) ": "Sway direction coefficient (dimensionless), based on covariance normalized by RMS.",
    "95% ellipse area    (cm²) ": "Area of the 95% confidence ellipse (cm²) derived from the covariance matrix.",
    "Princ. sway direct°   (°) ": "Principal sway direction (degrees), derived from the major eigenvector.",

    # --- DYN / Duration-dependent metrics ---
    "ML path length       (cm) ": "Sum of absolute ML increments over time (cm).",
    "AP path length       (cm) ": "Sum of absolute AP increments over time (cm).",
    "Global path length   (cm) ": "Sum of point-to-point 2D displacements (cm).",
    "LFS                (cm⁻¹) ": "Length Function of Surface: global path length / ellipse95 area (cm⁻¹).",

    # --- DYN / Velocities ---
    "ML mean velocity   (cm/s) ": "Mean absolute ML velocity (cm/s). Often displayed as mean ± SD.",
    "AP mean velocity   (cm/s) ": "Mean absolute AP velocity (cm/s). Often displayed as mean ± SD.",
    "Global mean vel.   (cm/s) ": "Mean 2D velocity magnitude (cm/s). Often displayed as mean ± SD.",
    "ML 0-crossings set    (-) ": "Number of sign changes (zero crossings) in ML velocity (dimensionless).",
    "AP 0-crossings set    (-) ": "Number of sign changes (zero crossings) in AP velocity (dimensionless).",

    # --- DYN / Temporal frequencies ---
    "ML mean frequency    (Hz) ": "Temporal frequency proxy: mean ML velocity / mean ML distance (Hz).",
    "AP mean frequency    (Hz) ": "Temporal frequency proxy: mean AP velocity / mean AP distance (Hz).",
    "Global mean freq.    (Hz) ": "Temporal frequency proxy: mean global velocity / mean radial distance (Hz).",

    # --- DYN / Advanced dynamics ---
    "VFY                   (-) ": "VFY (cm.s⁻²): variance of the COP velocity norm divided by the mean (non-centered) AP position.\nDepends on feet placement on the board; excluded by Quijoux et al. because of measurement error.",
    "Area per second   (cm²/s) ": "Sway area rate (cm²/s) based on polygon area increments over time.",
    "ML phase plane            ": "Phase-plane index: SD(position) + SD(velocity) for ML (dimensionless).",
    "AP phase plane            ": "Phase-plane index: SD(position) + SD(velocity) for AP (dimensionless).",
    "Fractal dimension     (-) ": "Fractal dimension (dimensionless): log(N) / log(N.d/L), with N samples, L global path length\nand d the diameter of the circle of same area as the 95% ellipse (Quijoux et al.).",
    "ML peak pos. vel.  (cm/s) ": "Mean positive peak ML velocity within sign-consistent segments (cm/s).",
    "ML peak neg. vel.  (cm/s) ": "Mean negative peak ML velocity within sign-consistent segments (cm/s).",
    "ML mean peak vel.  (cm/s) ": "Mean absolute peak ML velocity within sign-consistent segments (cm/s).",
    "AP peak pos. vel.  (cm/s) ": "Mean positive peak AP velocity within sign-consistent segments (cm/s).",
    "AP peak neg. vel.  (cm/s) ": "Mean negative peak AP velocity within sign-consistent segments (cm/s).",
    "AP mean peak vel.  (cm/s) ": "Mean absolute peak AP velocity within sign-consistent segments (cm/s).",
    "Mean SD peaks dist.  (cm) ": "SD of radial peak-to-peak distances (cm).",
    "Mean peaks' interval  (s) ": "Mean time interval between detected peaks of radial distance (s).",

    # --- SPECTRAL / Frequency metrics ---
    "ML total power      (cm²) ": "Total spectral power (area under PSD curve) for ML (cm²).",
    "AP total power      (cm²) ": "Total spectral power (area under PSD curve) for AP (cm²).",
    "ML 50% power freq.   (Hz) ": "Frequency below which 50% of total power is contained (median frequency) for ML.",
    "AP 50% power freq.   (Hz) ": "Frequency below which 50% of total power is contained (median frequency) for AP.",
    "ML 95% power freq.   (Hz) ": "Frequency below which 95% of total power is contained for ML.",
    "AP 95% power freq.   (Hz) ": "Frequency below which 95% of total power is contained for AP.",
    "ML power mode        (Hz) ": "Frequency of maximal PSD (dominant frequency) for ML.",
    "AP power mode        (Hz) ": "Frequency of maximal PSD (dominant frequency) for AP.",
    "ML centroidal freq.  (Hz) ": "Spectral centroid (first moment / total power) for ML (Hz).",
    "AP centroidal freq.  (Hz) ": "Spectral centroid (first moment / total power) for AP (Hz).",
    "ML freq. dispersion   (-) ": "Frequency dispersion (dimensionless), based on spectral moments.",
    "AP freq. dispersion   (-) ": "Frequency dispersion (dimensionless), based on spectral moments.",

    # --- SPECTRAL / Band energies ---
    "ML [0-0.5] Hz       (cm²) ": "Band energy for ML between 0 and 0.5 Hz (cm²).",
    "AP [0-0.5] Hz       (cm²) ": "Band energy for AP between 0 and 0.5 Hz (cm²).",
    "ML [0.5–2] Hz       (cm²) ": "Band energy for ML between 0.5 and 2 Hz (cm²).",
    "AP [0.5–2] Hz       (cm²) ": "Band energy for AP between 0.5 and 2 Hz (cm²).",
    "ML  [2–5]  Hz       (cm²) ": "Band energy for ML between 2 and 5 Hz (cm²).",
    "AP  [2–5]  Hz       (cm²) ": "Band energy for AP between 2 and 5 Hz (cm²).",
    "ML freq. quotient     (-) ": "Frequency quotient: energy(2–5 Hz) / [energy(0–0.5 Hz)+energy(0.5–2 Hz)] for ML.",
    "AP freq. quotient     (-) ": "Frequency quotient: energy(2–5 Hz) / [energy(0–0.5 Hz)+energy(0.5–2 Hz)] for AP.",

    # --- STOCHASTIC / SDA ---
    "ML ST Hurst exp.      (-) ": "Short-term Hurst exponent (dimensionless) from Stabilogram Diffusion Analysis (ML).\nMSD(Δt) = D.Δt^(2H), log-log fits on [1/fs ; Tc] and [Tc ; T/3], breakpoint searched in [0.3 ; 2.5] s.",
    "AP ST Hurst exp.      (-) ": "Short-term Hurst exponent (dimensionless) from Stabilogram Diffusion Analysis (AP).",
    "ML LT Hurst exp.      (-) ": "Long-term Hurst exponent (dimensionless) from Stabilogram Diffusion Analysis (ML).",
    "AP LT Hurst exp.      (-) ": "Long-term Hurst exponent (dimensionless) from Stabilogram Diffusion Analysis (AP).",
    "ML ST diffus. coeff.  (-) ": "Short-term diffusion coefficient D = exp(intercept) of the log-log fit (cm².s^-2H).",
    "AP ST diffus. coeff.  (-) ": "Short-term diffusion coefficient D = exp(intercept) of the log-log fit (cm².s^-2H).",
    "ML LT diffus. coeff.  (-) ": "Long-term diffusion coefficient D = exp(intercept) of the log-log fit (cm².s^-2H).",
    "AP LT diffus. coeff.  (-) ": "Long-term diffusion coefficient D = exp(intercept) of the log-log fit (cm².s^-2H).",

    # --- STOCHASTIC / Critical time & MSD ---
    "ML crit. time Tc      (s) ": "Critical time Tc (s), ML: intersection of the short- and long-term log-log fits, bounded to [1/fs ; T/3].",
    "AP crit. time Tc      (s) ": "Critical time Tc (s), AP: intersection of the short- and long-term log-log fits, bounded to [1/fs ; T/3].",
    "ML MSD at Tc        (cm²) ": "Mean Square Displacement at the critical time, ML (cm²).",
    "AP MSD at Tc        (cm²) ": "Mean Square Displacement at the critical time, AP (cm²).",

    # --- NONLINEAR / Sample entropy ---
    "ML sample entropy     (-) ": "Sample entropy SampEn(m, r) of ML COP increments by default (Richman & Moorman, 2000).\nLower = more regular. m and r (x SD) set in Parameters. Strongly depends on m, r, N and fs.",
    "AP sample entropy     (-) ": "Sample entropy SampEn(m, r) of AP COP increments by default (Richman & Moorman, 2000).\nLower = more regular. m and r (x SD) set in Parameters. Strongly depends on m, r, N and fs.",

    # --- NONLINEAR / DFA, RQA ---
    "ML RQA recurrence     (%) ": "RQA recurrence rate (%), ML. Equals the target rate (5%) in fixed recurrence rate mode;\nmeaningful only in fixed radius mode (Advanced settings),\nwhere it can drop near 0% with high embedding dimensions.",
    "AP RQA recurrence     (%) ": "RQA recurrence rate (%), AP. Equals the target rate (5%) in fixed recurrence rate mode;\nmeaningful only in fixed radius mode (Advanced settings),\nwhere it can drop near 0% with high embedding dimensions.",
    "ML DFA α short-term   (-) ": "DFA scaling exponent α (ML positions), windows from 4 samples to the crossover (1 s by default).\nα ≈ 0.5 uncorrelated noise, 1 = 1/f, 1.5 = brownian motion (Peng et al., 1994).",
    "AP DFA α short-term   (-) ": "DFA scaling exponent α (AP positions), windows from 4 samples to the crossover (1 s by default).\nα ≈ 0.5 uncorrelated noise, 1 = 1/f, 1.5 = brownian motion (Peng et al., 1994).",
    "ML DFA α long-term    (-) ": "DFA scaling exponent α (ML positions), windows from the crossover to N/4.\nLong-term estimates are unstable on short recordings (30 s).",
    "AP DFA α long-term    (-) ": "DFA scaling exponent α (AP positions), windows from the crossover to N/4.\nLong-term estimates are unstable on short recordings (30 s).",
    "ML RQA determinism    (%) ": "RQA determinism (%), ML: share of recurrent points forming diagonal lines (>= 2 points).\nRadius: fixed recurrence rate (5%) or fixed radius, Theiler window (m-1).tau.",
    "AP RQA determinism    (%) ": "RQA determinism (%), AP: share of recurrent points forming diagonal lines (>= 2 points).\nRadius: fixed recurrence rate (5%) or fixed radius, Theiler window (m-1).tau.",
    "ML RQA max. line    (pts) ": "RQA longest diagonal line (points), ML. Related to the stability of the recurrent trajectories.",
    "AP RQA max. line    (pts) ": "RQA longest diagonal line (points), AP. Related to the stability of the recurrent trajectories.",
    "ML RQA line entropy   (-) ": "RQA Shannon entropy of the diagonal line length distribution, ML (complexity of the deterministic structure).",
    "AP RQA line entropy   (-) ": "RQA Shannon entropy of the diagonal line length distribution, AP (complexity of the deterministic structure).",
    "ML embedding dim.     (-) ": "Embedding dimension m used for RQA (ML): false nearest neighbours rate < 1% (Kennel et al., 1992).",
    "AP embedding dim.     (-) ": "Embedding dimension m used for RQA (AP): false nearest neighbours rate < 1% (Kennel et al., 1992).",
    "ML embedding delay    (s) ": "Embedding delay tau used for RQA (ML, s): first minimum of the average mutual information.",
    "AP embedding delay    (s) ": "Embedding delay tau used for RQA (AP, s): first minimum of the average mutual information.",
}
