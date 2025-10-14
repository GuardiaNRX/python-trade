"""
Test integracyjny golden snapshot: odtwarzalność pipeline.
"""
import os
import hashlib
import subprocess
import re


GOLD = "tests/golden/20250105_abc12345"  # Przykład snapshotu
OUT = "backtests/reports"


def _md5(path: str) -> str:
    """Oblicza MD5 pliku."""
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def _normalize_md(text: str) -> str:
    """Normalizuje markdown (usuwa volatile pola)."""
    return "\n".join([
        ln for ln in text.splitlines()
        if not re.search(r"(Run ID|Data generacji|Snapshot)", ln)
    ])


def test_golden_replay():
    """
    Test odtwarzalności: dwa uruchomienia na tym samym snapshotcie powinny
    dać identyczne wyniki (po normalizacji).
    """
    # 1) Uruchom report w trybie dry-run
    env = dict(os.environ)
    env["DRY_RUN"] = "1"

    ret = subprocess.run(
        ["python", "backtests/report_daily.py", "--config", "configs/example_mom12_1.yaml"],
        env=env
    )
    assert ret.returncode == 0, "Pierwszy run failed"

    # 2) Znajdź najnowszy report.md i policz hash po normalizacji
    md_files = sorted([p for p in os.listdir(OUT) if p.endswith("_report.md")])
    assert md_files, "Brak raportów MD"

    md = md_files[-1]
    text = open(os.path.join(OUT, md), "r", encoding="utf-8").read()
    h1 = hashlib.md5(_normalize_md(text).encode()).hexdigest()

    # 3) Porównaj z goldenem (jeśli istnieje)
    gold_md = os.path.join(GOLD, "report.md")
    if os.path.exists(gold_md):
        gold_text = open(gold_md, "r", encoding="utf-8").read()
        h_gold = hashlib.md5(_normalize_md(gold_text).encode()).hexdigest()
        assert h1 == h_gold, "Markdown report drifted vs golden snapshot"

    # 4) Drugi run (odtwarzalność)
    ret2 = subprocess.run(
        ["python", "backtests/report_daily.py", "--config", "configs/example_mom12_1.yaml"],
        env=env
    )
    assert ret2.returncode == 0, "Drugi run failed"

    md2_files = sorted([p for p in os.listdir(OUT) if p.endswith("_report.md")])
    md2 = md2_files[-1]
    text2 = open(os.path.join(OUT, md2), "r", encoding="utf-8").read()
    h2 = hashlib.md5(_normalize_md(text2).encode()).hexdigest()

    assert h1 == h2, "Second run differs — pipeline not deterministic"

    print("✓ Golden snapshot test PASSED")


if __name__ == "__main__":
    test_golden_replay()
