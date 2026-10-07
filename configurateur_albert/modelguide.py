"""Guide « Quel modèle choisir ? » : à quoi sert chaque modèle, quand le choisir, exemple.

Les descriptions viennent du catalogue (vérifiées à la date `models_checked_on`) ; les
avertissements liés aux dates (phase d'essai terminée, retrait proche) sont calculés avec
la date du jour, pour rester justes après la publication de l'application."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from .albert import Model
from .paths import catalog

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]
RETRAIT_PROCHE_JOURS = 90


def date_fr(d: dt.date) -> str:
    return f"{'1er' if d.day == 1 else d.day} {MOIS[d.month - 1]} {d.year}"


def _date(value: str | None) -> dt.date | None:
    return dt.date.fromisoformat(value) if value else None


@dataclass
class Fiche:
    id: str
    name: str
    role: str
    choose_if: str
    example: str
    limits: str
    status: str          # "" ou avertissement daté
    level: str           # "ok", "attention"
    known: bool


def status(meta: dict, today: dt.date) -> tuple[str, str]:
    """Avertissement daté : phase d'essai, fin d'essai, retrait proche."""
    start, end = _date(meta.get("experimental_from")), _date(meta.get("experimental_until"))
    retirement = _date(meta.get("retirement"))
    if retirement and today >= retirement:
        return "attention", f"Retiré par Albert depuis le {date_fr(retirement)}."
    if retirement and (retirement - today).days <= RETRAIT_PROCHE_JOURS:
        return "attention", f"Sera retiré le {date_fr(retirement)} : évitez de vous y habituer."
    if end and today > end:
        return "attention", (f"Sa phase d'essai s'est terminée le {date_fr(end)} : Albert peut le "
                             "garder, le remplacer ou le retirer. S'il disparaît, l'application ne le proposera plus.")
    if end and (not start or today >= start):
        return "attention", f"En phase d'essai jusqu'au {date_fr(end)} : il peut changer ou disparaître ensuite."
    return "ok", ""


def fiche(model: Model, today: dt.date | None = None) -> Fiche:
    today = today or dt.date.today()
    meta = catalog()["models"].get(model.id)
    if not meta:
        return Fiche(model.id, model.name,
                     role="Nouveau modèle proposé par Albert, pas encore décrit dans ce guide.",
                     choose_if="Seulement pour l'essayer : il n'a pas été testé avec les assistants "
                               "(lecture de fichiers, outils).",
                     example="", limits=f"Mémoire de travail : {model.context:,} jetons.".replace(",", " "),
                     status="", level="attention", known=False)
    level, text = status(meta, today)
    return Fiche(model.id, meta["name"], meta.get("role", ""), meta.get("choose_if", ""),
                 meta.get("example", ""), meta.get("limits", ""), text, level, True)


def excluded_notes(today: dt.date | None = None) -> list[str]:
    """Modèles volontairement non proposés, avec la raison (datée)."""
    today = today or dt.date.today()
    notes = []
    for mid, info in catalog()["excluded_models"].items():
        r = _date(info.get("retirement"))
        when = (f"retiré depuis le {date_fr(r)}" if r and today >= r
                else f"retrait prévu le {date_fr(r)}" if r else "")
        repl = f" ; remplaçant : {info['replacement']}" if info.get("replacement") else ""
        notes.append(f"{mid} : non proposé ({info['reason']}{', ' + when if when else ''}{repl}).")
    return notes


HOW_TO_CHOOSE = [
    "Commencez par le modèle recommandé (gemma-4-31b-it) : il convient à presque tout.",
    "Changez seulement si vous avez une raison : tâche très difficile (gpt-oss-120b), "
    "programmation (deepseek), tâche simple ou quota atteint (ministral), scan à recopier (lightonocr).",
    "Un plus gros modèle n'est pas toujours mieux : il est plus lent et ses quotas sont plus bas. "
    "Un assistant envoie souvent plusieurs requêtes par demande.",
    "Le choix n'est pas définitif : tous les modèles sont déclarés, vous en changez à tout moment "
    "(/models dans OpenCode, /model dans Pi et Hermes).",
    "Quel que soit le modèle, aucune donnée nominative d'élève : anonymisez d'abord.",
]


def checked_on() -> str:
    return date_fr(dt.date.fromisoformat(catalog()["albert"]["models_checked_on"]))


def text_guide(models: list[Model], today: dt.date | None = None) -> str:
    """Version texte (mode terminal)."""
    lines = ["Quel modèle choisir ?", ""]
    lines += [f"  • {h}" for h in HOW_TO_CHOOSE]
    for m in models:
        f = fiche(m, today)
        lines += ["", f"{f.id} — {f.name}", f"  À quoi il sert : {f.role}", f"  Choisissez-le si : {f.choose_if}"]
        if f.example:
            lines.append(f"  Exemple : {f.example}")
        if f.limits:
            lines.append(f"  Limites : {f.limits}")
        if f.status:
            lines.append(f"  ⚠ {f.status}")
    excl = excluded_notes(today)
    if excl:
        lines += ["", "Non proposés :"] + [f"  • {n}" for n in excl]
    lines += ["", f"Descriptions vérifiées le {checked_on()} ; référence : {catalog()['albert']['models_doc_url']}"]
    return "\n".join(lines)
