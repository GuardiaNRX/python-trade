"""
Moduł run-lock: zapobiega równoległym uruchomieniom pipeline.
"""
import os
import time
import json
import errno
from contextlib import contextmanager
from typing import Dict, Any

DEFAULT_LOCK = "backtests/results/job.lock"


def _write_lock(path: str, data: Dict[str, Any]) -> None:
    """Zapisuje lockfile z metadanymi."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _read_lock(path: str) -> Dict[str, Any]:
    """Odczytuje lockfile."""
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


@contextmanager
def run_lock(path: str = DEFAULT_LOCK, stale_after_sec: int = 3600):
    """
    Context manager tworzący lockfile z PID i timestampem.

    Args:
        path: Ścieżka do lockfile
        stale_after_sec: Czas po którym lock uznajemy za stary (sekundy)

    Raises:
        RuntimeError: Jeśli inny run jest w toku
    """
    now = time.time()
    if os.path.exists(path):
        meta = _read_lock(path)
        if (now - float(meta.get("ts", 0))) < stale_after_sec:
            raise RuntimeError(
                f"Inny run w toku (lock: {path}; meta={meta})"
            )

    _write_lock(path, {"ts": now, "pid": os.getpid()})
    try:
        yield
    finally:
        try:
            os.remove(path)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
