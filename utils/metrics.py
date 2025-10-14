"""
Moduł z funkcjami obliczającymi metryki efektywności strategii.
"""
import numpy as np
import pandas as pd
from typing import Union
from scipy import stats


def sharpe(returns: pd.Series, freq: int = 252) -> float:
    """
    Oblicza Sharpe Ratio.
    
    Parameters:
    -----------
    returns : pd.Series
        Seria zwrotów
    freq : int
        Częstotliwość roczna (252 dla dni, 12 dla miesięcy)
        
    Returns:
    --------
    float
        Sharpe Ratio
    """
    if len(returns) == 0 or returns.std() == 0:
        return 0.0
    return returns.mean() / returns.std() * np.sqrt(freq)


def calmar(returns: pd.Series, freq: int = 252) -> float:
    """
    Oblicza Calmar Ratio (roczny zwrot / max drawdown).
    
    Parameters:
    -----------
    returns : pd.Series
        Seria zwrotów
    freq : int
        Częstotliwość roczna
        
    Returns:
    --------
    float
        Calmar Ratio
    """
    annual_return = returns.mean() * freq
    max_dd = max_drawdown(returns)
    
    if max_dd == 0:
        return 0.0
    return annual_return / abs(max_dd)


def max_drawdown(returns: pd.Series) -> float:
    """
    Oblicza maksymalny drawdown.
    
    Parameters:
    -----------
    returns : pd.Series
        Seria zwrotów
        
    Returns:
    --------
    float
        Maksymalny drawdown (wartość ujemna)
    """
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    return drawdown.min()


def rank_ic(factor_series: pd.Series, fwd_series: pd.Series) -> float:
    """
    Oblicza Rank Information Coefficient (Spearman correlation).
    
    Oczekuje serii z MultiIndex (date, ticker) lub pojedynczych serii.
    
    Parameters:
    -----------
    factor_series : pd.Series
        Wartości faktora
    fwd_series : pd.Series
        Przyszłe zwroty
        
    Returns:
    --------
    float
        Rank IC
    """
    # Usuń NaN
    valid = pd.DataFrame({"factor": factor_series, "fwd": fwd_series}).dropna()
    
    if len(valid) < 2:
        return 0.0
    
    correlation, _ = stats.spearmanr(valid["factor"], valid["fwd"])
    return correlation


def turnover(weights: pd.DataFrame) -> pd.Series:
    """
    Oblicza turnover (suma absolutnych zmian wag).
    
    Parameters:
    -----------
    weights : pd.DataFrame
        DataFrame z wagami portfela (index: daty, kolumny: tickery)
        
    Returns:
    --------
    pd.Series
        Seria turnover dla każdej daty
    """
    weight_changes = weights.diff().abs().sum(axis=1)
    return weight_changes


def deflated_sharpe_ratio(
    sharpe: float,
    n: int,
    skew: float = 0.0,
    kurt: float = 3.0
) -> float:
    """
    Oblicza Deflated Sharpe Ratio (DSR) wg de Prado.

    DSR koryguje Sharpe o wielokrotne testowanie i właściwości rozkładu zwrotów.

    Formuła przybliżona:
    DSR = (SR * sqrt(n - 1)) / sqrt(1 + (1 - skew*SR + (kurt-1)/4 * SR^2))

    Założenia:
    - skew: skośność rozkładu zwrotów (0 = rozkład symetryczny)
    - kurt: kurtoza rozkładu zwrotów (3 = rozkład normalny)
    - n: liczba obserwacji

    Parameters:
    -----------
    sharpe : float
        Sharpe Ratio
    n : int
        Liczba obserwacji
    skew : float
        Skośność rozkładu zwrotów (domyślnie 0)
    kurt : float
        Kurtoza rozkładu zwrotów (domyślnie 3)

    Returns:
    --------
    float
        Deflated Sharpe Ratio
    """
    if n <= 1:
        return 0.0

    # Formuła uproszczona de Prado
    sr_sq = sharpe ** 2
    denominator = 1 + (1 - skew * sharpe + (kurt - 1) / 4 * sr_sq)

    if denominator <= 0:
        return 0.0

    dsr = (sharpe * np.sqrt(n - 1)) / np.sqrt(denominator)
    return dsr


