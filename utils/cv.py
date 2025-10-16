"""
Moduł do cross-validation z purge i embargo.
"""
from typing import List, Tuple

import pandas as pd
from mlfinlab.cross_validation import PurgedKFold


def purged_folds(
    X: pd.DataFrame,
    t1: pd.Series,
    n_splits: int = 5,
    embargo_days: int = 5
) -> List[Tuple[pd.Index, pd.Index]]:
    """
    Wrapper na mlfinlab.cross_validation.PurgedKFold.
    
    Zwraca indeksy train/test z purge i embargo dla szeregów czasowych.
    
    Parameters:
    -----------
    X : pd.DataFrame
        Dane wejściowe (features)
    t1 : pd.Series
        Seria z czasem końca każdej próbki (end time)
    n_splits : int
        Liczba foldów
    embargo_days : int
        Liczba dni embargo po każdym foldie testowym
        
    Returns:
    --------
    List[Tuple[pd.Index, pd.Index]]
        Lista par (train_idx, test_idx)
    """
    # PurgedKFold wymaga pd.Series dla t1
    if not isinstance(t1, pd.Series):
        raise ValueError("t1 musi być pd.Series z indeksem datetime")
    
    cv = PurgedKFold(
        n_splits=n_splits,
        samples_info_sets=t1,
        pct_embargo=0.0  # Używamy timedelta zamiast pct
    )
    
    folds = []
    for train_idx, test_idx in cv.split(X):
        folds.append((train_idx, test_idx))
    
    return folds
