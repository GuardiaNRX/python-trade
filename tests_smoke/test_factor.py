"""
Smoke test: factor computation
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from factors.momentum_12_1 import compute_factor, percentile_rank


def test_compute_factor():
    """Test że compute_factor zwraca DataFrame z wartościami."""
    print("Test: compute_factor...")

    # Dummy prices
    dates = pd.date_range("2020-01-01", periods=500, freq="D")
    prices = pd.DataFrame(np.random.rand(500, 3) * 100 + 50, index=dates, columns=["A", "B", "C"])

    try:
        factor = compute_factor(prices, lookback_months=12, skip_recent_months=1)

        assert isinstance(factor, pd.DataFrame), "factor nie jest DataFrame"
        assert factor.shape == prices.shape, "factor ma inny kształt niż prices"
        assert not factor.isnull().all().all(), "factor zawiera tylko NaN"

        print("  ✓ OK: compute_factor działa")
        return True

    except Exception as e:
        print(f"  ✗ FAIL: {e}")
        return False


def test_percentile_rank():
    """Test że percentile_rank zwraca ranki w zakresie [0, 1]."""
    print("Test: percentile_rank...")

    # Dummy factor
    dates = pd.date_range("2023-01-01", periods=100, freq="D")
    factor = pd.DataFrame(np.random.randn(100, 5), index=dates, columns=list("ABCDE"))

    try:
        ranks = percentile_rank(factor)

        assert isinstance(ranks, pd.DataFrame), "ranks nie jest DataFrame"
        assert ranks.shape == factor.shape, "ranks ma inny kształt niż factor"

        # Sprawdź zakres [0, 1]
        ranks_clean = ranks.dropna()
        if not ranks_clean.empty:
            assert ranks_clean.min().min() >= 0, "ranks zawiera wartości < 0"
            assert ranks_clean.max().max() <= 1, "ranks zawiera wartości > 1"

        print("  ✓ OK: percentile_rank działa")
        return True

    except Exception as e:
        print(f"  ✗ FAIL: {e}")
        return False


if __name__ == "__main__":
    print("=== Smoke tests: factor ===\n")

    results = []
    results.append(test_compute_factor())
    results.append(test_percentile_rank())

    print(f"\n=== Wyniki: {sum(results)}/{len(results)} testów OK ===")

    if all(results):
        print("✓ Wszystkie testy przeszły")
        sys.exit(0)
    else:
        print("✗ Niektóre testy nie powiodły się")
        sys.exit(1)
