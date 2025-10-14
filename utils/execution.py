"""
Moduł do generowania wag portfela i zleceń.
"""
from typing import Dict, Optional
import pandas as pd
import numpy as np


def target_weights_from_ranks(
    ranks: pd.Series,
    top_quantile: float = 0.9,
    bottom_quantile: float = 0.1,
    long_only: bool = True,
    max_weight: float = 0.1
) -> pd.Series:
    """
    Generuje docelowe wagi portfela na podstawie rankingów.
    
    Parameters:
    -----------
    ranks : pd.Series
        Seria rankingów percentylowych (0-1)
    top_quantile : float
        Próg górny dla pozycji długich
    bottom_quantile : float
        Próg dolny dla pozycji krótkich (jeśli long_only=False)
    long_only : bool
        Czy tylko pozycje długie
    max_weight : float
        Maksymalna waga pojedynczej pozycji
        
    Returns:
    --------
    pd.Series
        Seria z wagami portfela (suma = 1.0)
    """
    weights = pd.Series(0.0, index=ranks.index)
    
    # Pozycje długie
    long_mask = ranks >= top_quantile
    n_long = long_mask.sum()
    
    if long_only:
        if n_long > 0:
            weights[long_mask] = 1.0 / n_long
            # Ogranicz maksymalną wagę
            weights = weights.clip(upper=max_weight)
            # Renormalizuj
            if weights.sum() > 0:
                weights = weights / weights.sum()
    else:
        # Long-short
        short_mask = ranks <= bottom_quantile
        n_short = short_mask.sum()
        
        if n_long > 0:
            weights[long_mask] = 0.5 / n_long
        if n_short > 0:
            weights[short_mask] = -0.5 / n_short
        
        # Ogranicz maksymalną wagę
        weights = weights.clip(lower=-max_weight, upper=max_weight)
    
    return weights


def rebalance_signal(index: pd.DatetimeIndex, freq: str = "M") -> pd.Series:
    """
    Generuje sygnał rebalansowania portfela.

    Zwraca bool Series z True w dniach, w których powinien nastąpić rebalans.
    Wspierane częstotliwości:
    - "M" (Monthly): Pierwszy dzień każdego miesiąca
    - "W" (Weekly): Pierwszy dzień każdego tygodnia (poniedziałek)
    - "D" (Daily): Każdy dzień

    Parameters:
    -----------
    index : pd.DatetimeIndex
        Indeks dat z backtestingu
    freq : str
        Częstotliwość rebalansowania: "M", "W", "D"

    Returns:
    --------
    pd.Series
        Bool Series (index: datetime, wartości: True/False)
        True oznacza dzień rebalansowania
    """
    if freq == "D":
        # Rebalansuj każdy dzień
        return pd.Series(True, index=index)

    elif freq == "W":
        # Rebalansuj w poniedziałki (lub pierwszy dzień tygodnia)
        is_monday = index.dayofweek == 0
        # Alternatywnie: pierwszy dzień tygodnia w danych
        week_num = index.isocalendar().week
        first_day_of_week = ~week_num.duplicated()
        return pd.Series(first_day_of_week, index=index)

    elif freq == "M":
        # Rebalansuj pierwszego dnia miesiąca
        is_first_day = ~index.to_period('M').duplicated()
        return pd.Series(is_first_day, index=index)

    else:
        raise ValueError(f"Nieobsługiwana częstotliwość rebalansowania: {freq}. Użyj 'M', 'W', lub 'D'.")


