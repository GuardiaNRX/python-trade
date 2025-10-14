"""
Moduł approval: two-man rule dla produkcji.
"""
import os
import json


def enforce_two_man(
    cfg_hash: str,
    approvals_path: str = "backtests/results/approvals.json",
    required: int = 2
) -> bool:
    """
    Wymusza two-man rule: config musi być zatwierdzony przez ≥2 osoby w prod.

    Args:
        cfg_hash: Hash konfiguracji
        approvals_path: Ścieżka do JSON z approvals
        required: Wymagana liczba aprobat

    Returns:
        True jeśli OK

    Raises:
        RuntimeError: Jeśli brak wymaganych aprobat
    """
    # Tylko w trybie produkcyjnym (ALPHA_PROD=1)
    if not os.environ.get("ALPHA_PROD"):
        return True

    if not os.path.exists(approvals_path):
        raise RuntimeError("Two-man rule: approvals.json missing")

    with open(approvals_path, "r") as f:
        data = json.load(f)

    arr = data.get(cfg_hash, [])
    unique_approvers = len(set(arr))

    if unique_approvers < required:
        raise RuntimeError(
            f"Two-man rule: config {cfg_hash[:8]} not approved "
            f"(have {unique_approvers}/{required})"
        )

    return True
