"""
Moduł robust spread: Corwin-Schultz spread z sanity checks na HL outliers.
"""
import numpy as np
import pandas as pd
from typing import Tuple
from .impact import corwin_schultz_spread


def robust_cs_spread(
    high: pd.DataFrame,
    low: pd.DataFrame,
    volume: pd.DataFrame,
    window: int = 2,
    sanity_sigma: float = 5.0,
    median_window: int = 20,
    fallback_bps: float = 25.0
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Robust Corwin-Schultz spread z outlier detection i fallbacks.

    Args:
        high: DataFrame High
        low: DataFrame Low
        volume: DataFrame Volume
        window: Okno CS (dni)
        sanity_sigma: Sigma dla outlier detection
        median_window: Okno rolling median
        fallback_bps: Fallback spread (bps)

    Returns:
        Tuple (spread_frac, outlier_mask)
    """
    # Wstępny CS
    cs = corwin_schultz_spread(high, low, window=window)

    # Log-range sanity
    logrng = (np.log(high) - np.log(low)).abs()
    rng_mu = logrng.rolling(median_window, min_periods=5).median()
    rng_sd = logrng.rolling(median_window, min_periods=5).std()
    vol_zero = (volume <= 0) | volume.isna()

    outlier = (logrng > (rng_mu + sanity_sigma * rng_sd)) & vol_zero
    cs = cs.mask(outlier)  # NaN zamiast podejrzanych wycen

    # Fallback 1: rolling median
    cs_med = cs.rolling(median_window, min_periods=5).median()
    cs = cs.fillna(cs_med)

    # Fallback 2: cross-sectional median
    cs = cs.apply(lambda row: row.fillna(row.median()), axis=1)

    # Fallback 3: stała
    cs = cs.fillna(fallback_bps / 1e4)

    # Clamp rozsądny zakres (0–5%)
    cs = cs.clip(lower=0.0, upper=0.05)

    return cs, outlier.fillna(False)
