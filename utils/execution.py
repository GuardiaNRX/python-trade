"""
ModuĹ‚ do generowania wag portfela i zleceĹ„.
"""
from typing import Dict, Optional

import pandas as pd


def target_weights_from_ranks(
    ranks: pd.Series,
    top_quantile: float = 0.9,
    bottom_quantile: float = 0.1,
    long_only: bool = True,
    max_weight: float = 0.1
) -> pd.Series:
    """
    Generuje docelowe wagi portfela na podstawie rankingĂłw.
    
    Parameters:
    -----------
    ranks : pd.Series
        Seria rankingĂłw percentylowych (0-1)
    top_quantile : float
        PrĂłg gĂłrny dla pozycji dĹ‚ugich
    bottom_quantile : float
        PrĂłg dolny dla pozycji krĂłtkich (jeĹ›li long_only=False)
    long_only : bool
        Czy tylko pozycje dĹ‚ugie
    max_weight : float
        Maksymalna waga pojedynczej pozycji
        
    Returns:
    --------
    pd.Series
        Seria z wagami portfela (suma = 1.0)
    """
    weights = pd.Series(0.0, index=ranks.index)
    
    # Pozycje dĹ‚ugie
    long_mask = ranks >= top_quantile
    n_long = long_mask.sum()
    
    if long_only:
        if n_long > 0:
            weights[long_mask] = 1.0 / n_long
            # Ogranicz maksymalnÄ… wagÄ™
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
        
        # Ogranicz maksymalnÄ… wagÄ™
        weights = weights.clip(lower=-max_weight, upper=max_weight)
    
    return weights


