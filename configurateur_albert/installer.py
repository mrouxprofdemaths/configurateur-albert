"""Enchaînement des étapes d'installation, de vérification et de désinstallation.

Indépendant de l'interface : l'interface graphique et le mode texte appellent
run_plan() / uninstall() avec un « Reporter » qui affiche la progression."""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from . import albert, configs, keystore, node, paths, skills, state, system
from .albert import Model
from .jsonfiles import ConfigError
from .paths import IS_WINDOWS

OPENCODE_PKG = "opencode-ai@1"                       # v1 : format de configuration testé
PI_PKG = "@earendil-works/pi-coding-agent@1"
PI_OLD_PKG = "@mariozechner/pi-coding-agent"        # ancien nom (avant 1.0)
VSCODE_EXTENSION = "sst-dev.opencode"
TEST_CODE = "ALBATROS-427"

OK, ERROR, WARN, SKIP, RUNNING = "ok", "erreur", "attention", "ignoré", "en cours"


class Reporter(Protocol):
    def log(self, message: str) -> None: ...
    def step(self, step_id: str, status: str, detail: str = "") -> None: ...


STEPS = [
    ("cle", "Ranger la clé Albert"),
    ("node", "Node.js"),
    ("windows", "Réglages Windows"),
    ("opencode", "Installer OpenCode"),
    ("pi", "Installer Pi"),
    ("config", "Brancher Albert (configurations)"),
    ("skills", "Installer les skills"),
    ("vscode", "Extension VS Code"),
    ("test", "Vérifications"),
]


@dataclass
class Plan:
    key: str
    models: list[Model]
    default_model: str
    opencode: bool = True
    pi: bool = True
    skills: list[str] = field(default_factory=list)
    mcp: list[str] = field(default_factory=list)
    vscode: bool = False
    run_tests: bool = True
    set_default: bool = True


@dataclass
class Diagnostic:
    os: str
    node: str | None
    node_ok_for_pi: bool
    npm_writable: bool
    git_bash: str | None
    opencode: str | None
    pi: str | None
    vscode: bool
    key: str | None

    @property
    def opencode_major(self) -> int | None:
        v = system.parse_version(self.opencode or "")
        return v[0] if v else None


def diagnose() -> Diagnostic:
    system.refresh_path()
    nv = system.node_version()
    gb = system.git_bash()
    return Diagnostic(
        os=paths.os_label(),
        node=".".join(map(str, nv)) if nv else None,
        node_ok_for_pi=system.node_ok_for_pi(),
        npm_writable=system.npm_global_writable(),
        git_bash=str(gb) if gb else None,
        opencode=system.tool_version("opencode"),
        pi=system.tool_version("pi"),
        vscode=system.which("code") is not None,
        key=keystore.existing_key(),
    )


def catalog_items(kind: str, ids: list[str]) -> list[dict]:
    return [i for i in paths.catalog()[kind] if i["id"] in ids]


# --- Étapes -------------------------------------------------------------------

