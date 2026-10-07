"""uv / uvx : nécessaires aux connecteurs MCP écrits en Python (ex. MarkItDown).

Lancé par la commande du terminal, le Configurateur a déjà installé uv dans
<data_dir>/uv (hors du PATH). Sinon (exécutable de secours), on l'installe au même
endroit avec l'installeur officiel, sans droits administrateur ni modification du PATH.
Les configurations d'OpenCode et de Pi reçoivent le chemin complet de uvx."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from . import net, paths, system
from .paths import IS_WINDOWS
from .system import Log

INSTALLER = "https://github.com/astral-sh/uv/releases/latest/download/uv-installer.{ext}"


def uv_dir() -> Path:
    return paths.data_dir() / "uv"


def find_uvx() -> str | None:
    local = uv_dir() / ("uvx.exe" if IS_WINDOWS else "uvx")
    if local.exists():
        return str(local)
    return shutil.which("uvx")


def install(log: Log) -> str | None:
    """Installe uv dans le dossier privé ; renvoie le chemin de uvx (ou None)."""
    ext = "ps1" if IS_WINDOWS else "sh"
    log("Installation de l'outil uv (nécessaire à certains connecteurs)…")
    script = net.download(INSTALLER.format(ext=ext))
    uv_dir().mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / f"uv-installer.{ext}"
        f.write_bytes(script)
        env = system.child_env({"UV_UNMANAGED_INSTALL": str(uv_dir())})
        if IS_WINDOWS:
            cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(f)]
        else:
            cmd = ["sh", str(f)]
        system.run(cmd, log, env=env, timeout=600)
    return find_uvx()


def ensure(log: Log) -> str | None:
    return find_uvx() or install(log)


def resolve(cmd: list[str]) -> list[str]:
    """Remplace « uvx » par son chemin complet (les assistants ne le trouveraient pas)."""
    if cmd and cmd[0] == "uvx":
        uvx = find_uvx()
        if uvx:
            return [uvx.replace(os.sep, "/") if IS_WINDOWS else uvx, *cmd[1:]]
    return cmd
