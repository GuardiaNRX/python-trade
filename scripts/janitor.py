"""
Skrypt janitor: czyszczenie starych artefaktów (retencja).
"""
import argparse
import glob
import os
import shutil
import time


def _prune_by_days(path: str, days: int) -> None:
    """
    Usuwa pliki/katalogi starsze niż N dni.

    Args:
        path: Ścieżka do katalogu
        days: Liczba dni retencji
    """
    if not os.path.exists(path):
        return

    cutoff = time.time() - days * 86400

    for p in glob.glob(os.path.join(path, "*")):
        try:
            if os.path.isdir(p):
                # Dla katalogów: sprawdź najnowszy plik wewnątrz
                mtimes = [os.path.getmtime(r) for r, _, _ in os.walk(p)]
                if mtimes and max(mtimes) < cutoff:
                    shutil.rmtree(p, ignore_errors=True)
                    print(f"Usunięto katalog: {p}")
            else:
                # Dla plików: sprawdź mtime
                if os.path.getmtime(p) < cutoff:
                    os.remove(p)
                    print(f"Usunięto plik: {p}")
        except Exception as e:
            print(f"Błąd przy usuwaniu {p}: {e}")


def main():
    """Główna funkcja janitor."""
    ap = argparse.ArgumentParser(description="Janitor: czyszczenie starych artefaktów")
    ap.add_argument("--reports_days", type=int, default=30, help="Retencja raportów (dni)")
    ap.add_argument("--orders_days", type=int, default=90, help="Retencja zleceń (dni)")
    ap.add_argument("--snapshots_days", type=int, default=365, help="Retencja snapshots (dni)")
    args = ap.parse_args()

    print(f"Czyszczenie artefaktów (retencja: reports={args.reports_days}d, orders={args.orders_days}d, snapshots={args.snapshots_days}d)")

    _prune_by_days("backtests/reports", args.reports_days)
    _prune_by_days("backtests/results/orders", args.orders_days)
    _prune_by_days("data/source_snapshots", args.snapshots_days)

    print("✓ Janitor zakończony")


if __name__ == "__main__":
    main()
