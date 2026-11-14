"""
Pilote de la Wii Balance Board sous Windows : appairage Bluetooth (API Windows
via ctypes, logique reprise de l'émulateur Dolphin) et lecture HID (hidapi).
"""
from __future__ import annotations

import struct
import sys
import time

NINTENDO_VID = 0x057E
WBB_PIDS     = (0x0306, 0x0330)
WBB_NAME     = "Nintendo RVL-WBC-01"

# Entraxe des capteurs (wiibrew) en cm
SENSOR_DX_CM = 43.3      # gauche-droite
SENSOR_DY_CM = 23.8      # avant-arrière


def pair_windows(timeout_mult: int = 3, log=print) -> bool:
    import ctypes
    from ctypes import wintypes as wt

    # Les fonctions sont réparties selon les versions de Windows entre
    # bthprops.cpl et BluetoothApis.dll : on cherche dans les deux.
    libs = []
    for name in ("bthprops.cpl", "BluetoothApis.dll"):
        try:
            libs.append(ctypes.WinDLL(name))
        except OSError:
            pass
    if not libs:
        log("[ERREUR] API Bluetooth Windows introuvable.")
        return False

    class BT_ADDR(ctypes.Union):
        _fields_ = [("ullLong", ctypes.c_ulonglong), ("rgBytes", ctypes.c_ubyte * 6)]

    class SYSTEMTIME(ctypes.Structure):
        _fields_ = [(n, wt.WORD) for n in
                    ("wYear", "wMonth", "wDayOfWeek", "wDay",
                     "wHour", "wMinute", "wSecond", "wMilliseconds")]

    class FIND_RADIO_PARAMS(ctypes.Structure):
        _fields_ = [("dwSize", wt.DWORD)]

    class RADIO_INFO(ctypes.Structure):
        _fields_ = [("dwSize", wt.DWORD), ("address", BT_ADDR),
                    ("szName", wt.WCHAR * 248), ("ulClassofDevice", wt.ULONG),
                    ("lmpSubversion", wt.USHORT), ("manufacturer", wt.USHORT)]

    class DEVICE_SEARCH_PARAMS(ctypes.Structure):
        _fields_ = [("dwSize", wt.DWORD),
                    ("fReturnAuthenticated", wt.BOOL), ("fReturnRemembered", wt.BOOL),
                    ("fReturnUnknown", wt.BOOL), ("fReturnConnected", wt.BOOL),
                    ("fIssueInquiry", wt.BOOL), ("cTimeoutMultiplier", ctypes.c_ubyte),
                    ("hRadio", wt.HANDLE)]

    class DEVICE_INFO(ctypes.Structure):
        _fields_ = [("dwSize", wt.DWORD), ("Address", BT_ADDR),
                    ("ulClassofDevice", wt.ULONG), ("fConnected", wt.BOOL),
                    ("fRemembered", wt.BOOL), ("fAuthenticated", wt.BOOL),
                    ("stLastSeen", SYSTEMTIME), ("stLastUsed", SYSTEMTIME),
                    ("szName", wt.WCHAR * 248)]

    class GUID(ctypes.Structure):
        _fields_ = [("Data1", wt.DWORD), ("Data2", wt.WORD),
                    ("Data3", wt.WORD), ("Data4", ctypes.c_ubyte * 8)]

    HID_SERVICE = GUID(0x00001124, 0x0000, 0x1000,
                       (ctypes.c_ubyte * 8)(0x80, 0x00, 0x00, 0x80, 0x5F, 0x9B, 0x34, 0xFB))
    BLUETOOTH_SERVICE_ENABLE = 0x01

    # Signatures explicites : indispensable en 64 bits (handles = pointeurs 64 bits)
    P = ctypes.POINTER
    bt = type("BT", (), {})()
    def sig(fn, res, *args):
        for lib in libs:
            try:
                f = getattr(lib, fn)
                break
            except AttributeError:
                continue
        else:
            raise RuntimeError(f"Fonction Bluetooth absente de Windows : {fn}")
        f.restype = res; f.argtypes = list(args)
        setattr(bt, fn, f)
    sig("BluetoothFindFirstRadio",  wt.HANDLE, P(FIND_RADIO_PARAMS), P(wt.HANDLE))
    sig("BluetoothFindRadioClose",  wt.BOOL,   wt.HANDLE)
    sig("BluetoothGetRadioInfo",    wt.DWORD,  wt.HANDLE, P(RADIO_INFO))
    sig("BluetoothFindFirstDevice", wt.HANDLE, P(DEVICE_SEARCH_PARAMS), P(DEVICE_INFO))
    sig("BluetoothFindNextDevice",  wt.BOOL,   wt.HANDLE, P(DEVICE_INFO))
    sig("BluetoothFindDeviceClose", wt.BOOL,   wt.HANDLE)
    sig("BluetoothRemoveDevice",    wt.DWORD,  P(BT_ADDR))

    sig("BluetoothAuthenticateDevice", wt.DWORD,
        wt.HWND, wt.HANDLE, P(DEVICE_INFO), P(wt.WCHAR), wt.ULONG)
    sig("BluetoothEnumerateInstalledServices", wt.DWORD,
        wt.HANDLE, P(DEVICE_INFO), P(wt.DWORD), ctypes.c_void_p)
    sig("BluetoothSetServiceState", wt.DWORD,
        wt.HANDLE, P(DEVICE_INFO), P(GUID), wt.DWORD)

    # --- radio locale ---
    rp = FIND_RADIO_PARAMS(ctypes.sizeof(FIND_RADIO_PARAMS))
    h_radio = wt.HANDLE()
    h_find = bt.BluetoothFindFirstRadio(ctypes.byref(rp), ctypes.byref(h_radio))
    if not h_find:
        log("[ERREUR] Aucun adaptateur Bluetooth trouvé.")
        return False
    bt.BluetoothFindRadioClose(h_find)

    ri = RADIO_INFO(); ri.dwSize = ctypes.sizeof(RADIO_INFO)
    bt.BluetoothGetRadioInfo(h_radio, ctypes.byref(ri))
    host = bytes(ri.address.rgBytes)          # ordre "inversé" usuel, comme Dolphin
    log(f"[BT] Adaptateur : {ri.szName}  ({':'.join(f'{b:02X}' for b in reversed(host))})")
    passkey = (wt.WCHAR * 6)(*[chr(b) for b in host])   # PIN = adresse hôte (bouton SYNC)

    seen = set()

    def search(inquiry: bool):
        sp = DEVICE_SEARCH_PARAMS(ctypes.sizeof(DEVICE_SEARCH_PARAMS),
                                  True, True, True, True, inquiry,
                                  timeout_mult if inquiry else 0, h_radio)
        di = DEVICE_INFO(); di.dwSize = ctypes.sizeof(DEVICE_INFO)
        found = []
        h = bt.BluetoothFindFirstDevice(ctypes.byref(sp), ctypes.byref(di))
        if not h:
            return found
        while True:
            seen.add(di.szName or "(sans nom)")
            if di.szName == WBB_NAME:
                found.append(DEVICE_INFO.from_buffer_copy(di))
            if not bt.BluetoothFindNextDevice(h, ctypes.byref(di)):
                break
        bt.BluetoothFindDeviceClose(h)
        return found

    # Logique reprise de l'émulateur Dolphin (WiimoteReal/IOWin.cpp) :
    # 1) ne retirer que les appairages inutilisables (mémorisés, non connectés,
    #    NON authentifiés) -- un appairage authentifié se reconnecte via POWER ;
    for d in search(inquiry=False):
        if d.fRemembered and not d.fConnected and not d.fAuthenticated:
            log("[BT] Appairage inutilisable retiré.")
            bt.BluetoothRemoveDevice(ctypes.byref(d.Address))

    # 2) 3 passes : authentifier si besoin (échoue souvent avec le code 31, c'est
    #    connu), puis activer le service HID DANS TOUS LES CAS.
    log("[BT] Recherche… (la LED de la planche doit clignoter)")
    def set_hid(d, flag):
        return bt.BluetoothSetServiceState(h_radio, ctypes.byref(d),
                                           ctypes.byref(HID_SERVICE), flag)

    ok = False
    for it in range(3):
        hits = search(inquiry=True)
        if not hits:
            log(f"[BT] Passe {it + 1}/3 : planche non vue.")
        for d in hits:
            if d.fConnected:
                log(f"[BT] Passe {it + 1}/3 : planche connectée (bouton POWER).")
            elif not d.fAuthenticated:
                r = bt.BluetoothAuthenticateDevice(None, h_radio, ctypes.byref(d), passkey, 6)
                log(f"[BT] Passe {it + 1}/3 : authentification code {r}"
                    + (" (OK)" if r == 0 else " (échec fréquent, on continue)"))
                if r == 0:
                    n = wt.DWORD(0)
                    bt.BluetoothEnumerateInstalledServices(h_radio, ctypes.byref(d),
                                                           ctypes.byref(n), None)
            # Service HID : activé dans tous les cas, même planche déjà connectée.
            # En cas de refus (ex. 0x80070057), désactivation puis réactivation :
            # cela relance le pilote HID de Windows pour cet appareil.
            r = set_hid(d, BLUETOOTH_SERVICE_ENABLE)
            log(f"[BT] Passe {it + 1}/3 : activation HID code {r}" + (" (OK)" if r == 0 else ""))
            if r != 0:
                r0 = set_hid(d, 0x00)                       # BLUETOOTH_SERVICE_DISABLE
                time.sleep(1.0)
                r = set_hid(d, BLUETOOTH_SERVICE_ENABLE)
                log(f"[BT] Passe {it + 1}/3 : HID désactivé ({r0}) puis réactivé, code {r}"
                    + (" (OK)" if r == 0 else ""))
            ok = ok or r == 0
        if ok:
            break

    if not ok:
        log(f"[BT] Appareils vus : {sorted(seen) or 'aucun'}")
        return False
    log("[BT] Appairage terminé. La LED doit rester allumée fixe.")
    return True


