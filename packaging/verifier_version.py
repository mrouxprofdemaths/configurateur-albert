"""Vérifie que la version est la même partout (scripts, README, code).

    python packaging/verifier_version.py                 # cohérence seule
    python packaging/verifier_version.py --etiquette v0.1.0   # + correspond à l'étiquette poussée
    python packaging/verifier_version.py --signaler-absente   # avertit si l'étiquette n'existe pas sur la Forge

Erreur (code 1) en cas d'incohérence. --signaler-absente n'échoue pas : il affiche un
avertissement, car l'étiquette est créée après la fusion sur main.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEPOT = "https://forge.apps.education.fr/rouxpierre-edouard/configurateur-albert"


def versions() -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    sh = (ROOT / "install.sh").read_text(encoding="utf-8")
    found["install.sh"] = set(re.findall(r'CONFIGURATEUR_REF:-(v[\d.]+)', sh))
    ps1 = (ROOT / "install.ps1").read_text(encoding="utf-8")
    found["install.ps1"] = set(re.findall(r'else \{ "(v[\d.]+)" \}', ps1))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    found["README.md"] = set(re.findall(rf"{re.escape(DEPOT)}/-/raw/(v[\d.]+)/install\.", readme))
    init = (ROOT / "configurateur_albert" / "__init__.py").read_text(encoding="utf-8")
    found["__init__.py"] = {"v" + v for v in re.findall(r'__version__ = "([\d.]+)"', init)}
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--etiquette")
    parser.add_argument("--signaler-absente", action="store_true")
    args = parser.parse_args()

    found = versions()
    for name, vs in found.items():
        print(f"{name:12} {', '.join(sorted(vs)) or '(aucune)'}")
    all_versions = set().union(*found.values())
    if len(all_versions) != 1 or any(not vs for vs in found.values()):
        print("::error::Versions incohérentes entre scripts, README et code.")
        return 1
    version = all_versions.pop()

    if args.etiquette and args.etiquette != version:
        print(f"::error::L'étiquette {args.etiquette} ne correspond pas à la version {version} des fichiers.")
        return 1

    if args.signaler_absente:
        out = subprocess.run(["git", "ls-remote", "--tags", f"{DEPOT}.git", version],
                             capture_output=True, text=True, check=False).stdout
        if version not in out:
            print(f"::warning::L'étiquette {version} n'existe pas encore sur la Forge : les commandes "
                  f"du README renvoient une erreur 404. Créez-la (Déploiement → Versions → "
                  f"Nouvelle version, étiquette {version}, cible main).")
        else:
            print(f"Étiquette {version} présente sur la Forge.")
    print(f"Version cohérente : {version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
