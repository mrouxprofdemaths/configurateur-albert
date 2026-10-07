"""Détection des outils et exécution de commandes (sans jamais exposer la clé)."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable

from . import paths
from .paths import IS_MAC, IS_WINDOWS

Log = Callable[[str], None]

PI_MIN_NODE = (22, 19, 0)

_secrets: set[str] = set()


def register_secret(value: str) -> None:
    """Toute chaîne enregistrée ici est masquée dans les journaux."""
    if value and len(value) >= 8:
        _secrets.add(value)


def redact(text: str) -> str:
    for s in _secrets:
        if s in text:
            text = text.replace(s, f"{s[:7]}…[masquée]")
    return text


# --- PATH ---------------------------------------------------------------------

def _candidate_dirs() -> list[Path]:
    h = paths.home()
    dirs = [paths.private_node_bin(), h / ".opencode" / "bin", h / ".local" / "bin",
            h / ".npm-global" / "bin"]
    if IS_WINDOWS:
        appdata = Path(os.environ.get("APPDATA", h / "AppData" / "Roaming"))
        local = Path(os.environ.get("LOCALAPPDATA", h / "AppData" / "Local"))
        pf = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        dirs += [appdata / "npm", pf / "nodejs", local / "Programs" / "Microsoft VS Code" / "bin",
                 pf / "Microsoft VS Code" / "bin", pf / "Git" / "cmd", local / "Programs" / "Git" / "cmd"]
    else:
        dirs += [Path("/opt/homebrew/bin"), Path("/usr/local/bin"), Path("/usr/bin"), Path("/bin")]
        if IS_MAC:
            dirs.append(Path("/Applications/Visual Studio Code.app/Contents/Resources/app/bin"))
    return dirs


def _login_shell_path() -> list[str]:
    """Sur macOS, une application lancée depuis le Finder hérite d'un PATH minimal :
    on récupère celui du shell de connexion (Homebrew, nvm…)."""
    if IS_WINDOWS:
        return []
    shell = os.environ.get("SHELL") or ("/bin/zsh" if IS_MAC else "/bin/bash")
    try:
        out = subprocess.run([shell, "-lc", 'printf "%s" "$PATH"'], capture_output=True,
                             text=True, timeout=8, stdin=subprocess.DEVNULL, check=False)
        return [p for p in out.stdout.strip().split(":") if p]
    except (OSError, subprocess.SubprocessError):
        return []


def refresh_path() -> None:
    """Complète le PATH du processus (et donc des commandes lancées ensuite)."""
    current = os.environ.get("PATH", "").split(os.pathsep)
    extra = _login_shell_path() + [str(d) for d in _candidate_dirs()]
    if IS_WINDOWS:
        extra = _windows_registry_path() + extra
    # Le Node.js personnel installé par l'application passe avant tout autre :
    # sinon « npm install -g » viserait un Node système (droits admin, version trop ancienne).
    first = [str(paths.private_node_bin())] if paths.private_node_bin().is_dir() else []
    if IS_WINDOWS and first:
        first.append(str(Path(os.environ.get("APPDATA", paths.home())) / "npm"))
    merged: list[str] = []
    for p in first + current + extra:
        if p and p not in merged:
            merged.append(p)
    os.environ["PATH"] = os.pathsep.join(merged)


def _windows_registry_path() -> list[str]:
    try:
        from . import winenv

        return winenv.registry_path_entries()
    except Exception:  # noqa: BLE001
        return []


def which(cmd: str) -> str | None:
    return shutil.which(cmd)


# --- Exécution ----------------------------------------------------------------

@dataclass
class Result:
    code: int
    output: str

    @property
    def ok(self) -> bool:
        return self.code == 0


def child_env(extra: dict | None = None) -> dict:
    env = os.environ.copy()
    env.setdefault("NO_COLOR", "1")
    env.update(extra or {})
    return env


def run(cmd: list[str], log: Log | None = None, *, env: dict | None = None,
        cwd: str | Path | None = None, timeout: float = 900) -> Result:
    """Lance une commande en diffusant sa sortie (masquée) dans le journal.
    Les secrets passent par l'environnement, jamais par la ligne de commande."""
    exe = which(cmd[0]) or cmd[0]
    argv = [exe, *cmd[1:]]
    kwargs: dict = {}
    if IS_WINDOWS:
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW : pas de console qui clignote
    if log:
        log("$ " + " ".join(cmd))
    try:
        proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, env=env or child_env(), cwd=cwd,
                                text=True, encoding="utf-8", errors="replace", **kwargs)
    except OSError as e:
        msg = f"Impossible de lancer {cmd[0]} : {e}"
        if log:
            log(msg)
        return Result(127, msg)
    lines: list[str] = []
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = redact(_strip_ansi(line.rstrip("\n")))
            lines.append(line)
            if log and line.strip():
                log("  " + line)
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        lines.append("(délai dépassé, commande interrompue)")
        return Result(124, "\n".join(lines))
    return Result(proc.returncode, "\n".join(lines))


_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


def _strip_ansi(s: str) -> str:
    return _ANSI.sub("", s)


def quiet(cmd: list[str], timeout: float = 30) -> Result:
    return run(cmd, None, timeout=timeout)


# --- Versions -----------------------------------------------------------------

def parse_version(text: str) -> tuple[int, ...] | None:
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", text)
    return tuple(int(x) for x in m.groups()) if m else None


def tool_version(cmd: str) -> str | None:
    if not which(cmd):
        return None
    r = quiet([cmd, "--version"], timeout=60)
    if not r.ok:
        return None
    v = parse_version(r.output)
    return ".".join(map(str, v)) if v else (r.output.strip().splitlines() or [""])[-1]


def node_version() -> tuple[int, ...] | None:
    if not which("node"):
        return None
    r = quiet(["node", "--version"])
    return parse_version(r.output) if r.ok else None


def node_ok_for_pi() -> bool:
    v = node_version()
    return v is not None and v >= PI_MIN_NODE


def npm_global_writable() -> bool:
    """Peut-on faire « npm install -g » sans droits administrateur ?"""
    if not which("npm"):
        return False
    r = quiet(["npm", "prefix", "-g"])
    if not r.ok or not r.output.strip():
        return False
    prefix = Path(r.output.strip().splitlines()[-1])
    target = prefix if IS_WINDOWS else prefix / "lib"
    while not target.exists() and target != target.parent:
        target = target.parent
    return os.access(target, os.W_OK)


def git_bash() -> Path | None:
    """Bash de Git for Windows (indispensable à Pi sous Windows)."""
    if not IS_WINDOWS:
        return None
    candidates = []
    for var in ("ProgramFiles", "ProgramFiles(x86)", "ProgramW6432"):
        if os.environ.get(var):
            candidates.append(Path(os.environ[var]) / "Git" / "bin" / "bash.exe")
    if os.environ.get("LOCALAPPDATA"):
        candidates.append(Path(os.environ["LOCALAPPDATA"]) / "Programs" / "Git" / "bin" / "bash.exe")
    for c in candidates:
        if c.exists():
            return c
    found = which("bash")
    return Path(found) if found and "system32" not in found.lower() else None


def git_bash_in_standard_place(p: Path) -> bool:
    """Pi trouve seul Git Bash sous Program Files ; ailleurs il faut le lui indiquer."""
    s = str(p).lower()
    return "program files" in s
