"""
Moduł structured logging (JSONL) dla pipeline.
"""
import datetime
import json
import os


def _log_path() -> str:
    """Zwraca ścieżkę do dziennego pliku logów JSONL."""
    d = "backtests/results/logs"
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{datetime.date.today().isoformat()}.jsonl")


def log_json(level: str, run_id: str | None, step: str, **fields):
    """
    Loguje wpis do structured log (JSONL).

    Args:
        level: Poziom (INFO, WARN, ERROR)
        run_id: ID runu lub None
        step: Nazwa kroku pipeline
        **fields: Dodatkowe pola
    """
    rec = {
        "ts": datetime.datetime.utcnow().isoformat() + "Z",
        "level": level.upper(),
        "run_id": run_id,
        "step": step,
        **fields
    }
    try:
        with open(_log_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass
