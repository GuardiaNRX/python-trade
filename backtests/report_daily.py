"""
Główny orkiestrator - dzienny raport alpha research.
Pipeline kompletny: filtry płynności, kalendarz sesji, neutralizacja, impact, capacity.
Generuje metryki Priorytetu A, wykresy i wysyła raport na Slack.
"""
import argparse
import sys
import os
import time
from datetime import datetime
import yaml
import pandas as pd
import numpy as np
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# INSERT HERE — IMPORTS (nowe moduły z 104.md)
from utils.data_io import load_ohlcv
from utils.snapshot import save_snapshot
from utils.atomic import atomic_write_text
from utils.run_id import make_run_id
from utils.ledger import cfg_hash as _cfg_hash
from utils.approval import enforce_two_man
from utils.risk_limits import (
    enforce_gross_limit, enforce_single_name_limit, limit_turnover, kill_switch_by_drawdown
)
from utils.order_throttle import apply_throttle
from utils.orders_state import save_plan, cancel_file_for_last_run
from utils.diff_planner import delta_from_positions
from utils.monitor import SLO, alert_thresholds
from utils.runlock import run_lock
from utils.universe import eligible_mask_per_date, birth_death_mask
from utils.exec_policy import plan_twap
from utils.spread_robust import robust_cs_spread
from utils.cost_params import k_gamma_today
from utils.ic_regime_state import ICRegimeCfg as ICRegimeCfgH, decide_multiplier
from utils.config_schema import validate_config
from utils.runtime_sla import RuntimeBudget
from utils.slack_client import post_message, upload_file
from utils.calendar import compute_forward_returns_sessions
from utils.neutralization import ridge_sector_beta_residuals, rolling_beta, load_sector_map
from utils.calibration import calibrate_costs
from utils.logger_json import log_json
from utils.run_status import start_run, end_run
from factors.momentum_12_1 import compute_factor, percentile_rank
from utils.metrics import (
    sharpe, sortino, calmar, max_drawdown, rank_ic, turnover, deflated_sharpe_ratio_v2,
    information_ratio, alpha_beta, expected_shortfall, tail_ratio,
    hit_rate, payoff_ratio, rolling_rank_ic
)
from utils.costs import apply_costs
from utils.impact import (
    compute_adv_usd, square_root_impact_cost, capacity_violations, compute_dollars_traded,
    spread_cost_fraction
)
from utils.execution import apply_rebalance_weights, rebalance_signal
from utils.reporting import ensure_dir
from utils.plotting import equity_curve, histogram_returns, rolling_ic_plot
from utils.slo_history import append_slo, rolling_warn
from utils.pbo import compute_pbo_simple
from utils.freshness_multi import region_freshness_gate
from utils.map_sanity import validate_mapping


