"""
Smoke test: report generation
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd

from utils.plotting import equity_curve, histogram_returns, rolling_ic_plot
from utils.reporting import ensure_dir, write_markdown


def test_ensure_dir():
    """Test tworzenia katalogu."""
    print("Test: ensure_dir...")

    try:
        test_dir = "test_output"
        ensure_dir(test_dir)
        assert os.path.exists(test_dir), f"Katalog {test_dir} nie został utworzony"

        # Cleanup
        os.rmdir(test_dir)

        print("  ✓ OK: ensure_dir")
        return True
    except Exception as e:
        print(f"  ✗ FAIL: {e}")
        return False


def test_write_markdown():
    """Test zapisu raportu MD."""
    print("Test: write_markdown...")

    try:
        test_dir = "test_output"
        ensure_dir(test_dir)

        report_content = "# Test Report\n\nTo jest test."
        path = write_markdown(report_content, test_dir, "test_report.md")

        assert os.path.exists(path), f"Plik {path} nie został utworzony"

        # Sprawdź zawartość
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "Test Report" in content, "Zawartość pliku niepoprawna"

        # Cleanup
        os.remove(path)
        os.rmdir(test_dir)

        print("  ✓ OK: write_markdown")
        return True
    except Exception as e:
        print(f"  ✗ FAIL: {e}")
        return False


def test_equity_curve():
    """Test generowania wykresu equity curve."""
    print("Test: equity_curve...")

    try:
        test_dir = "test_output"
        ensure_dir(test_dir)

        returns = pd.Series(np.random.randn(100) * 0.01, index=pd.date_range("2023-01-01", periods=100))
        path = equity_curve(returns, test_dir, "test_equity.png")

        assert os.path.exists(path), f"Wykres {path} nie został utworzony"
        assert path.endswith(".png"), "Plik nie jest PNG"

        # Cleanup
        os.remove(path)
        os.rmdir(test_dir)

        print("  ✓ OK: equity_curve")
        return True
    except Exception as e:
        print(f"  ✗ FAIL: {e}")
        return False


def test_histogram_returns():
    """Test generowania histogramu zwrotów."""
    print("Test: histogram_returns...")

    try:
        test_dir = "test_output"
        ensure_dir(test_dir)

        returns = pd.Series(np.random.randn(100) * 0.01, index=pd.date_range("2023-01-01", periods=100))
        path = histogram_returns(returns, test_dir, "test_hist.png")

        assert os.path.exists(path), f"Wykres {path} nie został utworzony"
        assert path.endswith(".png"), "Plik nie jest PNG"

        # Cleanup
        os.remove(path)
        os.rmdir(test_dir)

        print("  ✓ OK: histogram_returns")
        return True
    except Exception as e:
        print(f"  ✗ FAIL: {e}")
        return False


def test_rolling_ic_plot():
    """Test generowania wykresu rolling IC."""
    print("Test: rolling_ic_plot...")

    try:
        test_dir = "test_output"
        ensure_dir(test_dir)

        ic_series = pd.Series(np.random.randn(100) * 0.1, index=pd.date_range("2023-01-01", periods=100))
        path = rolling_ic_plot(ic_series, test_dir, "test_rolling_ic.png")

        assert os.path.exists(path), f"Wykres {path} nie został utworzony"
        assert path.endswith(".png"), "Plik nie jest PNG"

        # Cleanup
        os.remove(path)
        os.rmdir(test_dir)

        print("  ✓ OK: rolling_ic_plot")
        return True
    except Exception as e:
        print(f"  ✗ FAIL: {e}")
        return False


if __name__ == "__main__":
    print("=== Smoke tests: report ===\n")

    results = []
    results.append(test_ensure_dir())
    results.append(test_write_markdown())
    results.append(test_equity_curve())
    results.append(test_histogram_returns())
    results.append(test_rolling_ic_plot())

    print(f"\n=== Wyniki: {sum(results)}/{len(results)} testów OK ===")

    if all(results):
        print("✓ Wszystkie testy przeszły")
        sys.exit(0)
    else:
        print("✗ Niektóre testy nie powiodły się")
        sys.exit(1)
