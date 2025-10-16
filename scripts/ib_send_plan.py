import argparse
import os

from brokers.ib_exec import send_plan_csv


def main() -> None:
    parser = argparse.ArgumentParser(description="Wyślij plan zleceń do IBKR")
    parser.add_argument("--plan", required=True, help="Ścieżka do planu CSV (orders/plan_*.csv)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Tryb suchy – nie wysyłaj zleceń, tylko loguj.",
    )
    parser.add_argument("--account", default=os.getenv("IB_ACCOUNT"))
    parser.add_argument("--map", default="data/symbol_exchange_map.csv")
    args = parser.parse_args()

    send_plan_csv(
        args.plan,
        symbol_map_csv=args.map,
        account=args.account,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
