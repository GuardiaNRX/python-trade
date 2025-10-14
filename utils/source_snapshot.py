"""
Moduł source_snapshot: snapshoty źródłowe per symbol + backfill detection.
"""
import os
import json
import hashlib
import pandas as pd
from .atomic import atomic_write_text
from typing import Dict, Any


def _hash_df(df: pd.DataFrame) -> str:
    """Oblicza hash DataFrame."""
    return hashlib.sha1(pd.util.hash_pandas_object(df, index=True).values).hexdigest()


def save_symbol_snapshot(
    df: pd.DataFrame,
    symbol: str,
    asof: pd.Timestamp,
    out_dir: str = "data/source_snapshots"
) -> Dict[str, Any]:
    """
    Zapisuje snapshot surowych danych per symbol.

    Args:
        df: DataFrame z danymi OHLCV dla symbolu
        symbol: Symbol tickera
        asof: Data snapshot
        out_dir: Katalog docelowy

    Returns:
        Dict z metadanymi: symbol, asof, hash
    """
    os.makedirs(out_dir, exist_ok=True)

    date = pd.Timestamp(asof).strftime("%Y%m%d")
    base = os.path.join(out_dir, f"{symbol}_{date}")

    # Zapisz parquet
    df.to_parquet(base + ".parquet")

    # Metadata JSON
    meta = {
        "symbol": symbol,
        "asof": date,
        "hash": _hash_df(df.fillna(0))
    }
    atomic_write_text(base + ".json", json.dumps(meta, indent=2))

    return meta


def compare_meta(prev_meta_path: str, new_meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    Porównuje poprzedni snapshot z nowym (backfill detection).

    Args:
        prev_meta_path: Ścieżka do poprzedniego meta JSON
        new_meta: Nowe metadane

    Returns:
        Dict: changed (bool), reason, prev, new
    """
    if not os.path.exists(prev_meta_path):
        return {"changed": False, "reason": "no_previous"}

    with open(prev_meta_path, "r") as f:
        prev = json.load(f)

    changed = (prev.get("hash") != new_meta.get("hash"))

    return {
        "changed": changed,
        "prev": prev,
        "new": new_meta
    }