def apply_rebalance_weights(
    ranks: pd.DataFrame,
    top_quantile: float = 0.9,
    bottom_quantile: float = 0.1,
    long_only: bool = True,
    max_weight: float = 0.1,
    cash_buffer: float = 0.0,
    rebalance_flags: Optional[pd.Series] = None,
    eligibility_mask: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    Generuje wagi portfela z carry-over między rebalansami.

    W dniach rebalansowania oblicza nowe wagi na podstawie rankingów.
    W dniach bez rebalansowania przenosi wagi z poprzedniego dnia (carry-over),
    redukując turnover i koszty transakcyjne.

    Opcjonalnie stosuje maskę eligibilności (Point-in-Time) - w dniu rebalansowania
    uwzględniane są tylko tickery z eligible=True.

    Parameters:
    -----------
    ranks : pd.DataFrame
        DataFrame z rankingami percentylowymi (0-1)
        (index: datetime, kolumny: tickery)
    top_quantile : float
        Próg górny dla pozycji długich (domyślnie 0.9)
    bottom_quantile : float
        Próg dolny dla pozycji krótkich (domyślnie 0.1)
    long_only : bool
        Czy tylko pozycje długie (domyślnie True)
    max_weight : float
        Maksymalna waga pojedynczej pozycji (domyślnie 0.1)
    cash_buffer : float
        Bufory gotówkowy (0.0 = fully invested, domyślnie 0.0)
    rebalance_flags : Optional[pd.Series]
        Bool Series z flagami rebalansowania (True = rebalansuj w tym dniu)
        Jeśli None, rebalansuje każdy dzień
    eligibility_mask : Optional[pd.DataFrame]
        Bool DataFrame z eligibilnością (True = ticker eligible w danym dniu)
        Jeśli None, nie stosuje filtrowania

    Returns:
    --------
    pd.DataFrame
        DataFrame z wagami portfela (index: datetime, kolumny: tickery)
        W dniach bez rebalansowania wagi są przenoszone z poprzedniego dnia
    """
    if rebalance_flags is None:
        # Domyślnie rebalansuj każdy dzień
        rebalance_flags = pd.Series(True, index=ranks.index)

    # Zainicjuj DataFrame dla wag
    weights_df = pd.DataFrame(0.0, index=ranks.index, columns=ranks.columns)
    prev_weights = pd.Series(0.0, index=ranks.columns)

    for date in ranks.index:
        if rebalance_flags.loc[date]:
            # Dzień rebalansowania - oblicz nowe wagi
            rank_row = ranks.loc[date]

            # Aplikuj maskę eligibilności
            if eligibility_mask is not None:
                eligible = eligibility_mask.loc[date]
                rank_row = rank_row[eligible]

            # Usuń NaN
            rank_row = rank_row.dropna()

            if len(rank_row) == 0:
                # Brak eligible tickerów - zostaw poprzednie wagi lub zero
                weights_df.loc[date] = prev_weights
                continue

            # Generuj wagi
            weights = pd.Series(0.0, index=ranks.columns)

            # Pozycje długie
            long_mask = rank_row >= top_quantile
            n_long = long_mask.sum()

            if long_only:
                if n_long > 0:
                    target_weight = (1.0 - cash_buffer) / n_long
                    weights[long_mask.index[long_mask]] = target_weight
                    # Ogranicz maksymalną wagę
                    weights = weights.clip(upper=max_weight)
                    # Renormalizuj
                    total = weights.sum()
                    if total > 0:
                        weights = weights * (1.0 - cash_buffer) / total
            else:
                # Long-short
                short_mask = rank_row <= bottom_quantile
                n_short = short_mask.sum()

                gross_target = (1.0 - cash_buffer) / 2.0

                if n_long > 0:
                    weights[long_mask.index[long_mask]] = gross_target / n_long
                if n_short > 0:
                    weights[short_mask.index[short_mask]] = -gross_target / n_short

                # Ogranicz maksymalną wagę
                weights = weights.clip(lower=-max_weight, upper=max_weight)

            weights_df.loc[date] = weights
            prev_weights = weights.copy()

        else:
            # Dzień bez rebalansowania - carry-over poprzednich wag
            weights_df.loc[date] = prev_weights

    return weights_df


def orders_from_diff(
    current_positions: Dict[str, float],
    target_weights: pd.Series,
    portfolio_value: float
) -> pd.DataFrame:
    """
    Generuje zlecenia na podstawie różnicy między obecnymi a docelowymi pozycjami.

    UWAGA: To jest szkic demo. W środowisku live wymaga realnych cen i pozycji.

    Parameters:
    -----------
    current_positions : Dict[str, float]
        Obecne pozycje (ticker -> liczba akcji)
    target_weights : pd.Series
        Docelowe wagi portfela
    portfolio_value : float
        Obecna wartość portfela

    Returns:
    --------
    pd.DataFrame
        DataFrame ze zleceniami (kolumny: ticker, action, quantity)
    """
    orders = []

    for ticker in target_weights.index:
        target_value = target_weights[ticker] * portfolio_value
        current_shares = current_positions.get(ticker, 0.0)

        # Uproszczenie: zakładamy cenę = 1.0 (wymaga realnej ceny!)
        # W rzeczywistości: target_shares = target_value / current_price
        target_shares = target_value  # DEMO

        diff = target_shares - current_shares

        if abs(diff) > 0.01:  # Minimalna zmiana
            action = "BUY" if diff > 0 else "SELL"
            orders.append({
                "ticker": ticker,
                "action": action,
                "quantity": abs(diff)
            })

    return pd.DataFrame(orders)
