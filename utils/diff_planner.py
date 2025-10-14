"""
Moduł diff_planner: oblicza deltę między target a broker state.
"""
import pandas as pd


def delta_from_positions(
    target_w: pd.Series,
    broker_qty: pd.Series,
    last_px: pd.Series,
    equity: float
) -> pd.Series:
    """
    Oblicza różnicę USD między target weights a broker positions.

    Args:
        target_w: Target weights (frakcja kapitału)
        broker_qty: Broker quantities (liczba sztuk)
        last_px: Ostatnie ceny
        equity: Kapitał całkowity

    Returns:
        Seria delta USD (dodatnie = kupuj, ujemne = sprzedaj)
    """
    target_dollars = (target_w * equity).reindex(last_px.index).fillna(0.0)
    broker_dollars = (broker_qty.reindex(last_px.index).fillna(0.0) * last_px)
    delta_dollars = target_dollars - broker_dollars

    return delta_dollars