class _Run:
    def __init__(self, plan: Plan, rep: Reporter):
        self.plan, self.rep = plan, rep
        self.results: dict[str, str] = {}
        self.npm_ready = False

    def log(self, msg: str) -> None:
        self.rep.log(system.redact(msg))

    def set(self, step: str, status: str, detail: str = "") -> None:
        self.results[step] = status
        self.rep.step(step, status, system.redact(detail))

    def npm(self, args: list[str]):
        return system.run(["npm", *args], self.log, env=system.child_env())

    # 1. Clé
    def key(self) -> None:
        self.set("cle", RUNNING)
        try:
            for line in keystore.store_key(self.plan.key):
                self.log(line)
            extra = [str(paths.private_node_bin())] if node.private_node_installed() else []
            for line in keystore.install_rc_block(extra):
                self.log(line)
            state.update(key_stored=True, rc_block=not IS_WINDOWS, windows_env=IS_WINDOWS)
            self.set("cle", OK, f"Clé {albert.mask(self.plan.key)} rangée")
        except (OSError, ConfigError) as e:
            self.set("cle", ERROR, str(e))

    # 2. Node.js
    def nodejs(self) -> None:
        need_opencode = self.plan.opencode and not system.which("opencode")
        need_pi = self.plan.pi and (not system.which("pi") or self._pi_too_old())
        need_v1 = self.plan.opencode and self._opencode_major() not in (None, 1)
        if not (need_opencode or need_pi or need_v1):
            self.npm_ready = system.which("npm") is not None
            self.set("node", SKIP, "Rien à installer")
            return
        self.set("node", RUNNING)
        if system.which("npm") and system.node_ok_for_pi() and system.npm_global_writable():
            self.npm_ready = True
            self.set("node", OK, f"Node.js {'.'.join(map(str, system.node_version() or ()))} déjà présent")
            return
        if system.which("node"):
            self.log("Node.js est présent mais trop ancien ou installé pour tout l'ordinateur "
                     "(droits administrateur nécessaires) : installation d'une copie personnelle.")
        try:
            node.install_private_node(self.log)
        except Exception as e:  # noqa: BLE001
            self.set("node", ERROR, f"Échec de l'installation de Node.js : {e}. "
                                    "Installez la version LTS depuis https://nodejs.org puis relancez l'application.")
            return
        bin_dir = str(paths.private_node_bin())
        if IS_WINDOWS:
            from . import winenv

            npm_dir = str(Path(os.environ.get("APPDATA", paths.home())) / "npm")
            added = [d for d in (bin_dir, npm_dir) if winenv.add_user_path(d)]
            state.update(path_dirs=added)
        else:
            keystore.install_rc_block([bin_dir])
        state.update(private_node=True)
        system.refresh_path()
        self.npm_ready = system.which("npm") is not None
        self.set("node", OK if self.npm_ready else ERROR,
                 "Node.js installé dans votre dossier personnel" if self.npm_ready else "npm introuvable après installation")

    # 3. Windows
    def windows(self) -> None:
        if not IS_WINDOWS:
            self.set("windows", SKIP, "Non concerné")
            return
        self.set("windows", RUNNING)
        problems = []
        r = system.quiet(["powershell", "-NoProfile", "-Command", "Get-ExecutionPolicy"])
        if r.ok and r.output.strip().lower() in ("restricted", "allsigned"):
            self.log("Autorisation des scripts PowerShell pour votre compte (RemoteSigned)…")
            r2 = system.run(["powershell", "-NoProfile", "-Command",
                             "Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force"], self.log)
            if not r2.ok:
                problems.append("politique d'exécution PowerShell non modifiée (règle de l'établissement ?)")
        if self.plan.pi and not system.git_bash():
            if system.which("winget"):
                self.log("Installation de Git for Windows (nécessaire à Pi)…")
                system.run(["winget", "install", "--id", "Git.Git", "-e", "--scope", "user",
                            "--accept-package-agreements", "--accept-source-agreements",
                            "--disable-interactivity"], self.log)
            if not system.git_bash():
                problems.append("Git for Windows absent : installez-le depuis https://git-scm.com/download/win "
                                "(Pi en a besoin), puis relancez l'application")
        self.set("windows", WARN if problems else OK, " ; ".join(problems) or "Prêt")

    # 4. OpenCode
    def opencode(self) -> None:
        if not self.plan.opencode:
            self.set("opencode", SKIP, "Non demandé")
            return
        self.set("opencode", RUNNING)
        major = self._opencode_major()
        if major == 1:
            self.set("opencode", OK, f"Déjà installé (version {system.tool_version('opencode')})")
            return
        if major is not None:
            self.log(f"OpenCode {system.tool_version('opencode')} détecté : cette application "
                     "configure la version 1 (format testé). Installation de la v1…")
        if not self.npm_ready:
            self.set("opencode", ERROR, "npm indisponible (voir l'étape Node.js)")
            return
        r = self.npm(["install", "-g", OPENCODE_PKG])
        system.refresh_path()
        major = self._opencode_major()
        if r.ok and major == 1:
            self.set("opencode", OK, f"Version {system.tool_version('opencode')} installée")
        elif major and major != 1:
            self.set("opencode", ERROR, "Une autre version d'OpenCode (installée autrement, ex. Homebrew) "
                                        "reste prioritaire. Désinstallez-la puis relancez.")
        else:
            self.set("opencode", ERROR, "Échec de « npm install -g opencode-ai » (voir le journal)")

    def _opencode_major(self) -> int | None:
        v = system.parse_version(system.tool_version("opencode") or "")
        return v[0] if v else None

    def _pi_too_old(self) -> bool:
        v = system.parse_version(system.tool_version("pi") or "")
        return v is not None and v < (1, 0, 0)

    # 5. Pi
    def pi(self) -> None:
        if not self.plan.pi:
            self.set("pi", SKIP, "Non demandé")
            return
        self.set("pi", RUNNING)
        if system.which("pi") and not self._pi_too_old():
            self.set("pi", OK, f"Déjà installé (version {system.tool_version('pi')})")
            return
        if not self.npm_ready:
            self.set("pi", ERROR, "npm indisponible (voir l'étape Node.js)")
            return
        if self._pi_too_old():
            self.log("Ancienne version de Pi détectée : remplacement par la nouvelle (paquet renommé).")
            self.npm(["uninstall", "-g", PI_OLD_PKG])
        r = self.npm(["install", "-g", "--ignore-scripts", PI_PKG])
        system.refresh_path()
        if r.ok and system.which("pi"):
            self.set("pi", OK, f"Version {system.tool_version('pi')} installée")
        else:
            self.set("pi", ERROR, "Échec de l'installation de Pi (voir le journal)")

    # 6. Configurations
    def config(self) -> None:
        self.set("config", RUNNING)
        mcp_items = catalog_items("mcp", self.plan.mcp)
        errors = []
        if self.plan.opencode:
            if self._opencode_major() not in (None, 1):
                errors.append("OpenCode v2 détecté : configuration non écrite (format différent)")
            else:
                try:
                    for line in configs.write_opencode(self.plan.models, self.plan.default_model,
                                                       mcp_items, self.plan.set_default):
                        self.log(line)
                except (OSError, ConfigError) as e:
                    errors.append(str(e))
        if self.plan.pi:
            shell_path = None
            gb = system.git_bash()
            if IS_WINDOWS and gb and not system.git_bash_in_standard_place(gb):
                shell_path = str(gb)
            try:
                for line in configs.write_pi(self.plan.models, self.plan.default_model, mcp_items,
                                             self.plan.set_default, shell_path):
                    self.log(line)
                if shell_path:
                    state.update(pi_shell_path=True)
            except (OSError, ConfigError) as e:
                errors.append(str(e))
        state.update(mcp=self.plan.mcp)
        self.set("config", ERROR if errors else OK, " ; ".join(errors) or
                 f"Modèle par défaut : {self.plan.default_model}")

    # 7. Skills
    def skills(self) -> None:
        items = catalog_items("skills", self.plan.skills)
        if not items:
            self.set("skills", SKIP, "Aucun skill choisi")
            return
        self.set("skills", RUNNING)
        done, failed = [], []
        for item in items:
            try:
                status = skills.install(item, self.log)
                self.log(f"  {item['name']} : {status}")
                if status != "ignoré":
                    done.append(item["id"])
            except Exception as e:  # noqa: BLE001
                failed.append(item["name"])
                self.log(f"  {item['name']} : échec ({e})")
        state.update(skills=done)
        self.set("skills", WARN if failed else OK,
                 (f"Échec : {', '.join(failed)}" if failed else f"{len(done)} skill(s) dans {paths.skills_dir()}"))

    # 8. VS Code
    def vscode(self) -> None:
        if not (self.plan.vscode and self.plan.opencode):
            self.set("vscode", SKIP, "Non demandé")
            return
        if not system.which("code"):
            self.set("vscode", WARN, "Commande « code » introuvable : dans VS Code, palette → "
                                     "« Shell Command: Install 'code' command in PATH »")
            return
        self.set("vscode", RUNNING)
        r = system.run(["code", "--install-extension", VSCODE_EXTENSION], self.log)
        self.set("vscode", OK if r.ok else WARN, "Extension OpenCode installée" if r.ok else "Échec (voir le journal)")

    # 9. Vérifications
    def tests(self) -> None:
        if not self.plan.run_tests:
            self.set("test", SKIP, "Non demandé")
            return
        self.set("test", RUNNING)
        report, bad = [], False
        try:
            answer = albert.chat_test(self.plan.key, self.plan.default_model)
            self.log(f"Albert répond ({self.plan.default_model}) : {answer[:60]!r}")
            report.append("API : OK")
        except albert.AlbertError as e:
            self.log(f"Test de l'API : {e}")
            report.append("API : échec")
            bad = True
        tmp = Path(tempfile.mkdtemp(prefix="test-albert-"))
        try:
            (tmp / "consigne.txt").write_text(f"Le mot de code est : {TEST_CODE}\n", encoding="utf-8")
            prompt = ("Lis le fichier consigne.txt avec ton outil de lecture de fichiers, "
                      "puis réponds uniquement par le mot de code qu'il contient.")
            env = system.child_env({keystore.ENV_VAR: self.plan.key})
            if self.plan.opencode and system.which("opencode"):
                model = self.plan.default_model
                oc_ids = [m.id for m in self.plan.models if m.opencode]
                if model not in oc_ids and oc_ids:
                    model = oc_ids[0]
                self.log(f"Test d'OpenCode avec {model} (lecture d'un fichier)…")
                r = system.run(["opencode", "run", "-m", f"albert/{model}", prompt],
                               self.log, env=env, cwd=tmp, timeout=300)
                ok = TEST_CODE in r.output
                report.append("OpenCode : OK" if ok else "OpenCode : échec")
                bad |= not ok
            if self.plan.pi and system.which("pi"):
                self.log(f"Test de Pi avec {self.plan.default_model} (lecture d'un fichier)…")
                r = system.run(["pi", "-p", "--model", f"albert/{self.plan.default_model}", prompt],
                               self.log, env=env, cwd=tmp, timeout=300)
                ok = TEST_CODE in r.output
                report.append("Pi : OK" if ok else "Pi : échec")
                bad |= not ok
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        self.set("test", WARN if bad else OK, " · ".join(report))


