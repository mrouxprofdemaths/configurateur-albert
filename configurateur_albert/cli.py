"""Mode texte (sans interface graphique) : mêmes étapes, questions dans le terminal."""

from __future__ import annotations

import getpass
import webbrowser

from . import APP_NAME, __version__, albert, installer, paths, texts
from .installer import Plan


class ConsoleReporter:
    def log(self, message: str) -> None:
        print(message, flush=True)

    def step(self, step_id: str, status: str, detail: str = "") -> None:
        label = dict(installer.STEPS).get(step_id, step_id)
        print(f"{texts.STATUS_ICONS.get(status, '·')} {label}" + (f" — {detail}" if detail else ""), flush=True)


def ask_yes(question: str, default: bool = True) -> bool:
    suffix = " [O/n] " if default else " [o/N] "
    while True:
        a = input(question + suffix).strip().lower()
        if not a:
            return default
        if a in ("o", "oui", "y", "yes"):
            return True
        if a in ("n", "non", "no"):
            return False


def choose_key(diag: installer.Diagnostic) -> tuple[str, list[albert.Model]]:
    if diag.key and ask_yes(f"Une clé est déjà enregistrée ({albert.mask(diag.key)}). L'utiliser ?"):
        candidates = [diag.key]
    else:
        candidates = []
    print("\n" + texts.KEY_HELP + "\n")
    if not candidates and ask_yes("Ouvrir la page des clés dans le navigateur ?"):
        webbrowser.open(paths.catalog()["albert"]["keys_url"])
    while True:
        key = candidates.pop() if candidates else albert.normalize_key(
            getpass.getpass("Collez votre clé (elle ne s'affiche pas) : "))
        err = albert.check_key_format(key)
        if err:
            print("❌ " + err)
            continue
        try:
            models = albert.usable_models(albert.list_raw(key))
        except albert.AlbertError as e:
            print("❌ " + str(e))
            continue
        if not models:
            print("❌ Aucun modèle de conversation disponible avec cette clé.")
            continue
        print(f"✅ Clé valide ({albert.mask(key)}), {len(models)} modèle(s) disponible(s).")
        return key, models


def choose_from(title: str, items: list[dict]) -> list[str]:
    print(f"\n{title}")
    chosen = []
    for item in items:
        if ask_yes(f"  • {item['name']} — {item['description']}", item.get("default", False)):
            chosen.append(item["id"])
    return chosen


def main_install() -> int:
    print(f"{APP_NAME} {__version__}\n\n{texts.WELCOME}\n")
    print("Diagnostic du poste…")
    d = installer.diagnose()
    print(f"  Système : {d.os}\n  Node.js : {d.node or 'absent'}\n"
          f"  OpenCode : {d.opencode or 'absent'}\n  Pi : {d.pi or 'absent'}\n  Hermes : {d.hermes or 'absent'}")
    key, models = choose_key(d)

    default = albert.default_model_id(models)
    print("\nModèles disponibles :")
    for i, m in enumerate(models, 1):
        print(f"  {i}. {m.id} — {m.label}" + ("  (par défaut)" if m.id == default else ""))
    answer = input(f"Numéro du modèle par défaut [{default}] : ").strip()
    if answer.isdigit() and 1 <= int(answer) <= len(models):
        default = models[int(answer) - 1].id

    want_oc = ask_yes("\nInstaller et configurer OpenCode ?")
    want_pi = ask_yes("Installer et configurer Pi ?")
    want_hermes = ask_yes("Installer et configurer Hermes (installation longue : 5 à 15 min) ?", False)
    if not (want_oc or want_pi or want_hermes):
        print("Rien à faire.")
        return 0
    cat = paths.catalog()
    chosen_skills = choose_from("Skills (savoir-faire) :", cat["skills"])
    print("\n" + texts.MCP_WARNING)
    chosen_mcp = choose_from("Connecteurs MCP :", cat["mcp"])
    vscode = want_oc and d.vscode and ask_yes("Installer l'extension OpenCode pour VS Code ?", False)

    plan = Plan(key=key, models=models, default_model=default or models[0].id,
                opencode=want_oc, pi=want_pi, hermes=want_hermes, skills=chosen_skills, mcp=chosen_mcp, vscode=vscode)
    print()
    results = installer.run_plan(plan, ConsoleReporter())
    print("\n" + texts.USAGE)
    if any(s in ("erreur", "attention") for s in results.values()):
        print("En cas de souci :")
        for symptom, fix in texts.TROUBLESHOOTING:
            print(f"  • {symptom} : {fix}")
        return 1
    return 0


def main_uninstall() -> int:
    if not ask_yes("Retirer les réglages Albert, les skills et le chargement de la clé ?", False):
        return 0
    remove_key = ask_yes("Supprimer aussi la clé Albert de ce poste ?", True)
    remove_tools = ask_yes("Désinstaller aussi OpenCode, Pi et Hermes ?", False)
    installer.uninstall(ConsoleReporter(), remove_key=remove_key, remove_tools=remove_tools)
    return 0


def run(uninstall: bool = False) -> int:
    try:
        return main_uninstall() if uninstall else main_install()
    except (KeyboardInterrupt, EOFError):
        print("\nInterrompu.")
        return 130

