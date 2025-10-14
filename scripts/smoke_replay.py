"""
Skrypt smoke replay: uruchamia report z ostatnim snapshotem (deterministyczność).
"""
import os
import sys
from subprocess import run


def main(cfg: str = "configs/example_mom12_1.yaml"):
    """
    Uruchamia report_daily.py jako smoke test.

    Args:
        cfg: Ścieżka do configu
    """
    print(f"🔬 Smoke replay: {cfg}")

    rc = run([sys.executable, "backtests/report_daily.py", "--config", cfg], check=False)

    if rc.returncode == 0:
        print("✓ Smoke replay PASSED")
    else:
        print(f"❌ Smoke replay FAILED (exit code: {rc.returncode})")

    sys.exit(rc.returncode)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Smoke replay test")
    ap.add_argument("--config", default="configs/example_mom12_1.yaml", help="Config YAML")
    args = ap.parse_args()

    main(args.config)
