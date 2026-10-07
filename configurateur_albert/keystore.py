"""Le « coffre » de la clé Albert.

- macOS/Linux : ~/.albert.env (chmod 600) chargé par un bloc balisé dans ~/.zshrc / ~/.bashrc ;
- Windows : variable de compte ALBERT_API_KEY dans le registre.

La clé n'est écrite nulle part ailleurs : les configurations OpenCode et Pi
y font référence par {env:ALBERT_API_KEY} et $ALBERT_API_KEY."""

from __future__ import annotations

import os
import re
from pathlib import Path

from . import jsonfiles, paths
from .paths import IS_MAC, IS_WINDOWS

ENV_VAR = "ALBERT_API_KEY"
BEGIN = "# >>> configurateur-albert >>>"
END = "# <<< configurateur-albert <<<"
SOURCE_LINE = 'if [ -f "$HOME/.albert.env" ]; then set -a; . "$HOME/.albert.env"; set +a; fi'


# --- Lecture ------------------------------------------------------------------

def read_key_file() -> str | None:
    f = paths.key_file()
    if not f.exists():
        return None
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[7:].strip()
        if line.startswith(f"{ENV_VAR}="):
            return line.split("=", 1)[1].strip().strip("\"'") or None
    return None


def existing_key() -> str | None:
    """Clé déjà rangée (coffre, registre ou variable du processus)."""
    if IS_WINDOWS:
        from . import winenv

        value = winenv.get(ENV_VAR)
        if value:
            return value
    else:
        value = read_key_file()
        if value:
            return value
    return os.environ.get(ENV_VAR) or None


# --- Écriture -----------------------------------------------------------------

def store_key(key: str) -> list[str]:
    """Range la clé ; renvoie la liste des actions effectuées (pour le journal)."""
    os.environ[ENV_VAR] = key  # pour les commandes lancées par l'application
    if IS_WINDOWS:
        from . import winenv

        winenv.set_value(ENV_VAR, key)
        return ["Clé enregistrée comme variable de votre compte Windows (ALBERT_API_KEY)."]
    f = paths.key_file()
    if f.exists() and read_key_file() == key:
        os.chmod(f, 0o600)
        return [f"Clé déjà présente dans {f}."]
    jsonfiles.write_text_atomic(f, f"{ENV_VAR}={key}\n", private=True)
    return [f"Clé rangée dans {f} (lisible par vous seul)."]


def delete_key() -> bool:
    os.environ.pop(ENV_VAR, None)
    if IS_WINDOWS:
        from . import winenv

        return winenv.delete(ENV_VAR)
    f = paths.key_file()
    if f.exists():
        f.unlink()
        return True
    return False


# --- Fichiers de démarrage du shell (macOS/Linux) ------------------------------

def rc_files() -> list[Path]:
    h = paths.home()
    shell = os.environ.get("SHELL", "")
    files: list[Path] = []
    if IS_MAC or "zsh" in shell or (h / ".zshrc").exists():
        files.append(h / ".zshrc")
    if not IS_MAC or "bash" in shell:
        files.append(h / ".bashrc")
    if IS_MAC and "bash" in shell:
        files.append(h / ".bash_profile")
    return files


_BLOCK_RE = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", re.DOTALL)


def _block(path_dirs: list[str], include_source: bool) -> str:
    lines = [BEGIN, "# Ajouté par Configurateur Albert (retiré par sa désinstallation)."]
    if include_source:
        lines.append(SOURCE_LINE)
    for d in path_dirs:
        lines.append(f'export PATH="{d}:$PATH"')
    lines.append(END)
    return "\n".join(lines) + "\n"


def _manual_source_present(text_without_block: str) -> bool:
    """L'utilisateur a peut-être déjà suivi le diaporama (ligne « source ~/.albert.env »)."""
    return any(".albert.env" in line and not line.lstrip().startswith("#")
               for line in text_without_block.splitlines())


def install_rc_block(path_dirs: list[str] | None = None) -> list[str]:
    """Pose (ou met à jour) le bloc balisé, sans jamais le dupliquer."""
    if IS_WINDOWS:
        return []
    actions: list[str] = []
    for rc in rc_files():
        text = rc.read_text(encoding="utf-8") if rc.exists() else ""
        without = _BLOCK_RE.sub("", text)
        block = _block(path_dirs or [], include_source=not _manual_source_present(without))
        if block.count("\n") <= 3:  # rien d'utile à ajouter (source déjà présente, pas de PATH)
            new = without
        elif BEGIN in text:
            new = _BLOCK_RE.sub(block, text, count=1)
        else:
            new = text + ("" if not text or text.endswith("\n") else "\n") + "\n" + block
        if new != text:
            jsonfiles.backup(rc)
            jsonfiles.write_text_atomic(rc, new)
            actions.append(f"Chargement automatique de la clé ajouté à {rc}.")
        else:
            actions.append(f"{rc} déjà à jour.")
    return actions


def remove_rc_block() -> list[str]:
    actions: list[str] = []
    for rc in rc_files():
        if not rc.exists():
            continue
        text = rc.read_text(encoding="utf-8")
        if BEGIN not in text:
            continue
        jsonfiles.backup(rc)
        new = _BLOCK_RE.sub("", text).rstrip("\n") + "\n"
        jsonfiles.write_text_atomic(rc, new)
        actions.append(f"Bloc Configurateur Albert retiré de {rc}.")
    return actions