def run_plan(plan: Plan, rep: Reporter) -> dict[str, str]:
    system.register_secret(plan.key)
    system.refresh_path()
    r = _Run(plan, rep)
    r.key()
    r.nodejs()
    r.windows()
    r.opencode()
    r.pi()
    r.config()
    r.skills()
    r.vscode()
    r.tests()
    from . import __version__

    state.update(version=__version__, opencode=plan.opencode, pi=plan.pi)
    return r.results


# --- Désinstallation ----------------------------------------------------------

def uninstall(rep: Reporter, remove_key: bool = True, remove_node: bool = True,
              remove_tools: bool = False) -> None:
    st = state.load()
    mcp_ids = st.get("mcp", [])
    for line in configs.remove_opencode(mcp_ids):
        rep.log(line)
    for line in configs.remove_pi(mcp_ids, st.get("pi_shell_path", False)):
        rep.log(line)
    for sid in st.get("skills", []):
        if skills.remove(sid):
            rep.log(f"Skill retiré : {sid}")
    for line in keystore.remove_rc_block():
        rep.log(line)
    if remove_tools:
        system.refresh_path()
        if system.which("npm"):
            system.run(["npm", "uninstall", "-g", "opencode-ai", "@earendil-works/pi-coding-agent"], rep.log)
    if IS_WINDOWS:
        from . import winenv

        for d in st.get("path_dirs", []):
            if winenv.remove_user_path(d):
                rep.log(f"Retiré du PATH : {d}")
    if remove_node and st.get("private_node"):
        shutil.rmtree(paths.private_node_dir(), ignore_errors=True)
        rep.log("Copie personnelle de Node.js supprimée.")
    if remove_key and keystore.delete_key():
        rep.log("Clé Albert supprimée de ce poste (pensez à la révoquer dans le Playground si besoin).")
    try:
        paths.state_file().unlink()
    except FileNotFoundError:
        pass
    rep.log("Désinstallation terminée. Les sauvegardes .bak des fichiers modifiés sont conservées.")
