## Project: alpha-lab – automatyczny pipeline alpha research (momentum 12–1) 
## Goal: Codzienny raport (.md) z metrykami (IC, Sharpe, Calmar, MaxDD, DSR), wykresami i alertami na Slack; opcjonalny shadow/paper na IBKR. 
## Runtime: Python 3.11+, Linux (server/cloud), TZ=Europe/Warsaw.

## Ground rules (IMPORTANT)

- No secrets in code. Używaj os.environ[...] / .env (python-dotenv).
- Polish outputs. Wszystkie raporty/wiadomości po polsku.
- Resilience. Każdy punkt I/O (API, zapis plików, Slack) ma try/except i czytelny komunikat błędu.
- Reproducibility. Zapisuj w raporcie: data generacji, zakres danych, lista tickerów, wersje pakietów (pip freeze | grep).
- Plots. Twórz wykresy matplotlib (bez seaborn), jeden wykres na figurę, brak narzuconych styli/kolorów.

## Coding conventions

- PEP8, małe, czyste funkcje, docstringi z param/returns.
- Typy: from typing import ...; walidacja wejść (assert/ValueError).
- Struktura katalogów – jak w README (nie zmieniaj bez potrzeby).
- Logi – krótkie, camelCase dla kluczy w structured logs (jeśli użyte).
- Test/dry-run: Skrypty mają flagę --dry-run gdzie ma sens (np. Slack upload).

## Tasks you will get asked to do

- Implementacja funkcji w utils/*.py zgodnie ze spec (patrz MASTER PROMPT).
- Orkiestracja dzienna w backtests/report_daily.py.
- Walidacja PurgedKFold (mlfinlab) + liczenie Rank-IC.
- Deflated Sharpe Ratio (DSR) – dodaj funkcję i metrykę do raportu.
- Wysyłka Slack – slack_sdk: post text + upload .md/PNG; dziel długie wiadomości.
- Alerty – progi z configs/*.yaml; wysyłka ostrzeżeń (emoji, @here – opcjonalnie).
- Harmonogram – pokaż wpis cron i prosty Prefect flow (utils/schedule.py).

## Edge cases & gotchas

- **yfinance** bywa wolne – cache'uj do data/ i użyj ffill().
- Seria pusta / NaNs → raport ma mimo to powstać z informacją "brak nowych danych".
- **Slack limity** – długie raporty wysyłaj jako plik .md + krótkie streszczenie w tekście.
- **DSR** – zaznacz w raporcie założenia (skew/kurt), nie nadużywaj precyzji przy małej próbie.
- **PurgedKFold** – zadbaj, by t1 odpowiadało końcowi okna etykiety (np. T+21d).
- **Filtry płynności:** Dla małych universe (< 10 tickerów) filtry mogą odrzucić wszystko – rozważ wyłączenie lub obniżenie progów.
- **Kalendarz sesji:** Wymaga pandas-market-calendars; jeśli brak, fallback na dni kalendarzowe (mniej dokładne).
- **Impact:** Wymaga initial_equity w backtest config; model sqrt jest uproszczony.
- **PIT bias:** Forward returns obliczane z kalendarzem sesji (nie dni kalendarzowych) – unika PIT bias ale wymaga więcej RAM.
- **Neutralizacja:** Wymaga sector_map.csv dla sector_neutral; dla beta_neutral wymaga benchmarku (SPY).
- **Capacity violations:** > 5% dni = ostrzeżenie; > 10% = alert; wymaga ręcznej analizy.

## Acceptance checklist per PR
- `python backtests/make_factor.py --config ...` działa i zapisuje 3 pliki parquet.
- `python backtests/purged_cv_eval.py --config ...` drukuje średni IC i per-fold.
- `python backtests/report_daily.py --config ... --dry-run` generuje .md + 3× PNG (equity, histogram, rolling_ic).
- Błędy są obsłużone; exit code ≠ 0 na błędach; brak sekretów w repo.
- README ma sekcję cron + Prefect; .env.example kompletne.
- **Smoke tests:** Wszystkie 4 testy (`tests_smoke/test_*.py`) przechodzą.
- **Capacity violations:** Raport pokazuje % dni < 5% (jeśli impact enabled).
- **Rolling IC:** Raport zawiera wykres rolling_ic.png i średnie 3m/12m.
- **Impact costs:** Średni impact sensowny (< 50bps przy normalnym turnover).
- **Filtry płynności:** Raport pokazuje ile tickerów zostało odfiltrowanych.

## Style of the report (.md)

- Nagłówek z datą (PL), zakresem danych i listą tickerów.
- Tabela metryk (IC, Sharpe, Calmar, MaxDD, DSR, Turnover).
- Krótki komentarz o stabilności IC (PurgedKFold), decay i capacity/turnover.
- Wklej ścieżki/miniatury wykresów (equity, histogram).
- Sekcja “Ograniczenia i dalsze kroki”.

## IMPORTANT
- do a double check after you finish the task of the things you were asked to do versus what you actually did, 
- after every task write a compact style summary in "title-name"DDMMYYYY.md format, save this file in folder .claude/session-q as a new file.
