"""
Lecture continue en tâche de fond.

Le fil de lecture interroge la planche en permanence (aucun rapport ne
s'accumule dans le tampon système), horodate chaque mesure à sa réception,
applique la tare, calcule le CoP, et alimente :
  - un tampon « temps réel » pour l'affichage ;
  - la liste de l'enregistrement en cours, le cas échéant.
"""
from __future__ import annotations

import threading
import time
from collections import deque

import numpy as np

from .board import SENSOR_DX_CM, SENSOR_DY_CM

MIN_LOAD_KG = 1.0


def cop_from_sensors(tl, tr, bl, br):
    """CoP en cm, convention OpenSway : ML+ = droite, AP+ = avant."""
    tot = tl + tr + bl + br
    if tot <= MIN_LOAD_KG:
        return 0.0, 0.0, tot
    ml = (SENSOR_DX_CM / 2) * ((tr + br) - (tl + bl)) / tot
    ap = (SENSOR_DY_CM / 2) * ((tl + tr) - (bl + br)) / tot
    return ml, ap, tot


class Reader(threading.Thread):
    def __init__(self, device, live_seconds: float = 120.0):
        super().__init__(daemon=True)
        self.dev = device
        self.lock = threading.Lock()
        self.live = deque(maxlen=int(live_seconds * 120))
        self.count = 0                       # nb total de mesures reçues
        self.tare = [0.0, 0.0, 0.0, 0.0]     # TL, TR, BL, BR (kg)
        self.error = None
        self._running = True
        self._rec = None
        self._rec_t0 = 0.0
        self._tare_acc = None
        self._tare_done = threading.Event()
        self.t0 = time.perf_counter()
        self._last_batt = 0.0

    # ------------------------------------------------------------------ fil
    def run(self):
        while self._running:
            try:
                s = self.dev.read_raw(100)
            except Exception as e:           # planche éteinte, Bluetooth coupé…
                self.error = e
                self._running = False
                break
            now = time.perf_counter()
            if now - self._last_batt > 30:
                self._last_batt = now
                self.dev.request_battery()
            if s is None:
                continue
            with self.lock:
                if self._tare_acc is not None:
                    self._tare_acc.append(s)
                tl, tr, bl, br = (v - o for v, o in zip(s, self.tare))
                ml, ap, tot = cop_from_sensors(tl, tr, bl, br)
                row = (now - self.t0, tl, tr, bl, br, ml, ap, tot)
                self.live.append(row)
                self.count += 1
                if self._rec is not None:
                    self._rec.append(row)

    def stop(self):
        self._running = False

    # ---------------------------------------------------------- temps réel
    def latest(self, since_count: int):
        """Nouvelles lignes depuis `since_count` -> (lignes, nouveau compteur)."""
        with self.lock:
            n_new = min(self.count - since_count, len(self.live))
            rows = list(self.live)[-n_new:] if n_new > 0 else []
            return rows, self.count

    def window(self, seconds: float):
        with self.lock:
            if not self.live:
                return []
            t_end = self.live[-1][0]
            return [r for r in self.live if r[0] >= t_end - seconds]

    # ------------------------------------------------------- enregistrement
    def start_recording(self):
        with self.lock:
            self._rec = []
            self._rec_t0 = time.perf_counter() - self.t0

    def recording_elapsed(self) -> float:
        return (time.perf_counter() - self.t0) - self._rec_t0

    def stop_recording(self) -> np.ndarray:
        """Renvoie (n, 8) : t_ms depuis le départ, TL, TR, BL, BR, ML, AP, total."""
        with self.lock:
            rows, self._rec = self._rec or [], None
        if not rows:
            return np.empty((0, 8))
        a = np.array(rows, dtype=float)
        a[:, 0] = (a[:, 0] - self._rec_t0) * 1000.0
        return a[a[:, 0] >= 0]

    @property
    def recording(self) -> bool:
        return self._rec is not None

    # ----------------------------------------------------------------- tare
    def start_tare(self):
        with self.lock:
            self._tare_acc = []
        if hasattr(self.dev, "empty"):
            self.dev.empty = True

    def finish_tare(self) -> int:
        with self.lock:
            acc, self._tare_acc = self._tare_acc or [], None
        if hasattr(self.dev, "empty"):
            self.dev.empty = False
        if acc:
            # médiane : insensible aux quelques mesures prises en descendant
            a = np.array(acc)
            self.tare = list(np.median(a, axis=0))
        return len(acc)