def deflated_sharpe_ratio_v2(
    sr: float,
    n: int,
    skew: float = 0.0,
    kurt: float = 3.0,
    trials: int = 1
) -> float:
    """
    Oblicza Deflated Sharpe Ratio (DSR) v2 z korektą na multiple testing.

    Wersja rozszerzona z korektą na wielokrotne testowanie (trials).
    Używa formuły Lopez de Prado z "Advances in Financial Machine Learning".

    Formuła:
    1. Oblicz SR0 (expected SR pod H0):
       SR0 = sqrt(V[SR]) * ((1 - γ) * Φ^(-1)(1 - 1/trials) + γ * Φ^(-1)(1 - 1/(trials*e)))
       gdzie γ = skewness korygująca, V[SR] to wariancja SR

    2. DSR = Φ((SR - SR0) / sqrt(V[SR]))
       gdzie Φ to CDF rozkładu normalnego

    V[SR] = (1 + (1 - skew*SR + (kurt-3)/4 * SR^2)) / (n - 1)

    Parameters:
    -----------
    sr : float
        Sharpe Ratio
    n : int
        Liczba obserwacji
    skew : float
        Skośność rozkładu zwrotów (domyślnie 0.0)
    kurt : float
        Kurtoza rozkładu zwrotów (domyślnie 3.0)
    trials : int
        Liczba prób/testów (domyślnie 1, dla multiple testing > 1)

    Returns:
    --------
    float
        Deflated Sharpe Ratio z korektą na multiple testing
        (p-value transformed, wartość ~0.5 = neutralne, >0.5 = istotne statystycznie)
    """
    if n <= 2 or trials < 1:
        return 0.0

    # Oblicz wariancję SR
    var_sr = (1.0 + (1.0 - skew * sr + (kurt - 3.0) / 4.0 * sr**2)) / (n - 1)

    if var_sr <= 0:
        return 0.0

    std_sr = np.sqrt(var_sr)

    # Euler's number
    e = np.e

    # Gamma (Euler-Mascheroni constant approximation)
    # W uproszczonej wersji używamy gamma = skew / std_sr jako heurystyki
    # Dla dokładniejszej implementacji: gamma z literatury Lopez de Prado
    gamma = 0.5772156649  # Euler-Mascheroni constant

    # Oblicz SR0 (expected SR under H0 with multiple testing correction)
    # Używamy inverse CDF (percent point function) z scipy.stats.norm
    from scipy.stats import norm

    if trials == 1:
        # Bez korekty na multiple testing
        sr0 = 0.0
    else:
        # Z korektą na multiple testing
        z1 = norm.ppf(1.0 - 1.0 / trials)
        z2 = norm.ppf(1.0 - 1.0 / (trials * e))
        sr0 = std_sr * ((1.0 - gamma) * z1 + gamma * z2)

    # Oblicz DSR jako CDF z transformacji
    dsr_z = (sr - sr0) / std_sr
    dsr = norm.cdf(dsr_z)

    return dsr


def sortino(returns: pd.Series, freq: int = 252, target: float = 0.0) -> float:
    """
    Oblicza Sortino Ratio.

    Używa tylko downside deviation (zwroty poniżej target).

    Parameters:
    -----------
    returns : pd.Series
        Seria zwrotów
    freq : int
        Częstotliwość roczna
    target : float
        Target return (domyślnie 0.0)

    Returns:
    --------
    float
        Sortino Ratio
    """
    if len(returns) == 0:
        return 0.0

    excess = returns - target
    downside_returns = excess[excess < 0]

    if len(downside_returns) == 0 or downside_returns.std() == 0:
        return 0.0

    downside_dev = downside_returns.std()
    return excess.mean() / downside_dev * np.sqrt(freq)


def information_ratio(
    returns: pd.Series,
    bench_returns: pd.Series,
    freq: int = 252
) -> float:
    """
    Oblicza Information Ratio (IR).

    IR = (średni nadmiarowy zwrot) / (tracking error)

    Parameters:
    -----------
    returns : pd.Series
        Seria zwrotów strategii
    bench_returns : pd.Series
        Seria zwrotów benchmarku
    freq : int
        Częstotliwość roczna

    Returns:
    --------
    float
        Information Ratio
    """
    # Wyrównaj indeksy
    common_idx = returns.index.intersection(bench_returns.index)
    if len(common_idx) == 0:
        return 0.0

    ret = returns.loc[common_idx]
    bench = bench_returns.loc[common_idx]

    active_returns = ret - bench

    if active_returns.std() == 0:
        return 0.0

    ir = active_returns.mean() / active_returns.std() * np.sqrt(freq)
    return ir


def alpha_beta(
    returns: pd.Series,
    bench_returns: pd.Series,
    freq: int = 252
) -> tuple:
    """
    Oblicza alpha i beta względem benchmarku.

    Parameters:
    -----------
    returns : pd.Series
        Seria zwrotów strategii
    bench_returns : pd.Series
        Seria zwrotów benchmarku
    freq : int
        Częstotliwość roczna

    Returns:
    --------
    tuple
        (alpha_annualized, beta)
    """
    # Wyrównaj indeksy
    common_idx = returns.index.intersection(bench_returns.index)
    if len(common_idx) < 2:
        return (0.0, 0.0)

    ret = returns.loc[common_idx].values
    bench = bench_returns.loc[common_idx].values

    # Regresja liniowa
    slope, intercept, _, _, _ = stats.linregress(bench, ret)

    beta = slope
    alpha_daily = intercept
    alpha_annualized = alpha_daily * freq

    return (alpha_annualized, beta)


