"""
Moduł run_id: generowanie unikalnych ID dla runów pipeline.
"""
import hashlib
import time


def make_run_id(cfg_hash: str, snapshot_id: str) -> str:
    """
    Tworzy unikalny run_id z timestamp, cfg_hash i snapshot_id.

    Args:
        cfg_hash: Hash konfiguracji
        snapshot_id: ID snapshot danych

    Returns:
        Unikalny run_id (12 znaków hex)
    """
    ts = str(int(time.time()))
    base = f"{ts}_{cfg_hash[:8]}_{snapshot_id[:8]}"
    return hashlib.sha1(base.encode()).hexdigest()[:12]
