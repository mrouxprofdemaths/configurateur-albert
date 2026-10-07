"""Mémoire de ce que l'application a posé (pour réparer et désinstaller proprement)."""

from __future__ import annotations

import json

from . import jsonfiles, paths


def load() -> dict:
    f = paths.state_file()
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save(data: dict) -> None:
    jsonfiles.write_text_atomic(paths.state_file(),
                                json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def update(**changes) -> dict:
    """Fusionne : listes cumulées sans doublon, autres valeurs remplacées."""
    data = load()
    for k, v in changes.items():
        if isinstance(v, list):
            merged = list(data.get(k, []))
            merged += [x for x in v if x not in merged]
            data[k] = merged
        else:
            data[k] = v
    save(data)
    return data
