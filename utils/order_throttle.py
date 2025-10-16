"""
Moduł throttle zleceń: limity na liczbę, notional, per-symbol + greylista.
"""
from typing import Optional, Set

import pandas as pd


def apply_throttle(
    plan: pd.DataFrame,
    max_orders: int = 100,
    max_notional: float = 1_000_000,
    max_per_symbol: float = 100_000,
    greylist: Optional[Set[str]] = None
) -> pd.DataFrame:
    """
    Aplikuje limity na plan zleceń.

    Args:
        plan: DataFrame z planem zleceń (kolumny: symbol, qty_usd, ...)
        max_orders: Maksymalna liczba zleceń
        max_notional: Maksymalna suma USD w batch
        max_per_symbol: Maksymalna kwota USD per symbol
        greylist: Set symboli do pominięcia

    Returns:
        DataFrame z ograniczonym planem
    """
    p = plan.copy()

    # Usuń symbole z greylisty
    if greylist:
        p = p[~p["symbol"].isin(greylist)]

    # Per-symbol clamp
    p["qty_usd"] = p.groupby("symbol")["qty_usd"].transform(
        lambda s: s.clip(upper=max_per_symbol / max(1, len(s)))
    )

    # Global clamp: weź top N po qty_usd
    p = p.sort_values("qty_usd", ascending=False).head(max_orders)

    # Skaluj jeśli suma przekracza max_notional
    if p["qty_usd"].sum() > max_notional:
        scale = max_notional / p["qty_usd"].sum()
        p["qty_usd"] *= scale

    return p.sort_values(["slice_time", "symbol"]) if "slice_time" in p.columns else p.sort_values("symbol")
