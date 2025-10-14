"""
Moduł broker: Paper broker z retry + timeouts.
"""
import os
import time
import pandas as pd
from dataclasses import dataclass
from typing import List


@dataclass
class SubmitResult:
    """Wynik submitu zleceń."""
    ok: bool
    submitted: int
    errors: List[str]


class PaperBroker:
    """Paper broker: symuluje egzekucję zleceń z zapisem do CSV."""

    def __init__(
        self,
        out_dir: str = "backtests/results/paper",
        max_parallel: int = 20,
        timeout_sec: int = 5,
        retries: int = 2
    ):
        """
        Inicjalizacja paper brokera.

        Args:
            out_dir: Katalog na pliki fills/positions
            max_parallel: Maksymalna liczba równoległych zleceń
            timeout_sec: Timeout per zlecenie
            retries: Liczba prób
        """
        os.makedirs(out_dir, exist_ok=True)
        self.out_dir = out_dir
        self.max_parallel = max_parallel
        self.timeout_sec = timeout_sec
        self.retries = retries

    def positions(self) -> pd.Series:
        """
        Zwraca aktualne pozycje (z CSV).

        Returns:
            Seria position qty per symbol
        """
        p = os.path.join(self.out_dir, "positions.csv")
        if not os.path.exists(p):
            return pd.Series(dtype=float)

        df = pd.read_csv(p)
        return df.set_index("symbol")["quantity"].astype(float)

    def submit(self, plan: pd.DataFrame, run_id: str) -> SubmitResult:
        """
        Submituje plan zleceń (paper execution).

        Args:
            plan: DataFrame z planem (slice_time, symbol, side, qty_usd, limit_price)
            run_id: ID runu

        Returns:
            SubmitResult z wynikiem
        """
        # Throttle do max_parallel
        plan = plan.copy().head(self.max_parallel)
        plan["client_id"] = [f"{run_id}_{i}" for i in range(len(plan))]

        # Symulacja filli = wpis do CSV „fills"
        fills = []
        errs = []

        for _, row in plan.iterrows():
            ok = False
            for t in range(self.retries + 1):
                try:
                    time.sleep(0.01)  # Symulacja latency
                    fills.append({
                        "ts": pd.Timestamp.utcnow().isoformat(),
                        "symbol": row["symbol"],
                        "side": row["side"],
                        "exec_price": row.get("limit_price", 0.0),
                        "mid_price": row.get("limit_price", 0.0),
                        "notional": row.get("qty_usd", 0.0),
                        "adv_usd": 0.0,
                        "client_id": row["client_id"]
                    })
                    ok = True
                    break
                except Exception as e:
                    if t == self.retries:
                        errs.append(str(e))
                    time.sleep(2 ** t)

            if not ok:
                errs.append(f"submit_failed:{row['symbol']}")

        # Zapis fills
        fp = os.path.join(self.out_dir, "fills.csv")
        pd.DataFrame(fills).to_csv(fp, mode="a", index=False, header=not os.path.exists(fp))

        return SubmitResult(ok=(len(errs) == 0), submitted=len(fills), errors=errs)

    def cancel_stale(self) -> bool:
        """
        Anuluje stare zlecenia (w paper to tylko log).

        Returns:
            True jeśli OK
        """
        p = os.path.join(self.out_dir, "cancels.log")
        with open(p, "a") as f:
            f.write(pd.Timestamp.utcnow().isoformat() + " CANCEL ALL\n")
        return True
