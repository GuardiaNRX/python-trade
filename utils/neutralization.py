"""
Moduł do neutralizacji faktora względem sektorów i rynku (beta).
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional
from scipy import stats
from sklearn.linear_model import Ridge


def sector_residuals(
    factor: pd.DataFrame,
    sector_map: Dict[str, str]
) -> pd.DataFrame:
    """
    Neutralizacja sektorowa - zwraca residua z regresji na dummys sektorowe.

    Dla każdej daty przeprowadza regresję przekrojową:
    factor_i = α + Σ(β_s * sector_dummy_s) + ε_i

    Zwraca ε_i (residua) jako zneutralizowany faktor.

    Parameters:
    -----------
    factor : pd.DataFrame
        DataFrame z wartościami faktora (index: datetime, kolumny: tickery)
    sector_map : Dict[str, str]
        Mapowanie ticker -> sektor

    Returns:
    --------
    pd.DataFrame
        DataFrame z residuami (neutralizowane wartości faktora)
    """
    residuals = pd.DataFrame(index=factor.index, columns=factor.columns, dtype=float)

    for date in factor.index:
        factor_row = factor.loc[date].dropna()

        if len(factor_row) < 2:
            continue

        # Pobierz sektory dla dostępnych tickerów
        tickers = factor_row.index.tolist()
        sectors = [sector_map.get(t, "OTHER") for t in tickers]

        # Utwórz dummys sektorowe
        sector_df = pd.DataFrame({"factor": factor_row.values}, index=tickers)
        sector_dummies = pd.get_dummies(sectors, prefix="sector")
        sector_dummies.index = tickers

        # Regresja: factor ~ sector_dummies (bez interceptu - używamy dummies)
        from sklearn.linear_model import LinearRegression

        X = sector_dummies.values
        y = sector_df["factor"].values

        # Dodaj intercept manualnie
        X_with_intercept = np.column_stack([np.ones(len(X)), X])

        try:
            model = LinearRegression(fit_intercept=False)
            model.fit(X_with_intercept, y)
            predictions = model.predict(X_with_intercept)
            resid = y - predictions

            # Zapisz residua
            for i, ticker in enumerate(tickers):
                residuals.loc[date, ticker] = resid[i]

        except Exception as e:
            # Jeśli regresja nie działa, zostaw oryginalne wartości
            print(f"OSTRZEŻENIE ({date}): Nie udało się zneutralizować sektory: {e}")
            residuals.loc[date, tickers] = factor_row.values

    return residuals


def rolling_beta(
    prices: pd.DataFrame,
    bench_ret: pd.Series,
    window: int = 252
) -> pd.DataFrame:
    """
    Oblicza rolling beta względem benchmarku.

    Parameters:
    -----------
    prices : pd.DataFrame
        DataFrame z cenami (index: datetime, kolumny: tickery)
    bench_ret : pd.Series
        Seria zwrotów benchmarku (index: datetime)
    window : int
        Okno rolling (domyślnie 252 dni)

    Returns:
    --------
    pd.DataFrame
        DataFrame z beta (index: datetime, kolumny: tickery)
    """
    returns = prices.pct_change()
    betas = pd.DataFrame(index=returns.index, columns=returns.columns, dtype=float)

    for ticker in returns.columns:
        ret = returns[ticker]

        # Rolling covariance i variance
        rolling_cov = ret.rolling(window).cov(bench_ret)
        rolling_var = bench_ret.rolling(window).var()

        beta = rolling_cov / rolling_var
        betas[ticker] = beta

    return betas


def beta_residuals(
    factor: pd.DataFrame,
    betas: pd.DataFrame
) -> pd.DataFrame:
    """
    Neutralizacja beta - zwraca residua z regresji na beta.

    Dla każdej daty: factor_i = α + β_mkt * beta_i + ε_i

    Parameters:
    -----------
    factor : pd.DataFrame
        DataFrame z wartościami faktora
    betas : pd.DataFrame
        DataFrame z beta względem benchmarku

    Returns:
    --------
    pd.DataFrame
        DataFrame z residuami (neutralizowane wartości faktora)
    """
    residuals = pd.DataFrame(index=factor.index, columns=factor.columns, dtype=float)

    for date in factor.index:
        factor_row = factor.loc[date].dropna()
        beta_row = betas.loc[date].dropna() if date in betas.index else pd.Series()

        # Wspólne tickery
        common_tickers = factor_row.index.intersection(beta_row.index)

        if len(common_tickers) < 2:
            residuals.loc[date, factor_row.index] = factor_row.values
            continue

        factor_vals = factor_row[common_tickers].values
        beta_vals = beta_row[common_tickers].values

        # Regresja: factor ~ beta
        try:
            slope, intercept, _, _, _ = stats.linregress(beta_vals, factor_vals)
            predictions = intercept + slope * beta_vals
            resid = factor_vals - predictions

            for i, ticker in enumerate(common_tickers):
                residuals.loc[date, ticker] = resid[i]

        except Exception as e:
            print(f"OSTRZEŻENIE ({date}): Nie udało się zneutralizować beta: {e}")
            residuals.loc[date, common_tickers] = factor_vals

    return residuals


def winsorize_df(df: pd.DataFrame, pct: float = 0.01) -> pd.DataFrame:
    """
    Winsoryzuje DataFrame per data (clip outliers do kwantyli).

    Dla każdej daty (wiersza) clip'uje wartości do [pct, 1-pct] kwantyli.
    Redukuje wpływ outlierów na neutralizację.

    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame z wartościami faktora (index: datetime, kolumny: tickery)
    pct : float
        Percentyl do winsoryzacji (domyślnie 0.01 = 1%)

    Returns:
    --------
    pd.DataFrame
        Zwinsoryzowany DataFrame
    """
    winsorized = df.copy()

    for date in df.index:
        row = df.loc[date].dropna()

        if len(row) == 0:
            continue

        # Oblicz kwantyle
        lower_bound = row.quantile(pct)
        upper_bound = row.quantile(1 - pct)

        # Clip wartości
        clipped = row.clip(lower=lower_bound, upper=upper_bound)
        winsorized.loc[date, clipped.index] = clipped.values

    return winsorized


def ridge_sector_beta_residuals(
    factor: pd.DataFrame,
    sector_map: Dict[str, str],
    betas: Optional[pd.DataFrame] = None,
    alpha_ridge: float = 1.0,
    winsor_pct: float = 0.01
) -> pd.DataFrame:
    """
    Neutralizacja sektorowa + beta z użyciem Ridge regression i winsoryzacji.

    Dla każdej daty:
    1. Winsoryzuje wartości faktora (clip outliers)
    2. Przeprowadza Ridge regression: factor_i = α + Σ(β_s * sector_s) + γ * beta_i + ε_i
    3. Zwraca residua ε_i

    Ridge regression (L2 regularization) jest bardziej stabilna niż OLS,
    szczególnie przy współliniowości (np. sektor i beta skorelowane).

    Parameters:
    -----------
    factor : pd.DataFrame
        DataFrame z wartościami faktora (index: datetime, kolumny: tickery)
    sector_map : Dict[str, str]
        Mapowanie ticker -> sektor
    betas : Optional[pd.DataFrame]
        DataFrame z beta względem benchmarku (jeśli None, neutralizacja tylko sektorowa)
    alpha_ridge : float
        Parametr regularyzacji Ridge (domyślnie 1.0, wyższe = silniejsza regularyzacja)
    winsor_pct : float
        Percentyl do winsoryzacji (domyślnie 0.01)

    Returns:
    --------
    pd.DataFrame
        DataFrame z residuami (neutralizowane wartości faktora)
    """
    # Winsoryzuj faktor
    factor_winsor = winsorize_df(factor, pct=winsor_pct)

    residuals = pd.DataFrame(index=factor_winsor.index, columns=factor_winsor.columns, dtype=float)

    for date in factor_winsor.index:
        factor_row = factor_winsor.loc[date].dropna()

        if len(factor_row) < 2:
            continue

        # Tickery
        tickers = factor_row.index.tolist()

        # Utwórz sector dummies
        sectors = [sector_map.get(t, "OTHER") for t in tickers]
        sector_dummies = pd.get_dummies(sectors, prefix="sector", drop_first=True)
        sector_dummies.index = tickers

        # Buduj macierz X
        X = sector_dummies.values

        # Dodaj beta jeśli dostępne
        if betas is not None and date in betas.index:
            beta_row = betas.loc[date].dropna()
            common_tickers = factor_row.index.intersection(beta_row.index)

            if len(common_tickers) >= 2:
                # Przefiltruj do common tickers
                factor_row = factor_row[common_tickers]
                tickers = common_tickers.tolist()

                # Odbuduj sector dummies
                sectors = [sector_map.get(t, "OTHER") for t in tickers]
                sector_dummies = pd.get_dummies(sectors, prefix="sector", drop_first=True)
                sector_dummies.index = tickers

                # Dodaj kolumnę beta
                beta_vals = beta_row[common_tickers].values.reshape(-1, 1)
                X = np.column_stack([sector_dummies.values, beta_vals])

        y = factor_row.values

        # Ridge regression
        try:
            model = Ridge(alpha=alpha_ridge, fit_intercept=True)
            model.fit(X, y)
            predictions = model.predict(X)
            resid = y - predictions

            # Zapisz residua
            for i, ticker in enumerate(tickers):
                residuals.loc[date, ticker] = resid[i]

        except Exception as e:
            print(f"OSTRZEŻENIE ({date}): Ridge regression nie powiodła się: {e}")
            # Fallback: zostaw oryginalne wartości
            residuals.loc[date, tickers] = factor_row.values

    return residuals


def load_sector_map(csv_path: str) -> Dict[str, str]:
    """
    Wczytuje mapowanie ticker -> sektor z pliku CSV.

    Oczekiwany format CSV: ticker,sector

    Parameters:
    -----------
    csv_path : str
        Ścieżka do pliku CSV

    Returns:
    --------
    Dict[str, str]
        Słownik {ticker: sektor}
    """
    try:
        df = pd.read_csv(csv_path)
        if "ticker" not in df.columns or "sector" not in df.columns:
            raise ValueError("CSV musi zawierać kolumny: ticker, sector")

        sector_map = dict(zip(df["ticker"], df["sector"]))
        return sector_map

    except Exception as e:
        print(f"BŁĄD przy wczytywaniu sector_map z {csv_path}: {e}")
        return {}
