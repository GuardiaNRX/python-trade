"""
Moduł backfill_policy: polityka reakcji na backfill danych.
"""
from typing import Dict, Any, Literal


def decide_backfill(
    compare_result: Dict[str, Any],
    policy: Literal["fail", "flag", "allow"] = "fail"
) -> Dict[str, str]:
    """
    Decyduje o reakcji na backfill.

    Args:
        compare_result: Wynik porównania snapshots
        policy: Polityka reakcji ('fail', 'flag', 'allow')

    Returns:
        Dict z action ('ok', 'fail', 'flag') i msg
    """
    changed = compare_result.get("changed", False)

    if not changed:
        return {"action": "ok"}

    if policy == "fail":
        return {
            "action": "fail",
            "msg": "Backfill detected: hashes differ."
        }

    if policy == "flag":
        return {
            "action": "flag",
            "msg": "Backfill detected (flagged). Continue with caution."
        }

    # policy == "allow"
    return {"action": "allow"}
