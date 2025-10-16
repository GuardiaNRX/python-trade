"""
Moduł freshness-gate: sprawdza świeżość danych (fail-closed).
"""
from typing import Tuple

import pandas as pd
import pandas_market_calendars as mcal


def expected_last_session(
    exchange: str = "XNYS",
    asof: pd.Timestamp = None
) -> pd.Timestamp:
    """
    Zwraca oczekiwaną ostatnią sesję giełdy.

    Args:
        exchange: Kod giełdy (XNYS, XNAS, itp.)
        asof: Data odniesienia (domyślnie: dziś UTC)

    Returns:
        Timestamp ostatniej sesji
    """
    if asof is None:
        asof = pd.Timestamp.utcnow().normalize()
    else:
        asof = pd.Timestamp(asof)

    try:
        cal = mcal.get_calendar(exchange)
        sched = cal.schedule(
            start_date=asof - pd.Timedelta(days=10),
            end_date=asof + pd.Timedelta(days=1)
        )
        return pd.Timestamp(sched.index.max()).tz_localize(None)
    except Exception as e:
        print(f"⚠️  Błąd kalendarz {exchange}: {e}")
        # Fallback: poprzedni dzień roboczy
        return (asof - pd.tseries.offsets.BDay(1)).normalize()


def coverage_on_date(prices: pd.DataFrame, date: pd.Timestamp) -> float:
    """
    Oblicza pokrycie (% tickerów z danymi) na daną datę.

    Args:
        prices: DataFrame z cenami
        date: Data do sprawdzenia

    Returns:
        Frakcja tickerów z danymi (0.0 - 1.0)
    """
    row = prices.loc[prices.index >= date]
    if row.empty:
        return 0.0

    last = row.iloc[0]
    ok = last.notna().sum()
    return ok / len(last)


def assert_fresh(
    prices: pd.DataFrame,
    exchange: str = "XNYS",
    min_coverage: float = 0.95
) -> Tuple[pd.Timestamp, float, bool]:
    """
    Sprawdza świeżość danych (fail-closed).

    Args:
        prices: DataFrame z cenami
        exchange: Kod giełdy
        min_coverage: Minimalny wymagany % pokrycia

    Returns:
        Tuple (oczekiwana_sesja, pokrycie, czy_OK)
    """
    exp = expected_last_session(exchange)
    cov = coverage_on_date(prices, exp)
    return exp, cov, (cov >= min_coverage)
