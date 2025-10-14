# Jak odświeżyć lock plik (dev branch)

## Procedura

1. Użyj virtualenv:
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   pip freeze | sed '/^-e /d' > requirements.lock
   ```

2. Odpal smoke tests i rerun historyczny (snapshot-replay):
   ```bash
   python tests_smoke/test_data.py
   python tests_smoke/test_factor.py
   python tests_smoke/test_metrics.py
   python tests_smoke/test_report.py
   ```

3. Zmerguj do `main` tylko po review.

## Uwagi

- `requirements.lock` używany w produkcji (pinned versions)
- `requirements.txt` używany w dev (może zawierać zakresy wersji)
- Aktualizuj lock tylko świadomie, po pełnym testowaniu
- Never upgrade dependencies w środku tygodnia produkcyjnego
