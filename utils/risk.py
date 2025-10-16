"""
Moduł zarządzania ryzykiem: vol-targeting i drawdown clamp.
"""
from typing import Literal

import numpy as np
import pandas as pd


def ewma_vol(series: pd.Series, halflife: int = 20) -> pd.Series:
    """
    Oblicza EWMA volatility dla serii zwrotów.

    Args:
        series: Seria zwrotów
        halflife: Półokres EWMA

    Returns:
        Seria volatility
    """
    return series.ewm(halflife=halflife).std()


def scale_to_target(
    port_ret: pd.Series,
    target_vol: float = 0.10,
    freq: Literal["D", "W", "M"] = "D",
    halflife: int = 20,
    min_leverage: float = 0.5,
    max_leverage: float = 2.0
) -> pd.Series:
    """
    Skaluje wagi portfela do docelowej volatility.

    Args:
        port_ret: Seria zwrotów portfela
        target_vol: Docelowa volatility (annualized)
        freq: Częstotliwość (D=dzienne, W=tygodniowe, M=miesięczne)
        halflife: Półokres EWMA
        min_leverage: Minimalny leverage
        max_leverage: Maksymalny leverage

    Returns:
        Seria mnożników leverage
    """
    ann = {"D": 252, "W": 52, "M": 12}[freq.upper()]
    rv = ewma_vol(port_ret, halflife=halflife) * np.sqrt(ann)
    lev = (target_vol / rv).clip(lower=min_leverage, upper=max_leverage).shift(1).fillna(1.0)
    return lev


def dd_clamp(
    equity_curve: pd.Series,
    dd_soft: float = 0.08,
    dd_hard: float = 0.12
) -> pd.Series:
    """
    Linearnie redukuje ekspozycję przy drawdown.

    Args:
        equity_curve: Seria krzywej equity
        dd_soft: Próg soft DD (zaczyna redukcję)
        dd_hard: Próg hard DD (full clamp)

    Returns:
        Seria mnożników (1.0 = brak redukcji, 0.0 = full clamp)
    """
    peak = equity_curve.cummax()
    dd = equity_curve / peak - 1.0

    k = (dd - (-dd_soft)) / (dd_hard - dd_soft)
    clamp = (1 - k).clip(lower=0.0, upper=1.0)
    clamp[dd > -dd_soft] = 1.0

    return clamp
