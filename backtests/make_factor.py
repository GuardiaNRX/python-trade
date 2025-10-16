"""
Skrypt do generowania wartości faktora i rankingów.
Zapisuje do data/factors/ pliki parquet: values, ranks, forward_returns.
"""
import argparse
import os
import sys

import yaml

# Dodaj katalog główny do sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from factors.momentum_12_1 import compute_factor, percentile_rank
from utils.data_io import load_prices


def main():
    parser = argparse.ArgumentParser(description="Generowanie faktora momentum 12-1")
    parser.add_argument("--config", type=str, required=True, help="Ścieżka do pliku YAML")
    args = parser.parse_args()
    
    try:
        # Wczytaj config
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
        
        name = config["name"]
        print(f"=== Generowanie faktora: {name} ===")
        
        # Pobierz dane
        print("Pobieranie danych cenowych...")
        prices = load_prices(
            universe=config["universe"],
            start=config["data"]["start"],
            end=config["data"]["end"],
            source=config["data"]["source"],
            csv_dir=config["data"]["csv_dir"]
        )
        print(f"Pobrano dane: {prices.shape}")
        
        # Oblicz faktor
        print("Obliczanie faktora momentum...")
        factor_values = compute_factor(
            prices,
            **config["factor"]["params"]
        )
        
        # Oblicz rankingi
        print("Obliczanie rankingów percentylowych...")
        factor_ranks = percentile_rank(factor_values)
        
        # Oblicz forward returns (1 miesiąc = 21 dni)
        print("Obliczanie forward returns...")
        forward_returns = prices.pct_change(21).shift(-21)
        
        # Zapisz do parquet
        os.makedirs("data/factors", exist_ok=True)
        
        values_path = f"data/factors/{name}_values.parquet"
        ranks_path = f"data/factors/{name}_ranks.parquet"
        fwd_path = f"data/factors/{name}_forward_returns.parquet"
        
        factor_values.to_parquet(values_path)
        factor_ranks.to_parquet(ranks_path)
        forward_returns.to_parquet(fwd_path)
        
        print("Zapisano:")
        print(f"  - {values_path}")
        print(f"  - {ranks_path}")
        print(f"  - {fwd_path}")
        print("✓ Zakończono pomyślnie")
        
    except Exception as e:
        print(f"BŁĄD: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
