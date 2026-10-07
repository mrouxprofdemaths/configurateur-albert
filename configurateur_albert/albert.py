"""Dialogue avec Albert API : test de la clé, liste des modèles."""

from __future__ import annotations

import re
import urllib.error
from dataclasses import dataclass, field

from . import net
from .paths import catalog

KEY_RE = re.compile(r"^sk-[A-Za-z0-9._\-]{10,}$")


class AlbertError(Exception):
    """Erreur présentée telle quelle à l'utilisateur (message en français)."""


def normalize_key(raw: str) -> str:
    """Accepte une clé collée avec espaces, guillemets ou « ALBERT_API_KEY= » devant."""
    key = raw.strip().strip("\"'").strip()
    if "=" in key and key.split("=", 1)[0].strip().upper().endswith("ALBERT_API_KEY"):
        key = key.split("=", 1)[1].strip().strip("\"'").strip()
    if key.lower().startswith("bearer "):
        key = key[7:].strip()
    return key


def check_key_format(key: str) -> str | None:
    """Message d'erreur si le format est impossible, sinon None."""
    if not key:
        return "La clé est vide."
    if not KEY_RE.match(key):
        return ("Cette clé ne ressemble pas à une clé Albert (elle doit commencer par « sk- » "
                "et ne contenir ni espace ni accent). Recopiez-la depuis le Playground.")
    return None


def mask(key: str) -> str:
    """Seuls les 7 premiers caractères sont montrés (règle de sécurité)."""
    return f"{key[:7]}…" if key else ""


def _explain(e: Exception) -> str:
    if isinstance(e, net.HttpError):
        if e.status == 401 or "Invalid API key" in e.body:
            return "Albert refuse cette clé (401 « Invalid API key »). Vérifiez qu'elle est complète et non révoquée."
        if e.status == 403:
            return "Cette clé n'a pas accès à ce service (403)."
        if e.status == 404:
            return "Modèle introuvable (404) : il a peut-être été retiré."
        if e.status == 429:
            return "Quota atteint (429) : patientez une minute puis réessayez."
        if e.status in (502, 503, 504):
            return f"Albert est momentanément saturé ({e.status}). Réessayez dans quelques instants."
        return f"Albert a répondu une erreur {e.status}."
    if isinstance(e, urllib.error.URLError):
        return ("Impossible de joindre Albert API. Vérifiez la connexion Internet "
                "(ou le proxy/pare-feu de l'établissement).")
    if isinstance(e, TimeoutError):
        return "Albert API ne répond pas (délai dépassé)."
    return f"Erreur inattendue : {e}"


@dataclass
class Model:
    id: str
    type: str
    name: str
    input: list[str] = field(default_factory=lambda: ["text"])
    context: int = 131072
    output: int = 32768
    tools: bool = True          # appels d'outils (lecture de fichiers…) attendus
    opencode: bool = True       # à déclarer dans OpenCode
    note: str = ""
    known: bool = False         # présent dans le catalogue testé

    @property
    def label(self) -> str:
        suffix = self.note if self.known else "non testé avec les agents"
        return f"{self.name} — {suffix}" if suffix else self.name


def list_raw(key: str, base_url: str | None = None) -> list[dict]:
    base = (base_url or catalog()["albert"]["base_url"]).rstrip("/")
    try:
        data = net.get_json(f"{base}/models", headers={"Authorization": f"Bearer {key}"})
    except Exception as e:  # noqa: BLE001 — tout est traduit pour l'utilisateur
        raise AlbertError(_explain(e)) from None
    if not isinstance(data, dict) or data.get("object") != "list":
        raise AlbertError("Réponse inattendue d'Albert API (pas de liste de modèles).")
    return [m for m in data.get("data", []) if isinstance(m, dict) and m.get("id")]


def usable_models(raw: list[dict]) -> list[Model]:
    """Modèles de conversation disponibles, triés : testés d'abord, dans l'ordre du catalogue."""
    cat = catalog()
    known = cat["models"]
    excluded = cat["excluded_models"]
    chat_types = set(cat["albert"]["chat_types"])
    by_id = {m["id"]: m for m in raw}
    result: list[Model] = []

    for mid, meta in known.items():
        if mid in by_id:
            result.append(Model(
                id=mid, type=by_id[mid].get("type", ""), name=meta["name"],
                input=meta.get("input", ["text"]), context=meta.get("context", 131072),
                output=meta.get("output", 32768), tools=meta.get("tools", True),
                opencode=meta.get("opencode", True), note=meta.get("note", ""), known=True,
            ))

    for m in raw:
        mid, mtype = m["id"], m.get("type", "")
        if mid in known or mid in excluded or mtype not in chat_types:
            continue
        ctx = m.get("max_context_length") or 131072
        result.append(Model(
            id=mid, type=mtype, name=mid,
            input=["text", "image"] if "image" in mtype else ["text"],
            context=int(ctx), output=min(32768, max(1024, int(ctx) // 4)),
        ))
    return result


def default_model_id(models: list[Model]) -> str | None:
    wanted = catalog()["albert"]["default_model"]
    ids = [m.id for m in models]
    if wanted in ids:
        return wanted
    for m in models:
        if m.tools and m.opencode:
            return m.id
    return ids[0] if ids else None


def chat_test(key: str, model: str, base_url: str | None = None) -> str:
    """Petite requête de conversation ; renvoie le texte de la réponse."""
    base = (base_url or catalog()["albert"]["base_url"]).rstrip("/")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Réponds uniquement : OK"}],
        "max_tokens": 20,
    }
    try:
        data = net.post_json(f"{base}/chat/completions", payload,
                             headers={"Authorization": f"Bearer {key}"})
    except Exception as e:  # noqa: BLE001
        raise AlbertError(_explain(e)) from None
    try:
        return (data["choices"][0]["message"].get("content") or "").strip()
    except (KeyError, IndexError, TypeError):
        raise AlbertError("Réponse inattendue d'Albert API à la requête de test.") from None
