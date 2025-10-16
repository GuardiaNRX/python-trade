"""
Moduł do obliczania Probability of Backtest Overfitting (PBO).

Implementacja oparta na metodologii Lopez de Prado:
"Pseudo-Mathematics and Financial Charlatanism: The Effects of Backtest Overfitting on Out-of-Sample Performance"

PBO używa Combinatorially Symmetric Cross-Validation (CSCV) do wykrywania overfittingu.
"""
from itertools import combinations
from typing import Dict

import numpy as np
import pandas as pd


def compute_pbo_cscv(
    returns_matrix: pd.DataFrame,
    n_splits: int = 10,
    seed: int = 42
) -> Dict[str, float]:
    """
    Oblicza Probability of Backtest Overfitting (PBO) używając CSCV.

    Metodologia:
    1. Podziel serię zwrotów na n_splits grup (bloków)
    2. Dla każdej kombinacji S bloków do treningu (pozostałe = test):
       - Wybierz strategię z najwyższym Sharpe na treningu
       - Oblicz Sharpe tej strategii na tescie
    3. PBO = P(Sharpe_test <= mediana(Sharpe_test))
    4. Dodatkowo oblicz:
       - λ (lambda): log odds overfittingu
       - Degradation: spadek performance z train → test

    UWAGA: returns_matrix powinien zawierać zwroty dla RÓŻNYCH KONFIGURACJI strategii.
    Jeśli masz tylko jedną strategię, PBO nie ma sensu (trzeba testować wiele wariantów).

    Parameters:
    -----------
    returns_matrix : pd.DataFrame
        DataFrame z zwrotami różnych konfiguracji strategii
        (index: datetime, kolumny: nazwy konfiguracji, np. "config_1", "config_2", ...)
        Każda kolumna = inna konfiguracja/parametry strategii
    n_splits : int
        Liczba bloków do podziału (domyślnie 10)
        Liczba kombinacji = C(n_splits, n_splits//2)
    seed : int
        Seed dla reprodukowalności (domyślnie 42)

    Returns:
    --------
    Dict[str, float]
        {
            "PBO": Probability of Backtest Overfitting (0-1, >0.5 = overfitting)
            "lambda": Log odds overfittingu
            "degradation_mean": Średni spadek Sharpe (train → test)
            "degradation_median": Mediana spadku Sharpe
            "n_combinations": Liczba testowanych kombinacji
            "sharpe_train_median": Mediana Sharpe na treningu
            "sharpe_test_median": Mediana Sharpe na tescie
        }
    """
    np.random.seed(seed)

    # Sprawdź wymiary
    if returns_matrix.shape[1] < 2:
        raise ValueError("PBO wymaga co najmniej 2 konfiguracji strategii (kolumny w returns_matrix)")

    if len(returns_matrix) < n_splits:
        raise ValueError(f"Zbyt mało obserwacji ({len(returns_matrix)}) dla n_splits={n_splits}")

    # Podziel dane na bloki
    n_obs = len(returns_matrix)
    block_size = n_obs // n_splits
    blocks = []

    for i in range(n_splits):
        start_idx = i * block_size
        end_idx = start_idx + block_size if i < n_splits - 1 else n_obs
        blocks.append(returns_matrix.iloc[start_idx:end_idx])

    # Generuj kombinacje: połowa bloków do treningu, połowa do testu
    n_train_blocks = n_splits // 2
    train_combinations = list(combinations(range(n_splits), n_train_blocks))

    sharpe_train_list = []
    sharpe_test_list = []
    degradation_list = []

    for train_indices in train_combinations:
        test_indices = [i for i in range(n_splits) if i not in train_indices]

        # Połącz bloki treningowe i testowe
        train_data = pd.concat([blocks[i] for i in train_indices], axis=0)
        test_data = pd.concat([blocks[i] for i in test_indices], axis=0)

        # Oblicz Sharpe dla każdej konfiguracji na treningu
        sharpe_train = train_data.apply(lambda x: _sharpe_ratio(x), axis=0)

        # Znajdź konfigurację z najwyższym Sharpe na treningu
        best_config = sharpe_train.idxmax()
        best_sharpe_train = sharpe_train[best_config]

        # Oblicz Sharpe tej samej konfiguracji na tescie
        best_sharpe_test = _sharpe_ratio(test_data[best_config])

        sharpe_train_list.append(best_sharpe_train)
        sharpe_test_list.append(best_sharpe_test)
        degradation_list.append(best_sharpe_train - best_sharpe_test)

    sharpe_train_arr = np.array(sharpe_train_list)
    sharpe_test_arr = np.array(sharpe_test_list)
    degradation_arr = np.array(degradation_list)

    # Oblicz PBO: P(Sharpe_test <= mediana(Sharpe_test))
    sharpe_test_median = np.median(sharpe_test_arr)
    pbo = np.mean(sharpe_test_arr <= sharpe_test_median)

    # Oblicz lambda (log odds)
    if pbo == 0:
        lambda_val = -np.inf
    elif pbo == 1:
        lambda_val = np.inf
    else:
        lambda_val = np.log(pbo / (1 - pbo))

    # Degradacja
    degradation_mean = np.mean(degradation_arr)
    degradation_median = np.median(degradation_arr)

    results = {
        "PBO": pbo,
        "lambda": lambda_val,
        "degradation_mean": degradation_mean,
        "degradation_median": degradation_median,
        "n_combinations": len(train_combinations),
        "sharpe_train_median": np.median(sharpe_train_arr),
        "sharpe_test_median": sharpe_test_median,
    }

    return results


def _sharpe_ratio(returns: pd.Series) -> float:
    """
    Oblicza Sharpe Ratio dla serii zwrotów.

    Parameters:
    -----------
    returns : pd.Series
        Seria zwrotów

    Returns:
    --------
    float
        Sharpe Ratio
    """
    if len(returns) == 0 or returns.std() == 0:
        return 0.0

    mean_ret = returns.mean()
    std_ret = returns.std()
    sharpe = mean_ret / std_ret * np.sqrt(252)  # Annualized

    return sharpe


def compute_pbo_simple(
    returns_train: pd.Series,
    returns_test: pd.Series
) -> Dict[str, float]:
    """
    Oblicza uproszczoną wersję PBO dla jednej strategii (bez CSCV).

    Sprawdza czy performance na tescie jest istotnie gorszy niż na treningu.
    Nie wymaga wielu konfiguracji, ale jest mniej dokładny niż CSCV.

    Parameters:
    -----------
    returns_train : pd.Series
        Seria zwrotów na zbiorze treningowym
    returns_test : pd.Series
        Seria zwrotów na zbiorze testowym

    Returns:
    --------
    Dict[str, float]
        {
            "sharpe_train": Sharpe na treningu
            "sharpe_test": Sharpe na tescie
            "degradation": Spadek Sharpe (train - test)
            "degradation_pct": Spadek Sharpe w % względem train
        }
    """
    sharpe_train = _sharpe_ratio(returns_train)
    sharpe_test = _sharpe_ratio(returns_test)

    degradation = sharpe_train - sharpe_test

    if sharpe_train == 0:
        degradation_pct = 0.0
    else:
        degradation_pct = (degradation / abs(sharpe_train)) * 100.0

    results = {
        "sharpe_train": sharpe_train,
        "sharpe_test": sharpe_test,
        "degradation": degradation,
        "degradation_pct": degradation_pct,
    }

    return results
