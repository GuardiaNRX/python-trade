"""
Moduł do obliczania kosztów transakcyjnych.
"""
import pandas as pd


def bps_to_frac(bps: float) -> float:
    """
    Konwertuje punkty bazowe na ułamek dziesiętny.
    
    Parameters:
    -----------
    bps : float
        Wartość w punktach bazowych (basis points)
        
    Returns:
    --------
    float
        Ułamek dziesiętny
    """
    return bps / 10000.0


def apply_costs(
    returns: pd.Series,
    turnover_series: pd.Series,
    fees_bps: float,
    slippage_bps: float
) -> pd.Series:
    """
    Potrąca koszty transakcyjne od zwrotów.
    
    Koszty = turnover * (fees + slippage)
    
    Parameters:
    -----------
    returns : pd.Series
        Seria zwrotów brutto
    turnover_series : pd.Series
        Seria turnover (suma absolutnych zmian wag)
    fees_bps : float
        Opłaty w punktach bazowych
    slippage_bps : float
        Slippage w punktach bazowych
        
    Returns:
    --------
    pd.Series
        Seria zwrotów netto po kosztach
    """
    total_cost_bps = fees_bps + slippage_bps
    total_cost_frac = bps_to_frac(total_cost_bps)
    
    costs = turnover_series * total_cost_frac
    net_returns = returns - costs
    
    return net_returns
