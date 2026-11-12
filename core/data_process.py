import numpy as np
from scipy.signal import butter, filtfilt

from .params     import Params
from .fileformat import Recording, read_recording
from .swarii     import swarii


# %% === DATA PREPARATION ======================================================

IC = {99: 2.58, 95: 1.96, 90: 1.64, 85: 1.44, 80: 1.28}


def read_brainblox_csv(path: str) -> Recording:
    """ OpenSway or BrainBloX file (format detected from the header) """
    return read_recording(path)


def preprocess(rec: Recording, p: Params):
    nb        = len(rec.t_s)
    t_signal  = rec.t_s - rec.t_s[0]
    duration  = float(t_signal[-1])
    fs        = p.target_fs

    # Time axis uniform resampling at target_fs:
    #   SWARII (Audiffren & Contal, 2016) or linear interpolation (v2.3)
    t_uniform = np.arange(0.0, duration, 1.0/fs)

    # x axis (mediolateral, in cm) ; y axis (anteroposterior, in cm, + = anterior)
    if p.resampling == "swarii":
        x_uniform = swarii(t_signal, rec.ml, t_uniform, p.swarii_win_s)
        y_uniform = swarii(t_signal, rec.ap, t_uniform, p.swarii_win_s)
    else:
        x_uniform = np.interp(t_uniform, t_signal, rec.ml)
        y_uniform = np.interp(t_uniform, t_signal, rec.ap)

    # Butterworth filter, lowpass 10 Hz, zerolag (filtfilt)
    nyq       = 0.5*fs
    wn        = min(p.butter_fc/nyq, 0.99)
    b, a      = butter(p.butter_order, wn, btype='low', analog=False)
    x_filt    = filtfilt(b, a, x_uniform, method='gust')
    y_filt    = filtfilt(b, a, y_uniform, method='gust')

    ### POSITIONAL PARAMETERS: MEAN & STD ML/AP ################################
    mean_ML   = float(np.mean(x_filt))
    std_ML    = float(np.std(x_filt, ddof=1))
    mean_AP   = float(np.mean(y_filt))
    std_AP    = float(np.std(y_filt, ddof=1))

    # Centered data for stabilometric analyses
    x_centered = x_filt - mean_ML
    y_centered = y_filt - mean_AP

    # Acquisition quality: native rate of distinct samples (WBB repeats reports)
    distinct  = np.r_[True, np.any(np.diff(rec.sensors, axis=0) != 0, axis=1)]
    native_fs = (distinct.sum() - 1) / duration if duration > 0 else np.nan

    qc = {
        'original_nb':        int(nb),
        'duration':           round(duration,1),
        'uniform_n':          int(len(t_uniform)),
        'native_fs':          round(float(native_fs),1),
        'mean_weight':        round(float(np.mean(rec.total)),1),
        'mean_ML':            round(mean_ML,2),
        'std_ML':             round(std_ML,3),
        'mean_AP':            round(mean_AP,2),
        'std_AP':             round(std_AP,3)
    }

    return t_uniform, x_centered, y_centered, x_filt, y_filt, qc
