"""Hermes Agent (Nous Research) : installation, configuration et retrait.

La configuration de Hermes est un fichier YAML (~/.hermes/config.yaml, sous Windows
%LOCALAPPDATA%\\hermes\\config.yaml) que l'utilisateur a pu commenter : on ne le réécrit
jamais nous-mêmes. On passe par « hermes config set / unset », qui fusionne proprement et
vérifie les types. La clé n'apparaît nulle part : le fournisseur lit ALBERT_API_KEY
(key_env)."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import net, paths, system
from .albert import Model
from .paths import IS_MAC, IS_WINDOWS
from .system import Log

PROVIDER = "albert"
INSTALLER = "https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.{ext}"


class HermesError(Exception):
    pass


def find() -> str | None:
    return system.which("hermes")


def version() -> str | None:
    return system.tool_version("hermes")


def mac_developer_tools_ready() -> bool:
    """Sous macOS, Hermes a besoin de git, fourni par les « outils de ligne de commande »
    d'Apple. Sans eux, /usr/bin/git n'est qu'un raccourci qui ouvre une fenêtre d'installation."""
    if not IS_MAC:
        return True
    try:
        return subprocess.run(["xcode-select", "-p"], capture_output=True, timeout=20).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def request_mac_developer_tools() -> None:
    """Ouvre la fenêtre d'Apple « Installer les outils de ligne de commande »."""
    try:
        subprocess.run(["xcode-select", "--install"], capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        pass


def install(log: Log) -> bool:
    """Installeur officiel, en mode non interactif (pas d'assistant « hermes setup »)."""
    ext = "ps1" if IS_WINDOWS else "sh"
    log("Téléchargement de l'installeur officiel de Hermes…")
    script = net.download(INSTALLER.format(ext=ext))
    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / f"install.{ext}"
        f.write_bytes(script)
        if IS_WINDOWS:
            cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(f), "-NonInteractive"]
        else:
            cmd = ["bash", str(f), "--non-interactive"]
        log("Installation de Hermes (5 à 15 minutes : Python, Node.js et outils)…")
        r = system.run(cmd, log, env=system.child_env(), timeout=3600)
    system.refresh_path()
    return r.ok and find() is not None


# --- Configuration -------------------------------------------------------------------

def provider_entry(models: list[Model], default_model: str) -> dict:
    entries = {m.id: {"context_length": m.context} for m in models if m.tools}
    if default_model not in entries and entries:
        default_model = next(iter(entries))
    return {
        "name": "Albert API",
        "api": paths.catalog()["albert"]["base_url"],
        "key_env": "ALBERT_API_KEY",
        "transport": "chat_completions",
        "default_model": default_model,
        "discover_models": False,
        "models": entries,
    }


def model_overrides(models: list[Model]) -> dict:
    """Albert refuse le champ reasoning_effort que Hermes ajoute par défaut ;
    on déclare aussi la vision des modèles qui lisent les images."""
    return {m.id: {"context_window": m.context, "supports_tools": m.tools,
                   "supports_vision": "image" in m.input, "supports_reasoning": False}
            for m in models}


def _OUR_MODEL_IDS() -> list[str]:
    """Modèles qu'on a pu déclarer : catalogue + ceux mémorisés à l'installation."""
    from . import state

    return sorted(set(paths.catalog()["models"]) | set(state.load().get("hermes_models", [])))


def mcp_value(entry: dict, description: str = "") -> dict:
    if entry["type"] == "remote":
        return {"url": entry["url"], "enabled": True}
    return {"command": entry["command"][0], "args": entry["command"][1:], "enabled": True}


def _set(key: str, value, log: Log) -> None:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    r = system.run(["hermes", "config", "set", key, text, "--force"], log, timeout=120)
    if not r.ok:
        raise HermesError(f"« hermes config set {key} » a échoué (voir le journal)")


