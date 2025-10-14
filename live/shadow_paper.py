"""
Minimalny loop dla paper trading IBKR (ib_insync).

OSTRZEŻENIE: To jest szkic demo. Przed użyciem w środowisku live/paper:
1. Przetestuj dokładnie wszystkie funkcje
2. Dodaj pełną walidację zleceń
3. Zaimplementuj monitoring i alerting
4. Sprawdź limity ryzyka
5. Upewnij się, że masz odpowiednie uprawnienia i konfigurację IBKR
"""
import os
import sys
import time
import argparse
import yaml
from datetime import datetime
from dotenv import load_dotenv

try:
    from ib_insync import IB, Stock, MarketOrder, LimitOrder
except ImportError:
    print("BŁĄD: ib_insync nie jest zainstalowany. Uruchom: pip install ib-insync")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def connect_ib(host: str, port: int, client_id: int) -> IB:
    """
    Nawiązuje połączenie z IBKR.

    Parameters:
    -----------
    host : str
        Host IBKR (np. 127.0.0.1)
    port : int
        Port (7497 dla paper, 7496 dla live)
    client_id : int
        Client ID

    Returns:
    --------
    IB
        Obiekt połączenia
    """
    ib = IB()
    try:
        ib.connect(host, port, clientId=client_id)
        print(f"✓ Połączono z IBKR: {host}:{port}")
        return ib
    except Exception as e:
        print(f"BŁĄD przy połączeniu z IBKR: {e}")
        raise


def get_portfolio_positions(ib: IB):
    """Zwraca obecne pozycje portfela."""
    positions = ib.positions()
    print(f"\nObecne pozycje ({len(positions)}):")
    for pos in positions:
        print(f"  {pos.contract.symbol}: {pos.position} szt @ {pos.avgCost:.2f}")
    return positions


def main():
    parser = argparse.ArgumentParser(description="Shadow/Paper trading loop (IBKR)")
    parser.add_argument("--config", type=str, required=True, help="Ścieżka do pliku YAML")
    parser.add_argument("--dry-run", action="store_true", help="Tylko odczyt, bez wysyłania zleceń")
    args = parser.parse_args()

    try:
        # Załaduj ENV
        load_dotenv()

        # Wczytaj config
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)

        ibkr_config = config["ibkr"]

        # Połącz z IBKR
        ib = connect_ib(
            host=os.environ.get("IB_HOST", ibkr_config["host"]),
            port=int(os.environ.get("IB_PORT", ibkr_config["port"])),
            client_id=int(os.environ.get("IB_CLIENT_ID", ibkr_config["client_id"]))
        )

        # Pobierz pozycje
        positions = get_portfolio_positions(ib)

        # Demo: pobierz wartość konta
        account_values = ib.accountSummary()
        for av in account_values:
            if av.tag == 'NetLiquidation':
                print(f"\nWartość portfela: {av.value} {av.currency}")

        if args.dry_run:
            print("\n(--dry-run: pomijam wysyłkę zleceń)")
        else:
            print("\nUWAGA: Realna wysyłka zleceń jest zakomentowana dla bezpieczeństwa.")
            print("Przed aktywacją upewnij się, że kod jest przetestowany.")

            # PRZYKŁAD (zakomentowany):
            # ticker = "AAPL"
            # contract = Stock(ticker, ibkr_config["exchange"], ibkr_config["currency"])
            # ib.qualifyContracts(contract)
            # order = MarketOrder("BUY", 1)
            # trade = ib.placeOrder(contract, order)
            # print(f"Zlecenie wysłane: {trade}")

        # Rozłącz
        ib.disconnect()
        print("\n✓ Rozłączono z IBKR")

    except Exception as e:
        print(f"\nBŁĄD: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
