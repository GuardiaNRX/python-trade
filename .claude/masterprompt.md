## Utwórz kompletny, uruchamialny projekt alpha-lab na serwer/cloud, w Pythonie 3.11+, który:

automatycznie pobiera dane (yfinance),

liczy faktor momentum 12–1 oraz rankingi percentylowe,

wykonuje walidację PurgedKFold (mlfinlab) i liczy Rank-IC, Sharpe, Calmar, MaxDD, DSR (Deflated Sharpe Ratio),

generuje raport Markdown (.md) z wykresami,

wysyła raport i alerty na Slack (slack_sdk),

ma łatwy harmonogram: cron (domyślnie) + opcjonalny Prefect flow,

jest modularny, rozszerzalny i zgodny z wytycznymi z CLAUDE.md.

## Wymagania ogólne

Kod idiomatyczny, PEP8, podzielony na małe funkcje.

Brak sekretów w repo (tokeny tylko z ENV/.env).

Raporty i logi po polsku.

Domyślna strefa czasu raportów: Europe/Warsaw.

W każdym skrypcie if __name__ == "__main__": z argparse.

Dodatkowe bezpieczeństwo: obsługa wyjątków + wyjście ≠ 0 na błędzie (do integracji z cron/monitoringiem).

## Struktura repo (utwórz dokładnie):
alpha-lab/
  .gitignore
  README.md
  CLAUDE.md
  requirements.txt
  .env.example
  configs/
    example_mom12_1.yaml
  data/
    .gitkeep
    factors/
      .gitkeep
  utils/
    data_io.py
    metrics.py
    costs.py
    cv.py
    reporting.py
    plotting.py
    slack_client.py
    execution.py
    schedule.py
  factors/
    momentum_12_1.py
  backtests/
    make_factor.py
    grid_backtest.py
    purged_cv_eval.py
    report_daily.py
  live/
    shadow_paper.py

## Zawartość kluczowych plików (stwórz je z tymi treściami/zakresem)

## .gitignore

Ignoruj: __pycache__/, *.pyc, .venv/, .env*, data/**/*.parquet|feather|h5|pickle|pkl|zip|csv (zostaw data/.gitkeep), backtests/reports/, backtests/results/, .ipynb_checkpoints/, .DS_Store, .idea/, .vscode/.

## requirements.txt

pandas>=2.2
numpy>=1.26
scipy>=1.11
pyyaml>=6.0
yfinance>=0.2
vectorbt>=0.25
mlfinlab>=1.8
ib-insync>=0.9.86
tabulate>=0.9
matplotlib>=3.8
python-dotenv>=1.0
slack_sdk>=3.33
prefect>=3.0.0

## .env.example

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL=#alpha-lab
# Optional IBKR (for live/paper)
IB_HOST=127.0.0.1
IB_PORT=7497
IB_CLIENT_ID=7

## configs/example_mom12_1.yaml

Zdefiniuj:

name: mom12_1_cs

universe: [AAPL, MSFT, NVDA, AMZN, GOOGL]

data: { source: yfinance, csv_dir: data, start: "2015-01-01", end: null }

factor: { module: factors.momentum_12_1, params: { lookback_months: 12, skip_recent_months: 1 }, sector_neutral: false }

backtest: { rebalance: "M", long_only: true, top_quantile: 0.9, bottom_quantile: 0.1, max_weight: 0.1, fees_bps: 5, slippage_bps: 2, cash_buffer: 0.01 }

risk: { max_name_weight: 0.15, max_sector_weight: 0.4 }

report: { out_dir: "backtests/reports", title: "Raport dzienny – Momentum 12–1" }

alerts: { ic_min: 0.03, dsr_min: 0.5, max_dd: 0.15 }

ibkr: { host: ${IB_HOST}, port: ${IB_PORT}, client_id: ${IB_CLIENT_ID}, exchange: "SMART", currency: "USD", account: null }


## utils/data_io.py

load_prices(universe, start, end, source="yfinance", csv_dir="data"): preferuj lokalne CSV (kolumny: Date, Adj Close), fallback do yfinance; ffill(), filtr dat.

Zwracaj DataFrame Adj Close (index datetime, kolumny tickery).

## utils/metrics.py

Funkcje: sharpe(returns, freq), calmar(returns, freq), max_drawdown(returns), rank_ic(factor_series, fwd_series) (MultiIndex), turnover(weights).

DSR: dodaj def deflated_sharpe_ratio(sharpe, n, skew=0, kurt=3): wg formuły de Prado (przyjmij rozsądny przybliżony wariant—parametry wejściowe dokumentuj w docstring; jeśli brak danych o skew/kurt, użyj 0 i 3). Zadbaj o docstring wyjaśniający założenia.

