"""
Moduł do pracy z kalendarzem sesji giełdowych.
Używa pandas-market-calendars do obliczania forward returns po N sesjach.
"""
import pandas as pd
import numpy as np
from typing import Optional

try:
    import pandas_market_calendars as mcal
except ImportError:
    mcal = None
    print("OSTRZEŻENIE: pandas-market-calendars nie jest zainstalowany. Użyj: pip install pandas-market-calendars")


def compute_forward_returns_sessions(
    prices: pd.DataFrame,
    sessions_ahead: int,
    exchange: str = "XNYS"
) -> pd.DataFrame:
    """
    Oblicza forward returns po N sesjach giełdowych (nie dni kalendarzowych).

    Używa kalendarza giełdowego aby poprawnie obliczać zwroty pomijając
    weekendy i święta.

    Parameters:
    -----------
    prices : pd.DataFrame
        DataFrame z cenami (index: datetime, kolumny: tickery)
    sessions_ahead : int
        Liczba sesji naprzód (np. 21 = ~1 miesiąc)
    exchange : str
        Kod giełdy dla pandas-market-calendars (domyślnie XNYS = NYSE)

    Returns:
    --------
    pd.DataFrame
        DataFrame z forward returns
    """
    if mcal is None:
        # Fallback: użyj dni kalendarzowych zamiast sesji
        print(f"OSTRZEŻENIE: pandas-market-calendars niedostępny, używam {sessions_ahead} dni kalendarzowych")
        fwd_returns = prices.pct_change(sessions_ahead).shift(-sessions_ahead)
        return fwd_returns

    try:
        # Pobierz kalendarz giełdowy
        calendar = mcal.get_calendar(exchange)

        # Zakres dat
        start_date = prices.index.min()
        end_date = prices.index.max() + pd.Timedelta(days=365)  # Dodaj bufor

        # Pobierz sesje handlowe
        schedule = calendar.schedule(start_date=start_date, end_date=end_date)
        trading_days = schedule.index

        # Mapowanie: dla każdego dnia handlowego znajdź datę N sesji naprzód
        forward_map = {}
        trading_days_list = trading_days.tolist()

        for i, date in enumerate(trading_days_list):
            future_idx = i + sessions_ahead
            if future_idx < len(trading_days_list):
                forward_map[date] = trading_days_list[future_idx]

        # Oblicz forward returns
        fwd_returns = pd.DataFrame(index=prices.index, columns=prices.columns, dtype=float)

        for date in prices.index:
            # Znajdź najbliższą sesję handlową
            closest_session = trading_days[trading_days >= date]
            if len(closest_session) == 0:
                continue
            session = closest_session[0]

            if session in forward_map:
                future_session = forward_map[session]

                # Znajdź ceny
                if date in prices.index and future_session in prices.index:
                    current_prices = prices.loc[date]
                    future_prices = prices.loc[future_session]
                    fwd_returns.loc[date] = (future_prices / current_prices) - 1.0

        return fwd_returns

    except Exception as e:
        print(f"BŁĄD przy używaniu kalendarza {exchange}: {e}")
        print(f"Fallback: używam {sessions_ahead} dni kalendarzowych")
        fwd_returns = prices.pct_change(sessions_ahead).shift(-sessions_ahead)
        return fwd_returns


def get_trading_sessions(
    start_date: str,
    end_date: str,
    exchange: str = "XNYS"
) -> pd.DatetimeIndex:
    """
    Zwraca listę sesji handlowych dla danego zakresu.

    Parameters:
    -----------
    start_date : str
        Data początkowa (YYYY-MM-DD)
    end_date : str
        Data końcowa (YYYY-MM-DD)
    exchange : str
        Kod giełdy (domyślnie XNYS)

    Returns:
    --------
    pd.DatetimeIndex
        Indeks z datami sesji handlowych
    """
    if mcal is None:
        raise ImportError("pandas-market-calendars nie jest zainstalowany")

    calendar = mcal.get_calendar(exchange)
    schedule = calendar.schedule(start_date=start_date, end_date=end_date)
    return schedule.index
