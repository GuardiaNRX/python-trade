import os
from typing import Optional

import pandas as pd


def append_slo(history_path: str, date_str: str, step_times: dict) -> None:
    row = {"date": date_str} | {f"t_{key}": float(val) for key, val in step_times.items()}
    frame = pd.DataFrame([row])
    header = not os.path.exists(history_path)
    frame.to_csv(history_path, mode="a", index=False, header=header)


def rolling_warn(
    history_path: str,
    col: str,
    window: int = 5,
    budget: Optional[float] = None,
    factor: float = 1.2,
) -> Optional[str]:
    if not os.path.exists(history_path):
        return None
    frame = pd.read_csv(history_path)
    if col not in frame.columns or len(frame) < window:
        return None
    rolling_mean = frame[col].tail(window).mean()
    threshold = (budget * factor) if budget else None
    if threshold and rolling_mean > threshold:
        return f"{col} 5d avg {rolling_mean:.0f}s > budget {threshold:.0f}s"
    return None
