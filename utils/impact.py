"""
Moduł do modelowania impact kosztów i capacity.
Używa modelu square-root impact i monitoruje naruszenia %ADV.
"""
import numpy as np
import pandas as pd


def compute_adv_usd(
    prices: pd.DataFrame,
    volume: pd.DataFrame,
    lookback: int = 60
) -> pd.DataFrame:
    """
    Oblicza średni dzienny wolumen w USD (ADV USD).

    Parameters:
    -----------
    prices : pd.DataFrame
        DataFrame z cenami
    volume : pd.DataFrame
        DataFrame z volume
    lookback : int
        Okno rolling w dniach (domyślnie 60)

    Returns:
    --------
    pd.DataFrame
        DataFrame z ADV USD
    """
    dollar_volume = prices * volume
    adv_usd = dollar_volume.rolling(window=lookback, min_periods=1).mean()
    return adv_usd


def square_root_impact_cost(
    dollars_traded: pd.DataFrame,
    adv_usd: pd.DataFrame,
    k_bps=15.0
) -> pd.DataFrame:
    """
    Oblicza koszt impact według modelu square-root.

    Formula: cost = k * sqrt(dollars_traded / ADV_USD)

    gdzie k jest w basis points.

    Parameters:
    -----------
    dollars_traded : pd.DataFrame
        DataFrame z wartością handlowaną w USD (index: datetime, kolumny: tickery)
    adv_usd : pd.DataFrame
        DataFrame z ADV USD
    k_bps : float or pd.Series
        Współczynnik impact w basis points (domyślnie 15.0)
        Może być float (stała) lub Series per symbol

    Returns:
    --------
    pd.DataFrame
        DataFrame z kosztami impact (frakcja, nie bps)
    """
    # Unikaj dzielenia przez 0
    adv_usd_safe = adv_usd.replace(0, np.nan)

    # Oblicz stosunek
    ratio = dollars_traded / adv_usd_safe

    # Jeśli k_bps jest Series, rozszerz do DataFrame
    if hasattr(k_bps, "reindex"):  # Series per symbol
        k_mat = pd.DataFrame(
            [k_bps.reindex(dollars_traded.columns)] * len(dollars_traded),
            index=dollars_traded.index
        )
        impact = (k_mat / 10000.0) * np.sqrt(ratio.clip(lower=0))
    else:
        # k_bps jest float (stała)
        impact = (float(k_bps) / 10000.0) * np.sqrt(ratio.clip(lower=0))

    # Zamień NaN na 0
    impact = impact.fillna(0)

    return impact


def capacity_violations(
    dollars_traded: pd.DataFrame,
    adv_usd: pd.DataFrame,
    cap_pct: float = 0.10
) -> pd.DataFrame:
    """
    Oblicza naruszenia capacity (% ADV).

    Zwraca DataFrame z 1 tam gdzie dollars_traded > cap_pct * ADV_USD, 0 w przeciwnym wypadku.

    Parameters:
    -----------
    dollars_traded : pd.DataFrame
        DataFrame z wartością handlowaną w USD
    adv_usd : pd.DataFrame
        DataFrame z ADV USD
    cap_pct : float
        Próg capacity jako %ADV (domyślnie 0.10 = 10%)

    Returns:
    --------
    pd.DataFrame
        DataFrame z naruszeniami (1 = naruszenie, 0 = ok)
    """
    # Unikaj dzielenia przez 0
    adv_usd_safe = adv_usd.replace(0, np.nan)

    # Oblicz stosunek
    ratio = dollars_traded / adv_usd_safe

    # Naruszenia
    violations = (ratio > cap_pct).astype(int)

    # Zamień NaN na 0
    violations = violations.fillna(0)

    return violations


def compute_dollars_traded(
    weight_changes: pd.DataFrame,
    equity: float,
    prices: pd.DataFrame
) -> pd.DataFrame:
    """
    Oblicza wartość handlowaną w USD na podstawie zmian wag portfela.

    dollars_traded = |Δw| * equity

    (Uproszczenie: zakładamy że equity jest stałe; w rzeczywistości zmienia się dziennie)

    Parameters:
    -----------
    weight_changes : pd.DataFrame
        DataFrame z absolutnymi zmianami wag |Δw|
    equity : float
        Wartość kapitału portfela w USD
    prices : pd.DataFrame
        DataFrame z cenami (opcjonalnie do przyszłych rozszerzeń)

    Returns:
    --------
    pd.DataFrame
        DataFrame z dollars_traded
    """
    dollars_traded = weight_changes * equity
    return dollars_traded


