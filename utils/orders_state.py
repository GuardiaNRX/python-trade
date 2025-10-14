"""
Moduł orders_state: zapisywanie i anulowanie planów zleceń.
"""
import os
import pandas as pd


def save_plan(plan: pd.DataFrame, run_id: str, out_dir: str = "backtests/results/orders") -> str:
    """
    Zapisuje plan zleceń do CSV z run_id.

    Args:
        plan: DataFrame z planem zleceń
        run_id: Unikalny ID runu
        out_dir: Katalog docelowy

    Returns:
        Ścieżka do zapisanego pliku
    """
    os.makedirs(out_dir, exist_ok=True)

    p = os.path.join(out_dir, f"plan_{run_id}.csv")
    plan.to_csv(p, index=False)

    # Zapisz ostatni run_id
    with open(os.path.join(out_dir, "last_run_id.txt"), "w") as f:
        f.write(run_id + "\n")

    return p


def cancel_file_for_last_run(out_dir: str = "backtests/results/orders") -> str:
    """
    Generuje plik anulowań dla ostatniego runu.

    Args:
        out_dir: Katalog z planami

    Returns:
        Ścieżka do pliku cancel CSV lub None jeśli brak ostatniego planu
    """
    last = os.path.join(out_dir, "last_run_id.txt")
    if not os.path.exists(last):
        return None

    runid = open(last).read().strip()
    plan_path = os.path.join(out_dir, f"plan_{runid}.csv")

    if not os.path.exists(plan_path):
        return None

    df = pd.read_csv(plan_path)
    df["action"] = "CANCEL"

    cancel_path = os.path.join(out_dir, f"cancel_{runid}.csv")
    df[["symbol", "side", "qty_usd", "action"]].to_csv(cancel_path, index=False)

    return cancel_path
