"""
Skrypt do szybkiego backtestingu strategii przy użyciu vectorbt.
"""
import argparse
import os
import sys

import pandas as pd
import yaml
from tabulate import tabulate

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    parser = argparse.ArgumentParser(description="Grid backtest z vectorbt")
    parser.add_argument("--config", type=str, required=True, help="Ścieżka do pliku YAML")
    args = parser.parse_args()
    
    try:
        # Wczytaj config
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
        
        name = config["name"]
        print(f"=== Grid Backtest: {name} ===")
        
        # Wczytaj rankingi i ceny
        ranks_path = f"data/factors/{name}_ranks.parquet"
        
        if not os.path.exists(ranks_path):
            print(f"BŁĄD: Brak pliku {ranks_path}. Uruchom najpierw make_factor.py")
            sys.exit(1)
        
        ranks = pd.read_parquet(ranks_path)
        print(f"Wczytano rankingi: {ranks.shape}")
        
        # Uproszczona symulacja - tu można dodać vectorbt
        print("\nUWAGA: Pełna integracja z vectorbt wymaga rozszerzenia.")
        print("Przykładowe statystyki:")
        
        stats_data = [
            ["Total Days", len(ranks)],
            ["Assets", ranks.shape[1]],
            ["Non-null values", ranks.count().sum()]
        ]
        
        print(tabulate(stats_data, headers=["Metryka", "Wartość"], tablefmt="grid"))
        print("\n✓ Zakończono")
        
    except Exception as e:
        print(f"BŁĄD: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
