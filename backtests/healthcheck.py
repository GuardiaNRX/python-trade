"""
Skrypt healthcheck: sprawdza, czy ostatni raport nie jest zbyt stary.
"""
import argparse
import glob
import os
import sys
import time


def main(out_dir: str = "backtests/reports", max_age_min: int = 120):
    """
    Sprawdza świeżość ostatniego raportu.

    Args:
        out_dir: Katalog z raportami
        max_age_min: Maksymalny wiek raportu w minutach

    Returns:
        Exit code: 0 = OK, 2 = brak plików, 3 = raport zbyt stary
    """
    pattern = os.path.join(out_dir, "*_report*.md")
    files = sorted(glob.glob(pattern))

    if not files:
        print(f"❌ Brak raportów w {out_dir}", file=sys.stderr)
        sys.exit(2)

    last = max(files, key=os.path.getmtime)
    age = (time.time() - os.path.getmtime(last)) / 60

    if age <= max_age_min:
        print(f"✓ Ostatni raport: {os.path.basename(last)} ({age:.1f} min temu)")
        sys.exit(0)
    else:
        print(f"❌ Ostatni raport zbyt stary: {age:.1f} min (max: {max_age_min})", file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Sprawdza świeżość ostatniego raportu")
    ap.add_argument("--out_dir", default="backtests/reports", help="Katalog z raportami")
    ap.add_argument("--max_age_min", type=int, default=120, help="Maksymalny wiek w minutach")
    args = ap.parse_args()

    main(args.out_dir, args.max_age_min)
