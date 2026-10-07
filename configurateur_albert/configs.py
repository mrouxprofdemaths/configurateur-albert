"""Écriture (fusion) et retrait des configurations OpenCode et Pi.

Règle : on ne touche qu'à ce qui nous appartient (provider « albert », MCP du
catalogue) ; tout le reste du fichier est conservé. Sauvegarde .bak horodatée
avant chaque modification."""

from __future__ import annotations

from pathlib import Path

from . import jsonfiles, paths, uvtool
from .albert import Model
from .paths import IS_WINDOWS

PROVIDER = "albert"
OPENCODE_SCHEMA = "https://opencode.ai/config.json"


def _albert_base() -> str:
    return paths.catalog()["albert"]["base_url"]


def mcp_entry(item: dict) -> dict:
    """Entrée du catalogue → description neutre {type, url | command/args}."""
    if item["type"] == "remote":
        return {"type": "remote", "url": item["url"]}
    cmd = uvtool.resolve(list(item["command"]))
    if IS_WINDOWS and cmd and cmd[0] in ("npx", "npm", "node"):
        # Sous Windows, npx est un script .cmd : il faut passer par cmd /c.
        cmd = ["cmd", "/c", *cmd]
    return {"type": "local", "command": cmd}


def albert_configured() -> list[str]:
    """Assistants dont la configuration déclare déjà le fournisseur Albert."""
    found = []
    try:
        if PROVIDER in (jsonfiles.load(paths.opencode_config_file()).get("provider") or {}):
            found.append("OpenCode")
    except (OSError, jsonfiles.ConfigError, ValueError):
        pass
    try:
        if PROVIDER in (jsonfiles.load(paths.pi_models_file()).get("providers") or {}):
            found.append("Pi")
    except (OSError, jsonfiles.ConfigError, ValueError):
        pass
    return found


# --- OpenCode -----------------------------------------------------------------

def opencode_provider(models: list[Model]) -> dict:
    entries = {}
    for m in models:
        if not m.opencode:
            continue
        entries[m.id] = {
            "name": m.name,
            "tool_call": m.tools,
            "limit": {"context": m.context, "output": m.output},
        }
    return {
        "npm": "@ai-sdk/openai-compatible",
        "name": "Albert API",
        "options": {"baseURL": _albert_base(), "apiKey": "{env:ALBERT_API_KEY}"},
        "models": entries,
    }


def write_opencode(models: list[Model], default_model: str | None, mcp_items: list[dict],
                   set_default: bool = True, path: Path | None = None) -> list[str]:
    path = path or paths.opencode_config_file()
    notes: list[str] = []
    data = jsonfiles.load(path)
    if jsonfiles.has_comments(path):
        notes.append(f"{path.name} contenait des commentaires : ils sont conservés dans la sauvegarde .bak.")
    data.setdefault("$schema", OPENCODE_SCHEMA)
    providers = data.setdefault("provider", {})
    providers[PROVIDER] = opencode_provider(models)
    oc_ids = [m.id for m in models if m.opencode]
    if default_model and default_model not in oc_ids:
        default_model = oc_ids[0] if oc_ids else None
    current = str(data.get("model", ""))
    if default_model and (set_default or not current or current.startswith(PROVIDER + "/")):
        data["model"] = f"{PROVIDER}/{default_model}"
    # small_model pointant vers un modèle Albert retiré : on le recale.
    small = str(data.get("small_model", ""))
    if small.startswith(PROVIDER + "/") and small.split("/", 1)[1] not in oc_ids and default_model:
        data["small_model"] = f"{PROVIDER}/{default_model}"
    if mcp_items:
        mcp = data.setdefault("mcp", {})
        for item in mcp_items:
            e = mcp_entry(item)
            if e["type"] == "remote":
                mcp[item["id"]] = {"type": "remote", "url": e["url"], "enabled": True}
            else:
                mcp[item["id"]] = {"type": "local", "command": e["command"], "enabled": True}
    bak = jsonfiles.save(path, data)
    notes.insert(0, f"OpenCode configuré : {path}" + (f" (ancienne version : {bak.name})" if bak else ""))
    return notes


