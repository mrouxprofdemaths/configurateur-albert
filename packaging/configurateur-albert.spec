# -*- mode: python ; coding: utf-8 -*-
# Construction : pyinstaller packaging/configurateur-albert.spec
import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent
PKG = ROOT / "configurateur_albert"
NAME = "ConfigurateurAlbert"

datas = [(str(PKG / "catalog.json"), "configurateur_albert")]
for f in (PKG / "skills").rglob("*"):
    if f.is_file():
        datas.append((str(f), str(Path("configurateur_albert") / f.parent.relative_to(PKG))))

a = Analysis([str(ROOT / "packaging" / "launcher.py")], pathex=[str(ROOT)], datas=datas,
             hiddenimports=["certifi"], excludes=["numpy", "PIL", "pytest"])
pyz = PYZ(a.pure)

if sys.platform == "darwin":
    # macOS : une application .app (dossier), plus fiable que --onefile avec Gatekeeper.
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=NAME, console=False,
              argv_emulation=False)
    coll = COLLECT(exe, a.binaries, a.datas, name=NAME)
    app = BUNDLE(coll, name=f"{NAME}.app", bundle_identifier="fr.drane.configurateur-albert",
                 info_plist={"CFBundleDisplayName": "Configurateur Albert",
                             "NSHighResolutionCapable": True,
                             "LSMinimumSystemVersion": "11.0"})
else:
    # Windows : un seul .exe sans console. Linux : un seul binaire.
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name=NAME,
              console=not sys.platform.startswith("win"), upx=False)
