"""
Smoke test: metrics calculations
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from utils.metrics import (
    alpha_beta,
    expected_shortfall,
    hit_rate,
    information_ratio,
    max_drawdown,
    payoff_ratio,
    rank_ic,
    sharpe,
    sortino,
    tail_ratio,
)


def test_sharpe():
    """Test Sharpe Ratio."""
    print("Test: sharpe...")
    returns = pd.Series(np.random.randn(100) * 0.01)

    try:
        sr = sharpe(returns, freq=252)
        assert isinstance(sr, (int, float)), "sharpe nie zwraca liczby"
        assert not np.isnan(sr), "sharpe zwraca NaN"
        print("  ✓ OK: sharpe")
        return True
    except Exception as e:
        print(f"  ✗ FAIL: {e}")
        return False


def test_sortino():
    """Test Sortino Ratio."""
    print("Test: sortino...")
    returns = pd.Series(np.random.randn(100) * 0.01)

    try:
        sortino_r = sortino(returns, freq=252)
        assert isinstance(sortino_r, (int, float)), "sortino nie zwraca liczby"
        print("  ✓ OK: sortino")
        return True
    except Exception as e:
        print(f"  ✗ FAIL: {e}")
        return False


def test_max_drawdown():
    """Test Max Drawdown."""
    print("Test: max_drawdown...")
    returns = pd.Series(np.random.randn(100) * 0.01)

    try:
        mdd = max_drawdown(returns)
        assert isinstance(mdd, (int, float)), "max_drawdown nie zwraca liczby"
        assert mdd <= 0, "max_drawdown powinno być <= 0"
        print("  ✓ OK: max_drawdown")
        return True
    except Exception as e:
        print(f"  ✗ FAIL: {e}")
        return False


def test_rank_ic():
    """Test Rank IC."""
    print("Test: rank_ic...")
    factor = pd.Series(np.random.randn(50), index=range(50))
    fwd = pd.Series(np.random.randn(50), index=range(50))

    try:
        ic = rank_ic(factor, fwd)
        assert isinstance(ic, (int, float)), "rank_ic nie zwraca liczby"
        assert -1 <= ic <= 1, "rank_ic poza zakresem [-1, 1]"
        print("  ✓ OK: rank_ic")
        return True
    except Exception as e:
        print(f"  ✗ FAIL: {e}")
        return False


def test_information_ratio():
    """Test Information Ratio."""
    print("Test: information_ratio...")
    returns = pd.Series(np.random.randn(100) * 0.01, index=pd.date_range("2023-01-01", periods=100))
    bench = pd.Series(np.random.randn(100) * 0.01, index=pd.date_range("2023-01-01", periods=100))

    try:
        ir = information_ratio(returns, bench, freq=252)
        assert isinstance(ir, (int, float)), "information_ratio nie zwraca liczby"
        print("  ✓ OK: information_ratio")
        return True
    except Exception as e:
        print(f"  ✗ FAIL: {e}")
        return False


def test_alpha_beta():
    """Test Alpha/Beta."""
    print("Test: alpha_beta...")
    returns = pd.Series(np.random.randn(100) * 0.01, index=pd.date_range("2023-01-01", periods=100))
    bench = pd.Series(np.random.randn(100) * 0.01, index=pd.date_range("2023-01-01", periods=100))

    try:
        alpha, beta = alpha_beta(returns, bench, freq=252)
        assert isinstance(alpha, (int, float)), "alpha nie jest liczbą"
        assert isinstance(beta, (int, float)), "beta nie jest liczbą"
        print("  ✓ OK: alpha_beta")
        return True
    except Exception as e:
        print(f"  ✗ FAIL: {e}")
        return False


def test_expected_shortfall():
    """Test Expected Shortfall."""
    print("Test: expected_shortfall...")
    returns = pd.Series(np.random.randn(100) * 0.01)

    try:
        es = expected_shortfall(returns, confidence=0.95)
        assert isinstance(es, (int, float)), "expected_shortfall nie zwraca liczby"
        print("  ✓ OK: expected_shortfall")
        return True
    except Exception as e:
        print(f"  ✗ FAIL: {e}")
        return False


def test_tail_ratio():
    """Test Tail Ratio."""
    print("Test: tail_ratio...")
    returns = pd.Series(np.random.randn(100) * 0.01)

    try:
        tr = tail_ratio(returns)
        assert isinstance(tr, (int, float)), "tail_ratio nie zwraca liczby"
        print("  ✓ OK: tail_ratio")
        return True
    except Exception as e:
        print(f"  ✗ FAIL: {e}")
        return False


def test_hit_rate():
    """Test Hit Rate."""
    print("Test: hit_rate...")
    factor = pd.Series(np.random.randn(50), index=range(50))
    fwd = pd.Series(np.random.randn(50), index=range(50))

    try:
        hr = hit_rate(factor, fwd)
        assert isinstance(hr, (int, float)), "hit_rate nie zwraca liczby"
        assert 0 <= hr <= 1, "hit_rate poza zakresem [0, 1]"
        print("  ✓ OK: hit_rate")
        return True
    except Exception as e:
        print(f"  ✗ FAIL: {e}")
        return False


def test_payoff_ratio():
    """Test Payoff Ratio."""
    print("Test: payoff_ratio...")
    factor = pd.Series(np.random.randn(50), index=range(50))
    fwd = pd.Series(np.random.randn(50), index=range(50))

    try:
        pr = payoff_ratio(factor, fwd)
        assert isinstance(pr, (int, float)), "payoff_ratio nie zwraca liczby"
        print("  ✓ OK: payoff_ratio")
        return True
    except Exception as e:
        print(f"  ✗ FAIL: {e}")
        return False


if __name__ == "__main__":
    print("=== Smoke tests: metrics ===\n")

    results = []
    results.append(test_sharpe())
    results.append(test_sortino())
    results.append(test_max_drawdown())
    results.append(test_rank_ic())
    results.append(test_information_ratio())
    results.append(test_alpha_beta())
    results.append(test_expected_shortfall())
    results.append(test_tail_ratio())
    results.append(test_hit_rate())
    results.append(test_payoff_ratio())

    print(f"\n=== Wyniki: {sum(results)}/{len(results)} testów OK ===")

    if all(results):
        print("✓ Wszystkie testy przeszły")
        sys.exit(0)
    else:
        print("✗ Niektóre testy nie powiodły się")
        sys.exit(1)