def _get(key: str):
    """Valeur simple, ou liste (« hermes config get » affiche du YAML : « [] » ou « - élément »)."""
    r = system.quiet(["hermes", "config", "get", key], timeout=60)
    if not r.ok:
        return None
    out = r.output.strip()
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        pass
    lines = [ln for ln in out.splitlines() if ln.strip()]
    if lines and all(ln.lstrip().startswith("- ") for ln in lines):
        return [ln.lstrip()[2:].strip().strip("\"'") for ln in lines]
    return out or None


def config_file() -> Path | None:
    r = system.quiet(["hermes", "config", "path"], timeout=60)
    lines = [ln.strip() for ln in r.output.splitlines() if ln.strip()]
    return Path(lines[-1]) if r.ok and lines else None


def backup_config(log: Log) -> None:
    from . import jsonfiles

    f = config_file()
    if f and f.exists():
        bak = jsonfiles.backup(f)
        if bak:
            log(f"Sauvegarde de la configuration de Hermes : {bak.name}")


def configure(models: list[Model], default_model: str, mcp_entries: list[tuple[str, dict]],
              skills_dir: Path, set_default: bool, log: Log) -> list[str]:
    backup_config(log)
    entry = provider_entry(models, default_model)
    _set(f"providers.{PROVIDER}", entry, log)
    # Hermes cherche ces réglages sous le nom exact du fournisseur ; selon les chemins de code,
    # un fournisseur nommé apparaît comme « albert », « custom:albert » ou « custom ».
    overrides = model_overrides(models)
    for key in (PROVIDER, f"custom:{PROVIDER}"):        # sections propres à Albert
        _set(f"model_overrides.{key}", overrides, log)
    for mid, value in overrides.items():               # section partagée : modèle par modèle
        _set(f"model_overrides.custom.{mid}", value, log)
    current = _get("model.provider")
    if set_default or not current or current in ("auto", PROVIDER):
        _set("model.provider", PROVIDER, log)
        _set("model.default", entry["default_model"], log)
    for name, value in mcp_entries:
        _set(f"mcp_servers.{name}", value, log)
    dirs = _get("skills.external_dirs")
    dirs = dirs if isinstance(dirs, list) else []
    skills_path = str(skills_dir)
    if skills_path not in dirs and "~/.agents/skills" not in dirs:
        _set("skills.external_dirs", [*dirs, skills_path], log)
    return [f"Hermes configuré (fournisseur « {PROVIDER} », modèle {entry['default_model']})"]


def remove(mcp_ids: list[str], skills_dir: Path, log: Log) -> None:
    if not find():
        return
    backup_config(log)
    for key in (f"providers.{PROVIDER}", f"model_overrides.{PROVIDER}", f"model_overrides.custom:{PROVIDER}",
                *(f"mcp_servers.{m}" for m in mcp_ids)):
        system.run(["hermes", "config", "unset", key], log, timeout=60)
    # Dans la section partagée « custom », on ne retire que nos modèles.
    for mid in _OUR_MODEL_IDS():
        if _get(f"model_overrides.custom.{mid}") is not None:
            system.run(["hermes", "config", "unset", f"model_overrides.custom.{mid}"], log, timeout=60)
    if _get("model.provider") == PROVIDER:
        system.run(["hermes", "config", "unset", "model.provider"], log, timeout=60)
        system.run(["hermes", "config", "unset", "model.default"], log, timeout=60)
    dirs = _get("skills.external_dirs")
    if isinstance(dirs, list) and str(skills_dir) in dirs:
        rest = [d for d in dirs if d != str(skills_dir)]
        if rest:
            _set("skills.external_dirs", rest, log)
        else:
            system.run(["hermes", "config", "unset", "skills.external_dirs"], log, timeout=60)


def uninstall_program(log: Log) -> None:
    """Hermes fournit sa propre désinstallation."""
    if shutil.which("hermes"):
        system.run(["hermes", "uninstall", "--yes"], log, timeout=600)


def oneshot_command(prompt: str, model: str) -> list[str]:
    """Requête ponctuelle (répond puis quitte) avec le fournisseur Albert."""
    return ["hermes", "chat", "--oneshot", "--provider", PROVIDER, "-m", model, "-q", prompt]
