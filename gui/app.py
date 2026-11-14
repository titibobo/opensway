"""Fenêtre principale d'OpenSway : onglets Acquisition et Analyse, connexion partagée."""
import queue
import sys
import threading
import time
import traceback

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, messagebox

from acquisition.reader import Reader
from acquisition.simulator import SimulatedBoard
from core.i18n import tr, fr, set_language
from gui.common import VERSION, load_config


class BoardManager:
    """Connexion à la planche (ou au simulateur) et fil de lecture partagé."""

    def __init__(self, app):
        self.app = app
        self.device = None
        self.reader = None
        self.busy = False

    @property
    def connected(self) -> bool:
        return self.reader is not None and self.reader.is_alive()

    @property
    def is_simulator(self) -> bool:
        return isinstance(self.device, SimulatedBoard)

    def _start_reader(self, dev):
        self.device = dev
        self.reader = Reader(dev)
        self.reader.start()

    def connect(self, source: str, on_done):
        """on_done(status, message) appelé dans le fil Tk.
        status : 'ok' | 'not_found' | 'error'."""
        if self.busy:
            return
        self.busy = True

        def work():
            try:
                if source == "sim":
                    dev = SimulatedBoard()
                    dev.open()
                else:
                    from acquisition.board import BalanceBoard
                    dev = BalanceBoard()
                    dev.open()
                self._start_reader(dev)
                status, msg = "ok", f"{fr(dev.name)} : {fr('connexion établie.')}"
            except ImportError:
                status, msg = "error", fr("Module 'hidapi' absent : "
                                          "pip install hidapi (inutile avec le .exe).")
            except RuntimeError as e:
                status, msg = "not_found", str(e)
            except Exception as e:
                status, msg = "error", f"{type(e).__name__} : {e}"
            self.busy = False
            self.app.post(lambda: on_done(status, msg))

        threading.Thread(target=work, daemon=True).start()

    def pair_and_connect(self, on_done):
        """Appairage (bouton SYNC) puis ouverture, avec 20 s de patience."""
        if self.busy:
            return
        self.busy = True

        def log(m):
            self.app.post(lambda m=m: self.app.log(m))

        def work():
            status, msg = "error", fr("Appairage échoué.")
            try:
                if sys.platform != "win32":
                    raise RuntimeError(fr("Appairage automatique disponible sous Windows uniquement."))
                from acquisition.board import BalanceBoard, pair_windows
                if pair_windows(log=log):
                    t_end = time.perf_counter() + 20
                    while True:
                        try:
                            dev = BalanceBoard()
                            dev.open()
                            self._start_reader(dev)
                            status, msg = "ok", fr("Wii Balance Board appairée et connectée.")
                            break
                        except RuntimeError:
                            if time.perf_counter() > t_end:
                                msg = fr("Appairage fait, mais la planche n'apparaît pas.")
                                break
                            time.sleep(2)
            except Exception as e:
                msg = f"{type(e).__name__} : {e}"
                log(traceback.format_exc())
            self.busy = False
            self.app.post(lambda: on_done(status, msg))

        threading.Thread(target=work, daemon=True).start()

    def disconnect(self):
        if self.reader:
            self.reader.stop()
            self.reader.join(timeout=1.0)
        if self.device:
            try:
                self.device.close()
            except Exception:
                pass
        self.reader = None
        self.device = None


class OpenSwayApp(tk.Tk):
    def __init__(self):
        super().__init__()
        set_language(load_config().get("language", "fr"))

        self.ui_fixed = tkfont.Font(family='Courier New', size=8)
        self.option_add('*Font', self.ui_fixed)
        self.style = ttk.Style(self)
        self.style.configure('.', font=self.ui_fixed)
        self.style.configure('TNotebook.Tab', padding=(6, 2))
        self.style.configure('TButton', padding=(6, 2))
        self.style.configure('TEntry', padding=(2, 1))
        self.style.configure('Big.TButton', padding=(6, 6),
                             font=(self.ui_fixed.actual('family'), 10, 'bold'))

        self.title(f"OpenSway v{VERSION} - ESO, Research Department")
        self.geometry('1200x690')
        self.minsize(1200, 690)

        self._q = queue.Queue()
        self.board = BoardManager(self)

        from gui.analysis import AnalysisPanel
        from gui.acquisition import AcquisitionPanel
        from gui.settings import SettingsPanel

        self.restart = False
        nb = ttk.Notebook(self)
        nb.pack(fill='both', expand=True)
        self.analysis    = AnalysisPanel(nb, self)
        self.acquisition = AcquisitionPanel(nb, self)
        self.settings    = SettingsPanel(nb, self)
        nb.add(self.acquisition, text=tr("Acquisition"))
        nb.add(self.analysis,    text=tr("Analysis"))
        nb.add(self.settings,    text=tr("Settings"))
        nb.add(self.analysis.logs_tab, text=tr("Logs"))
        self.notebook = nb

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(50, self._drain)

    # Exécuter une fonction dans le fil Tk (depuis un autre fil)
    def post(self, fn):
        self._q.put(fn)

    def _drain(self):
        try:
            while True:
                self._q.get_nowait()()
        except queue.Empty:
            pass
        except Exception:
            self.log(traceback.format_exc())
        self.after(50, self._drain)

    def log(self, msg: str):
        self.analysis._log(msg)
        self.acquisition.set_status_line(msg)

    def _cancel_afters(self):
        """Annule les rafraîchissements programmés avant de fermer la fenêtre."""
        # Annulation au niveau Tcl : les commandes Python associées sont
        # supprimées ensuite par destroy() (after_cancel les supprimerait deux fois)
        for aid in self.tk.splitlist(self.tk.call('after', 'info')):
            try:
                self.tk.call('after', 'cancel', aid)
            except tk.TclError:
                pass

    def request_restart(self):
        """Ferme et relance la fenêtre principale (changement de langue)."""
        self.restart = True
        self.board.disconnect()
        self._cancel_afters()
        self.destroy()

    def _on_close(self):
        if self.acquisition.busy_recording():
            if not messagebox.askyesno("OpenSway", fr("Un enregistrement est en cours. Quitter ?")):
                return
        self.board.disconnect()
        self._cancel_afters()
        self.destroy()


def main():
    while True:
        app = OpenSwayApp()
        app.mainloop()
        if not app.restart:
            break