def expected_shortfall(returns: pd.Series, confidence: float = 0.95) -> float:
    """
    Oblicza Expected Shortfall (ES) / Conditional VaR.

    ES = średnia ze zwrotów poniżej VaR.

    Parameters:
    -----------
    returns : pd.Series
        Seria zwrotów
    confidence : float
        Poziom ufności (domyślnie 0.95)

    Returns:
    --------
    float
        Expected Shortfall (wartość ujemna)
    """
    if len(returns) == 0:
        return 0.0

    var_threshold = returns.quantile(1 - confidence)
    tail_returns = returns[returns <= var_threshold]

    if len(tail_returns) == 0:
        return 0.0

    es = tail_returns.mean()
    return es


def tail_ratio(returns: pd.Series) -> float:
    """
    Oblicza Tail Ratio = abs(95th percentile / 5th percentile).

    Parameters:
    -----------
    returns : pd.Series
        Seria zwrotów

    Returns:
    --------
    float
        Tail Ratio
    """
    if len(returns) == 0:
        return 0.0

    p95 = returns.quantile(0.95)
    p5 = returns.quantile(0.05)

    if p5 == 0:
        return 0.0

    tail_r = abs(p95 / p5)
    return tail_r


def hit_rate(factor: pd.Series, forward_returns: pd.Series) -> float:
    """
    Oblicza Hit Rate (% przypadków gdy factor i fwd_ret mają ten sam znak).

    Parameters:
    -----------
    factor : pd.Series
        Seria wartości faktora
    forward_returns : pd.Series
        Seria przyszłych zwrotów

    Returns:
    --------
    float
        Hit Rate (0-1)
    """
    # Wspólny indeks
    common_idx = factor.index.intersection(forward_returns.index)
    if len(common_idx) == 0:
        return 0.0

    fac = factor.loc[common_idx]
    fwd = forward_returns.loc[common_idx]

    # Usuń NaN
    valid = pd.DataFrame({"f": fac, "fwd": fwd}).dropna()
    if len(valid) == 0:
        return 0.0

    # Zgodność znaku
    same_sign = np.sign(valid["f"]) == np.sign(valid["fwd"])
    hit = same_sign.sum() / len(same_sign)

    return hit


def payoff_ratio(factor: pd.Series, forward_returns: pd.Series) -> float:
    """
    Oblicza Payoff Ratio = (średni zysk przy trafieniu) / (średnia strata przy błędzie).

    Parameters:
    -----------
    factor : pd.Series
        Seria wartości faktora
    forward_returns : pd.Series
        Seria przyszłych zwrotów

    Returns:
    --------
    float
        Payoff Ratio
    """
    common_idx = factor.index.intersection(forward_returns.index)
    if len(common_idx) == 0:
        return 0.0

    fac = factor.loc[common_idx]
    fwd = forward_returns.loc[common_idx]

    valid = pd.DataFrame({"f": fac, "fwd": fwd}).dropna()
    if len(valid) == 0:
        return 0.0

    # Zgodność znaku
    same_sign = np.sign(valid["f"]) == np.sign(valid["fwd"])

    wins = valid.loc[same_sign, "fwd"]
    losses = valid.loc[~same_sign, "fwd"]

    if len(wins) == 0 or len(losses) == 0:
        return 0.0

    avg_win = wins.abs().mean()
    avg_loss = losses.abs().mean()

    if avg_loss == 0:
        return 0.0

    payoff = avg_win / avg_loss
    return payoff


def rolling_rank_ic(
    factor: pd.DataFrame,
    forward_returns: pd.DataFrame,
    window: int = 60
) -> pd.Series:
    """
    Oblicza rolling Rank IC (Spearman correlation) między faktorem a forward returns.

    Parameters:
    -----------
    factor : pd.DataFrame
        DataFrame z wartościami faktora (index: datetime, kolumny: tickery)
    forward_returns : pd.DataFrame
        DataFrame z forward returns
    window : int
        Okno rolling w dniach (domyślnie 60)

    Returns:
    --------
    pd.Series
        Seria z rolling Rank IC dla każdej daty
    """
    ic_series = pd.Series(index=factor.index, dtype=float)

    for i in range(window, len(factor)):
        window_start = i - window
        window_factor = factor.iloc[window_start:i]
        window_fwd = forward_returns.iloc[window_start:i]

        # Flatten
        fac_flat = window_factor.stack()
        fwd_flat = window_fwd.stack()

        # Wspólny indeks
        valid = pd.DataFrame({"f": fac_flat, "fwd": fwd_flat}).dropna()

        if len(valid) < 2:
            continue

        # Spearman correlation
        try:
            corr, _ = stats.spearmanr(valid["f"], valid["fwd"])
            ic_series.iloc[i] = corr
        except:
            continue

    return ic_series
