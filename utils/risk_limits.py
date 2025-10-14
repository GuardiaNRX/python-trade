"""
Moduł hard-limits: turnover, exposure, single-name + kill-switch.
"""
import numpy as np
import pandas as pd


def enforce_gross_limit(weights: pd.DataFrame, max_gross: float = 1.5) -> pd.DataFrame:
    """
    Ogranicza gross exposure (suma abs wag).

    Args:
        weights: DataFrame z wagami portfela
        max_gross: Maksymalna gross exposure

    Returns:
        DataFrame z ograniczonymi wagami
    """
    gross = weights.abs().sum(axis=1)
    scale = (max_gross / gross).clip(upper=1.0).fillna(1.0)
    return (weights.T * scale).T


def enforce_single_name_limit(weights: pd.DataFrame, max_name: float = 0.10) -> pd.DataFrame:
    """
    Ogranicza wagę pojedynczego tickera.

    Args:
        weights: DataFrame z wagami portfela
        max_name: Maksymalna waga pojedynczego tickera (frakcja)

    Returns:
        DataFrame z ograniczonymi wagami
    """
    return weights.clip(upper=max_name, lower=-max_name)


def turnover_series(weights: pd.DataFrame) -> pd.Series:
    """
    Oblicza dzienną serię turnover (suma abs zmian wag).

    Args:
        weights: DataFrame z wagami portfela

    Returns:
        Seria turnover
    """
    return weights.diff().abs().sum(axis=1).fillna(0.0)


def limit_turnover(weights: pd.DataFrame, max_turnover: float = 0.30) -> pd.DataFrame:
    """
    Ogranicza turnover per dzień poprzez skalowanie zmian wag.

    Args:
        weights: DataFrame z wagami portfela
        max_turnover: Maksymalny turnover (frakcja)

    Returns:
        DataFrame z ograniczonym turnover
    """
    to = turnover_series(weights)
    scale = (max_turnover / to).clip(upper=1.0).replace([np.inf, -np.inf], 1.0).fillna(1.0)
    adj = (weights.diff().T * scale).T.fillna(0.0)
    w0 = weights.shift(1).fillna(0.0)
    return (w0 + adj).clip(-1.0, 1.0)


def kill_switch_by_drawdown(port_ret: pd.Series, dd_hard: float = 0.15) -> bool:
    """
    Kill-switch: sprawdza, czy drawdown przekroczył próg hard.

    Args:
        port_ret: Seria zwrotów portfela
        dd_hard: Hard drawdown threshold

    Returns:
        True jeśli kill-switch zadziałał
    """
    eq = (1 + port_ret.fillna(0)).cumprod()
    dd = (eq / eq.cummax() - 1.0).min()
    return dd <= -abs(dd_hard)
