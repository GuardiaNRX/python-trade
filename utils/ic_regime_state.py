import json
import os
from dataclasses import dataclass


@dataclass
class ICRegimeCfg:
    low_enter: float = -0.05
    low_exit: float = -0.02
    high_enter: float = 0.03
    high_exit: float = 0.01
    low_mult: float = 0.50
    base_mult: float = 1.00
    high_mult: float = 1.25
    min_streak: int = 10


def _load_state(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path) as handle:
                return json.load(handle)
        except Exception:
            pass
    return {"regime": "base", "low_streak": 0, "high_streak": 0}


def _save_state(path: str, state: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(state, handle)


def decide_multiplier(
    ic3: float | None,
    ic12: float | None,
    cfg: ICRegimeCfg,
    state_path: str = "backtests/results/ic_state.json",
) -> tuple[float, dict]:
    state = _load_state(state_path)
    if ic3 is None or ic12 is None:
        return cfg.base_mult, state
    gap = ic3 - ic12
    state["low_streak"] = (
        state.get("low_streak", 0) + 1 if gap <= cfg.low_enter else 0
    )
    state["high_streak"] = (
        state.get("high_streak", 0) + 1 if gap >= cfg.high_enter else 0
    )
    regime = state.get("regime", "base")
    if regime != "low" and gap <= cfg.low_enter and state["low_streak"] >= cfg.min_streak:
        regime = "low"
    if regime != "high" and gap >= cfg.high_enter and state["high_streak"] >= cfg.min_streak:
        regime = "high"
    if regime == "low" and gap >= cfg.low_exit:
        regime = "base"
    if regime == "high" and gap <= cfg.high_exit:
        regime = "base"
    state["regime"] = regime
    multiplier_map = {"low": cfg.low_mult, "base": cfg.base_mult, "high": cfg.high_mult}
    multiplier = multiplier_map[regime]
    _save_state(state_path, state)
    return multiplier, state
