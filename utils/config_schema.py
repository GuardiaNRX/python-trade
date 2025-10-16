"""
Moduł walidacji config schema: fail-fast z czytelnym błędem.
"""
from typing import Any, Dict, List


def _in_01(x) -> bool:
    """Sprawdza czy wartość w [0,1]."""
    return isinstance(x, (int, float)) and 0 <= x <= 1


def _nonneg(x) -> bool:
    """Sprawdza czy wartość >= 0."""
    return isinstance(x, (int, float)) and x >= 0


def _pos(x) -> bool:
    """Sprawdza czy wartość > 0."""
    return isinstance(x, (int, float)) and x > 0


def validate_config(cfg: Dict[str, Any]) -> None:
    """
    Waliduje strukturę i zakresy wartości w configu.

    Args:
        cfg: Słownik konfiguracji

    Raises:
        ValueError: Jeśli config zawiera błędy
    """
    errs: List[str] = []

    # Universe
    if "universe" not in cfg or not isinstance(cfg["universe"], (list, tuple)) or not cfg["universe"]:
        errs.append("universe: musi być niepustą listą tickerów")

    # Backtest
    bt = cfg.get("backtest", {})
    if not _in_01(bt.get("top_quantile", 0.5)):
        errs.append("backtest.top_quantile ∈ [0,1]")
    if not _in_01(bt.get("bottom_quantile", 0.5)):
        errs.append("backtest.bottom_quantile ∈ [0,1]")
    if not _in_01(bt.get("max_weight", 0.1)):
        errs.append("backtest.max_weight ∈ [0,1]")
    if not _in_01(bt.get("cash_buffer", 0.0)):
        errs.append("backtest.cash_buffer ∈ [0,1]")
    if not _nonneg(bt.get("fees_bps", 0)):
        errs.append("backtest.fees_bps ≥ 0")
    if not _nonneg(bt.get("slippage_bps", 0)):
        errs.append("backtest.slippage_bps ≥ 0")

    # Impact
    imp = cfg.get("impact", {})
    if not _nonneg(imp.get("k_bps", 0)):
        errs.append("impact.k_bps ≥ 0")
    if not _in_01(imp.get("adv_cap_pct", 0.1)):
        errs.append("impact.adv_cap_pct ∈ [0,1]")
    if not isinstance(imp.get("lookback_days", 60), int) or imp.get("lookback_days", 60) <= 0:
        errs.append("impact.lookback_days > 0 (int)")

    # Risk
    rk = cfg.get("risk", {})
    if not _in_01(rk.get("max_name_weight", 0.15)):
        errs.append("risk.max_name_weight ∈ [0,1]")
    if not _pos(rk.get("max_gross", 1.5)):
        errs.append("risk.max_gross > 0")

    # Data
    dt = cfg.get("data", {})
    if not _in_01(dt.get("min_coverage", 0.95)):
        errs.append("data.min_coverage ∈ [0,1]")

    # IC regime
    ir = cfg.get("ic_regime", {})
    if ir:
        if not isinstance(ir.get("low_gap", -0.05), (int, float)):
            errs.append("ic_regime.low_gap float")
        if not isinstance(ir.get("high_gap", 0.03), (int, float)):
            errs.append("ic_regime.high_gap float")

    # Relacje i spójność dodatkowa (109.md)
    if bt.get("rebalance", "M") not in ("D", "W", "M"):
        errs.append("backtest.rebalance ∈ {D,W,M}")
    if bt.get("fees_bps", 0) > 100:
        errs.append("backtest.fees_bps ≤ 100")
    if bt.get("slippage_bps", 0) > 100:
        errs.append("backtest.slippage_bps ≤ 100")
    if bt.get("max_weight", 0.1) > min(0.25, rk.get("max_name_weight", 0.15)):
        errs.append("backtest.max_weight ≤ min(0.25, risk.max_name_weight)")

    # Monitor
    mon = cfg.get("monitor", {})
    for k in ("max_added", "max_removed"):
        v = mon.get(k)
        if v is not None and (not isinstance(v, int) or v < 0):
            errs.append(f"monitor.{k} musi być nieujemną liczbą całkowitą")

    if errs:
        raise ValueError("Config validation failed:\n- " + "\n- ".join(errs))