def remove_opencode(mcp_ids: list[str], path: Path | None = None) -> list[str]:
    path = path or paths.opencode_config_file()
    if not path.exists():
        return []
    data = jsonfiles.load(path)
    data.get("provider", {}).pop(PROVIDER, None)
    if not data.get("provider"):
        data.pop("provider", None)
    for key in ("model", "small_model"):
        if str(data.get(key, "")).startswith(PROVIDER + "/"):
            data.pop(key)
    for mid in mcp_ids:
        data.get("mcp", {}).pop(mid, None)
    if "mcp" in data and not data["mcp"]:
        data.pop("mcp")
    bak = jsonfiles.save(path, data)
    return [f"Albert retiré de {path}" + (f" (sauvegarde : {bak.name})" if bak else "")]


# --- Pi -----------------------------------------------------------------------

def pi_provider(models: list[Model]) -> dict:
    entries = []
    for m in models:
        e: dict = {"id": m.id, "name": m.name, "input": m.input,
                   "contextWindow": m.context, "maxTokens": m.output}
        if m.tools:
            # Albert n'active les appels d'outils que si on les demande explicitement.
            e["samplingParams"] = {"tool_choice": "auto"}
        entries.append(e)
    return {
        "baseUrl": _albert_base(),
        "api": "openai-completions",
        "apiKey": "$ALBERT_API_KEY",
        "models": entries,
    }


def write_pi(models: list[Model], default_model: str | None, mcp_items: list[dict],
             set_default: bool = True, shell_path: str | None = None) -> list[str]:
    notes: list[str] = []

    models_file = paths.pi_models_file()
    data = jsonfiles.load(models_file)
    data.setdefault("providers", {})[PROVIDER] = pi_provider(models)
    bak = jsonfiles.save(models_file, data)
    notes.append(f"Pi configuré : {models_file}" + (f" (ancienne version : {bak.name})" if bak else ""))

    settings_file = paths.pi_settings_file()
    settings = jsonfiles.load(settings_file)
    changed = False
    if default_model and (set_default or not settings.get("defaultProvider")
                          or settings.get("defaultProvider") == PROVIDER):
        settings["defaultProvider"] = PROVIDER
        settings["defaultModel"] = default_model
        changed = True
    if shell_path and not settings.get("shellPath"):
        settings["shellPath"] = shell_path
        changed = True
    if changed:
        jsonfiles.save(settings_file, settings)
        notes.append(f"Modèle par défaut de Pi : {PROVIDER}/{default_model}")

    if mcp_items:
        mcp_file = paths.pi_mcp_file()
        mcp = jsonfiles.load(mcp_file)
        servers = mcp.setdefault("mcpServers", {})
        for item in mcp_items:
            e = mcp_entry(item)
            if e["type"] == "remote":
                servers[item["id"]] = {"url": e["url"], "description": item.get("description", "")}
            else:
                servers[item["id"]] = {"command": e["command"][0], "args": e["command"][1:],
                                       "description": item.get("description", "")}
        jsonfiles.save(mcp_file, mcp)
        notes.append(f"MCP de Pi : {mcp_file}")
    return notes


def remove_pi(mcp_ids: list[str], shell_path_set: bool = False) -> list[str]:
    notes: list[str] = []
    models_file = paths.pi_models_file()
    if models_file.exists():
        data = jsonfiles.load(models_file)
        if data.get("providers", {}).pop(PROVIDER, None) is not None:
            jsonfiles.save(models_file, data)
            notes.append(f"Albert retiré de {models_file}")
    settings_file = paths.pi_settings_file()
    if settings_file.exists():
        s = jsonfiles.load(settings_file)
        if s.get("defaultProvider") == PROVIDER:
            s.pop("defaultProvider", None)
            s.pop("defaultModel", None)
        if shell_path_set:
            s.pop("shellPath", None)
        jsonfiles.save(settings_file, s)
    mcp_file = paths.pi_mcp_file()
    if mcp_file.exists() and mcp_ids:
        m = jsonfiles.load(mcp_file)
        for mid in mcp_ids:
            m.get("mcpServers", {}).pop(mid, None)
        jsonfiles.save(mcp_file, m)
    return notes
