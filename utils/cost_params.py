"""
Moduł cost_params: wybór k/γ per symbol na podstawie segmentacji.
"""
import os
import json
import numpy as np
import pandas as pd
from typing import Tuple, Optional


def _load_json(path: str) -> dict:
    """Ładuje JSON lub zwraca pusty dict."""
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)


def k_gamma_today(
    calib_json: str,
    spread_today: Optional[pd.Series],
    adv_today: Optional[pd.Series],
    default_k_bps: float,
    default_gamma: float
) -> Tuple[pd.Series, float]:
    """
    Zwraca k_bps per symbol i gamma scalar na podstawie kalibracji segmentowej.

    Args:
        calib_json: Ścieżka do JSON z kalibracją
        spread_today: Spread per symbol dziś
        adv_today: ADV per symbol dziś
        default_k_bps: Domyślne k (bps)
        default_gamma: Domyślne gamma

    Returns:
        Tuple (k_bps_series, gamma_scalar)
    """
    cfg = _load_json(calib_json)

    # Domyślne wartości
    if spread_today is not None:
        k_ser = pd.Series(default_k_bps, index=spread_today.index)
    elif adv_today is not None:
        k_ser = pd.Series(default_k_bps, index=adv_today.index)
    else:
        k_ser = pd.Series(dtype=float)

    gamma_vals = [default_gamma]

    # Segmentacja po spread_frac (tercyle)
    byb = cfg.get("by_bucket", {})
    if byb and byb.get("metric") == "spread_frac" and spread_today is not None:
        for b in byb.get("buckets", []):
            mask = (spread_today > b["edge_lo"]) & (spread_today <= b["edge_hi"])
            if "k_bps" in b:
                k_ser.loc[mask] = b["k_bps"]
            if b.get("gamma") is not None:
                gamma_vals.append(b["gamma"])

    gamma_scalar = float(np.median(gamma_vals))

    return k_ser.astype(float), gamma_scalar
