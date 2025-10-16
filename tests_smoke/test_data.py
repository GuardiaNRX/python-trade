"""
Smoke test: data loading + liquidity filters
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd

from utils.data_io import apply_liquidity_filters, load_prices_and_volume


def test_load_prices_and_volume():
    """Test że load_prices_and_volume zwraca DataFrames."""
    print("Test: load_prices_and_volume...")

    universe = ["AAPL", "MSFT"]
    start = "2023-01-01"
    end = "2023-12-31"

    try:
        prices, volume = load_prices_and_volume(universe, start, end, source="yfinance", csv_dir="data")

        assert isinstance(prices, pd.DataFrame), "prices nie jest DataFrame"
        assert isinstance(volume, pd.DataFrame), "volume nie jest DataFrame"
        assert prices.shape[0] > 0, "prices jest pusty"
        assert volume.shape[0] > 0, "volume jest pusty"
        assert prices.shape == volume.shape, "prices i volume mają różne kształty"

        print("  ✓ OK: load_prices_and_volume działa")
        return True

    except Exception as e:
        print(f"  ✗ FAIL: {e}")
        return False


def test_apply_liquidity_filters():
    """Test że filtry płynności działają."""
    print("Test: apply_liquidity_filters...")

    # Dummy data
    import numpy as np
    dates = pd.date_range("2023-01-01", periods=100, freq="D")
    prices = pd.DataFrame(np.random.rand(100, 3) * 100, index=dates, columns=["A", "B", "C"])
    volume = pd.DataFrame(np.random.rand(100, 3) * 1_000_000, index=dates, columns=["A", "B", "C"])

    # Ustaw jeden ticker poniżej progu
    prices["C"] = 3.0  # < 5.0

    try:
        filtered_prices, filtered_volume = apply_liquidity_filters(
            prices, volume,
            min_price=5.0,
            adv_window=30,
            min_adv_usd=10_000
        )

        assert isinstance(filtered_prices, pd.DataFrame), "filtered_prices nie jest DataFrame"
        assert filtered_prices.shape[1] <= prices.shape[1], "Filtry nie usunęły żadnych tickerów"
        assert "C" not in filtered_prices.columns, "Ticker C powinien być odfiltrowany (cena < 5.0)"

        print("  ✓ OK: apply_liquidity_filters działa")
        return True

    except Exception as e:
        print(f"  ✗ FAIL: {e}")
        return False


if __name__ == "__main__":
    print("=== Smoke tests: data ===\n")

    results = []
    results.append(test_load_prices_and_volume())
    results.append(test_apply_liquidity_filters())

    print(f"\n=== Wyniki: {sum(results)}/{len(results)} testów OK ===")

    if all(results):
        print("✓ Wszystkie testy przeszły")
        sys.exit(0)
    else:
        print("✗ Niektóre testy nie powiodły się")
        sys.exit(1)
