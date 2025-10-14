"""
Moduł snapshot: deterministyczne snapshoty danych wejściowych.
"""
import os
import json
import hashlib
import pandas as pd
from typing import Dict, Any


def _hash_df(df: pd.DataFrame) -> str:
    """Oblicza hash SHA1 DataFrame."""
    h = hashlib.sha1()
    h.update(pd.util.hash_pandas_object(df, index=True).values)
    return h.hexdigest()


def save_snapshot(
    prices: pd.DataFrame,
    volume: pd.DataFrame,
    high: pd.DataFrame,
    low: pd.DataFrame,
    out_dir: str = "data/snapshots"
) -> Dict[str, Any]:
    """
    Zapisuje snapshot danych wejściowych (OHLCV).

    Args:
        prices: DataFrame z cenami (Adj Close)
        volume: DataFrame z wolumenem
        high: DataFrame z High
        low: DataFrame z Low
        out_dir: Katalog docelowy

    Returns:
        Dict z metadanymi snapshot: snapshot_id, rows, cols
    """
    os.makedirs(out_dir, exist_ok=True)

    # ID snapshot = hash cen (12 pierwszych znaków)
    snap_id = _hash_df(prices.fillna(0))[:12]
    base = os.path.join(out_dir, snap_id)

    # Zapisz 4 pliki parquet
    prices.to_parquet(base + "_adjclose.parquet")
    volume.to_parquet(base + "_volume.parquet")
    high.to_parquet(base + "_high.parquet")
    low.to_parquet(base + "_low.parquet")

    # Metadata
    meta = {
        "snapshot_id": snap_id,
        "rows": int(prices.shape[0]),
        "cols": int(prices.shape[1])
    }

    with open(base + "_meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    return meta
