import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def home(tmp_path, monkeypatch):
    """Dossier personnel jetable : aucun test ne touche au vrai $HOME."""
    h = tmp_path / "home"
    h.mkdir()
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    monkeypatch.setenv("LOCALAPPDATA", str(h / "AppData" / "Local"))
    monkeypatch.setenv("APPDATA", str(h / "AppData" / "Roaming"))
    monkeypatch.setenv("SHELL", "/bin/zsh")
    monkeypatch.delenv("PI_CODING_AGENT_DIR", raising=False)
    monkeypatch.delenv("ALBERT_API_KEY", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: h))
    yield h
    os.environ.pop("ALBERT_API_KEY", None)
