"""
ModuĹ‚ Ĺ›ledzenia statusu runu (running/ok/failed/degraded).
"""
import datetime
import json
import os
from typing import Any, Dict, List, Optional

STATUS_FILE = "backtests/results/run_status.json"
HIST_FILE = "backtests/results/run_status_history.jsonl"


def start_run(run_id: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Rozpoczyna run - zapisuje status 'running'.

    Args:
        run_id: ID runu
        meta: Dodatkowe metadane

    Returns:
        Dict ze statusem
    """
    os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)

    st = {
        "run_id": run_id,
        "started_at": datetime.datetime.utcnow().isoformat() + "Z",
        "finished_at": None,
        "status": "running",
        "reasons": [],
        "meta": meta or {}
    }

    with open(STATUS_FILE, "w") as f:
        json.dump(st, f, indent=2)

    with open(HIST_FILE, "a") as f:
        f.write(json.dumps(st) + "\n")

    return st


def finalize_run(
    run_id: str,
    status: str = "ok",
    reasons: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Finalizuje run - ustawia status koĹ„cowy.

    Args:
        run_id: ID runu
        status: Status koĹ„cowy (ok/failed/degraded)
        reasons: Lista powodĂłw

    Returns:
        Dict ze statusem
    """
    try:
        st = json.load(open(STATUS_FILE))
    except Exception:
        st = {"run_id": run_id}

    st.update({
        "run_id": run_id,
        "finished_at": datetime.datetime.utcnow().isoformat() + "Z",
        "status": status,
        "reasons": reasons or []
    })

    with open(STATUS_FILE, "w") as f:
        json.dump(st, f, indent=2)

    with open(HIST_FILE, "a") as f:
        f.write(json.dumps(st) + "\n")

    return st

# Alias for backwards compatibility
end_run = finalize_run
