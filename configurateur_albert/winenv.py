"""Variables d'environnement « de compte » sous Windows (HKCU\\Environment).

Équivalent de « Modifier les variables d'environnement pour votre compte »,
sans passer par setx (qui laisserait la clé dans l'historique PowerShell)."""

from __future__ import annotations

import os
import sys

if sys.platform == "win32":
    import ctypes
    import winreg
    from ctypes import wintypes

_KEY = "Environment"


def _open(write: bool = False):
    access = winreg.KEY_READ | (winreg.KEY_SET_VALUE if write else 0)
    return winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KEY, 0, access)


def get(name: str) -> str | None:
    try:
        with _open() as k:
            value, _ = winreg.QueryValueEx(k, name)
            return str(value)
    except FileNotFoundError:
        return None


def set_value(name: str, value: str, expand: bool = False) -> None:
    with _open(write=True) as k:
        winreg.SetValueEx(k, name, 0, winreg.REG_EXPAND_SZ if expand else winreg.REG_SZ, value)
    broadcast()


def delete(name: str) -> bool:
    try:
        with _open(write=True) as k:
            winreg.DeleteValue(k, name)
        broadcast()
        return True
    except FileNotFoundError:
        return False


def broadcast() -> None:
    """Prévient l'Explorateur : les terminaux ouverts ensuite voient la variable."""
    HWND_BROADCAST, WM_SETTINGCHANGE, SMTO_ABORTIFHUNG = 0xFFFF, 0x001A, 0x0002
    result = wintypes.DWORD()
    ctypes.windll.user32.SendMessageTimeoutW(
        HWND_BROADCAST, WM_SETTINGCHANGE, 0, "Environment", SMTO_ABORTIFHUNG, 5000,
        ctypes.byref(result))


def registry_path_entries() -> list[str]:
    """PATH utilisateur + système, tels qu'enregistrés (après une installation récente)."""
    entries: list[str] = []
    locations = [
        (winreg.HKEY_CURRENT_USER, _KEY),
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
    ]
    for root, sub in locations:
        try:
            with winreg.OpenKey(root, sub) as k:
                value, _ = winreg.QueryValueEx(k, "Path")
                entries += [os.path.expandvars(p) for p in str(value).split(";") if p]
        except OSError:
            pass
    return entries


def add_user_path(directory: str) -> bool:
    """Ajoute un dossier au PATH du compte ; False s'il y était déjà."""
    current = get("Path") or ""
    parts = [p for p in current.split(";") if p]
    if any(os.path.normcase(os.path.expandvars(p)) == os.path.normcase(directory) for p in parts):
        return False
    parts.append(directory)
    set_value("Path", ";".join(parts), expand=True)
    return True


def remove_user_path(directory: str) -> bool:
    current = get("Path") or ""
    parts = [p for p in current.split(";") if p]
    kept = [p for p in parts
            if os.path.normcase(os.path.expandvars(p)) != os.path.normcase(directory)]
    if len(kept) == len(parts):
        return False
    set_value("Path", ";".join(kept), expand=True)
    return True
