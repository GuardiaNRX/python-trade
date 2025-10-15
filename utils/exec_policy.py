"""
Moduł polityki egzekucji: planowanie zleceń TWAP z limitami.
"""
import numpy as np
import pandas as pd


def plan_twap(
    delta_w: pd.Series,
    prices: pd.DataFrame,
    adv_usd: pd.DataFrame,
    spread: pd.DataFrame,
    equity: float,
    window_minutes: int = 60,
    slices: int = 6,
    adv_cap: float = 0.1,
    gamma: float = 0.25,
) -> pd.DataFrame:
    """
    Zwraca DataFrame z planem zleceń TWAP: slice_time, symbol, side, qty_usd, limit_price.
    """
    px = (
        prices.iloc[-1]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(method="ffill")
        .fillna(method="bfill")
        .fillna(0.0)
    )
    dollars = (delta_w.abs() * equity * px).fillna(0.0)

    adv_last = adv_usd.iloc[-1] if not adv_usd.empty else pd.Series(0.0, index=px.index)
    cap_base = adv_last.fillna(0.0)
    cap_dollars = (cap_base * adv_cap).fillna(0.0)
    dollars = dollars.clip(upper=cap_dollars)

    spr_last = spread.iloc[-1] if not spread.empty else pd.Series(dtype=float)

    rows = []
    for sym, total in dollars.items():
        total = float(total)
        if total <= 0:
            continue

        mid = float(px.get(sym, 0.0))
        if mid <= 0:
            continue

        per_slice = total / slices
        side = "BUY" if float(delta_w.get(sym, 0.0)) > 0 else "SELL"
        spr_val = float(spr_last.get(sym, 0.0))
        lim = mid * (1 + (gamma * spr_val) * (1 if side == "BUY" else -1))

        for i in range(slices):
            offset = pd.Timedelta(minutes=i * window_minutes // slices)
            tstamp = pd.Timestamp.utcnow().floor("min") + offset
            rows.append([tstamp, sym, side, per_slice, lim])

    return pd.DataFrame(rows, columns=["slice_time", "symbol", "side", "qty_usd", "limit_price"])
