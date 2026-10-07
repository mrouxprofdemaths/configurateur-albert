"""Génère les captures d'écran du README (interface réelle, données fictives).

Linux, avec Xvfb et un Python qui contient Tkinter (celui de uv convient). Le Tk de uv
n'utilise que les polices « X11 » : on déclare donc les polices DejaVu au serveur X.

    F=$(mktemp -d); cp /usr/share/fonts/truetype/dejavu/DejaVuSans*.ttf "$F"
    (cd "$F" && mkfontscale && mkfontdir)
    xvfb-run -a -s "-screen 0 1280x900x24 -fp $F,/usr/share/fonts/X11/misc" \\
        uv run --no-project --managed-python --python 3.12 --with pillow \\
        python docs/captures/generer.py

Aucune donnée réelle n'est utilisée : la clé est factice et les étapes d'installation
sont simulées, pour montrer l'enchaînement des écrans sans rien modifier sur le poste.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from PIL import ImageGrab  # noqa: E402

from configurateur_albert import albert, gui, installer  # noqa: E402

# Dossier personnel fictif : les chemins affichés ne révèlent rien de la machine de capture.
Path.home = classmethod(lambda cls: Path("/Users/prenom.nom"))  # type: ignore[method-assign]

FAKE_KEY = "sk-eyJhbGciOiJfactice.exemple-de-cle-pour-captures"
RAW_MODELS = [
    {"id": "gemma-4-31b-it", "type": "image-text-to-text"},
    {"id": "gpt-oss-120b", "type": "text-generation"},
    {"id": "deepseek-v4-flash-0731", "type": "text-generation"},
    {"id": "ministral-3-8b-instruct-2512", "type": "image-text-to-text"},
    {"id": "lightonocr-2-1b", "type": "image-text-to-text"},
]

installer.diagnose = lambda: installer.Diagnostic(
    os="macOS 15.6 (arm64)", node="20.11.0", node_ok_for_pi=False, npm_writable=False,
    git_bash=None, opencode=None, pi=None, vscode=True, key=None)
albert.list_raw = lambda key, base_url=None: RAW_MODELS

STEPS_DONE = [
    ("cle", "ok", "Clé sk-eyJh… rangée"),
    ("node", "ok", "Node.js installé dans votre dossier personnel"),
    ("windows", "ignoré", "Non concerné"),
    ("opencode", "ok", "Version 1.18.35 installée"),
    ("pi", "ok", "Version 1.0.4 installée"),
    ("config", "ok", "Modèle par défaut : gemma-4-31b-it"),
    ("skills", "ok", "3 skill(s) dans ~/.agents/skills"),
    ("vscode", "ok", "Extension OpenCode installée"),
    ("test", "ok", "API : OK · OpenCode : OK · Pi : OK"),
]
LOG = [
    "Clé rangée dans ~/.albert.env (lisible par vous seul).",
    "Chargement automatique de la clé ajouté à ~/.zshrc.",
    "Recherche de la dernière version LTS de Node.js…",
    "Téléchargement de node-v24.21.0-darwin-arm64.tar.gz…",
    "Archive vérifiée (SHA-256).",
    "$ npm install -g opencode-ai@1",
    "  added 3 packages in 14s",
    "$ npm install -g --ignore-scripts @earendil-works/pi-coding-agent@1",
    "  added 121 packages in 11s",
    "OpenCode configuré : ~/.config/opencode/opencode.json",
    "Pi configuré : ~/.pi/agent/models.json",
    "  Anonymiser un texte : installé",
    "  Transcrire un enregistrement audio : installé",
    "  Cadre d'usage de l'IA (DINUM) : installé",
    "Albert répond (gemma-4-31b-it) : 'OK'",
    "Test d'OpenCode avec gemma-4-31b-it (lecture d'un fichier)…",
    "  ALBATROS-427",
    "Test de Pi avec gemma-4-31b-it (lecture d'un fichier)…",
    "  ALBATROS-427",
]


def fake_run(plan, rep):
    for line in LOG:
        rep.log(line)
    for sid, status, detail in STEPS_DONE:
        rep.step(sid, status, detail)
    return {sid: status for sid, status, _ in STEPS_DONE}


installer.run_plan = fake_run


def use_readable_fonts(app) -> None:
    """Polices lisibles sous Xvfb (sur un vrai poste, Tk choisit celles du système)."""
    from tkinter import font as tkfont

    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont"):
        tkfont.nametofont(name).configure(family="DejaVu Sans", size=10)
    tkfont.nametofont("TkFixedFont").configure(family="DejaVu Sans Mono", size=9)
    app.font_title.configure(family="DejaVu Sans", size=16, weight="bold")
    app.font_icon.configure(family="DejaVu Sans", size=10, weight="bold")


def settle(widget, n: int = 20) -> None:
    for _ in range(n):
        widget.update()
        time.sleep(0.03)


def shot(widget, name: str) -> None:
    settle(widget)
    x, y = widget.winfo_rootx(), widget.winfo_rooty()
    img = ImageGrab.grab(bbox=(x, y, x + widget.winfo_width(), y + widget.winfo_height()))
    img.save(OUT / f"{name}.png", optimize=True)
    print("capture :", name)


def main() -> None:
    app = gui.App()
    use_readable_fonts(app)
    app.show()
    shot(app, "01-accueil")
    app.next()
    settle(app, 40)
    shot(app, "02-diagnostic")
    app.next()
    shot(app, "03-cle-vide")
    app.entry_key.insert(0, FAKE_KEY)
    app.test_key()
    settle(app, 40)
    shot(app, "04-cle-valide")
    app.next()
    shot(app, "05-assistants-modele")
    app.next()
    shot(app, "06-skills")
    app.next()
    shot(app, "07-connecteurs")
    app.next()
    shot(app, "08-recapitulatif")
    app.next()
    settle(app, 60)
    shot(app, "09-installation")
    app.next()
    shot(app, "10-termine")

    app.index = 0
    app.show()
    app.open_uninstall()
    settle(app, 20)
    win = [w for w in app.winfo_children() if w.winfo_class() == "Toplevel"][0]
    shot(win, "11-desinstaller")
    app.destroy()


if __name__ == "__main__":
    main()