## utils/costs.py

bps_to_frac(bps), apply_costs(returns, turnover, fees_bps, slippage_bps) – potrącaj liniowe koszty ~ turnover * (fees+slip).

## utils/cv.py

purged_folds(X, t1, n_splits=5, embargo_days=5) – wrapper na mlfinlab.cross_validation.PurgedKFold.

## utils/reporting.py

ensure_dir(path), save_table(df, outdir, name) -> path, save_metadata(meta, outdir, name) -> path, write_markdown(report_md: str, outdir: str, filename: str) -> path.

## utils/plotting.py

equity_curve(returns: pd.Series) -> plt.Figure

histogram_returns(returns: pd.Series) -> plt.Figure

Zapisuj wykresy do PNG; zwracaj ścieżki.

## utils/slack_client.py

Inicjuj WebClient z SLACK_BOT_TOKEN (ENV).

post_message(channel, text) – prosty wrapper; jeśli > 3000 znaków, podziel lub wyślij plik .md.

upload_file(channel, file_bytes_or_path, filename, initial_comment="") – wsparcie dla obrazów PNG i plików .md.

## utils/execution.py

target_weights_from_ranks(...) (long-only / long-short) – jak w poprzednim szablonie.

orders_from_diff(...) – szkic (demo), z komentarzem o konieczności realnych cen i pozycji przy live.

## utils/schedule.py

cron_example() – wypisz przykładowy wpis crona (Warszawa; np. 22:30 CET, pn–pt).

prefect_flow(config_path) – zbuduj prosty Prefect flow: task_fetch -> task_factor -> task_eval -> task_report -> task_slack.

## factors/momentum_12_1.py

compute_factor(prices, lookback_months=12, skip_recent_months=1) (rolling product bez ostatniego miesiąca).

percentile_rank(df) → rank pctl per data.

## backtests/make_factor.py

Wczytaj config, pobierz ceny, policz faktor i ranks, zapisz data/factors/{name}_values.parquet i _ranks.parquet.

Policz i zapisz forward 1m returns: %chg(periods=21).shift(-21).

## backtests/grid_backtest.py

Użyj vectorbt do szybkiego sprawdzenia strategii (na podstawie ranks → entries/exits).

Wydrukuj podstawowe staty (tabulate).

## backtests/purged_cv_eval.py

Wczytaj factor i forward 1m; zbuduj X i t1; policz Rank-IC na foldach Purged/Embargo; wypisz średnią i per-fold.

## backtests/report_daily.py (orkiestrator)

- Wejście: --config, --mode {shadow,paper}, --prefect (opcjonalnie).

- Kroki:

Load config & ENV, ensure_dir(report_out).

Fetch prices (data_io).

Compute factor + ranks (factors).

Forward returns; policz: IC (in-sample bieżący) i OOS IC via PurgedKFold (cv).

Zbuduj pseudo-portfel z ranks → weights; policz dzienne zwroty portfela (przyjmij prosty EOD rebal M/W/D zgodnie z configiem).

Koszty: policz turnover(weights) i zastosuj fees/slippage (costs).

Metryki: Sharpe, Calmar, MaxDD, DSR (metrics).

Wygeneruj wykresy: equity curve, histogram (plotting).

Złóż Markdown: nagłówek, tabela metryk, komentarz dot. stabilności IC (PurgedKFold), decay, turnover, lista ograniczeń/założeń.

Zapisz backtests/reports/{YYYYMMDD}_report.md (reporting) oraz PNG wykresów.

Alerty: jeśli IC < ic_min lub DSR < dsr_min lub MaxDD < -max_dd → wyślij dodatkową wiadomość alarmową.

Slack: wyślij .md (jako tekst lub upload pliku, jeśli długie), dołącz PNG (upload_file).

Jeśli --mode paper → wypisz (lub zademonstruj) diff zleceń (execution); realne wysyłki zostaw zakomentowane (bezpieczeństwo).

- Zwróć kod wyjścia ≠0 na błędach (do crona).

## live/shadow_paper.py

Minimalny loop dla paper trading IBKR (ib_insync) – copy z wcześniejszego szablonu, z ostrzeżeniami w komentarzach.

## README.md

Krótkie intro (po polsku), jak zainstalować, jak uruchomić kroki 1–4, jak skonfigurować Slack i cron/Prefect. Dodaj przykładowy wpis cron:

# pn–pt 22:30 czasu PL
30 22 * * 1-5 /usr/bin/env bash -lc 'cd /srv/alpha-lab && source .venv/bin/activate && python backtests/report_daily.py --config configs/example_mom12_1.yaml >> logs/report.log 2>&1'


i przykład wywołania Prefect flow (python -m utils.schedule --prefect --config ...).