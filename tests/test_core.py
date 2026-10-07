import io
import json
import sys
import tarfile

import pytest

from configurateur_albert import albert, configs, installer, jsonfiles, keystore, paths, skills, state, system

KEY = "sk-eyJhbGciOiJIUzI1NiJ9.test-cle-factice_0123456789"

RAW_MODELS = [
    {"id": "gemma-4-31b-it", "type": "image-text-to-text", "max_context_length": 262144},
    {"id": "gpt-oss-120b", "type": "text-generation"},
    {"id": "lightonocr-2-1b", "type": "image-text-to-text"},
    {"id": "mistral-small-3-2-24b-instruct-2506", "type": "image-text-to-text"},
    {"id": "nouveau-modele-7b", "type": "text-generation", "max_context_length": 32768},
    {"id": "bge-m3", "type": "text-embeddings-inference"},
    {"id": "whisper-large-v3", "type": "automatic-speech-recognition"},
]


def models():
    return albert.usable_models(RAW_MODELS)


# --- JSONC ---------------------------------------------------------------------

def test_strip_jsonc_keeps_strings():
    text = '{\n // commentaire\n "url": "https://a.b/c", /* bloc */ "x": [1, 2,],\n}'
    assert json.loads(jsonfiles.strip_jsonc(text)) == {"url": "https://a.b/c", "x": [1, 2]}


def test_invalid_json_is_never_overwritten(tmp_path):
    f = tmp_path / "opencode.json"
    f.write_text("{ pas du json")
    with pytest.raises(jsonfiles.ConfigError):
        configs.write_opencode(models(), "gemma-4-31b-it", [], path=f)
    assert f.read_text() == "{ pas du json"


# --- Clé ---------------------------------------------------------------------------

def test_normalize_key_variants():
    assert albert.normalize_key(f'  "{KEY}" ') == KEY
    assert albert.normalize_key(f"ALBERT_API_KEY={KEY}") == KEY
    assert albert.normalize_key(f"export ALBERT_API_KEY='{KEY}'") == KEY
    assert albert.normalize_key(f"Bearer {KEY}") == KEY
    assert albert.check_key_format(KEY) is None
    assert albert.check_key_format("sk-avec espace") is not None
    assert albert.mask(KEY) == "sk-eyJh…"


def test_redact_hides_key():
    system.register_secret(KEY)
    assert KEY not in system.redact(f"erreur avec {KEY} dedans")


# --- Modèles -----------------------------------------------------------------------

def test_usable_models_filters_and_orders():
    ids = [m.id for m in models()]
    assert ids[0] == "gemma-4-31b-it"                       # testés d'abord, ordre du catalogue
    assert "mistral-small-3-2-24b-instruct-2506" not in ids  # exclu (outils mal formés)
    assert "bge-m3" not in ids and "whisper-large-v3" not in ids
    unknown = next(m for m in models() if m.id == "nouveau-modele-7b")
    assert not unknown.known and unknown.context == 32768
    assert albert.default_model_id(models()) == "gemma-4-31b-it"


# --- Configurations ----------------------------------------------------------------

def test_opencode_merge_preserves_user_settings(home):
    f = paths.opencode_config_file()
    f.parent.mkdir(parents=True)
    f.write_text(json.dumps({
        "provider": {"autre": {"npm": "x"}},
        "mcp": {"perso": {"type": "local", "command": ["x"]}},
        "theme": "dark",
    }))
    items = installer.catalog_items("mcp", ["data-gouv"])
    configs.write_opencode(models(), "gemma-4-31b-it", items)
    data = json.loads(f.read_text())
    assert data["theme"] == "dark"
    assert "autre" in data["provider"] and "perso" in data["mcp"]
    albert_p = data["provider"]["albert"]
    assert albert_p["options"]["apiKey"] == "{env:ALBERT_API_KEY}"
    assert "lightonocr-2-1b" not in albert_p["models"]            # pas d'OCR dans OpenCode
    assert albert_p["models"]["gemma-4-31b-it"]["tool_call"] is True
    assert data["model"] == "albert/gemma-4-31b-it"
    assert data["mcp"]["data-gouv"] == {"type": "remote", "url": "https://mcp.data.gouv.fr/mcp", "enabled": True}
    assert KEY not in f.read_text()
    assert list(f.parent.glob("opencode.json.bak-*")), "une sauvegarde doit exister"


def test_opencode_idempotent_no_new_backup(home):
    configs.write_opencode(models(), "gemma-4-31b-it", [])
    configs.write_opencode(models(), "gemma-4-31b-it", [])
    assert not list(paths.opencode_config_dir().glob("*.bak-*"))


def test_pi_config(home):
    configs.write_pi(models(), "gpt-oss-120b", installer.catalog_items("mcp", ["data-gouv"]))
    m = json.loads(paths.pi_models_file().read_text())["providers"]["albert"]
    assert m["apiKey"] == "$ALBERT_API_KEY" and m["api"] == "openai-completions"
    by_id = {e["id"]: e for e in m["models"]}
    assert by_id["gemma-4-31b-it"]["samplingParams"] == {"tool_choice": "auto"}
    assert "samplingParams" not in by_id["lightonocr-2-1b"]
    assert by_id["gemma-4-31b-it"]["input"] == ["text", "image"]
    s = json.loads(paths.pi_settings_file().read_text())
    assert s == {"defaultProvider": "albert", "defaultModel": "gpt-oss-120b"}
    mcp = json.loads(paths.pi_mcp_file().read_text())
    assert mcp["mcpServers"]["data-gouv"]["url"] == "https://mcp.data.gouv.fr/mcp"


