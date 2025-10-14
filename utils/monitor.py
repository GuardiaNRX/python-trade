"""
Moduł monitoring: SLO + alerty progowe.
"""
import numpy as np
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class SLO:
    """Service Level Objectives dla pipeline."""
    step_times: Dict[str, float]
    n_assets_after_filter: int
    pct_missing_today: float
    ic_3m: float
    ic_12m: float
    adv_viol_share: float


def alert_thresholds(slo: SLO) -> List[str]:
    """
    Sprawdza progi alertów i zwraca listę ostrzeżeń.

    Args:
        slo: Obiekt SLO z metrykami

    Returns:
        Lista alertów (puste = brak alertów)
    """
    alerts = []

    # Czas total > 20 minut
    if slo.step_times.get("total", 0) > 1200:
        alerts.append(f"Czas total > 20m ({slo.step_times['total']:.0f}s)")

    # Bardzo mało aktywów po filtrze
    if slo.n_assets_after_filter < 3:
        alerts.append("Bardzo mało aktywów po filtrze (<3)")

    # Braki danych dziś > 10%
    if slo.pct_missing_today > 0.1:
        alerts.append(f"Braki danych dziś >10% ({slo.pct_missing_today:.1%})")

    # IC 3m << 12m (decay)
    if np.isfinite(slo.ic_3m) and np.isfinite(slo.ic_12m):
        if slo.ic_3m < slo.ic_12m - 0.05:
            alerts.append(f"IC 3m {slo.ic_3m:.3f} << 12m {slo.ic_12m:.3f}")

    # Capacity violations > 5%
    if slo.adv_viol_share > 0.05:
        alerts.append(f"Naruszenia %ADV >5% ({slo.adv_viol_share:.1%})")

    return alerts
