# alpha-lab-pro

Automatyczny pipeline do alpha research – strategia momentum 12-1 z pełnym modelem kosztów, impact i capacity.

## Opis projektu

**alpha-lab-pro** to zaawansowany, modularny system do:
- Automatycznego pobierania danych giełdowych (yfinance) + Volume
- **Filtrów płynności** (min cena, ADV USD)
- Obliczania faktora momentum 12-1 i rankingów percentylowych
- **Neutralizacji** (opcjonalnie: sektorowa, beta vs benchmark)
- **Kalendarz sesji** (forward returns po N sesjach handlowych, nie dni kalendarzowych)
- Walidacji strategii metodą PurgedKFold (mlfinlab)
- **Metryk Priorytetu A:** Sharpe, Sortino, Calmar, MaxDD, DSR, IR, α/β, ES95, Tail, Hit/Payoff, Rolling IC
- **Modelu impact** (square-root) i **capacity violations** (%ADV)
- Generowania raportów Markdown z wykresami (equity, histogram, rolling IC)
- Wysyłania raportów i alertów na Slack
- Opcjonalnego paper trading (IBKR via ib-insync)

## Wymagania

- Python 3.11+
- Linux/Windows (preferowany Linux dla serwera/cloud)
- Strefa czasowa: Europe/Warsaw

## Instalacja

### 1. Klonowanie repozytorium

```bash
git clone <repo-url>
cd Python-trading
```

### 2. Utworzenie środowiska wirtualnego

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# lub
.venv\Scripts\activate  # Windows
```

### 3. Instalacja zależności

```bash
pip install -r requirements.txt
```

**Uwaga:** Instalacja może zająć kilka minut ze względu na:
- `mlfinlab` (duży pakiet)
- `pandas-market-calendars` (kalendarz sesji)
- `scikit-learn` (neutralizacja)

### 4. Konfiguracja zmiennych środowiskowych

Skopiuj `.env.example` do `.env` i uzupełnij tokeny:

```bash
cp .env.example .env
```

Edytuj `.env`:

```bash
# Slack
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_CHANNEL=#alpha-lab

# Opcjonalnie IBKR (dla live/paper)
IB_HOST=127.0.0.1
IB_PORT=7497
IB_CLIENT_ID=7
```

## Podstawowe użycie

### Krok 1: Generowanie faktora

```bash
python backtests/make_factor.py --config configs/example_mom12_1.yaml
```

Tworzy 3 pliki parquet w `data/factors/`:
- `{name}_values.parquet` – wartości faktora momentum
- `{name}_ranks.parquet` – rankingi percentylowe
- `{name}_forward_returns.parquet` – przyszłe zwroty (1m forward)

### Krok 2: Walidacja PurgedKFold

```bash
python backtests/purged_cv_eval.py --config configs/example_mom12_1.yaml
```

Oblicza Rank-IC na foldach z purge i embargo.

### Krok 3: Raport dzienny (GŁÓWNY PIPELINE)

```bash
python backtests/report_daily.py --config configs/example_mom12_1.yaml --dry-run
```

**Pipeline 12 kroków:**
1. Load data + volume
2. Filtry płynności (ADV, min price)
3. Compute factor + neutralizacja (opcjonalnie)
4. Forward returns (kalendarz sesji)
5. Rank IC + Rolling IC
6. Portfolio weights
7. Portfolio returns
8. Turnover + dollars traded
9. Impact costs (sqrt model)
10. Capacity violations
11. Metryki Priorytetu A (15+ metryk)
12. Wykresy + Raport MD + Slack

**Generuje:**
- Raport Markdown w `backtests/reports/`
- 3 wykresy (equity curve, histogram, rolling IC)
- Wysyłka na Slack (jeśli skonfigurowane i bez `--dry-run`)

## Filtry płynności

Filtry automatycznie odrzucają tickery o niskiej płynności:

```yaml
filters:
  min_price: 5.0           # Minimalna cena (unika penny stocks)
  adv_window: 60           # Okno rolling dla ADV (dni)
  min_adv_usd: 1000000     # Minimalny ADV w USD
```

**Dlaczego?** Ogranicza mikro-cap, high slippage, i nierealistyczne backtesty.

## Kalendarz sesji

Forward returns obliczane **po N sesjach handlowych** (nie dni kalendarzowych):

```yaml
calendar:
  exchange: XNYS           # NYSE calendar
  forward_horizon_sessions: 21  # 21 sesji = ~1 miesiąc
```

**Dlaczego?** Unika Point-in-Time bias (weekendy/święta).

## Neutralizacja (opcjonalnie)

### Sektorowa

```yaml
factor:
  sector_neutral: true
  sector_map_csv: data/sector_map.csv
```

Format `sector_map.csv`:
```csv
ticker,sector
AAPL,Technology
MSFT,Technology
AMZN,Consumer
```

### Beta

```yaml
factor:
  beta_neutral: true
  beta_window: 252
```

Wymaga `benchmark.ticker` w configu (np. SPY).

## Impact & Capacity

Model square-root impact + monitoring violations:

```yaml
impact:
  enabled: true
  k_bps: 15.0              # Współczynnik impact
  adv_cap_pct: 0.10        # Limit 10% ADV
  lookback_days: 60
