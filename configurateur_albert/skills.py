"""Installation des skills dans ~/.agents/skills/ (lu par OpenCode et par Pi)."""

from __future__ import annotations

import io
import posixpath
import shutil
import tarfile
from pathlib import Path

from . import net, paths
from .paths import SKILL_MARKER
from .system import Log

_tar_cache: dict[tuple[str, str], bytes] = {}


def _github_tarball(repo: str, ref: str) -> bytes:
    key = (repo, ref)
    if key not in _tar_cache:
        _tar_cache[key] = net.download(f"https://codeload.github.com/{repo}/tar.gz/{ref}", timeout=300)
    return _tar_cache[key]


def extract_subdir(tar_bytes: bytes, subdir: str, dest: Path) -> int:
    """Extrait <racine>/<subdir>/… de l'archive dans dest. Ignore liens et chemins suspects."""
    count = 0
    subdir = subdir.strip("/")
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tf:
        for m in tf.getmembers():
            parts = m.name.split("/", 1)
            if len(parts) < 2:
                continue
            rel = parts[1]
            if rel != subdir and not rel.startswith(subdir + "/"):
                continue
            inner = posixpath.normpath(rel[len(subdir):].lstrip("/") or ".")
            if inner.startswith(("..", "/")):
                continue
            target = dest / inner
            if m.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif m.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                f = tf.extractfile(m)
                if f is None:
                    continue
                target.write_bytes(f.read())
                if m.mode & 0o111:
                    target.chmod(0o755)
                count += 1
    return count


def list_skill_dirs(tar_bytes: bytes, parent: str) -> list[str]:
    """Noms des sous-dossiers de <parent>/ qui contiennent un SKILL.md."""
    parent = parent.strip("/")
    names: set[str] = set()
    with tarfile.open(fileobj=io.BytesIO(tar_bytes), mode="r:gz") as tf:
        for m in tf.getmembers():
            parts = m.name.split("/")
            # <racine>/<parent…>/<nom>/SKILL.md
            rel = "/".join(parts[1:])
            if m.isfile() and rel.startswith(parent + "/") and rel.endswith("/SKILL.md"):
                inner = rel[len(parent) + 1:].split("/")
                if len(inner) == 2 and not inner[0].startswith("."):
                    names.add(inner[0])
    return sorted(names)


def expand(item: dict) -> list[dict]:
    """Un « pack » (dossier de skills d'un dépôt) devient une liste de skills individuels.
    On installe le pack entier : ses skills se citent entre eux."""
    src = item["source"]
    if src["type"] != "github-pack":
        return [item]
    ref = src.get("ref", "main")
    names = list_skill_dirs(_github_tarball(src["repo"], ref), src["path"])
    if not names:
        raise RuntimeError(f"aucun skill trouvé dans {src['repo']}/{src['path']}")
    return [{"id": n, "name": n,
             "source": {"type": "github", "repo": src["repo"], "ref": ref, "path": f"{src['path'].strip('/')}/{n}"}}
            for n in names]


def is_ours(skill_dir: Path) -> bool:
    return (skill_dir / SKILL_MARKER).exists()


def install(item: dict, log: Log, base: Path | None = None) -> str:
    """Installe un skill ; renvoie 'installé', 'mis à jour' ou 'ignoré'."""
    base = base or paths.skills_dir()
    dest = base / item["id"]
    if dest.exists() and not is_ours(dest):
        log(f"  « {item['id']} » existe déjà et n'a pas été installé par cette application : conservé tel quel.")
        return "ignoré"
    existed = dest.exists()
    tmp = base / f".{item['id']}.tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    try:
        src = item["source"]
        if src["type"] == "bundled":
            shutil.copytree(paths.BUNDLED_SKILLS_DIR / item["id"], tmp, dirs_exist_ok=True)
        elif src["type"] == "github":
            n = extract_subdir(_github_tarball(src["repo"], src.get("ref", "main")), src["path"], tmp)
            if n == 0:
                raise RuntimeError(f"dossier {src['path']} introuvable dans {src['repo']}")
        else:
            raise RuntimeError(f"source inconnue : {src['type']}")
        if not (tmp / "SKILL.md").exists():
            raise RuntimeError("SKILL.md manquant")
        (tmp / SKILL_MARKER).write_text(
            "Installé par Configurateur Albert. Supprimez ce fichier pour que l'application "
            "ne remplace plus ce dossier.\n", encoding="utf-8")
        shutil.rmtree(dest, ignore_errors=True)
        tmp.rename(dest)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return "mis à jour" if existed else "installé"


def remove(skill_id: str, base: Path | None = None) -> bool:
    dest = (base or paths.skills_dir()) / skill_id
    if dest.exists() and is_ours(dest):
        shutil.rmtree(dest)
        return True
    return False
