"""Point d'entrée : interface graphique par défaut, mode texte en secours.

  configurateur-albert                → interface graphique
  configurateur-albert --texte        → mode texte (terminal)
  configurateur-albert --desinstaller → désinstallation (mode texte)
"""

from __future__ import annotations

import argparse
import os
import sys

from . import APP_NAME, __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="configurateur-albert", description=APP_NAME)
    parser.add_argument("--texte", "--cli", action="store_true", help="mode texte, sans fenêtre")
    parser.add_argument("--desinstaller", action="store_true", help="retirer les réglages Albert")
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {__version__}")
    parser.add_argument("--test-interface", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.test_interface:  # utilisé par la CI : l'interface démarre-t-elle dans l'exécutable ?
        from . import gui

        app = gui.App()
        app.update()
        app.destroy()
        print("Interface graphique OK")
        return 0

    headless = sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    if args.texte or args.desinstaller or headless:
        from . import cli

        return cli.run(uninstall=args.desinstaller)
    try:
        from . import gui
    except ImportError:  # Python sans Tkinter
        from . import cli

        print("Interface graphique indisponible : passage en mode texte.\n")
        return cli.run()
    return gui.run()


if __name__ == "__main__":
    sys.exit(main())
