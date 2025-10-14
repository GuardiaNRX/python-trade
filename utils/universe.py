"""
Moduł zarządzania wszechświatem tickerów: filtry płynności i eligibility per date.
"""
import pandas as pd
from typing import Optional


def eligible_mask_per_date(
    prices: pd.DataFrame,
    volume: pd.DataFrame,
    min_price: float,
    adv_window: int,
    min_adv_usd: float
) -> pd.DataFrame:
    """
    Tworzy maskę eligible (True/False) per data i symbol na podstawie kryteriów płynności.

    Args:
        prices: DataFrame z cenami (index=date, columns=symbols)
        volume: DataFrame z wolumenem
        min_price: Minimalna cena (np. 5.0)
        adv_window: Okno rolling dla ADV (dni)
        min_adv_usd: Minimalny ADV w USD

    Returns:
        DataFrame boolean (True = eligible)
    """
    adv_usd = (prices * volume).rolling(adv_window).mean()
    mask = (prices >= min_price) & (adv_usd >= min_adv_usd)
    return mask.astype(bool)


def birth_death_mask(
    prices: pd.DataFrame,
    min_days_from_ipo: int = 60
) -> pd.DataFrame:
    """
    Tworzy maskę uwzględniającą daty IPO i delistingu.

    Args:
        prices: DataFrame z cenami
        min_days_from_ipo: Minimalna liczba dni handlowych od pierwszej obserwacji

    Returns:
        DataFrame boolean (True = symbol aktywny)
    """
    first_seen = prices.apply(lambda s: s.first_valid_index())
    birth_ok = pd.DataFrame(index=prices.index, columns=prices.columns, data=False)

    for c in prices.columns:
        if first_seen[c] is None:
            continue
        # Dodaj offset w dniach handlowych
        birth_ok.loc[
            prices.index >= (first_seen[c] + pd.tseries.offsets.BDay(min_days_from_ipo)), c
        ] = True

    # Death = brak dalszych notowań → maska False po ostatniej dacie notowanej
    last_seen = prices.apply(lambda s: s.last_valid_index())
    for c in prices.columns:
        if last_seen[c] is None:
            continue
        birth_ok.loc[prices.index > last_seen[c], c] = False

    return birth_ok
