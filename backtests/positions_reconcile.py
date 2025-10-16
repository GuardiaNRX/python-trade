"""
Skrypt rekonsyliacji pozycji: porównuje target vs broker state.
"""
import argparse

import pandas as pd


def load_broker_positions_csv(path: str) -> pd.Series:
    """
    Ładuje pozycje z CSV brokera.

    Args:
        path: Ścieżka do CSV (kolumny: symbol, quantity)

    Returns:
        Seria position_size per symbol (w sztukach)
    """
    df = pd.read_csv(path)
    df["symbol"] = df["symbol"].astype(str)
    return df.set_index("symbol")["quantity"].astype(float)


def target_positions_from_weights(
    weights: pd.Series,
    equity: float,
    last_prices: pd.Series
) -> pd.Series:
    """
    Oblicza docelowe pozycje w sztukach z wag.

    Args:
        weights: Seria wag (frakcja kapitału)
        equity: Kapitał całkowity
        last_prices: Ceny aktualne

    Returns:
        Seria ilości sztuk (zaokrąglone)
    """
    dollars = (weights * equity).fillna(0.0)
    qty = (dollars / last_prices.reindex(weights.index)).fillna(0.0)
    return qty.round(0)


def main(broker_csv: str, target_weights_csv: str, equity: float):
    """
    Porównuje target vs broker positions i wyświetla różnice.

    Args:
        broker_csv: CSV z pozycjami brokera
        target_weights_csv: CSV z target weights (symbol, weight, last_price)
        equity: Kapitał całkowity
    """
    broker = load_broker_positions_csv(broker_csv)
    tw = pd.read_csv(target_weights_csv).set_index("symbol")["weight"].astype(float)
    last_px = pd.read_csv(target_weights_csv).set_index("symbol")["last_price"].astype(float)

    tgt = target_positions_from_weights(tw, equity, last_px)
    aligned = pd.concat([
        tgt.rename("target_qty"),
        broker.rename("broker_qty")
    ], axis=1).fillna(0.0)

    aligned["diff_qty"] = aligned["target_qty"] - aligned["broker_qty"]
    print(aligned.sort_index())

    # Exit code ≠0 jeśli są różnice
    large = aligned["diff_qty"].abs().sum()
    if large > 0:
        print(f"\n⚠️  Wykryto różnice w pozycjach (suma abs: {large:.0f})")
        exit(1)
    else:
        print("\n✓ Pozycje zgodne (target = broker)")
        exit(0)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Rekonsyliacja pozycji broker vs target")
    ap.add_argument("--broker_csv", required=True, help="CSV z pozycjami brokera")
    ap.add_argument("--target_weights_csv", required=True, help="CSV: symbol,weight,last_price")
    ap.add_argument("--equity", type=float, required=True, help="Kapitał całkowity")
    args = ap.parse_args()

    main(args.broker_csv, args.target_weights_csv, args.equity)
