"""
Moduł HTTP cache dla yfinance: cache + retry + timeout.
"""
import os
import time
from typing import List, Optional, Tuple

import pandas as pd


def _cache_dir() -> str:
    """Zwraca katalog cache."""
    d = "data/http_cache"
    os.makedirs(d, exist_ok=True)
    return d


def _sym_path(sym: str) -> str:
    """Zwraca ścieżkę cache dla symbolu."""
    return os.path.join(_cache_dir(), f"{sym}.parquet")


def _fetch_yf(sym: str, start: Optional[str], end: Optional[str], timeout: int = 15) -> pd.DataFrame:
    """
    Fetch z yfinance.

    Args:
        sym: Symbol
        start: Data początkowa
        end: Data końcowa
        timeout: Timeout (obecnie nieużywany przez yfinance API)

    Returns:
        DataFrame OHLCV
    """
    import yfinance as yf
    _ = timeout  # placeholder until yfinance exposes timeout
    # yfinance nie ma bezpośredniego timeoutu; rely on underlying requests default
    return yf.Ticker(sym).history(start=start, end=end, auto_adjust=False)


def get_ohlcv_yf(
    symbols: List[str],
    start: Optional[str],
    end: Optional[str],
    retries: int = 2,
    backoff: float = 1.5
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Pobiera OHLCV z yfinance z cache i retry.

    Args:
        symbols: Lista symboli
        start: Data początkowa
        end: Data końcowa
        retries: Liczba prób
        backoff: Mnożnik backoff

    Returns:
        Tuple (prices, volume, high, low)
    """
    px, vol, hi, lo = {}, {}, {}, {}

    for s in symbols:
        df = None
        pth = _sym_path(s)

        # Sprawdź cache
        if os.path.exists(pth):
            try:
                c = pd.read_parquet(pth)
                df = c

                # Sprawdź czy cache jest aktualny
                if end and not c.index.empty:
                    last_date = str(c.index.max().date())
                    end_date = str(pd.to_datetime(end).date())
                    if last_date < end_date:
                        df = None  # Cache przestarzały
            except Exception:
                df = None

        # Fetch z retry jeśli brak cache lub przestarzały
        if df is None:
            last_err = None
            for t in range(retries + 1):
                try:
                    f = _fetch_yf(s, start=start, end=end)
                    if f is not None and not f.empty:
                        f.to_parquet(pth)
                        df = f
                        break
                except Exception as e:
                    last_err = e
                    if t < retries:
                        time.sleep(backoff ** t)

            if df is None:
                print(f"⚠️  yfinance fetch failed for {s}: {last_err}")
                continue

        if df is None or df.empty:
            continue

        # Ekstraktuj kolumny
        if "Adj Close" in df.columns:
            px[s] = df["Adj Close"].rename(s)
        elif "Close" in df.columns:
            px[s] = df["Close"].rename(s)

        if "Volume" in df.columns:
            vol[s] = df["Volume"].rename(s)

        if "High" in df.columns:
            hi[s] = df["High"].rename(s)

        if "Low" in df.columns:
            lo[s] = df["Low"].rename(s)

    # Sklej DataFrames
    px = pd.concat(px.values(), axis=1) if px else pd.DataFrame()
    vol = pd.concat(vol.values(), axis=1) if vol else pd.DataFrame()
    hi = pd.concat(hi.values(), axis=1) if hi else pd.DataFrame()
    lo = pd.concat(lo.values(), axis=1) if lo else pd.DataFrame()

    return px, vol, hi, lo
