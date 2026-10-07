"""Point d'entrée pour PyInstaller (import absolu du paquet)."""

import sys

from configurateur_albert.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
