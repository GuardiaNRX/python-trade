"""
Moduł do wczytywania danych cenowych z różnych źródeł.
"""
import os
from typing import List, Optional, Tuple
from datetime import datetime
import pandas as pd
import numpy as np
import yfinance as yf


def load_prices(
    universe: List[str],
    start: str,
    end: Optional[str] = None,
    source: str = "yfinance",
    csv_dir: str = "data"
) -> pd.DataFrame:
    """
    Wczytuje ceny dostosowane (Adj Close) dla zadanego uniwersum.
    
    Preferuje lokalne pliki CSV (kolumny: Date, Adj Close),
    w przypadku braku pobiera z yfinance i cache'uje.
    Stosuje forward fill dla brakujących wartości.
    
    Parameters:
    -----------
    universe : List[str]
        Lista symboli giełdowych
    start : str
        Data początkowa (YYYY-MM-DD)
    end : Optional[str]
        Data końcowa (YYYY-MM-DD), None = dzisiaj
    source : str
        Źródło danych ('yfinance')
    csv_dir : str
        Katalog z lokalnymi plikami CSV
        
    Returns:
    --------
    pd.DataFrame
        DataFrame z Adj Close (index: datetime, kolumny: tickery)
    """
    if end is None:
        end = datetime.now().strftime("%Y-%m-%d")
    
    prices = pd.DataFrame()
    
    for ticker in universe:
        csv_path = os.path.join(csv_dir, f"{ticker}.csv")
        
        try:
            # Próba wczytania z lokalnego CSV
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path, parse_dates=["Date"], index_col="Date")
                if "Adj Close" in df.columns:
                    prices[ticker] = df["Adj Close"]
                    print(f"Wczytano {ticker} z lokalnego CSV")
                    continue
            
            # Fallback do yfinance
            if source == "yfinance":
                print(f"Pobieranie {ticker} z yfinance...")
                data = yf.download(ticker, start=start, end=end, progress=False)
                if not data.empty and "Adj Close" in data.columns:
                    prices[ticker] = data["Adj Close"]
                    
                    # Cache do CSV
                    os.makedirs(csv_dir, exist_ok=True)
                    data.to_csv(csv_path)
                    print(f"Zapisano {ticker} do {csv_path}")
                else:
                    print(f"OSTRZEŻENIE: Brak danych dla {ticker}")
            
        except Exception as e:
            print(f"BŁĄD przy wczytywaniu {ticker}: {e}")
            continue
    
    if prices.empty:
        raise ValueError("Nie udało się wczytać żadnych danych cenowych")
    
    # Forward fill brakujących wartości
    prices = prices.ffill()
    
    # Filtruj zakres dat
    prices = prices.loc[start:end]

    return prices