# =============================================================================
# 2) PILOTE HID DE LA PLANCHE
# =============================================================================
class BalanceBoard:
    name = "Wii Balance Board"
    def __init__(self, hid_module=None):
        if hid_module is None:
            import hid as hid_module     # import explicite : détecté par PyInstaller
        self.hid = hid_module
        self.dev = None
        self.cal = None            # [[0kg, 17kg, 34kg] pour TR, BR, TL, BL]
        self.battery_raw = None

    # ---------- connexion ----------
    def open(self) -> None:
        cands = [d for d in self.hid.enumerate(NINTENDO_VID, 0)
                 if d["product_id"] in WBB_PIDS]
        if not cands:
            raise RuntimeError("Aucune planche HID visible. Est-elle allumée / appairée ?")
        last = None
        for c in cands:            # une Wiimote peut aussi être là : on teste chacune
            try:
                dev = self.hid.device()
                dev.open_path(c["path"])
                self.dev = dev
                self._init_extension()
                self.cal = self._read_calibration()
                self.request_status()
                self.start_stream()
                return
            except Exception as e:  # pas une planche ou chemin mort
                last = e
                try:
                    dev.close()
                except Exception:
                    pass
                self.dev = None
        raise RuntimeError(f"Impossible d'initialiser la planche : {last}")

    def close(self):
        if self.dev:
            self.dev.close()
            self.dev = None

    # ---------- bas niveau ----------
    def _write(self, data: list[int]):
        if self.dev.write(data) < 0:
            raise IOError("Échec d'écriture HID")

    def _write_mem(self, addr: int, payload: bytes):
        buf = list(payload) + [0] * (16 - len(payload))
        self._write([0x16, 0x04, (addr >> 16) & 0xFF, (addr >> 8) & 0xFF, addr & 0xFF,
                     len(payload)] + buf)
        self._wait_for(0x22, 1.0)

    def _wait_for(self, report_id: int, timeout_s: float):
        t_end = time.perf_counter() + timeout_s
        while time.perf_counter() < t_end:
            r = self.dev.read(22, 50)
            if r and r[0] == report_id:
                return r
        return None

    def _init_extension(self):
        self._write([0x11, 0x10])                     # allume la LED (fin du clignotement)
        self._write_mem(0xA400F0, b"\x55")            # init extension sans chiffrement
        self._write_mem(0xA400FB, b"\x00")

    def _read_calibration(self):
        self._write([0x17, 0x04, 0xA4, 0x00, 0x20, 0x00, 0x20])   # 32 octets @A40020
        mem = {}
        t_end = time.perf_counter() + 2.0
        while len(mem) < 2 and time.perf_counter() < t_end:
            r = self.dev.read(22, 50)
            if r and r[0] == 0x21:
                if r[3] & 0x0F:
                    raise IOError(f"Erreur de lecture mémoire (0x{r[3]:02X})")
                mem[(r[4] << 8) | r[5]] = bytes(r[6:22])
        if 0x0020 not in mem or 0x0030 not in mem:
            raise IOError("Calibration non reçue (pas une Balance Board ?)")
        blk = (mem[0x0020] + mem[0x0030])[4:28]
        v = struct.unpack(">12H", blk)                # 0kg x4, 17kg x4, 34kg x4
        return [[v[i], v[i + 4], v[i + 8]] for i in range(4)]

    def request_status(self):
        self._write([0x15, 0x00])
        r = self._wait_for(0x20, 1.0)
        if r:
            self.battery_raw = r[6]
        return self.battery_raw

    def start_stream(self):
        self._write([0x12, 0x04, 0x32])               # mode continu, boutons + 8 oct. ext.

    # ---------- conversion ----------
    def _to_kg(self, i: int, raw: int) -> float:
        c0, c17, c34 = self.cal[i]
        if raw < c17:
            return 17.0 * (raw - c0) / (c17 - c0)
        return 17.0 + 17.0 * (raw - c17) / (c34 - c17)

    def parse(self, r):
        """Rapport 0x32 -> (TL, TR, BL, BR) en kg (sans tare), ou None.
        Un rapport d'état 0x20 met à jour la batterie au passage."""
        if not r:
            return None
        if r[0] == 0x20 and len(r) > 6:
            self.battery_raw = r[6]
            # Après un rapport d'état, la Wii exige que le mode de rapport soit
            # renvoyé, sinon le flux de données s'arrête (wiibrew).
            self.start_stream()
            return None
        if r[0] != 0x32:
            return None
        raw = struct.unpack(">4H", bytes(r[3:11]))       # TR, BR, TL, BL
        tr, br, tl, bl = (self._to_kg(i, raw[i]) for i in range(4))
        return tl, tr, bl, br

    def read_raw(self, timeout_ms: int = 100):
        return self.parse(self.dev.read(22, timeout_ms))

    def request_battery(self):
        """Demande non bloquante (réponse lue par read_raw)."""
        try:
            self._write([0x15, 0x00])
        except Exception:
            pass

    def battery_percent(self):
        # Octet batterie de la Balance Board : ~0xD0 plein (approximation)
        if self.battery_raw is None:
            return None
        return max(0, min(100, round(100 * self.battery_raw / 0xD0)))