def test_local_mcp_uses_cmd_on_windows(monkeypatch):
    item = {"id": "x", "type": "local", "command": ["npx", "-y", "paquet"]}
    monkeypatch.setattr(configs, "IS_WINDOWS", True)
    assert configs.mcp_entry(item)["command"] == ["cmd", "/c", "npx", "-y", "paquet"]
    monkeypatch.setattr(configs, "IS_WINDOWS", False)
    assert configs.mcp_entry(item)["command"] == ["npx", "-y", "paquet"]


# --- Coffre et fichiers du shell -------------------------------------------------------

@pytest.mark.skipif(sys.platform == "win32", reason="coffre fichier : macOS/Linux")
def test_key_file_and_rc_block_idempotent(home):
    keystore.store_key(KEY)
    f = paths.key_file()
    assert f.read_text() == f"ALBERT_API_KEY={KEY}\n"
    assert (f.stat().st_mode & 0o777) == 0o600
    assert keystore.existing_key() == KEY
    keystore.install_rc_block()
    keystore.install_rc_block()
    keystore.install_rc_block(["/opt/node/bin"])
    rc = (home / ".zshrc").read_text()
    assert rc.count(keystore.BEGIN) == 1
    assert sum(".albert.env" in line for line in rc.splitlines()) == 1
    assert "/opt/node/bin" in rc
    keystore.remove_rc_block()
    assert keystore.BEGIN not in (home / ".zshrc").read_text()


@pytest.mark.skipif(sys.platform == "win32", reason="macOS/Linux")
def test_rc_respects_manual_line(home):
    (home / ".zshrc").write_text("set -a; source ~/.albert.env; set +a\n")
    keystore.install_rc_block()
    assert sum(".albert.env" in line for line in (home / ".zshrc").read_text().splitlines()) == 1


# --- Skills ----------------------------------------------------------------------------

def _fake_tarball() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        def add(name, content=b""):
            info = tarfile.TarInfo(name)
            info.size = len(content)
            tf.addfile(info, io.BytesIO(content))
        add("skills-main/skills/demo/SKILL.md", b"---\nname: demo\ndescription: d\n---\n")
        add("skills-main/skills/demo/references/a.md", b"a")
        add("skills-main/skills/autre/SKILL.md", b"x")
        add("skills-main/skills/demo/../../evil.txt", b"x")
    return buf.getvalue()


def test_github_skill_install_and_protection(home, monkeypatch):
    monkeypatch.setattr(skills, "_github_tarball", lambda repo, ref: _fake_tarball())
    item = {"id": "demo", "source": {"type": "github", "repo": "x/y", "path": "skills/demo"}}
    assert skills.install(item, print) == "installé"
    d = paths.skills_dir() / "demo"
    assert (d / "SKILL.md").exists() and (d / "references" / "a.md").exists()
    assert not (paths.skills_dir() / "evil.txt").exists()
    assert skills.install(item, print) == "mis à jour"
    # Un skill personnel du même nom n'est jamais écrasé.
    (d / paths.SKILL_MARKER).unlink()
    assert skills.install(item, print) == "ignoré"
    assert not skills.remove("demo")


def test_bundled_skills_are_valid(home):
    for item in paths.catalog()["skills"]:
        if item["source"]["type"] != "bundled":
            continue
        skills.install(item, print)
        text = (paths.skills_dir() / item["id"] / "SKILL.md").read_text(encoding="utf-8")
        assert text.startswith("---\n") and f"name: {item['id']}\n" in text


# --- Désinstallation ---------------------------------------------------------------------

class Rec:
    def __init__(self):
        self.lines = []

    def log(self, m):
        self.lines.append(m)

    def step(self, *a):
        pass


@pytest.mark.skipif(sys.platform == "win32", reason="macOS/Linux")
def test_uninstall_removes_only_ours(home):
    f = paths.opencode_config_file()
    f.parent.mkdir(parents=True)
    f.write_text(json.dumps({"provider": {"autre": {}}, "model": "autre/x"}))
    keystore.store_key(KEY)
    keystore.install_rc_block()
    configs.write_opencode(models(), "gemma-4-31b-it", installer.catalog_items("mcp", ["data-gouv"]),
                           set_default=False)
    configs.write_pi(models(), "gemma-4-31b-it", [])
    skills.install(installer.catalog_items("skills", ["anonymisation-textes"])[0], print)
    state.update(mcp=["data-gouv"], skills=["anonymisation-textes"])

    assert json.loads(f.read_text())["model"] == "autre/x"   # set_default=False respecté
    installer.uninstall(Rec(), remove_key=True)

    data = json.loads(f.read_text())
    data.pop("$schema", None)
    assert data == {"provider": {"autre": {}}, "model": "autre/x"}
    assert "albert" not in json.loads(paths.pi_models_file().read_text())["providers"]
    assert not (paths.skills_dir() / "anonymisation-textes").exists()
    assert not paths.key_file().exists()
    assert keystore.BEGIN not in (home / ".zshrc").read_text()


# --- Node.js -----------------------------------------------------------------------------

def test_pick_node_release():
    from configurateur_albert import node

    index = [
        {"version": "v25.1.0", "lts": False, "files": ["linux-x64"]},
        {"version": "v24.9.0", "lts": "Krypton", "files": ["osx-arm64-tar"]},
        {"version": "v22.20.0", "lts": "Jod", "files": ["linux-x64"]},
        {"version": "v22.18.0", "lts": "Jod", "files": ["linux-x64"]},
    ]
    assert node.pick_release(index, "linux-x64") == "v22.20.0"
    assert node.pick_release(index, "osx-arm64-tar") == "v24.9.0"
    assert node.pick_release(index[3:], "linux-x64") is None
