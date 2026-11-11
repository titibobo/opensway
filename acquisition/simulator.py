"""
Planche simulée : même interface que BalanceBoard (open / close / read_raw).

Sert à préparer un TP ou à montrer le logiciel sans planche. Le signal imite
une planche réelle : rythme irrégulier (~65 mesures distinctes/s, avec rafales et
répétitions), oscillations lentes de type Ornstein-Uhlenbeck et bruit capteur.
Ce n'est PAS un modèle physiologique : ne pas l'utiliser pour des données.
"""
from __future__ import annotations

import math
import random
import time

from .board import SENSOR_DX_CM, SENSOR_DY_CM


class SimulatedBoard:
    name = "Simulateur"

    def __init__(self, weight_kg: float = 70.0):
        self.weight = weight_kg
        self.cal = None
        self.battery_raw = None
        self.instability = 1.0          # 1 = yeux ouverts sol dur ; plus = plus instable
        self.empty = False              # simule « personne sur la planche »
        self.offsets = [0.4, -0.3, 0.2, -0.1]   # dérive de zéro des capteurs (kg)
        self._x = self._y = 0.0
        self._fx = self._fy = 0.0
        self._last = None
        self._t = None
        self._pending = []

    def open(self):
        self._t = time.perf_counter()

    def close(self):
        pass

    def request_battery(self):
        pass

    def battery_percent(self):
        return None

    # Processus lent (OU) + composante rapide, en cm
    def _step(self, dt: float):
        k = self.instability
        for attr, th, sig in (("_x", 0.6, 0.45), ("_y", 0.4, 0.70)):
            v = getattr(self, attr)
            v += -th * v * dt + sig * k * math.sqrt(2 * th * dt) * random.gauss(0, 1)
            setattr(self, attr, v)
        for attr in ("_fx", "_fy"):
            v = getattr(self, attr)
            v += -8.0 * v * dt + 0.08 * k * math.sqrt(16 * dt) * random.gauss(0, 1)
            setattr(self, attr, v)

    def _sensors(self):
        if self.empty:
            w, x, y = 0.0, 0.0, 0.0
        else:
            w = self.weight + random.gauss(0, 0.05)
            x = self._x + self._fx
            y = -2.0 + self._y + self._fy          # CoP un peu en arrière du centre
        fx = 0.5 + x / SENSOR_DX_CM
        fy = 0.5 + y / SENSOR_DY_CM
        tl = w * fy * (1 - fx)
        tr = w * fy * fx
        bl = w * (1 - fy) * (1 - fx)
        br = w * (1 - fy) * fx
        return tuple(v + o + random.gauss(0, 0.02)
                     for v, o in zip((tl, tr, bl, br), self.offsets))

    def read_raw(self, timeout_ms: int = 100):
        if self._pending:                 # rafale : rapports déjà « reçus »
            return self._pending.pop()
        # intervalle irrégulier : 12-17 ms la plupart du temps, parfois 25 ms
        dt = random.choice([0.0120, 0.0135, 0.0150, 0.0165, 0.0250])
        time.sleep(dt)
        now = time.perf_counter()
        self._step(now - self._t)
        self._t = now
        s = self._sensors()
        if random.random() < 0.10 and self._last is not None:
            s = self._last                # répétition à l'identique
        self._last = s
        if random.random() < 0.05:
            self._pending = [s]           # rapport dupliqué en rafale
        return s
