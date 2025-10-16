"""
Moduł freshness multi-venue: sprawdzanie świeżości per region (USA/EU/APAC).
"""
from typing import Dict, List, Optional, Tuple

import pandas as pd
import pandas_market_calendars as mcal


def expected_last_session_for_exchanges(
    exchanges: List[str],
    asof: Optional[pd.Timestamp] = None
) -> Dict[str, pd.Timestamp]:
    """
    Zwraca oczekiwane ostatnie sesje dla wielu giełd.

    Args:
        exchanges: Lista kodów giełd
        asof: Data odniesienia

    Returns:
        Dict exchange → last_session timestamp
    """
    if asof is None:
        asof = pd.Timestamp.utcnow().normalize()
    else:
        asof = pd.Timestamp(asof)

    out = {}
    for ex in exchanges:
        try:
            cal = mcal.get_calendar(ex)
            sched = cal.schedule(
                start_date=asof - pd.Timedelta(days=10),
                end_date=asof + pd.Timedelta(days=1)
            )
            out[ex] = pd.Timestamp(sched.index.max()).tz_localize(None)
        except Exception as e:
            print(f"⚠️  Błąd kalendarz {ex}: {e}")
            # Fallback: poprzedni dzień roboczy
            out[ex] = (asof - pd.tseries.offsets.BDay(1)).normalize()

    return out


def region_freshness_gate(
    prices: pd.DataFrame,
    mapping: pd.DataFrame,
    thresholds: Dict[str, float]
) -> Tuple[Dict[str, float], Optional[str]]:
    """
    Sprawdza pokrycie danych per region z osobnymi progami.

    Args:
        prices: DataFrame z cenami
        mapping: DataFrame[symbol, exchange, region]
        thresholds: Dict region → min_coverage (np. {"USA":0.95, "EU":0.90})

    Returns:
        Tuple (coverage_by_region, failing_region_or_None)
    """
    ex_last = expected_last_session_for_exchanges(
        sorted(mapping["exchange"].unique().tolist())
    )

    cov_by_region = {}
    failing = None

    for region, thr in thresholds.items():
        subs = mapping[mapping["region"] == region]
        if subs.empty:
            cov_by_region[region] = 1.0
            continue

        # Coverage: symbol ma nie-NaN na swojej dacie exchange
        ok = 0
        for _, row in subs.iterrows():
            sym, ex = row["symbol"], row["exchange"]
            dt = ex_last.get(ex)
            if dt is None or dt not in prices.index:
                continue
            val = prices.at[dt, sym] if sym in prices.columns else None
            ok += int(pd.notna(val))

        cov = ok / max(1, len(subs))
        cov_by_region[region] = cov

        if failing is None and cov < thr:
            failing = region

    return cov_by_region, failing