def rebalance_signal(index: pd.DatetimeIndex, freq: str = "M") -> pd.Series:
    """
    Generuje sygnaĹ‚ rebalansowania portfela.

    Zwraca bool Series z True w dniach, w ktĂłrych powinien nastÄ…piÄ‡ rebalans.
    Wspierane czÄ™stotliwoĹ›ci:
    - "M" (Monthly): Pierwszy dzieĹ„ kaĹĽdego miesiÄ…ca
    - "W" (Weekly): Pierwszy dzieĹ„ kaĹĽdego tygodnia (poniedziaĹ‚ek)
    - "D" (Daily): KaĹĽdy dzieĹ„

    Parameters:
    -----------
    index : pd.DatetimeIndex
        Indeks dat z backtestingu
    freq : str
        CzÄ™stotliwoĹ›Ä‡ rebalansowania: "M", "W", "D"

    Returns:
    --------
    pd.Series
        Bool Series (index: datetime, wartoĹ›ci: True/False)
        True oznacza dzieĹ„ rebalansowania
    """
    if freq == "D":
        # Rebalansuj kaĹĽdy dzieĹ„
        return pd.Series(True, index=index)

    elif freq == "W":
        # Rebalansuj w poniedziaĹ‚ki (lub pierwszy dzieĹ„ tygodnia)
        # Alternatywnie: pierwszy dzieĹ„ tygodnia w danych
        week_num = index.isocalendar().week
        first_day_of_week = ~week_num.duplicated()
        return pd.Series(first_day_of_week, index=index)

    elif freq == "M":
        # Rebalansuj pierwszego dnia miesiÄ…ca
        is_first_day = ~index.to_period('M').duplicated()
        return pd.Series(is_first_day, index=index)

    else:
        raise ValueError(f"NieobsĹ‚ugiwana czÄ™stotliwoĹ›Ä‡ rebalansowania: {freq}. UĹĽyj 'M', 'W', lub 'D'.")


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
    Generuje wagi portfela z carry-over miÄ™dzy rebalansami.

    W dniach rebalansowania oblicza nowe wagi na podstawie rankingĂłw.
    W dniach bez rebalansowania przenosi wagi z poprzedniego dnia (carry-over),
    redukujÄ…c turnover i koszty transakcyjne.

    Opcjonalnie stosuje maskÄ™ eligibilnoĹ›ci (Point-in-Time) - w dniu rebalansowania
    uwzglÄ™dniane sÄ… tylko tickery z eligible=True.

    Parameters:
    -----------
    ranks : pd.DataFrame
        DataFrame z rankingami percentylowymi (0-1)
        (index: datetime, kolumny: tickery)
    top_quantile : float
        PrĂłg gĂłrny dla pozycji dĹ‚ugich (domyĹ›lnie 0.9)
    bottom_quantile : float
        PrĂłg dolny dla pozycji krĂłtkich (domyĹ›lnie 0.1)
    long_only : bool
        Czy tylko pozycje dĹ‚ugie (domyĹ›lnie True)
    max_weight : float
        Maksymalna waga pojedynczej pozycji (domyĹ›lnie 0.1)
    cash_buffer : float
        Bufory gotĂłwkowy (0.0 = fully invested, domyĹ›lnie 0.0)
    rebalance_flags : Optional[pd.Series]
        Bool Series z flagami rebalansowania (True = rebalansuj w tym dniu)
        JeĹ›li None, rebalansuje kaĹĽdy dzieĹ„
    eligibility_mask : Optional[pd.DataFrame]
        Bool DataFrame z eligibilnoĹ›ciÄ… (True = ticker eligible w danym dniu)
        JeĹ›li None, nie stosuje filtrowania

    Returns:
    --------
    pd.DataFrame
        DataFrame z wagami portfela (index: datetime, kolumny: tickery)
        W dniach bez rebalansowania wagi sÄ… przenoszone z poprzedniego dnia
    """
    if rebalance_flags is None:
        # DomyĹ›lnie rebalansuj kaĹĽdy dzieĹ„
        rebalance_flags = pd.Series(True, index=ranks.index)

    # Zainicjuj DataFrame dla wag
    weights_df = pd.DataFrame(0.0, index=ranks.index, columns=ranks.columns)
    prev_weights = pd.Series(0.0, index=ranks.columns)

    for date in ranks.index:
        if rebalance_flags.loc[date]:
            # DzieĹ„ rebalansowania - oblicz nowe wagi
            rank_row = ranks.loc[date]

            # Aplikuj maskÄ™ eligibilnoĹ›ci
            if eligibility_mask is not None:
                eligible = eligibility_mask.loc[date]
                rank_row = rank_row[eligible]

            # UsuĹ„ NaN
            rank_row = rank_row.dropna()

            if len(rank_row) == 0:
                # Brak eligible tickerĂłw - zostaw poprzednie wagi lub zero
                weights_df.loc[date] = prev_weights
                continue

            # Generuj wagi
            weights = pd.Series(0.0, index=ranks.columns)

            # Pozycje dĹ‚ugie
            long_mask = rank_row >= top_quantile
            n_long = long_mask.sum()

            if long_only:
                if n_long > 0:
                    target_weight = (1.0 - cash_buffer) / n_long
                    weights[long_mask.index[long_mask]] = target_weight
                    # Ogranicz maksymalnÄ… wagÄ™
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

                # Ogranicz maksymalnÄ… wagÄ™
                weights = weights.clip(lower=-max_weight, upper=max_weight)

            weights_df.loc[date] = weights
            prev_weights = weights.copy()

        else:
            # DzieĹ„ bez rebalansowania - carry-over poprzednich wag
            weights_df.loc[date] = prev_weights

    return weights_df


def orders_from_diff(
    current_positions: Dict[str, float],
    target_weights: pd.Series,
    portfolio_value: float
) -> pd.DataFrame:
    """
    Generuje zlecenia na podstawie rĂłĹĽnicy miÄ™dzy obecnymi a docelowymi pozycjami.

    UWAGA: To jest szkic demo. W Ĺ›rodowisku live wymaga realnych cen i pozycji.

    Parameters:
    -----------
    current_positions : Dict[str, float]
        Obecne pozycje (ticker -> liczba akcji)
    target_weights : pd.Series
        Docelowe wagi portfela
    portfolio_value : float
        Obecna wartoĹ›Ä‡ portfela

    Returns:
    --------
    pd.DataFrame
        DataFrame ze zleceniami (kolumny: ticker, action, quantity)
    """
    orders = []

    for ticker in target_weights.index:
        target_value = target_weights[ticker] * portfolio_value
        current_shares = current_positions.get(ticker, 0.0)

        # Uproszczenie: zakĹ‚adamy cenÄ™ = 1.0 (wymaga realnej ceny!)
        # W rzeczywistoĹ›ci: target_shares = target_value / current_price
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
