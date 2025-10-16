"""
Moduł do tworzenia wykresów.
"""
import os

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.use('Agg')  # Backend bez GUI


def equity_curve(returns: pd.Series, outdir: str, filename: str = "equity_curve.png") -> str:
    """
    Tworzy wykres krzywej kapitału.
    
    Parameters:
    -----------
    returns : pd.Series
        Seria zwrotów
    outdir : str
        Katalog wyjściowy
    filename : str
        Nazwa pliku
        
    Returns:
    --------
    str
        Ścieżka do zapisanego pliku PNG
    """
    os.makedirs(outdir, exist_ok=True)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    cumulative = (1 + returns).cumprod()
    ax.plot(cumulative.index, cumulative.values)
    ax.set_xlabel("Data")
    ax.set_ylabel("Wartość portfela (1 = początek)")
    ax.set_title("Krzywa kapitału")
    ax.grid(True, alpha=0.3)
    
    filepath = os.path.join(outdir, filename)
    fig.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    return filepath


def histogram_returns(returns: pd.Series, outdir: str, filename: str = "returns_histogram.png") -> str:
    """
    Tworzy histogram zwrotów.
    
    Parameters:
    -----------
    returns : pd.Series
        Seria zwrotów
    outdir : str
        Katalog wyjściowy
    filename : str
        Nazwa pliku
        
    Returns:
    --------
    str
        Ścieżka do zapisanego pliku PNG
    """
    os.makedirs(outdir, exist_ok=True)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.hist(returns.dropna(), bins=50, edgecolor='black', alpha=0.7)
    ax.set_xlabel("Zwrot")
    ax.set_ylabel("Częstość")
    ax.set_title("Histogram zwrotów")
    ax.axvline(x=0, color='r', linestyle='--', alpha=0.5)
    ax.grid(True, alpha=0.3)

    filepath = os.path.join(outdir, filename)
    fig.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close(fig)

    return filepath


def rolling_ic_plot(ic_series: pd.Series, outdir: str, filename: str = "rolling_ic.png") -> str:
    """
    Tworzy wykres rolling IC.

    Parameters:
    -----------
    ic_series : pd.Series
        Seria z rolling IC
    outdir : str
        Katalog wyjściowy
    filename : str
        Nazwa pliku

    Returns:
    --------
    str
        Ścieżka do zapisanego pliku PNG
    """
    os.makedirs(outdir, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 6))

    ic_clean = ic_series.dropna()
    ax.plot(ic_clean.index, ic_clean.values, alpha=0.7)
    ax.axhline(y=0, color='r', linestyle='--', alpha=0.5)
    ax.set_xlabel("Data")
    ax.set_ylabel("Rank IC")
    ax.set_title("Rolling Rank IC (60d)")
    ax.grid(True, alpha=0.3)

    filepath = os.path.join(outdir, filename)
    fig.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close(fig)

    return filepath