def load_prices_and_volume(
    universe: List[str],
    start: str,
    end: Optional[str] = None,
    source: str = "yfinance",
    csv_dir: str = "data"
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Wczytuje ceny dostosowane (Adj Close) i Volume dla zadanego uniwersum.

    Preferuje lokalne pliki CSV (kolumny: Date, Adj Close, Volume),
    w przypadku braku pobiera z yfinance i cache'uje.
    Stosuje forward fill dla brakujących wartości.

    Parameters:
    -----------
    universe : List[str]
        Lista symboli giełdowych
    start : str
        Data początkowa (YYYY-MM-DD)
    end : Optional[str]
        Data końcowa (YYYY-MM-DD), None = dzisiaj
    source : str
        Źródło danych ('yfinance')
    csv_dir : str
        Katalog z lokalnymi plikami CSV

    Returns:
    --------
    Tuple[pd.DataFrame, pd.DataFrame]
        (prices, volume) - DataFrames z Adj Close i Volume
        (index: datetime, kolumny: tickery)
    """
    if end is None:
        end = datetime.now().strftime("%Y-%m-%d")

    prices = pd.DataFrame()
    volumes = pd.DataFrame()

    for ticker in universe:
        csv_path = os.path.join(csv_dir, f"{ticker}.csv")

        try:
            # Próba wczytania z lokalnego CSV
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path, parse_dates=["Date"], index_col="Date")
                if "Adj Close" in df.columns and "Volume" in df.columns:
                    prices[ticker] = df["Adj Close"]
                    volumes[ticker] = df["Volume"]
                    print(f"Wczytano {ticker} z lokalnego CSV")
                    continue

            # Fallback do yfinance
            if source == "yfinance":
                print(f"Pobieranie {ticker} z yfinance...")
                data = yf.download(ticker, start=start, end=end, progress=False)
                if not data.empty:
                    if "Adj Close" in data.columns:
                        prices[ticker] = data["Adj Close"]
                    if "Volume" in data.columns:
                        volumes[ticker] = data["Volume"]

                    # Cache do CSV
                    os.makedirs(csv_dir, exist_ok=True)
                    data.to_csv(csv_path)
                    print(f"Zapisano {ticker} do {csv_path}")
                else:
                    print(f"OSTRZEŻENIE: Brak danych dla {ticker}")

        except Exception as e:
            print(f"BŁĄD przy wczytywaniu {ticker}: {e}")
            continue

    if prices.empty:
        raise ValueError("Nie udało się wczytać żadnych danych cenowych")

    # Forward fill brakujących wartości
    prices = prices.ffill()
    volumes = volumes.ffill()

    # Filtruj zakres dat
    prices = prices.loc[start:end]
    volumes = volumes.loc[start:end]

    return prices, volumes


def load_ohlcv(
    universe: List[str],
    start: str,
    end: Optional[str] = None,
    source: str = "yfinance",
    csv_dir: str = "data"
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Wczytuje OHLCV (Open, High, Low, Close, Volume) dla zadanego uniwersum.

    Preferuje lokalne pliki CSV (kolumny: Date, Adj Close, Volume, High, Low),
    w przypadku braku pobiera z yfinance i cache'uje.
    Stosuje forward fill dla brakujących wartości.

    Parameters:
    -----------
    universe : List[str]
        Lista symboli giełdowych
    start : str
        Data początkowa (YYYY-MM-DD)
    end : Optional[str]
        Data końcowa (YYYY-MM-DD), None = dzisiaj
    source : str
        Źródło danych ('yfinance')
    csv_dir : str
        Katalog z lokalnymi plikami CSV

    Returns:
    --------
    Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]
        (adj_close, volume, high, low) - DataFrames z danymi OHLCV
        (index: datetime, kolumny: tickery)
    """
    if end is None:
        end = datetime.now().strftime("%Y-%m-%d")

    adj_close = pd.DataFrame()
    volumes = pd.DataFrame()
    highs = pd.DataFrame()
    lows = pd.DataFrame()

    for ticker in universe:
        csv_path = os.path.join(csv_dir, f"{ticker}.csv")

        try:
            # Próba wczytania z lokalnego CSV
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path, parse_dates=["Date"], index_col="Date")
                required_cols = ["Adj Close", "Volume", "High", "Low"]
                if all(col in df.columns for col in required_cols):
                    adj_close[ticker] = df["Adj Close"]
                    volumes[ticker] = df["Volume"]
                    highs[ticker] = df["High"]
                    lows[ticker] = df["Low"]
                    print(f"Wczytano {ticker} (OHLCV) z lokalnego CSV")
                    continue

            # Fallback do yfinance
            if source == "yfinance":
                print(f"Pobieranie {ticker} (OHLCV) z yfinance...")
                data = yf.download(ticker, start=start, end=end, progress=False)
                if not data.empty:
                    if "Adj Close" in data.columns:
                        adj_close[ticker] = data["Adj Close"]
                    if "Volume" in data.columns:
                        volumes[ticker] = data["Volume"]
                    if "High" in data.columns:
                        highs[ticker] = data["High"]
                    if "Low" in data.columns:
                        lows[ticker] = data["Low"]

                    # Cache do CSV
                    os.makedirs(csv_dir, exist_ok=True)
                    data.to_csv(csv_path)
                    print(f"Zapisano {ticker} do {csv_path}")
                else:
                    print(f"OSTRZEŻENIE: Brak danych dla {ticker}")

        except Exception as e:
            print(f"BŁĄD przy wczytywaniu {ticker}: {e}")
            continue

    if adj_close.empty:
        raise ValueError("Nie udało się wczytać żadnych danych cenowych")

    # Forward fill brakujących wartości
    adj_close = adj_close.ffill()
    volumes = volumes.ffill()
    highs = highs.ffill()
    lows = lows.ffill()

    # Filtruj zakres dat
    adj_close = adj_close.loc[start:end]
    volumes = volumes.loc[start:end]
    highs = highs.loc[start:end]
    lows = lows.loc[start:end]

    return adj_close, volumes, highs, lows


