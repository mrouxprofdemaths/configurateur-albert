"""Installation de Node.js dans le dossier de l'utilisateur (sans droits administrateur).

Utile sur les postes d'établissement : aucun installeur système, aucun sudo.
L'archive officielle de nodejs.org est vérifiée par son empreinte SHA-256."""

from __future__ import annotations

import hashlib
import io
import platform
import posixpath
import shutil
import tarfile
import zipfile
from pathlib import Path

from . import net, paths, system
from .paths import IS_MAC, IS_WINDOWS
from .system import Log

DIST = "https://nodejs.org/dist"


def _platform_tag() -> tuple[str, str]:
    """(clé dans index.json, suffixe du nom d'archive)."""
    machine = platform.machine().lower()
    arch = "arm64" if machine in ("arm64", "aarch64") else "x64"
    if IS_WINDOWS:
        return f"win-{arch}-zip", f"win-{arch}.zip"
    if IS_MAC:
        return f"osx-{arch}-tar", f"darwin-{arch}.tar.gz"
    return f"linux-{arch}", f"linux-{arch}.tar.gz"


def pick_release(index: list[dict], file_key: str) -> str | None:
    """Dernière version LTS compatible avec Pi (≥ 22.19) disponible pour ce système."""
    for entry in index:  # index.json est trié du plus récent au plus ancien
        if not entry.get("lts") or file_key not in entry.get("files", []):
            continue
        v = system.parse_version(entry["version"])
        if v and v >= system.PI_MIN_NODE:
            return entry["version"]
    return None


def _safe_members_tar(tf: tarfile.TarFile, root: str):
    """Membres situés sous root/, liens compris s'ils pointent à l'intérieur de root/."""
    for m in tf.getmembers():
        name = m.name
        if not name.startswith(root + "/") or name.startswith("/") or ".." in Path(name).parts:
            continue
        if m.issym() or m.islnk():
            base = posixpath.dirname(name) if m.issym() else ""
            target = posixpath.normpath(posixpath.join(base, m.linkname))
            if m.linkname.startswith("/") or not target.startswith(root + "/"):
                continue
        yield m


def install_private_node(log: Log) -> Path:
    file_key, suffix = _platform_tag()
    log("Recherche de la dernière version LTS de Node.js…")
    index = net.get_json(f"{DIST}/index.json")
    version = pick_release(index, file_key)
    if not version:
        raise RuntimeError("Aucune version de Node.js adaptée à ce système n'a été trouvée.")
    name = f"node-{version}-{suffix}"
    log(f"Téléchargement de {name}…")
    archive = net.download(f"{DIST}/{version}/{name}", timeout=600)
    sums = net.download(f"{DIST}/{version}/SHASUMS256.txt").decode()
    expected = next((line.split()[0] for line in sums.splitlines()
                     if line.strip().endswith(name)), None)
    actual = hashlib.sha256(archive).hexdigest()
    if expected != actual:
        raise RuntimeError("L'archive Node.js téléchargée est corrompue (empreinte incorrecte).")
    log("Archive vérifiée (SHA-256).")

    dest = paths.private_node_dir()
    tmp = dest.with_name("node.tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    root = name.removesuffix(".zip").removesuffix(".tar.gz")
    if name.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            for info in zf.infolist():
                parts = Path(info.filename).parts
                if not parts or parts[0] != root or ".." in parts:
                    continue
                zf.extract(info, tmp)
    else:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tf:
            members = list(_safe_members_tar(tf, root))
            if hasattr(tarfile, "data_filter"):
                tf.extractall(tmp, members=members, filter="data")
            else:
                tf.extractall(tmp, members=members)
    shutil.rmtree(dest, ignore_errors=True)
    (tmp / root).rename(dest)
    shutil.rmtree(tmp, ignore_errors=True)
    log(f"Node.js {version} installé dans {dest}.")
    system.refresh_path()
    return dest


def private_node_installed() -> bool:
    exe = "node.exe" if IS_WINDOWS else "node"
    return (paths.private_node_bin() / exe).exists()
