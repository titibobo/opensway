"""OpenSway - stabilométrie sur Wii Balance Board : acquisition et analyse.

ESO Paris, Research Department.
Lancement : python opensway.py
"""
import sys
import traceback

try:
    import pyi_splash          # écran de démarrage (version .exe)
except Exception:
    pyi_splash = None


def main():
    from gui.app import OpenSwayApp
    first = True
    while True:
        app = OpenSwayApp()
        if first and pyi_splash:
            pyi_splash.close()
        first = False
        app.mainloop()
        if not app.restart:          # relance après changement de langue
            break


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Fatal error:", e, file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