def eligibility_mask(
    prices: pd.DataFrame,
    volume: pd.DataFrame,
    min_price: float = 5.0,
    adv_window: int = 60,
    min_adv_usd: float = 1_000_000
) -> pd.DataFrame:
    """
    Tworzy dynamiczną maskę eligibilności per data (Point-in-Time).

    W przeciwieństwie do apply_liquidity_filters(), która filtruje kolumny
    na podstawie ostatniego stanu, ta funkcja zwraca bool DataFrame
    z wartością True dla każdego (data, ticker) spełniającego warunki:
    - Cena >= min_price
    - ADV USD (rolling mean(price * volume)) >= min_adv_usd

    Umożliwia to dynamiczny dobór uniwersum w czasie, unikając survivorship bias.

    Parameters:
    -----------
    prices : pd.DataFrame
        DataFrame z cenami (index: datetime, kolumny: tickery)
    volume : pd.DataFrame
        DataFrame z volume (index: datetime, kolumny: tickery)
    min_price : float
        Minimalny poziom ceny (domyślnie 5.0)
    adv_window : int
        Okno rolling dla ADV w dniach (domyślnie 60)
    min_adv_usd : float
        Minimalny średni dzienny wolumen w USD (domyślnie 1M)

    Returns:
    --------
    pd.DataFrame
        Bool DataFrame (index: datetime, kolumny: tickery)
        True = ticker jest eligible w danym dniu
    """
    # Oblicz ADV USD (rolling mean)
    dollar_volume = prices * volume
    adv_usd = dollar_volume.rolling(window=adv_window, min_periods=1).mean()

    # Maska per data
    price_ok = prices >= min_price
    adv_ok = adv_usd >= min_adv_usd
    eligible = price_ok & adv_ok

    # Wypełnij NaN jako False (nie eligible)
    eligible = eligible.fillna(False)

    return eligible


def apply_liquidity_filters(
    prices: pd.DataFrame,
    volume: pd.DataFrame,
    min_price: float = 5.0,
    adv_window: int = 60,
    min_adv_usd: float = 1_000_000
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Aplikuje filtry płynności na dane cenowe i volume.

    Filtruje aktywa na podstawie ostatniego stanu:
    - Cena >= min_price
    - ADV USD (rolling mean(price * volume)) >= min_adv_usd

    UWAGA: Ta funkcja stosuje statyczny filtr na podstawie ostatniego stanu.
    Do Point-in-Time eligibility użyj eligibility_mask().

    Parameters:
    -----------
    prices : pd.DataFrame
        DataFrame z cenami (index: datetime, kolumny: tickery)
    volume : pd.DataFrame
        DataFrame z volume (index: datetime, kolumny: tickery)
    min_price : float
        Minimalny poziom ceny (domyślnie 5.0)
    adv_window : int
        Okno rolling dla ADV w dniach (domyślnie 60)
    min_adv_usd : float
        Minimalny średni dzienny wolumen w USD (domyślnie 1M)

    Returns:
    --------
    Tuple[pd.DataFrame, pd.DataFrame]
        (filtered_prices, filtered_volume) - DataFrames po filtrach
    """
    # Oblicz ADV USD (rolling mean)
    dollar_volume = prices * volume
    adv_usd = dollar_volume.rolling(window=adv_window, min_periods=1).mean()

    # Ostatni stan
    last_prices = prices.iloc[-1]
    last_adv = adv_usd.iloc[-1]

    # Maska filtrów
    price_ok = last_prices >= min_price
    adv_ok = last_adv >= min_adv_usd
    passed_filter = price_ok & adv_ok

    # Tickery po filtrze
    valid_tickers = passed_filter[passed_filter].index.tolist()

    if not valid_tickers:
        raise ValueError("Żaden ticker nie przeszedł filtrów płynności")

    print(f"Filtry płynności: {len(prices.columns)} → {len(valid_tickers)} tickerów")
    print(f"  Odrzucone (cena < {min_price}): {(~price_ok).sum()}")
    print(f"  Odrzucone (ADV < {min_adv_usd:,.0f}): {(~adv_ok).sum()}")

    # Zwróć przefiltrowane
    filtered_prices = prices[valid_tickers]
    filtered_volume = volume[valid_tickers]

    return filtered_prices, filtered_volume
