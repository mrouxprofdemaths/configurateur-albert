"""Accès HTTP (bibliothèque standard + certificats certifi si disponibles)."""

from __future__ import annotations

import http.client
import json
import ssl
import time
import urllib.error
import urllib.request

from . import __version__

USER_AGENT = f"configurateur-albert/{__version__}"


def _ssl_context() -> ssl.SSLContext:
    # Certificats du système (dont ceux qu'un réseau d'établissement ajoute pour inspecter
    # le trafic HTTPS) + ceux de certifi (le Python de python.org sous macOS et les
    # exécutables PyInstaller n'ont pas toujours accès à ceux du système).
    ctx = ssl.create_default_context()
    try:
        import certifi

        ctx.load_verify_locations(cafile=certifi.where())
    except (ImportError, OSError):
        pass
    return ctx


class HttpError(Exception):
    def __init__(self, status: int, body: str):
        super().__init__(f"HTTP {status}")
        self.status = status
        self.body = body


def request(url: str, *, method: str = "GET", headers: dict | None = None,
            data: bytes | None = None, timeout: float = 30) -> bytes:
    h = {"User-Agent": USER_AGENT}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise HttpError(e.code, body) from None


def get_json(url: str, headers: dict | None = None, timeout: float = 30):
    return json.loads(request(url, headers=headers, timeout=timeout))


def post_json(url: str, payload: dict, headers: dict | None = None, timeout: float = 60):
    h = {"Content-Type": "application/json"}
    h.update(headers or {})
    return json.loads(request(url, method="POST", headers=h,
                              data=json.dumps(payload).encode(), timeout=timeout))


def download(url: str, timeout: float = 120, attempts: int = 3) -> bytes:
    """Téléchargement avec nouvelles tentatives (réseaux d'établissement capricieux)."""
    for i in range(attempts):
        try:
            return request(url, timeout=timeout)
        except HttpError as e:
            if e.status < 500 or i == attempts - 1:
                raise
        except (urllib.error.URLError, http.client.IncompleteRead, ConnectionError, TimeoutError):
            if i == attempts - 1:
                raise
        time.sleep(2 * (i + 1))
    raise AssertionError("inatteignable")
