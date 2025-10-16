"""
ModuĹ‚ do wczytywania danych cenowych z rĂłĹĽnych ĹşrĂłdeĹ‚.
"""
import os
from datetime import datetime
from typing import List, Optional, Tuple

import pandas as pd
import yfinance as yf


def load_prices(
    universe: List[str],
    start: str,
    end: Optional[str] = None,
    source: str = "yfinance",
    csv_dir: Optional[str] = "data",
) -> pd.DataFrame:
    """Load adjusted close prices for the universe."""
    if end is None:
        end = datetime.now().strftime("%Y-%m-%d")

    cache_dir = csv_dir if csv_dir else None
    prices = pd.DataFrame()

    for ticker in universe:
        csv_path = os.path.join(cache_dir, f"{ticker}.csv") if cache_dir else None
        try:
            if csv_path and os.path.exists(csv_path):
                df = pd.read_csv(csv_path, parse_dates=["Date"], index_col="Date")
                if "Adj Close" in df.columns:
                    prices[ticker] = df["Adj Close"]
                    print(f"Loaded {ticker} from cache")
                    continue

            if source.lower() == "yfinance":
                print(f"Downloading {ticker} from yfinance...")
                data = yf.download(ticker, start=start, end=end, progress=False)
                if not data.empty and "Adj Close" in data.columns:
                    series = None
                if not data.empty:
                    if "Adj Close" in data.columns:
                        series = data["Adj Close"]
                    elif "Close" in data.columns:
                        series = data["Close"]
                    if series is not None:
                        prices[ticker] = series
                        if cache_dir:
                            os.makedirs(cache_dir, exist_ok=True)
                            data.to_csv(csv_path)
                            print(f"Cached {ticker} to {csv_path}")
                    else:
                        print(f"WARNING: no price column for {ticker}")
                else:
                    print(f"WARNING: no data for {ticker}")

        except Exception as exc:
            print(f"ERROR loading {ticker}: {exc}")
            continue

    if prices.empty:
        raise ValueError("No price data loaded")

    prices = prices.ffill().loc[start:end]
    return prices