```

Raport pokazuje:
- Średni impact cost (bps)
- % dni z capacity violations

## Metryki Priorytetu A

Raport zawiera **15+ metryk**:
- **IC:** Rank-IC, Rolling IC (3m/12m)
- **Risk-adjusted:** Sharpe, Sortino, Calmar, DSR
- **Downside:** MaxDD, ES95, Tail Ratio
- **Predictability:** Hit Rate, Payoff Ratio
- **Benchmark:** IR, Alpha, Beta (jeśli SPY dostępny)
- **Turnover & Costs**

## Harmonogram (cron)

Aby uruchamiać raport codziennie, dodaj do crontab:

```bash
crontab -e
```

Przykładowy wpis (pn-pt, 22:30 czasu PL):

```cron
# Raport dzienny alpha-lab-pro
30 22 * * 1-5 /usr/bin/env bash -lc 'cd /srv/Python-trading && source .venv/bin/activate && python backtests/report_daily.py --config configs/example_mom12_1.yaml >> logs/report.log 2>&1'
```

Utworz katalog na logi:

```bash
mkdir -p logs
```

## Prefect Flow (opcjonalnie)

Aby wyświetlić przykładowy wpis cron:

```bash
python -m utils.schedule --cron
```

Aby uruchomić Prefect flow:

```bash
python -m utils.schedule --prefect --config configs/example_mom12_1.yaml
```

## Smoke Tests

Przed uruchomieniem w produkcji, uruchom smoke tests:

```bash
python tests_smoke/test_data.py
python tests_smoke/test_factor.py
python tests_smoke/test_metrics.py
python tests_smoke/test_report.py
```

Wszystkie powinny wyświetlić `✓ Wszystkie testy przeszły`.

## Paper Trading (IBKR)

**OSTRZEŻENIE:** Funkcjonalność paper trading jest w fazie demo. Przed użyciem:
1. Przetestuj dokładnie
2. Sprawdź konfigurację IBKR (TWS/Gateway)
3. Użyj najpierw z flagą `--dry-run`

```bash
python live/shadow_paper.py --config configs/example_mom12_1.yaml --dry-run
```

## Struktura projektu

```
Python-trading/
├── .gitignore
├── README.md
├── requirements.txt
├── .env.example
├── configs/
│   └── example_mom12_1.yaml
├── data/
│   ├── factors/
│   └── sector_map.csv
├── utils/
│   ├── data_io.py           # Load prices + volume, filtry
│   ├── calendar.py          # Sesje giełdowe
│   ├── neutralization.py    # Sector/beta neutral
│   ├── metrics.py           # 15+ metryk
│   ├── impact.py            # Impact model + capacity
│   ├── costs.py             # Fees + slippage
│   ├── cv.py                # PurgedKFold
│   ├── reporting.py         # Zapis raportów
│   ├── plotting.py          # Wykresy (equity, hist, rolling IC)
│   ├── slack_client.py      # Integracja Slack
│   ├── execution.py         # Generowanie wag/zleceń
│   └── schedule.py          # Harmonogramowanie (cron/Prefect)
├── factors/
│   └── momentum_12_1.py     # Faktor momentum 12-1
├── backtests/
│   ├── make_factor.py       # Generowanie faktora
│   ├── grid_backtest.py     # Grid backtest (vectorbt)
│   ├── purged_cv_eval.py    # Walidacja PurgedKFold
│   └── report_daily.py      # ⭐ Orkiestrator główny (12 kroków)
├── live/
│   └── shadow_paper.py      # Paper trading IBKR
└── tests_smoke/
    ├── test_data.py
    ├── test_factor.py
    ├── test_metrics.py
    └── test_report.py
```

## Konfiguracja strategii

Edytuj `configs/example_mom12_1.yaml` aby dostosować:
- Universe tickerów
- Filtry płynności (min_price, min_adv_usd)
- Kalendarz sesji (exchange, forward_horizon_sessions)
- Parametry faktora (lookback, skip)
- Neutralizacja (sector_neutral, beta_neutral)
- Parametry backtestingu (rebalance, top/bottom quantile, fees)
- Impact model (enabled, k_bps, adv_cap_pct)
- Progi alertów (ic_min, dsr_min, max_dd)

## Troubleshooting

### Błąd: "No module named 'pandas_market_calendars'"

```bash
pip install pandas-market-calendars
```

### Błąd: "No module named 'sklearn'"

```bash
pip install scikit-learn
```

### Błąd: "SLACK_BOT_TOKEN not found"

Upewnij się, że plik `.env` istnieje i zawiera token:

```bash
cat .env
```

### Brak danych z yfinance

Sprawdź połączenie internetowe i poprawność symboli tickerów. yfinance czasami jest wolny - dane są cache'owane lokalnie w `data/*.csv`.

### Calendar fallback

Jeśli `pandas-market-calendars` nie działa, system automatycznie używa dni kalendarzowych zamiast sesji.

### Filtry płynności odrzuciły wszystkie tickery

Zmniejsz `min_adv_usd` lub `min_price` w configu. Dla małych universe (< 10 tickerów) rozważ wyłączenie filtrów.

## Licencja

Projekt do użytku wewnętrznego.

## Kontakt

W przypadku pytań skontaktuj się z zespołem alpha-lab.
