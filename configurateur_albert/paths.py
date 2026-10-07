"""Emplacements des fichiers, selon le système."""

from __future__ import annotations

import json
import os
import platform
import sys
from functools import lru_cache
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

PACKAGE_DIR = Path(__file__).resolve().parent
BUNDLED_SKILLS_DIR = PACKAGE_DIR / "skills"

# Fichier témoin posé dans chaque skill installé par l'application :
# on ne remplace ni ne supprime jamais un dossier qui ne le contient pas.
SKILL_MARKER = ".installe-par-configurateur-albert"


def home() -> Path:
    return Path.home()


def os_label() -> str:
    if IS_MAC:
        return f"macOS {platform.mac_ver()[0]} ({platform.machine()})"
    if IS_WINDOWS:
        return f"Windows {platform.release()} ({platform.machine()})"
    return f"Linux {platform.release()} ({platform.machine()})"


def data_dir() -> Path:
    """Dossier privé de l'application (état, Node.js « utilisateur »)."""
    if IS_WINDOWS:
        base = Path(os.environ.get("LOCALAPPDATA", home() / "AppData" / "Local"))
        return base / "configurateur-albert"
    return home() / ".local" / "share" / "configurateur-albert"


def state_file() -> Path:
    return data_dir() / "etat.json"


def key_file() -> Path:
    """Le « coffre » macOS/Linux : une ligne ALBERT_API_KEY=…"""
    return home() / ".albert.env"


def private_node_dir() -> Path:
    return data_dir() / "node"


def private_node_bin() -> Path:
    return private_node_dir() if IS_WINDOWS else private_node_dir() / "bin"


# --- OpenCode -----------------------------------------------------------------

def opencode_config_dir() -> Path:
    return home() / ".config" / "opencode"


def opencode_config_file() -> Path:
    d = opencode_config_dir()
    # OpenCode accepte aussi opencode.jsonc : on modifie celui qui existe.
    for name in ("opencode.json", "opencode.jsonc"):
        if (d / name).exists():
            return d / name
    return d / "opencode.json"


# --- Pi -----------------------------------------------------------------------

def pi_agent_dir() -> Path:
    custom = os.environ.get("PI_CODING_AGENT_DIR")
    return Path(custom).expanduser() if custom else home() / ".pi" / "agent"


def pi_models_file() -> Path:
    return pi_agent_dir() / "models.json"


def pi_settings_file() -> Path:
    return pi_agent_dir() / "settings.json"


def pi_mcp_file() -> Path:
    return pi_agent_dir() / "mcp.json"


# --- Skills -------------------------------------------------------------------

def skills_dir() -> Path:
    """Lu à la fois par OpenCode et par Pi."""
    return home() / ".agents" / "skills"


# --- Catalogue ----------------------------------------------------------------

@lru_cache(maxsize=1)
def catalog() -> dict:
    with open(PACKAGE_DIR / "catalog.json", encoding="utf-8") as f:
        return json.load(f)
