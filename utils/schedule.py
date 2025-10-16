"""
Moduł do harmonogramowania zadań (cron + Prefect).
"""
import argparse

import yaml


def cron_example() -> None:
    """Wypisuje przykładowy wpis cron dla Europe/Warsaw."""
    print("=" * 60)
    print("Przykładowy wpis cron (pn-pt, 22:30 czasu PL):")
    print("=" * 60)
    print("""
# Uruchamianie raportu dziennego
30 22 * * 1-5 /usr/bin/env bash -lc 'cd /srv/alpha-lab && source .venv/bin/activate && python backtests/report_daily.py --config configs/example_mom12_1.yaml >> logs/report.log 2>&1'
    """)
    print("=" * 60)


def prefect_flow(config_path: str) -> None:
    """
    Buduje prosty Prefect flow dla pipeline'u.
    
    Parameters:
    -----------
    config_path : str
        Ścieżka do pliku konfiguracyjnego YAML
    """
    try:
        from prefect import flow, task
    except ImportError:
        print("BŁĄD: Prefect nie jest zainstalowany. Uruchom: pip install prefect")
        return
    
    # Import modułów projektu
    from factors.momentum_12_1 import compute_factor, percentile_rank
    from utils.data_io import load_prices
    from utils.metrics import rank_ic
    
    @task(name="Fetch Data")
    def task_fetch(config):
        """Pobiera dane cenowe."""
        print("Pobieranie danych...")
        prices = load_prices(
            universe=config["universe"],
            start=config["data"]["start"],
            end=config["data"]["end"],
            source=config["data"]["source"],
            csv_dir=config["data"]["csv_dir"]
        )
        return prices
    
    @task(name="Compute Factor")
    def task_factor(prices, config):
        """Oblicza faktor momentum."""
        print("Obliczanie faktora momentum...")
        factor = compute_factor(
            prices,
            **config["factor"]["params"]
        )
        ranks = percentile_rank(factor)
        return factor, ranks
    
    @task(name="Evaluate")
    def task_eval(factor, ranks, prices):
        """Oblicza metryki."""
        print("Obliczanie metryk...")
        # Forward returns (uproszczone)
        fwd_returns = prices.pct_change(21).shift(-21)
        
        # Flatten dla IC
        factor_flat = factor.stack()
        fwd_flat = fwd_returns.stack()
        
        ic = rank_ic(factor_flat, fwd_flat)
        print(f"Rank IC: {ic:.4f}")
        return ic
    
    @task(name="Generate Report")
    def task_report(ic):
        """Generuje raport."""
        print(f"Generowanie raportu... IC={ic:.4f}")
        return f"Raport: IC={ic:.4f}"
    
    @task(name="Send to Slack")
    def task_slack(report):
        """Wysyła raport na Slack."""
        print(f"Wysyłanie na Slack: {report}")
        # W rzeczywistości: SlackNotifier().post_message(report)
    
    @flow(name="Alpha-Lab Daily Pipeline")
    def alpha_lab_flow(config_path: str):
        """Główny flow Prefect."""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        prices = task_fetch(config)
        factor, ranks = task_factor(prices, config)
        ic = task_eval(factor, ranks, prices)
        report = task_report(ic)
        task_slack(report)
    
    print(f"Uruchamianie Prefect flow z configiem: {config_path}")
    alpha_lab_flow(config_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Harmonogramowanie alpha-lab")
    parser.add_argument("--cron", action="store_true", help="Wyświetl przykład cron")
    parser.add_argument("--prefect", action="store_true", help="Uruchom Prefect flow")
    parser.add_argument("--config", type=str, help="Ścieżka do pliku config YAML")
    
    args = parser.parse_args()
    
    if args.cron:
        cron_example()
    elif args.prefect:
        if not args.config:
            print("BŁĄD: --prefect wymaga --config")
            exit(1)
        prefect_flow(args.config)
    else:
        parser.print_help()
