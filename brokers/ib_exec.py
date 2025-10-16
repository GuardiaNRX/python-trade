from __future__ import annotations

import math
import os
import time
from typing import Optional

import pandas as pd
from ib_insync import IB, Contract, LimitOrder, Stock

_EXCHANGE_MAP = {
    "XNAS": ("SMART", "USD", "NASDAQ"),
    "XNYS": ("SMART", "USD", "NYSE"),
    "ARCX": ("SMART", "USD", "ARCA"),
}


def _stock(symbol: str, primary_code: Optional[str]) -> Contract:
    smart, currency, primary = _EXCHANGE_MAP.get(primary_code or "", ("SMART", "USD", None))
    if primary:
        return Stock(symbol, smart, currency, primaryExchange=primary)
    return Stock(symbol, smart, currency)


def _round_shares(qty_usd: float, price: float) -> int:
    if price <= 0:
        return 0
    return max(int(math.floor(qty_usd / price)), 0)


def connect_ib() -> IB:
    ib = IB()
    host = os.getenv("IB_HOST", "127.0.0.1")
    port = int(os.getenv("IB_PORT", "7497"))
    client_id = int(os.getenv("IB_CLIENT_ID", "123"))
    readonly = os.getenv("CONFIRM_SEND", "0") != "1"
    ib.connect(host, port, clientId=client_id, readonly=readonly)
    return ib


def send_plan_csv(
    plan_csv: str,
    symbol_map_csv: Optional[str] = "data/symbol_exchange_map.csv",
    account: Optional[str] = None,
    dry_run: bool = True,
    sleep_s: float = 0.2,
) -> None:
    plan = pd.read_csv(plan_csv, parse_dates=["slice_time"])
    if plan.empty:
        print("Plan pusty – nic do wysłania.")
        return

    prim_map: dict[str, str] = {}
    if symbol_map_csv and os.path.exists(symbol_map_csv):
        symbol_df = pd.read_csv(symbol_map_csv)
        prim_map = {row.symbol: row.exchange for row in symbol_df.itertuples()}

    ib = connect_ib()
    try:
        symbols = sorted(set(plan["symbol"]))
        contracts = [_stock(symbol, prim_map.get(symbol)) for symbol in symbols]
        if contracts:
            ib.qualifyContracts(*contracts)
        lookup = {contract.symbol: contract for contract in contracts}

        for row in plan.itertuples(index=False):
            symbol = row.symbol
            side = str(row.side).upper()
            qty_usd = float(row.qty_usd)
            limit_px = float(row.limit_price)

            contract = lookup.get(symbol) or _stock(symbol, prim_map.get(symbol))
            qty = _round_shares(qty_usd, limit_px)
            if qty <= 0:
                print(f"[SKIP] {symbol}: qty=0 (usd={qty_usd:.2f}, px={limit_px:.4f})")
                continue

            action = "BUY" if side == "BUY" else "SELL"
            order = LimitOrder(
                action,
                qty,
                limit_px,
                tif="DAY",
                account=account or os.getenv("IB_ACCOUNT"),
            )
            print(f"[{action}] {symbol} x{qty} @ {limit_px:.4f} (usd≈{qty * limit_px:,.2f})")

            if not dry_run and os.getenv("CONFIRM_SEND", "0") == "1":
                ib.placeOrder(contract, order)
                ib.sleep(0.01)

            time.sleep(sleep_s)
    finally:
        ib.disconnect()