def corwin_schultz_spread(
    high: pd.DataFrame,
    low: pd.DataFrame,
    window: int = 2
) -> pd.DataFrame:
    """
    Estymuje bid-ask spread używając metody Corwin-Schultz (2012).

    Wykorzystuje dane High/Low z N kolejnych dni do estymacji spreadu.
    Metoda oparta na volatility decomposition.

    Formula (uproszczona):
    β = E[log(High/Low)^2]
    γ = E[log(High_t/Low_{t-1})^2 + log(High_{t-1}/Low_t)^2]
    spread = 2 * (exp(α) - 1) / (1 + exp(α))
    gdzie α jest estymowany z β i γ

    Reference:
    Corwin, Shane A., and Paul Schultz. "A simple way to estimate bid‐ask spreads
    from daily high and low prices." The Journal of Finance 67.2 (2012): 719-760.

    Parameters:
    -----------
    high : pd.DataFrame
        DataFrame z High prices (index: datetime, kolumny: tickery)
    low : pd.DataFrame
        DataFrame z Low prices
    window : int
        Okno w dniach (domyślnie 2, zgodnie z oryginalną metodą)

    Returns:
    --------
    pd.DataFrame
        DataFrame z estymowanym spreadem jako frakcja ceny (0-1)
    """
    # Oblicz log(High/Low) dla każdego dnia
    hl_ratio = np.log(high / low).replace([np.inf, -np.inf], np.nan)

    # β: rolling mean of log(H/L)^2
    beta = (hl_ratio ** 2).rolling(window=window, min_periods=1).mean()

    # γ: cross-day component
    # log(H_t / L_{t-1})^2 + log(H_{t-1} / L_t)^2
    high_shifted = high.shift(1)
    low_shifted = low.shift(1)

    cross_component = (
        np.log(high / low_shifted).replace([np.inf, -np.inf], np.nan) ** 2 +
        np.log(high_shifted / low).replace([np.inf, -np.inf], np.nan) ** 2
    )

    gamma = cross_component.rolling(window=window, min_periods=1).mean()

    # Oblicz α
    # α = (sqrt(2*β) - sqrt(β)) / (3 - 2*sqrt(2)) - sqrt(γ / (3 - 2*sqrt(2)))
    sqrt2 = np.sqrt(2)
    denom = 3 - 2 * sqrt2

    alpha = (np.sqrt(2 * beta) - np.sqrt(beta)) / denom - np.sqrt(gamma / denom)

    # Upewnij się że alpha >= 0
    alpha = alpha.clip(lower=0)

    # Spread = 2 * (exp(α) - 1) / (1 + exp(α))
    exp_alpha = np.exp(alpha)
    spread = 2 * (exp_alpha - 1) / (1 + exp_alpha)

    # Clip spread do rozsądnych wartości (0-50%)
    spread = spread.clip(lower=0, upper=0.5)

    # Wypełnij NaN jako 0
    spread = spread.fillna(0)

    return spread


def spread_cost_fraction(
    weights_diff: pd.DataFrame,
    spread: pd.DataFrame
) -> pd.Series:
    """
    Oblicza koszt spreadu bid-ask jako frakcję wartości portfela.

    Koszt = sum_i |Δw_i| * (spread_i / 2)

    Kupujemy po Ask (cena + spread/2), sprzedajemy po Bid (cena - spread/2).
    Dla każdej zmiany wagi ponosimy koszt połowy spreadu.

    Parameters:
    -----------
    weights_diff : pd.DataFrame
        DataFrame z absolutnymi zmianami wag |Δw_i|
        (index: datetime, kolumny: tickery)
    spread : pd.DataFrame
        DataFrame ze spreadem jako frakcja ceny (0-1)

    Returns:
    --------
    pd.Series
        Seria z kosztem spreadu per data (frakcja wartości portfela)
    """
    # Koszt = |Δw| * (spread / 2)
    cost_per_ticker = weights_diff * (spread / 2.0)

    # Sumuj po wszystkich tickerach dla każdej daty
    total_cost = cost_per_ticker.sum(axis=1)

    return total_cost
