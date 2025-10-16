"""
ModuĹ‚ kalibracji kosztĂłw: porĂłwnanie modeled vs realized slippage.
"""
import json
import os
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd


def calibrate_costs(
    fills_csv: str,
    out_json: str = "backtests/results/calibration.json",
    ew_halflife_days: int = 14
) -> Optional[Dict[str, Any]]:
    """
    Kalibruje koszty na podstawie realized fills (paper/live).

    Args:
        fills_csv: CSV z wykonanymi zleceniami (ts, symbol, side, exec_price, mid_price, adv_usd, notional)
        out_json: ĹšcieĹĽka do JSON z rekomendacjami
        ew_halflife_days: PĂłĹ‚okres EWMA

    Returns:
        Dict z rekomendacjami: k_bps_recommended, gamma_recommended
    """
    _ = ew_halflife_days  # placeholder for future EWMA weighting
    if not os.path.exists(fills_csv):
        return None

    df = pd.read_csv(fills_csv, parse_dates=["ts"])

    # Slip fraction: (exec - mid) / mid * sign(side)
    df["slip_frac"] = (
        (df["exec_price"] - df["mid_price"]) / df["mid_price"]
        * np.where(df["side"].str.upper() == "BUY", 1, -1)
    )

    # Estymacja k_bps wzglÄ™dem sqrt(notional/ADV)
    ratio = (df["notional"] / df["adv_usd"]).clip(lower=1e-9)
    x = np.sqrt(ratio)
    k_est = (df["slip_frac"].mean() / x.mean()) * 1e4  # bps

    # Estymacja gamma ~ Ĺ›rednia |slip| / (spread/2)
    if "spread_frac" in df.columns:
        gamma_est = (df["slip_frac"].abs() / (df["spread_frac"] / 2).replace(0, np.nan)).median()
    else:
        gamma_est = np.nan

    rec = {
        "k_bps_recommended": float(max(1.0, k_est)),
        "gamma_recommended": None if np.isnan(gamma_est) else float(min(max(gamma_est, 0.1), 1.0))
    }

    # Segmentacja per tercyle spreadu (tight/mid/wide)
    if "spread_frac" in df.columns and df["spread_frac"].notna().any():
        q1, q2 = df["spread_frac"].quantile([1/3, 2/3])
        buckets = []

        for name, lo, hi in [("tight", -np.inf, q1), ("mid", q1, q2), ("wide", q2, np.inf)]:
            sub = df[(df["spread_frac"] > lo) & (df["spread_frac"] <= hi)]
            if len(sub) >= 10:
                ratio_sub = (sub["notional"] / sub["adv_usd"]).clip(lower=1e-9)
                x_sub = np.sqrt(ratio_sub)
                k_b = (sub["slip_frac"].mean() / x_sub.mean()) * 1e4
                g_b = (sub["slip_frac"].abs() / (sub["spread_frac"] / 2).replace(0, np.nan)).median()

                buckets.append({
                    "name": name,
                    "k_bps": float(max(1.0, k_b)),
                    "gamma": float(min(max(g_b, 0.1), 1.0)) if np.isfinite(g_b) else None,
                    "edge_lo": float(lo),
                    "edge_hi": float(hi)
                })

        if buckets:
            rec["by_bucket"] = {
                "metric": "spread_frac",
                "buckets": buckets
            }

    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, "w") as f:
        json.dump(rec, f, indent=2)

    return rec


def update_calibration_history(
    rec: Dict[str, Any],
    modeled_bps: float,
    realized_bps: float,
    hist_path: str = "backtests/results/calibration_history.csv"
) -> None:
    """
    Dopisuje rekord do historii kalibracji (trend modeled vs realized).

    Args:
        rec: Dict z rekomendacjami (k_rec, gamma_rec)
        modeled_bps: Modelowany koszt (bps)
        realized_bps: Realized koszt z fills (bps)
        hist_path: ĹšcieĹĽka do CSV historii
    """
    row = {
        "date": pd.Timestamp.utcnow().date().isoformat(),
        "modeled_bps": modeled_bps,
        "realized_bps": realized_bps,
        "k_rec": rec.get("k_bps_recommended"),
        "gamma_rec": rec.get("gamma_recommended")
    }

    df = pd.DataFrame([row])
    header = not os.path.exists(hist_path)
    df.to_csv(hist_path, mode="a", index=False, header=header)