def main():
    parser = argparse.ArgumentParser(description="Raport dzienny alpha-lab-pro")
    parser.add_argument("--config", type=str, required=True, help="Ścieżka do pliku YAML")
    parser.add_argument("--mode", type=str, choices=["shadow", "paper"], default="shadow",
                        help="Tryb: shadow (tylko raport) lub paper (+ demo zleceń)")
    parser.add_argument("--dry-run", action="store_true", help="Nie wysyłaj na Slack")
    args = parser.parse_args()

    # INSERT HERE — POCZĄTEK main() (104.md sekcja 1)
    t0 = time.time()

    try:
        with run_lock():  # anty-duplikacja uruchomień
            # Załaduj ENV
            load_dotenv()

            # Wczytaj config
            with open(args.config, 'r') as f:
                config = yaml.safe_load(f)

            # Walidacja schema configu
            validate_config(config)

            # Two-man rule (prod guard)
            enforce_two_man(_cfg_hash(config))

            # Runtime budget (SLA)
            runtime = RuntimeBudget(
                max_total_sec=config.get("runtime", {}).get("max_total_sec", 1200),
                degrade_threshold=config.get("runtime", {}).get("degrade_threshold", 0.9)
            )
            runtime.start("total")
            impact_config = config.get("impact", {})

            name = config["name"]
            print(f"=== Raport dzienny: {name} ===")
            print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Europe/Warsaw")

            # ============================================================
            # [1/12] Pobierz dane OHLCV
            # ============================================================
            print("\n[1/12] Pobieranie danych OHLCV...")
            runtime.start("data")

            # INSERT HERE — HTTP cache toggle (109.md)
            uni = config["universe"]
            if config.get("data", {}).get("http_cache", {}).get("enabled", True):
                os.environ["HTTP_CACHE"] = "1"
            else:
                os.environ["HTTP_CACHE"] = "0"

            prices, volume, high, low = load_ohlcv(
                universe=uni,
                start=config["data"]["start"],
                end=config["data"]["end"],
                source=config["data"]["source"],
                csv_dir=config["data"]["csv_dir"]
            )
            runtime.end("data")
            print(f"  Pobrano: prices={prices.shape}, volume={volume.shape}")

            # INSERT HERE — FRESHNESS + SNAPSHOT + RUN_ID (104.md sekcja 2)
            # Freshness per-region/exchange (nowy mechanizm)
            mapping = pd.read_csv("data/symbol_exchange_map.csv")  # symbol,exchange,region
            map_errs = validate_mapping(mapping, prices.columns.tolist())
            if map_errs:
                msg = ":no_entry: Map sanity FAIL:\n- " + "\n- ".join(map_errs)
                post_message(os.environ.get("SLACK_CHANNEL", "#alpha-lab"), msg)
                log_json("ERROR", None, "map_sanity_fail", errors=map_errs)
                sys.exit(7)
            thr = config.get("data", {}).get("region_thresholds", {"USA": 0.95, "EU": 0.90, "APAC": 0.90})
            cov, bad = region_freshness_gate(prices, mapping, thr)
            if bad:
                details = ', '.join([f"{k}:{v:.1%}" for k, v in cov.items()])
                post_message(
                    os.environ.get("SLACK_CHANNEL", "#alpha-lab"),
                    f":no_entry: Freshness FAIL {bad} ({details}) — przerywam run."
                )
                log_json("ERROR", None, "freshness_fail", details=details, failing_region=bad)
                sys.exit(4)
            log_json("INFO", None, "freshness_ok", coverage=cov)

            # Snapshot wejścia + run_id
            snap_meta = save_snapshot(prices, volume, high, low)
            runid = make_run_id(_cfg_hash(config), snap_meta["snapshot_id"])

            # Approval dla produkcyjnych runów (paper mode)
            start_run(runid, meta={"cfg_hash": _cfg_hash(config), "snapshot_id": snap_meta["snapshot_id"]})
            log_json("INFO", runid, "run_start", universe=len(prices.columns))

            # Precompute: ADV i robust spread (potrzebne do impact i do plan_twap)
            adv_usd = compute_adv_usd(
                prices,
                volume,
                lookback=impact_config.get("lookback_days", 60),
            )
            if adv_usd.empty:
                adv_usd = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)

            spr, hl_outlier_mask = robust_cs_spread(
                high,
                low,
                volume,
                window=2,
                sanity_sigma=5.0,
                median_window=20,
                fallback_bps=25.0,
            )
            if spr.empty:
                spr = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
                hl_outlier_mask = pd.DataFrame(False, index=prices.index, columns=prices.columns)
            # ============================================================
            # [2/12] Filtry płynności (dynamiczna maska) + birth/death
            # ============================================================
            print("[2/12] Tworzenie maski eligibilności (Point-in-Time)...")
            filters_config = config.get("filters", {})

            # INSERT HERE — eligible_mask_per_date + birth/death (104.md sekcja 3)
            eligible = eligible_mask_per_date(
                prices, volume,
                min_price=filters_config.get("min_price", 5.0),
                adv_window=filters_config.get("adv_window", 60),
                min_adv_usd=filters_config.get("min_adv_usd", 1_000_000)
            )
            life = birth_death_mask(prices, filters_config.get("min_days_from_ipo", 60))
            eligible = eligible & life

            eligible_count = eligible.sum(axis=1).mean()
            print(f"  Średnio eligible: {eligible_count:.1f} / {prices.shape[1]} tickerów per dzień")

            # Eligibility T-1 (dla rebalansowania)
            elig_tminus1 = eligible.shift(1).fillna(False)

        # ============================================================
        # [3/12] Oblicz faktor + neutralizacja Ridge (opcjonalnie)
        # ============================================================
        print("[3/12] Obliczanie faktora momentum...")
        factor_config = config["factor"]
        factor_values = compute_factor(prices, **factor_config["params"])

        # Neutralizacja Ridge (sector + beta)
        if factor_config.get("sector_neutral", False) or factor_config.get("beta_neutral", False):
            print("  Neutralizacja Ridge (sector + beta + winsorization)...")
            sector_map_path = factor_config.get("sector_map_csv", "data/sector_map.csv")

            # Load sector map
            sector_map = {}
            if os.path.exists(sector_map_path):
                sector_map = load_sector_map(sector_map_path)
            else:
                print(f"  OSTRZEŻENIE: Brak pliku {sector_map_path}, używam pustej mapy sektorów")
                # Fallback: wszyscy w "OTHER"
                sector_map = {ticker: "OTHER" for ticker in prices.columns}

            # Load beta if needed
            betas = None
            if factor_config.get("beta_neutral", False):
                beta_window = factor_config.get("beta_window", 252)
                bench_ticker = config.get("benchmark", {}).get("ticker", "SPY")
                try:
                    bench_data = pd.read_csv(f"data/{bench_ticker}.csv", parse_dates=["Date"], index_col="Date")
                    bench_prices = bench_data["Adj Close"]
                    bench_ret = bench_prices.pct_change()
                    betas = rolling_beta(prices, bench_ret, beta_window)
                    print(f"  Beta obliczona względem {bench_ticker}")
                except Exception as e:
                    print(f"  OSTRZEŻENIE: Nie udało się obliczyć beta: {e}")

            # Ridge neutralization with winsorization
            alpha_ridge = factor_config.get("ridge_alpha", 1.0)
            winsor_pct = factor_config.get("winsor_pct", 0.01)

            factor_values = ridge_sector_beta_residuals(
                factor_values,
                sector_map=sector_map,
                betas=betas,
                alpha_ridge=alpha_ridge,
                winsor_pct=winsor_pct
            )
            print(f"  Neutralizacja zakończona (Ridge α={alpha_ridge}, winsor={winsor_pct})")

        factor_ranks = percentile_rank(factor_values)
        print(f"  Factor shape: {factor_values.shape}")

        # ============================================================
        # [4/12] Forward returns z kalendarzem sesji
        # ============================================================
        print("[4/12] Obliczanie forward returns (kalendarz sesji)...")
        calendar_config = config.get("calendar", {})
        fwd_returns = compute_forward_returns_sessions(
            prices,
            sessions_ahead=calendar_config.get("forward_horizon_sessions", 21),
            exchange=calendar_config.get("exchange", "XNYS")
        )
        print(f"  Forward returns shape: {fwd_returns.shape}")

        # ============================================================
        # [5/12] Rank IC + Rolling IC
        # ============================================================
        print("[5/12] Obliczanie IC...")
        factor_flat = factor_values.stack()
        fwd_flat = fwd_returns.stack()
        ic = rank_ic(factor_flat, fwd_flat)
        print(f"  Rank-IC: {ic:.4f}")

        # Rolling IC
        rolling_ic_series = rolling_rank_ic(factor_values, fwd_returns, window=60)
        ic_3m = rolling_ic_series.tail(63).mean()  # ~3 miesiące
        ic_12m = rolling_ic_series.tail(252).mean()  # ~12 miesięcy
        print(f"  Rolling IC (3m): {ic_3m:.4f}, (12m): {ic_12m:.4f}")

        # ============================================================
        # [6/12] Budowa portfela (wagi) z rebalansowaniem
        # ============================================================
        print("[6/12] Budowanie portfela z calendar rebalancing...")
        bt_config = config["backtest"]

        # Określ częstotliwość rebalansowania
        rebalance_freq = bt_config.get("rebalance_freq", "M")  # M/W/D
        rebalance_flags = rebalance_signal(factor_ranks.index, freq=rebalance_freq)
        rebalance_days_count = rebalance_flags.sum()
        print(f"  Częstotliwość: {rebalance_freq}, liczba rebalansów: {rebalance_days_count}")

        # Generuj wagi z carry-over między rebalansami
        weights = apply_rebalance_weights(
            ranks=factor_ranks,
            top_quantile=bt_config["top_quantile"],
            bottom_quantile=bt_config["bottom_quantile"],
            long_only=bt_config["long_only"],
            max_weight=bt_config["max_weight"],
            cash_buffer=bt_config.get("cash_buffer", 0.0),
            rebalance_flags=rebalance_flags,
            eligibility_mask=elig_tminus1  # Use T-1 eligibility
        )

        # INSERT HERE — IC-REGIME SCALER (104.md + 107.md)
        ic_cfg = config.get("ic_regime", {})
        ic_mult, _ic_state = decide_multiplier(
            ic3=float(ic_3m) if pd.notna(ic_3m) else None,
            ic12=float(ic_12m) if pd.notna(ic_12m) else None,
            cfg=ICRegimeCfgH(
                low_enter=ic_cfg.get("low_enter", -0.05),
                low_exit=ic_cfg.get("low_exit", -0.02),
                high_enter=ic_cfg.get("high_enter", 0.03),
                high_exit=ic_cfg.get("high_exit", 0.01),
                low_mult=ic_cfg.get("low_mult", 0.50),
                base_mult=ic_cfg.get("base_mult", 1.00),
                high_mult=ic_cfg.get("high_mult", 1.25),
                min_streak=ic_cfg.get("min_streak", 10),
            ),
            state_path=ic_cfg.get("state_path", "backtests/results/ic_state.json"),
        )
        weights = (weights * ic_mult).clip(-2.0, 2.0)
        print(f"  IC-regime multiplier: {ic_mult:.2f}")

        # INSERT HERE — HARD LIMITS (104.md sekcja 4)
        rl = config.get("risk", {})
        weights = enforce_single_name_limit(weights, rl.get("max_name_weight", 0.15))
        weights = enforce_gross_limit(weights, rl.get("max_gross", 1.5))
        if rl.get("max_turnover") is not None:
            weights = limit_turnover(weights, rl["max_turnover"])

        print(f"  Weights shape: {weights.shape}")
        print(f"  Średnia liczba pozycji per dzień: {(weights != 0).sum(axis=1).mean():.1f}")

        # ============================================================
        # [7/12] Zwroty portfela
        # ============================================================
        print("[7/12] Obliczanie zwrotów portfela...")
        daily_returns = prices.pct_change()
        portfolio_returns = (weights.shift(1) * daily_returns).sum(axis=1)
        portfolio_returns = portfolio_returns.dropna()

        # ============================================================
        # [8/12] Turnover + dollars traded
        # ============================================================
        print("[8/12] Obliczanie turnover...")
        turnover_series = turnover(weights)
        avg_turnover = turnover_series.mean()
        print(f"  Średni turnover: {avg_turnover:.2%}")

        # Dollars traded
        initial_equity = bt_config.get("initial_equity", 10_000_000)
        weight_changes = weights.diff().abs()
        dollars_traded_df = compute_dollars_traded(weight_changes, initial_equity, prices)

        # ============================================================
        # [9/12] Impact costs + Spread costs (Corwin-Schultz)
        # ============================================================
        print("[9/12] Obliczanie impact costs + spread costs...")

        gamma_today = impact_config.get("gamma", 0.25)
        outlier_pct = 0.0
        impact_enabled = impact_config.get("enabled", False)

        if impact_enabled:
            
            # Square-root impact cost
            impact_costs_sqrt = square_root_impact_cost(
                dollars_traded_df,
                adv_usd,
                k_bps=impact_config.get("k_bps", 15.0)
            )

            # Średni impact cost (market impact)
            impact_cost_series = impact_costs_sqrt.mean(axis=1)
            avg_impact_cost = impact_cost_series.mean()
            print(f"  Średni market impact: {avg_impact_cost:.4f} ({avg_impact_cost*10000:.2f}bps)")

            print("  Obliczanie robust spread costs (z outlier detection)...")

            # Segmented k per symbol (tercyle spreadu)
            calib_path = config.get("impact", {}).get("calibration", {}).get("out_json", "backtests/results/calibration.json")
            k_series, gamma_today = k_gamma_today(
                calib_json=calib_path,
                spread_today=spr.iloc[-1] if not spr.empty else None,
                adv_today=adv_usd.iloc[-1] if not adv_usd.empty else None,
                default_k_bps=impact_config.get("k_bps", 15.0),
                default_gamma=impact_config.get("gamma", 0.25)
            )

            # Przelicz market impact z segmentowanym k (k_bps now a Series)
            impact_costs_sqrt = square_root_impact_cost(dollars_traded_df, adv_usd, k_bps=k_series)

            # Spread cost
            spread_cost_series = spread_cost_fraction(weight_changes, spr)
            avg_spread_cost = spread_cost_series.mean()
            print(f"  Średni spread cost: {avg_spread_cost:.4f} ({avg_spread_cost*10000:.2f}bps)")

            # H/L outliers
            outlier_pct = (hl_outlier_mask.sum().sum() / hl_outlier_mask.size) * 100 if hl_outlier_mask.size > 0 else 0.0
            print(f"  H/L outliers wykryte: {outlier_pct:.2f}%")

            # Total impact (market impact + spread)
            total_impact_series = impact_cost_series + spread_cost_series
            avg_total_impact = total_impact_series.mean()
            print(f"  Total impact (market+spread): {avg_total_impact:.4f} ({avg_total_impact*10000:.2f}bps)")

        else:
            impact_cost_series = pd.Series(0, index=portfolio_returns.index)
            spread_cost_series = pd.Series(0, index=portfolio_returns.index)
            total_impact_series = pd.Series(0, index=portfolio_returns.index)
            avg_impact_cost = 0.0
            avg_spread_cost = 0.0
            avg_total_impact = 0.0
            print("  Impact wyłączony")

        # ============================================================
        # [10/12] Capacity violations
        # ============================================================
        print("[10/12] Sprawdzanie capacity violations...")
        if impact_enabled:
            violations_df = capacity_violations(
                dollars_traded_df,
                adv_usd,
                cap_pct=impact_config.get("adv_cap_pct", 0.10)
            )

            # % dni z naruszeniami
            violations_pct = (violations_df.sum(axis=1) > 0).sum() / len(violations_df) * 100
            print(f"  Capacity violations: {violations_pct:.1f}% dni")
        else:
            violations_pct = 0.0

        # ============================================================
        # [11/12] Koszty łączne + metryki + DSR v2 + PBO
        # ============================================================
        print("[11/12] Obliczanie metryk...")

        # Koszty: fees + slippage + impact (total)
        portfolio_returns_net = apply_costs(
            portfolio_returns,
            turnover_series,
            fees_bps=bt_config["fees_bps"],
            slippage_bps=bt_config["slippage_bps"]
        )

        # Odejmij total impact (market + spread)
        portfolio_returns_net = portfolio_returns_net - total_impact_series

        # ============================================================
        # SECTION 6 (104.md): KILL-SWITCH + CANCEL STALE
        # ============================================================
        print("[KILL-SWITCH] Sprawdzanie drawdown...")
        ks_cfg = config.get("risk", {}).get("kill_switch", {"dd_hard": 0.20})
        ks_tripped = kill_switch_by_drawdown(portfolio_returns_net, ks_cfg.get("dd_hard", 0.20))
        if ks_tripped:
            post_message(
                os.environ.get("SLACK_CHANNEL", "#alpha-lab"),
                ":no_entry: **KILL-SWITCH**: przekroczono hard drawdown — zamrażam zmiany wag."
            )
            cpath = cancel_file_for_last_run()
            if cpath:
                post_message(
                    os.environ.get("SLACK_CHANNEL", "#alpha-lab"),
                    f"Generuję anulacje pending orders: {os.path.basename(cpath)}"
                )
            # Zamrożenie wag – użyj poprzednich wag
            weights = weights.shift(1).fillna(0.0)
            print("  KILL-SWITCH aktywny – wagi zamrożone na poprzednim stanie.")
        else:
            print("  KILL-SWITCH OK – drawdown w normie.")

        # Metryki Priorytetu A
        sharpe_ratio = sharpe(portfolio_returns_net, freq=252)
        sortino_ratio = sortino(portfolio_returns_net, freq=252)
        calmar_ratio = calmar(portfolio_returns_net, freq=252)
        max_dd = max_drawdown(portfolio_returns_net)

        # DSR v2 (Lopez de Prado with multiple testing correction)
        skewness = portfolio_returns_net.skew()
        kurtosis = portfolio_returns_net.kurtosis()
        n_trials = config.get("dsr_trials", 1)  # Liczba prób/testów parametrów
        dsr_v2 = deflated_sharpe_ratio_v2(
            sharpe_ratio,
            len(portfolio_returns_net),
            skew=skewness,
            kurt=kurtosis,
            trials=n_trials
        )
        print(f"  DSR v2 (trials={n_trials}): {dsr_v2:.4f}")

        es95 = expected_shortfall(portfolio_returns_net, confidence=0.95)
        tail_r = tail_ratio(portfolio_returns_net)

        # PBO (Probability of Backtest Overfitting) - simple version
        # Split data train/test (70/30)
        split_idx = int(len(portfolio_returns_net) * 0.7)
        returns_train = portfolio_returns_net.iloc[:split_idx]
        returns_test = portfolio_returns_net.iloc[split_idx:]

        pbo_results = compute_pbo_simple(returns_train, returns_test)
        pbo_degradation = pbo_results["degradation"]
        pbo_degradation_pct = pbo_results["degradation_pct"]
        print(f"  PBO degradation: {pbo_degradation:.4f} ({pbo_degradation_pct:.1f}%)")

        # Hit rate / Payoff
        factor_flat_clean = factor_flat.dropna()
        fwd_flat_clean = fwd_flat.dropna()
        common_idx = factor_flat_clean.index.intersection(fwd_flat_clean.index)
        if len(common_idx) > 0:
            hit = hit_rate(factor_flat_clean, fwd_flat_clean)
            payoff = payoff_ratio(factor_flat_clean, fwd_flat_clean)
        else:
            hit = 0.0
            payoff = 0.0

        # IR / Alpha / Beta (jeśli benchmark dostępny)
        bench_ticker = config.get("benchmark", {}).get("ticker", None)
        if bench_ticker:
            try:
                bench_data = pd.read_csv(f"data/{bench_ticker}.csv", parse_dates=["Date"], index_col="Date")
                bench_prices = bench_data["Adj Close"]
                bench_ret = bench_prices.pct_change()
                ir = information_ratio(portfolio_returns_net, bench_ret, freq=252)
                alpha, beta = alpha_beta(portfolio_returns_net, bench_ret, freq=252)
                print(f"  IR: {ir:.4f}, Alpha: {alpha:.2%}, Beta: {beta:.2f}")
            except:
                ir, alpha, beta = 0.0, 0.0, 0.0
        else:
            ir, alpha, beta = 0.0, 0.0, 0.0

        print(f"  Sharpe: {sharpe_ratio:.4f}, Sortino: {sortino_ratio:.4f}")
        print(f"  Calmar: {calmar_ratio:.4f}, MaxDD: {max_dd:.2%}")
        print(f"  DSR v2: {dsr_v2:.4f}, ES95: {es95:.4f}")
        print(f"  Hit Rate: {hit:.2%}, Payoff: {payoff:.2f}")
        print(f"  Skewness: {skewness:.2f}, Kurtosis: {kurtosis:.2f}")

        # ============================================================
        # SECTION 7 (104.md): PLAN ZLECEŃ (delta → plan_twap → throttle → save)
        # ============================================================
        print("[PLAN] Generowanie planu zleceń...")

        # a) Delta względem stanu brokera (jeśli mamy CSV), fallback do Δw
        broker_csv = config.get("trading", {}).get("broker_positions_csv")
        if broker_csv and os.path.exists(broker_csv):
            bdf = pd.read_csv(broker_csv).set_index("symbol")["quantity"].astype(float)
            delta_dollars = delta_from_positions(weights.iloc[-1], bdf, prices.iloc[-1], initial_equity)
            print(f"  Delta obliczona względem broker positions CSV: {broker_csv}")
        else:
            # Fallback: Δw
            delta_w = weights.iloc[-1] - weights.iloc[-2] if len(weights) > 1 else weights.iloc[-1]
            delta_dollars = (delta_w * initial_equity * prices.iloc[-1]).fillna(0.0)
            print(f"  Delta obliczona z różnicy wag (fallback).")

        # b) Plan TWAP
        plan = plan_twap(
            delta_w=(delta_dollars / (initial_equity * prices.iloc[-1])).fillna(0.0),
            prices=prices,
            adv_usd=adv_usd,
            spread=spr,
            equity=initial_equity,
            window_minutes=60,
            slices=6,
            adv_cap=impact_config.get("adv_cap_pct", 0.10),
            gamma=gamma_today
        )

        # c) Throttle/ratelimit + greylist
        grey = set(config.get("trading", {}).get("greylist", []))
        lims = config.get("trading", {}).get("limits", {
            "max_orders": 100,
            "max_notional": 1_000_000,
            "max_per_symbol": 100_000
        })
        plan = apply_throttle(
            plan,
            max_orders=lims["max_orders"],
            max_notional=lims["max_notional"],
            max_per_symbol=lims["max_per_symbol"],
            greylist=grey
        )

        # d) Zapisz plan (z run_id)
        orders_dir = "backtests/results/orders"
        plan_path = save_plan(plan, runid, out_dir=orders_dir)
        print(f"  Plan zapisany: {plan_path}")

        # ============================================================
        # SECTION 8 (104.md): WYKRESY + RAPORT MD (z run_id, snapshot, atomic write)
        # ============================================================
        print("[12/12] Generowanie wykresów i raportu...")
        report_dir = config["report"]["out_dir"]
        ensure_dir(report_dir)

        cfg_name = config.get("name", "alpha_lab")

        # Wykresy z run_id w nazwie pliku
        eq_path = os.path.join(report_dir, f"{cfg_name}_{runid}_equity.png")
        hist_path = os.path.join(report_dir, f"{cfg_name}_{runid}_hist.png")
        ric_path = os.path.join(report_dir, f"{cfg_name}_{runid}_rolling_ic.png")

        equity_curve(portfolio_returns_net, report_dir, os.path.basename(eq_path))
        histogram_returns(portfolio_returns_net, report_dir, os.path.basename(hist_path))
        rolling_ic_plot(rolling_ic_series, report_dir, os.path.basename(ric_path))

        # Nagłówek raportu z run_id + snapshot
        now_utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        header = (
            f"# {config.get('report', {}).get('title', 'Raport dzienny')}\n\n"
            f"*Run ID:* `{runid}`  \\\n"
            f"*Snapshot:* `{snap_meta['snapshot_id']}`  \\\n"
            f"*Data generacji:* {now_utc}\n\n"
            f"**Zakres danych:** {config['data']['start']} – {prices.index[-1].strftime('%Y-%m-%d')}  \\\n"
            f"**Universe:** {len(config['universe'])} tickerów → średnio {eligible_count:.1f} eligible per dzień (Point-in-Time)\n"
        )
        # Podsumowanie freshness per-region
        cov_line = ", ".join([f"{k}:{v:.1%}" for k, v in cov.items()])

        # Body raportu
        body = f"""
---

## Data Health

- **Freshness (per region):** {cov_line}
- **H/L Outliers:** {outlier_pct:.2f}% wykrytych (robust spread filter)
- **Missing data (ostatni dzień):** {prices.iloc[-1].isna().mean()*100:.1f}%
- **Backfill detection:** {'✓ brak' if not snap_meta.get('backfill_detected', False) else '⚠ wykryto backfill'}

---

## Filtry płynności (Point-in-Time)

- **Min price:** {filters_config.get('min_price', 5.0)}
- **ADV window:** {filters_config.get('adv_window', 60)}d
- **Min ADV USD:** ${filters_config.get('min_adv_usd', 1_000_000):,.0f}
- **Średnio eligible per dzień:** {eligible_count:.1f} / {prices.shape[1]} ({eligible_count/prices.shape[1]*100:.0f}%)
- **Rebalance freq:** {rebalance_freq} ({rebalance_days_count} rebalansów)

---

## Metryki efektywności (Priorytet A+)

| Metryka | Wartość |
|---------|---------|
| **Rank-IC** | {ic:.4f} |
| **IC 3m** | {ic_3m:.4f} |
| **IC 12m** | {ic_12m:.4f} |
| **Sharpe Ratio** | {sharpe_ratio:.4f} |
| **Sortino Ratio** | {sortino_ratio:.4f} |
| **Calmar Ratio** | {calmar_ratio:.4f} |
| **Max Drawdown** | {max_dd:.2%} |
| **DSR v2 (Lopez de Prado)** | {dsr_v2:.4f} |
| **PBO Degradation** | {pbo_degradation:.4f} ({pbo_degradation_pct:.1f}%) |
| **Expected Shortfall (95%)** | {es95:.4f} |
| **Tail Ratio** | {tail_r:.2f} |
| **Skewness** | {skewness:.2f} |
| **Kurtosis** | {kurtosis:.2f} |
| **Hit Rate** | {hit:.2%} |
| **Payoff Ratio** | {payoff:.2f} |
| **Średni Turnover** | {avg_turnover:.2%} |

"""

        # Dodaj benchmark metrics jeśli dostępne
        if bench_ticker and ir != 0.0:
            body += f"""
### Benchmark Analysis (vs {bench_ticker})

| Metryka | Wartość |
|---------|---------|
| **Information Ratio** | {ir:.4f} |
| **Alpha (annualized)** | {alpha:.2%} |
| **Beta** | {beta:.2f} |

"""

        body += f"""
---

## Koszty i capacity (3-component model)

- **Fees + Slippage:** {bt_config['fees_bps']}bps + {bt_config['slippage_bps']}bps
- **Impact enabled:** {'Tak' if impact_enabled else 'Nie'}
- **Market impact (sqrt):** {avg_impact_cost*10000:.2f}bps
- **Spread cost (Corwin-Schultz):** {avg_spread_cost*10000:.2f}bps
- **Total impact (market+spread):** {avg_total_impact*10000:.2f}bps
- **Capacity violations:** {violations_pct:.1f}% dni (próg: {impact_config.get('adv_cap_pct', 0.10)*100:.0f}% ADV)

---

## Komentarz

### Stabilność IC
- Ogólny Rank-IC: **{ic:.4f}** {'✓ pozytywny' if ic > 0 else '⚠ wymaga analizy'}
- Rolling IC 3m: **{ic_3m:.4f}**, 12m: **{ic_12m:.4f}**
- {'✓ Stabilny' if abs(ic_3m - ic_12m) < 0.05 else '⚠ Zmienność IC'}

### Decay i Capacity
- Średni turnover: **{avg_turnover:.2%}** – {'✓ niski (dobry dla capacity)' if avg_turnover < 0.2 else '⚠ wysoki (może ograniczać capacity)'}
- Impact model: {'aktywny' if impact_enabled else 'wyłączony'}
- Capacity violations: {'✓ poniżej 5%' if violations_pct < 5 else '⚠ powyżej 5%'}

### Jakość zwrotów i overfitting
- Sharpe: **{sharpe_ratio:.4f}**, DSR v2: **{dsr_v2:.4f}** – {'✓ stabilna alfa' if dsr_v2 > 0.5 else '⚠ niska pewność statystyczna'}
- PBO degradation: **{pbo_degradation:.4f}** ({pbo_degradation_pct:.1f}%) – {'✓ dobra generalizacja' if abs(pbo_degradation_pct) < 20 else '⚠ możliwy overfitting'}
- ES95: **{es95:.4f}**, Tail Ratio: **{tail_r:.2f}** – {'✓ kontrolowany tail risk' if abs(es95) < 0.03 else '⚠ wysoki tail risk'}
- Hit Rate: **{hit:.2%}**, Payoff: **{payoff:.2f}** – {'✓ dobra trafność' if hit > 0.5 else '⚠ niska trafność'}

---

## Wykresy

### Krzywa kapitału
![Equity Curve]({os.path.basename(eq_path)})

### Histogram zwrotów
![Histogram]({os.path.basename(hist_path)})

### Rolling Rank IC (60d)
![Rolling IC]({os.path.basename(ric_path)})

---

## Ulepszenia i metodologia

1. **Point-in-Time eligibility:** Dynamiczna maska per data (unika survivorship bias)
2. **Calendar rebalancing:** Częstotliwość **{rebalance_freq}** z carry-over wag między rebalansami (redukuje turnover)
3. **Ridge neutralization:** Stabilniejsza niż OLS, z winsoryzacją outlierów (pct={factor_config.get('winsor_pct', 0.01)})
4. **3-component cost model:**
   - Fees + slippage: {bt_config['fees_bps']}bps + {bt_config['slippage_bps']}bps
   - Market impact (sqrt): {avg_impact_cost*10000:.2f}bps
   - Spread (Corwin-Schultz): {avg_spread_cost*10000:.2f}bps
5. **DSR v2:** Lopez de Prado z korektą na multiple testing (trials={n_trials})
6. **PBO:** Degradacja performance train→test jako miara overfittingu
7. **Forward returns:** Kalendarz sesji NYSE (unika look-ahead bias)

---

## Ograniczenia

1. **Dane:** yfinance (może zawierać błędy, brak corporate actions poza splitami)
2. **Universe:** Średnio {eligible_count:.1f} eligible tickerów per dzień
3. **PBO:** Użyto prostej wersji (train/test split); pełna CSCV wymaga wielu konfiguracji
4. **Spread estimator:** Corwin-Schultz może nie oddawać rzeczywistych spreadów dla illiquid stocks

---

_Raport wygenerowany automatycznie przez alpha-lab-pro pipeline (enhanced)._
_Pipeline: OHLCV → PIT eligibility → faktor → Ridge neutralization → kalendarz → IC → rebalancing → 3-cost model → DSR v2 + PBO → raport._
"""

        # Pełny raport: header + body
        report_md = header + body

        # Atomowy zapis raportu
        md_path = os.path.join(report_dir, f"{cfg_name}_{runid}_report.md")
        atomic_write_text(md_path, report_md)
        print(f"  Zapisano raport (atomic): {md_path}")

        # ============================================================
        # SECTION 9 (104.md): SLO + ALERTY + SLACK
        # ============================================================
        print("[SLO] Obliczanie Service Level Objectives...")

        # SLO
        ic3_slo = rolling_ic_series.tail(63).mean() if rolling_ic_series.notna().any() else float("nan")
        ic12_slo = rolling_ic_series.tail(252).mean() if rolling_ic_series.notna().any() else float("nan")

        slo = SLO(
            step_times={"total": runtime.elapsed()},
            n_assets_after_filter=weights.shape[1],
            pct_missing_today=float(prices.iloc[-1].isna().mean()),
            ic_3m=float(ic3_slo) if ic3_slo == ic3_slo else float("nan"),
            ic_12m=float(ic12_slo) if ic12_slo == ic12_slo else float("nan"),
            adv_viol_share=violations_pct / 100.0 if violations_pct > 0 else 0.0
        )

        slo_alerts = alert_thresholds(slo)

        # Trend 5d po czasie całkowitym (t_total)
        hist_path = config.get("report", {}).get("slo_history", "backtests/results/slo_history.csv")
        hist_dir = os.path.dirname(hist_path)
        if hist_dir:
            os.makedirs(hist_dir, exist_ok=True)
        append_slo(hist_path, datetime.utcnow().strftime("%Y-%m-%d"), {"total": runtime.elapsed()})
        twarn = rolling_warn(
            hist_path,
            "t_total",
            window=5,
            budget=config.get("runtime", {}).get("max_total_sec", 1200),
            factor=1.2,
        )
        if twarn:
            slo_alerts.append(f"SLO trend: {twarn}")

        # Summary dla Slacka
        summary = (
            f"**{config.get('report', {}).get('title', 'Raport')}** - {now_utc}\n"
            f"Run: `{runid}` | Snapshot: `{snap_meta['snapshot_id']}`"
        )

        triggered = []
        if ks_tripped:
            triggered.append("KILL-SWITCH")

        # ============================================================
        # Slack wysyłka
        # ============================================================
        if not args.dry_run:
            try:
                print("\nWysyłanie na Slack...")
                channel = os.environ.get("SLACK_CHANNEL", "#alpha-lab")

                # Wysłanie alertów SLO (jeśli są)
                if slo_alerts:
                    post_message(channel, ":rotating_light: " + "; ".join(slo_alerts) + "\n" + summary)
                else:
                    post_message(channel, summary)

                # Upload plików
                upload_file(channel, eq_path, os.path.basename(eq_path), "Equity Curve")
                upload_file(channel, hist_path, os.path.basename(hist_path), "Histogram")
                upload_file(channel, ric_path, os.path.basename(ric_path), "Rolling IC")
                upload_file(channel, md_path, os.path.basename(md_path), "Raport .md")

                print("✓ Wysłano na Slack")

            except Exception as e:
                print(f"BŁĄD przy wysyłaniu na Slack: {e}")
        else:
            print("\n(--dry-run: pomijam wysyłkę na Slack)")

        # Mode paper
        if args.mode == "paper":
            print("\n[PAPER MODE] Generowanie demo zleceń...")
            print("(Realne wysyłki zakomentowane - bezpieczeństwo)")

        # ============================================================
        # SECTION 10 (104.md): KALIBRACJA KOSZTÓW + FINALIZACJA
        # ============================================================
        print("[KALIBRACJA] Sprawdzanie paper fills...")
        calibr = config.get("impact", {}).get("calibration", {})
        if calibr.get("fills_csv"):
            rec = calibrate_costs(calibr["fills_csv"])
            if rec:
                post_message(
                    os.environ.get("SLACK_CHANNEL", "#alpha-lab"),
                    f"Rekomendacja kosztów (paper): k≈{rec['k_bps_recommended']:.1f} bps; gamma≈{rec.get('gamma_recommended', 'n/a')}"
                )
                print(f"  k_bps rekomendacja: {rec['k_bps_recommended']:.1f} bps")
                print(f"  gamma rekomendacja: {rec.get('gamma_recommended', 'n/a')}")
        else:
            print("  Brak fills CSV – kalibracja pominięta.")

        # Finalizacja run
        runtime.end("total")
        end_run(runid, status="success", final_metrics={
            "sharpe": sharpe_ratio,
            "ic": ic,
            "max_dd": max_dd,
            "dsr_v2": dsr_v2,
            "avg_turnover": avg_turnover
        })
        log_json("INFO", runid, "run_end", status="success", elapsed_sec=runtime.elapsed())

        print("\n✓ Raport zakończony pomyślnie")

    except Exception as e:
        print(f"\nBŁĄD: {e}")
        import traceback
        traceback.print_exc()

        # Zapisz failed run (jeśli runid istnieje)
        if 'runid' in locals():
            end_run(runid, status="failed", error=str(e))
            log_json("ERROR", runid, "run_failed", error=str(e))

        sys.exit(1)


if __name__ == "__main__":
    main()
