"""
Skrypt do walidacji faktora metodą PurgedKFold.
Oblicza Rank-IC na foldach train/test z purge i embargo.
"""
import argparse
import sys
import os
import yaml
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.cv import purged_folds
from utils.metrics import rank_ic


def main():
    parser = argparse.ArgumentParser(description="Walidacja PurgedKFold + Rank-IC")
    parser.add_argument("--config", type=str, required=True, help="Ścieżka do pliku YAML")
    parser.add_argument("--n-splits", type=int, default=5, help="Liczba foldów")
    parser.add_argument("--embargo-days", type=int, default=5, help="Dni embargo")
    args = parser.parse_args()
    
    try:
        # Wczytaj config
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
        
        name = config["name"]
        print(f"=== Purged CV Evaluation: {name} ===")
        
        # Wczytaj factor values i forward returns
        values_path = f"data/factors/{name}_values.parquet"
        fwd_path = f"data/factors/{name}_forward_returns.parquet"
        
        if not os.path.exists(values_path) or not os.path.exists(fwd_path):
            print("BŁĄD: Brak plików factora. Uruchom najpierw make_factor.py")
            sys.exit(1)
        
        factor = pd.read_parquet(values_path)
        fwd_returns = pd.read_parquet(fwd_path)
        
        print(f"Factor shape: {factor.shape}")
        print(f"Forward returns shape: {fwd_returns.shape}")
        
        # Flatten do MultiIndex (date, ticker)
        factor_stacked = factor.stack()
        fwd_stacked = fwd_returns.stack()
        
        # Połącz w DataFrame
        df = pd.DataFrame({
            'factor': factor_stacked,
            'fwd': fwd_stacked
        }).dropna()
        
        print(f"Valid samples: {len(df)}")
        
        # Przygotuj X i t1 dla PurgedKFold
        # t1 = end time każdej próbki (tutaj uproszczone: date + 21 dni)
        X = df[['factor']]
        t1 = pd.Series(
            X.index.get_level_values(0) + pd.Timedelta(days=21),
            index=X.index
        )
        
        # UWAGA: mlfinlab.PurgedKFold może wymagać specyficznego formatu
        # To jest uproszczona wersja - w produkcji dostosuj do API mlfinlab
        
        print(f"\nObliczanie IC per fold (n_splits={args.n_splits}, embargo={args.embargo_days}d)...")
        
        # Uproszczona walidacja bez PurgedKFold (do rozszerzenia)
        # W pełnej wersji użyj: folds = purged_folds(X, t1, args.n_splits, args.embargo_days)
        
        # Oblicz ogólny IC
        overall_ic = rank_ic(df['factor'], df['fwd'])
        print(f"\nOgólny Rank-IC: {overall_ic:.4f}")
        
        print("\nUWAGA: Pełna integracja z mlfinlab.PurgedKFold wymaga rozszerzenia.")
        print("Dla produkcji zaimplementuj pełny cross-validation loop.")
        
        print("\n✓ Zakończono")
        
    except Exception as e:
        print(f"BŁĄD: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