def load_prices_and_volume(
    universe: List[str],
    start: str,
    end: Optional[str] = None,
    source: str = "yfinance",
    csv_dir: Optional[str] = "data",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load adjusted close and volume for the universe."""
    if end is None:
        end = datetime.now().strftime("%Y-%m-%d")

    cache_dir = csv_dir if csv_dir else None
    prices = pd.DataFrame()
    volumes = pd.DataFrame()

    for ticker in universe:
        csv_path = os.path.join(cache_dir, f"{ticker}.csv") if cache_dir else None
        try:
            if csv_path and os.path.exists(csv_path):
                df = pd.read_csv(csv_path, parse_dates=["Date"], index_col="Date")
                if {"Adj Close", "Volume"}.issubset(df.columns):
                    prices[ticker] = df["Adj Close"]
                    volumes[ticker] = df["Volume"]
                    print(f"Loaded {ticker} (price+vol) from cache")
                    continue

            if source.lower() == "yfinance":
                print(f"Downloading {ticker} (price+vol) from yfinance...")
                data = yf.download(ticker, start=start, end=end, progress=False)
                if not data.empty:
                    price_series = None
                    if "Adj Close" in data.columns:
                        price_series = data["Adj Close"]
                    elif "Close" in data.columns:
                        price_series = data["Close"]
                    if price_series is not None:
                        prices[ticker] = price_series
                    if "Volume" in data.columns:
                        volumes[ticker] = data["Volume"]
                    if cache_dir:
                        os.makedirs(cache_dir, exist_ok=True)
                        data.to_csv(csv_path)
                        print(f"Cached {ticker} to {csv_path}")
                else:
                    print(f"WARNING: no data for {ticker}")

        except Exception as exc:
            print(f"ERROR loading {ticker}: {exc}")
            continue

    if prices.empty:
        raise ValueError("No price data loaded")

    prices = prices.ffill().loc[start:end]
    volumes = volumes.ffill().loc[start:end]
    return prices, volumes



def load_ohlcv(
    universe: List[str],
    start: str,
    end: Optional[str] = None,
    source: str = "yfinance",
    csv_dir: Optional[str] = "data",
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load OHLCV for the universe."""
    if end is None:
        end = datetime.now().strftime("%Y-%m-%d")

    cache_dir = csv_dir if csv_dir else None
    adj_close = pd.DataFrame()
    volumes = pd.DataFrame()
    highs = pd.DataFrame()
    lows = pd.DataFrame()

    for ticker in universe:
        csv_path = os.path.join(cache_dir, f"{ticker}.csv") if cache_dir else None
        try:
            if csv_path and os.path.exists(csv_path):
                df = pd.read_csv(csv_path, parse_dates=["Date"], index_col="Date")
                required_cols = ["Adj Close", "Volume", "High", "Low"]
                if all(col in df.columns for col in required_cols):
                    adj_close[ticker] = df["Adj Close"]
                    volumes[ticker] = df["Volume"]
                    highs[ticker] = df["High"]
                    lows[ticker] = df["Low"]
                    print(f"Loaded {ticker} (OHLCV) from cache")
                    continue

            if source.lower() == "yfinance":
                print(f"Downloading {ticker} (OHLCV) from yfinance...")
                data = yf.download(ticker, start=start, end=end, progress=False)
                if not data.empty:
                    price_series = None
                    if "Adj Close" in data.columns:
                        price_series = data["Adj Close"]
                    elif "Close" in data.columns:
                        price_series = data["Close"]
                    if price_series is not None:
                        adj_close[ticker] = price_series
                    if "Volume" in data.columns:
                        volumes[ticker] = data["Volume"]
                    if "High" in data.columns:
                        highs[ticker] = data["High"]
                    if "Low" in data.columns:
                        lows[ticker] = data["Low"]
                    if cache_dir:
                        os.makedirs(cache_dir, exist_ok=True)
                        data.to_csv(csv_path)
                        print(f"Cached {ticker} to {csv_path}")
                else:
                    print(f"WARNING: no data for {ticker}")

        except Exception as exc:
            print(f"ERROR loading {ticker}: {exc}")
            continue

    if adj_close.empty:
        raise ValueError("No OHLCV data loaded")

    adj_close = adj_close.ffill().loc[start:end]
    volumes = volumes.ffill().loc[start:end]
    highs = highs.ffill().loc[start:end]
    lows = lows.ffill().loc[start:end]
    return adj_close, volumes, highs, lows



def eligibility_mask(
    prices: pd.DataFrame,
    volume: pd.DataFrame,
    min_price: float = 5.0,
    adv_window: int = 60,
    min_adv_usd: float = 1_000_000
) -> pd.DataFrame:
    """
    Tworzy dynamicznÄ… maskÄ™ eligibilnoĹ›ci per data (Point-in-Time).

    W przeciwieĹ„stwie do apply_liquidity_filters(), ktĂłra filtruje kolumny
    na podstawie ostatniego stanu, ta funkcja zwraca bool DataFrame
    z wartoĹ›ciÄ… True dla kaĹĽdego (data, ticker) speĹ‚niajÄ…cego warunki:
    - Cena >= min_price
    - ADV USD (rolling mean(price * volume)) >= min_adv_usd

    UmoĹĽliwia to dynamiczny dobĂłr uniwersum w czasie, unikajÄ…c survivorship bias.

    Parameters:
    -----------
    prices : pd.DataFrame
        DataFrame z cenami (index: datetime, kolumny: tickery)
    volume : pd.DataFrame
        DataFrame z volume (index: datetime, kolumny: tickery)
    min_price : float
        Minimalny poziom ceny (domyĹ›lnie 5.0)
    adv_window : int
        Okno rolling dla ADV w dniach (domyĹ›lnie 60)
    min_adv_usd : float
        Minimalny Ĺ›redni dzienny wolumen w USD (domyĹ›lnie 1M)

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

    # WypeĹ‚nij NaN jako False (nie eligible)
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
    Aplikuje filtry pĹ‚ynnoĹ›ci na dane cenowe i volume.

    Filtruje aktywa na podstawie ostatniego stanu:
    - Cena >= min_price
    - ADV USD (rolling mean(price * volume)) >= min_adv_usd

    UWAGA: Ta funkcja stosuje statyczny filtr na podstawie ostatniego stanu.
    Do Point-in-Time eligibility uĹĽyj eligibility_mask().

    Parameters:
    -----------
    prices : pd.DataFrame
        DataFrame z cenami (index: datetime, kolumny: tickery)
    volume : pd.DataFrame
        DataFrame z volume (index: datetime, kolumny: tickery)
    min_price : float
        Minimalny poziom ceny (domyĹ›lnie 5.0)
    adv_window : int
        Okno rolling dla ADV w dniach (domyĹ›lnie 60)
    min_adv_usd : float
        Minimalny Ĺ›redni dzienny wolumen w USD (domyĹ›lnie 1M)

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

    # Maska filtrĂłw
    price_ok = last_prices >= min_price
    adv_ok = last_adv >= min_adv_usd
    passed_filter = price_ok & adv_ok

    # Tickery po filtrze
    valid_tickers = passed_filter[passed_filter].index.tolist()

    if not valid_tickers:
        raise ValueError("Ĺ»aden ticker nie przeszedĹ‚ filtrĂłw pĹ‚ynnoĹ›ci")

    print(f"Filtry pĹ‚ynnoĹ›ci: {len(prices.columns)} â†’ {len(valid_tickers)} tickerĂłw")
    print(f"  Odrzucone (cena < {min_price}): {(~price_ok).sum()}")
    print(f"  Odrzucone (ADV < {min_adv_usd:,.0f}): {(~adv_ok).sum()}")

    # ZwrĂłÄ‡ przefiltrowane
    filtered_prices = prices[valid_tickers]
    filtered_volume = volume[valid_tickers]

    return filtered_prices, filtered_volume
