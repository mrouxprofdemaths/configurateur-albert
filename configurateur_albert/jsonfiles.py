"""Lecture tolérante (JSONC) et écriture sûre (sauvegarde + écriture atomique)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path


class ConfigError(Exception):
    """Fichier de configuration illisible : on refuse de l'écraser."""


def strip_jsonc(text: str) -> str:
    """Retire commentaires // et /* */ et virgules finales, sans toucher aux chaînes."""
    out: list[str] = []
    i, n = 0, len(text)
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
        elif text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end == -1 else end + 2
        elif c == ",":
            # Virgule finale : suivie (aux blancs près) de } ou ]
            j = i + 1
            while j < n and text[j] in " \t\r\n":
                j += 1
            if j < n and text[j] in "}]":
                i += 1
            else:
                out.append(c)
                i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def load(path: Path) -> dict:
    """Charge un JSON/JSONC. Fichier absent ou vide → {}."""
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8-sig")
    if not raw.strip():
        return {}
    try:
        data = json.loads(strip_jsonc(raw))
    except json.JSONDecodeError as e:
        raise ConfigError(
            f"Le fichier {path} n'est pas un JSON valide (ligne {e.lineno}). "
            "Il n'a pas été modifié."
        ) from e
    if not isinstance(data, dict):
        raise ConfigError(f"Le fichier {path} ne contient pas un objet JSON. Il n'a pas été modifié.")
    return data


def has_comments(path: Path) -> bool:
    if not path.exists():
        return False
    raw = path.read_text(encoding="utf-8-sig")
    try:
        json.loads(raw)
        return False
    except json.JSONDecodeError:
        return True


def backup(path: Path) -> Path | None:
    """Copie horodatée : opencode.json → opencode.json.bak-20261007-142501."""
    if not path.exists():
        return None
    stamp = time.strftime("%Y%m%d-%H%M%S")
    dest = path.with_name(f"{path.name}.bak-{stamp}")
    k = 1
    while dest.exists():
        dest = path.with_name(f"{path.name}.bak-{stamp}-{k}")
        k += 1
    dest.write_bytes(path.read_bytes())
    try:
        os.chmod(dest, path.stat().st_mode & 0o777)
    except OSError:
        pass
    return dest


def write_text_atomic(path: Path, content: str, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    if private:
        # Créé directement en 600 : la clé n'est jamais lisible par d'autres, même un instant.
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
    else:
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        if path.exists():
            try:
                os.chmod(tmp, path.stat().st_mode & 0o777)
            except OSError:
                pass
    os.replace(tmp, path)
    if private:
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


def save(path: Path, data: dict) -> Path | None:
    """Écrit si le contenu change ; renvoie le chemin de la sauvegarde éventuelle."""
    content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if path.exists() and path.read_text(encoding="utf-8-sig") == content:
        return None
    bak = backup(path)
    write_text_atomic(path, content)
    return bak
