"""
Moduł polityki egzekucji: planowanie zleceń TWAP z limitami.
"""
import pandas as pd
import numpy as np
from typing import Optional


def plan_twap(
    delta_w: pd.Series,
    prices: pd.DataFrame,
    adv_usd: pd.DataFrame,
    spread: pd.DataFrame,
    equity: float,
    window_minutes: int = 60,
    slices: int = 6,
    adv_cap: float = 0.1,
    gamma: float = 0.25
) -> pd.DataFrame:
    """
    Zwraca DataFrame z planem zleceń TWAP: slice_time, symbol, side, qty_usd, limit_price.

    Args:
        delta_w: Seria zmian wag (docelowa - poprzednia) per symbol
        prices: DataFrame z cenami
        adv_usd: Average Daily Volume w USD
        spread: Spread bid-ask (frakcja)
        equity: Kapitał (equity) do alokacji
        window_minutes: Okno czasowe TWAP w minutach
        slices: Liczba kroków TWAP
        adv_cap: Cap na % ADV per dzień
        gamma: Mnożnik spreadu dla limitu cenowego

    Returns:
        DataFrame z kolumnami: slice_time, symbol, side, qty_usd, limit_price
    """
    # Docelowa kwota USD do przesunięcia na symbol
    dollars = (delta_w.abs() * equity * prices.iloc[-1]).fillna(0.0)

    # Cap per dzień
    cap_dollars = (adv_usd.iloc[-1] * adv_cap).fillna(0.0)
    dollars = dollars.clip(upper=cap_dollars)

    rows = []
    for sym in dollars.index:
        total = float(dollars[sym])
        if total <= 0:
            continue

        per_slice = total / slices
        side = "BUY" if delta_w[sym] > 0 else "SELL"
        mid = float(prices.iloc[-1][sym])

        # Limit price: mid ± γ·spread
        spr = float(spread.iloc[-1].get(sym, 0.0))
        lim = mid * (1 + (gamma * spr) * (1 if side == "BUY" else -1))

        for i in range(slices):
            t = pd.Timestamp.utcnow().floor("min") + pd.Timedelta(minutes=i * window_minutes // slices)
            rows.append([t, sym, side, per_slice, lim])

    return pd.DataFrame(rows, columns=["slice_time", "symbol", "side", "qty_usd", "limit_price"])
