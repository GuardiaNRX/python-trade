# Deploy Checklist

## Przed deployem na produkcję

### 1. Zaktualizuj lock file
```bash
pip-compile || pip freeze | sed '/^-e /d' > requirements.lock
```

### 2. Uruchom smoke tests
```bash
python scripts/smoke_replay.py
```

Sprawdź, czy exit code = 0.

### 3. Uruchom wszystkie testy smoke
```bash
python tests_smoke/test_data.py
python tests_smoke/test_factor.py
python tests_smoke/test_metrics.py
python tests_smoke/test_report.py
```

Wszystkie muszą przejść (✓).

### 4. Zmerguj PR (two-man rule)
- Co najmniej 2 osoby muszą zaaprobować changes
- Sprawdź, czy cfg_hash jest w approvals.json (dla prod)

### 5. Tag release
```bash
git tag -a v1.0.X -m "Release 1.0.X"
git push origin v1.0.X
```

### 6. Deploy na prod
```bash
# Na serwerze prod
cd /srv/Python-trading
git pull origin main
git checkout v1.0.X
pip install -r requirements.lock
```

### 7. Weryfikacja
```bash
# Test healthcheck
python backtests/healthcheck.py --out_dir backtests/reports
```

### 8. Monitoring
- Sprawdź logi w `logs/report.log`
- Sprawdź Slack: czy raporty przychodzą
- Sprawdź `backtests/results/calibration_history.csv` (koszty)

## Rollback

Jeśli coś poszło nie tak:

```bash
git checkout v1.0.X-1  # poprzednia wersja
pip install -r requirements.lock
```

## Notatki

- **NIGDY** nie deploy'uj w środku tygodnia handlowego bez ważnego powodu
- **ZAWSZE** testuj na staging przed prod
- **ZAWSZE** miej backup ostatniego działającego configu
