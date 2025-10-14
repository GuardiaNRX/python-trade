"""
Moduł map_sanity: walidacja symbol→exchange/region mapping.
"""
import pandas as pd
import pandas_market_calendars as mcal
from typing import List


def validate_mapping(mapping: pd.DataFrame, symbols: List[str]) -> List[str]:
    """
    Waliduje mapę symbol→exchange→region.

    Args:
        mapping: DataFrame z kolumnami [symbol, exchange, region]
        symbols: Lista symboli do walidacji

    Returns:
        Lista błędów walidacji (pusta = OK)
    """
    errs = []

    # Sprawdź kolumny
    if not {"symbol", "exchange", "region"}.issubset(set(mapping.columns)):
        errs.append("mapping musi zawierać kolumny: symbol, exchange, region")
        return errs

    # Pokrycie
    miss = sorted(set(symbols) - set(mapping["symbol"]))
    if miss:
        errs.append(f"brak mapy dla {len(miss)} symboli (np. {', '.join(miss[:5])}...)")

    # Duplikaty
    dups = mapping["symbol"][mapping["symbol"].duplicated()].unique().tolist()
    if dups:
        errs.append(f"duplikaty symboli w mapie: {', '.join(map(str, dups[:5]))}...")

    # Exchange znane w mcal
    uniq_ex = mapping["exchange"].unique().tolist()
    for ex in uniq_ex:
        try:
            mcal.get_calendar(ex)
        except Exception:
            errs.append(f"nieznany exchange w pandas_market_calendars: {ex}")

    return errs
