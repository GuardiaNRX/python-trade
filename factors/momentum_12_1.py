"""
Moduł obliczający faktor momentum 12-1.
"""
import pandas as pd
import numpy as np


def compute_factor(
    prices: pd.DataFrame,
    lookback_months: int = 12,
    skip_recent_months: int = 1
) -> pd.DataFrame:
    """
    Oblicza faktor momentum 12-1 (zwrot z ostatnich 12 miesięcy, pomijając ostatni miesiąc).
    
    Formuła: (cena[t] / cena[t-12m+1m]) - 1
    
    Parameters:
    -----------
    prices : pd.DataFrame
        DataFrame z cenami (index: datetime, kolumny: tickery)
    lookback_months : int
        Okres lookback w miesiącach (domyślnie 12)
    skip_recent_months : int
        Liczba ostatnich miesięcy do pominięcia (domyślnie 1)
        
    Returns:
    --------
    pd.DataFrame
        DataFrame z wartościami faktora
    """
    # Konwersja miesięcy na dni (przybliżenie: 21 dni handlowych = 1 miesiąc)
    lookback_days = lookback_months * 21
    skip_days = skip_recent_months * 21
    
    # Oblicz momentum: (P[t-skip] / P[t-lookback]) - 1
    prices_lagged = prices.shift(skip_days)
    prices_start = prices.shift(lookback_days)
    
    momentum = (prices_lagged / prices_start) - 1.0
    
    return momentum


def percentile_rank(df: pd.DataFrame) -> pd.DataFrame:
    """
    Oblicza percentylowe rankingi cross-section na każdy dzień.
    
    Dla każdej daty, ranguje wszystkie tickery od 0 do 1.
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame z wartościami (index: datetime, kolumny: tickery)
        
    Returns:
    --------
    pd.DataFrame
        DataFrame z rankingami percentylowymi (0-1)
    """
    # Rank per row (date), normalize to 0-1
    ranks = df.rank(axis=1, method='average', pct=True)
    return ranks
