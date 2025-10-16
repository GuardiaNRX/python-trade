"""
Moduł universe drift: wykrywa dodane/usunięte tickery day-over-day.
"""
from typing import Dict, List, Union

import pandas as pd


def universe_drift(
    today_mask: Union[pd.Series, pd.DataFrame],
    yday_mask: Union[pd.Series, pd.DataFrame]
) -> Dict[str, Union[int, List[str]]]:
    """
    Porównuje eligible tickery dziś vs wczoraj.

    Args:
        today_mask: Maska eligible dziś (Series lub DataFrame)
        yday_mask: Maska eligible wczoraj (Series lub DataFrame)

    Returns:
        Dict z: n_added, n_removed, added (lista), removed (lista)
    """
    # Konwertuj do Series jeśli DataFrame
    t = today_mask.astype(bool)
    y = yday_mask.astype(bool)

    if hasattr(t, "to_frame"):
        t = t.iloc[0] if t.ndim > 1 else t

    if hasattr(y, "to_frame"):
        y = y.iloc[0] if y.ndim > 1 else y

    # Zrównaj indeksy
    common_idx = t.index.union(y.index)
    t = t.reindex(common_idx, fill_value=False)
    y = y.reindex(common_idx, fill_value=False)

    added = t.index[t & ~y].tolist()
    removed = t.index[~t & y].tolist()

    return {
        "n_added": len(added),
        "n_removed": len(removed),
        "added": added,
        "removed": removed
    }
