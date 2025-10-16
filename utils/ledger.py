"""
Moduł ledger: licznik eksperymentów dla Deflated Sharpe Ratio.
"""
import hashlib
import json
import os
import time
from typing import Any, Dict


def cfg_hash(cfg: Dict[str, Any]) -> str:
    """
    Oblicza hash SHA1 konfiguracji.

    Args:
        cfg: Słownik konfiguracji

    Returns:
        Hash hex string
    """
    return hashlib.sha1(json.dumps(cfg, sort_keys=True).encode()).hexdigest()


def append_ledger(path: str, cfg_hash: str) -> int:
    """
    Dodaje wpis do ledger z timestampem i hashem configu.

    Args:
        path: Ścieżka do pliku ledger (JSON)
        cfg_hash: Hash konfiguracji

    Returns:
        Łączna liczba eksperymentów (testów)
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)

    L = []
    if os.path.exists(path):
        with open(path, "r") as f:
            L = json.load(f)

    L.append({"ts": time.time(), "hash": cfg_hash})

    with open(path, "w") as f:
        json.dump(L, f, indent=2)

    return len(L)
