"""
Crypto Payment Monitor for Q-Mol
Check Ethereum wallet for incoming payments/transfers.
Uses public Etherscan API (free tier).
"""
import requests
import json
from typing import List, Dict, Optional
from datetime import datetime

# Q-Mol Ethereum wallet
WALLET_ADDRESS = "0x75B30d0dE751D9628510f3cb273F09f7137f9E3F"

# Etherscan API (free public endpoint — no key needed for basic checks)
ETHERSCAN_API = "https://api.etherscan.io/api"


def get_wallet_balance() -> Optional[float]:
    """Get ETH balance of the Q-Mol wallet."""
    params = {
        "module": "account",
        "action": "balance",
        "address": WALLET_ADDRESS,
        "tag": "latest",
    }
    try:
        resp = requests.get(ETHERSCAN_API, params=params, timeout=15)
        data = resp.json()
        if data.get("status") == "1":
            wei = int(data["result"])
            return wei / 1e18
        return None
    except Exception as e:
        print(f"Error fetching balance: {e}")
        return None


def get_recent_transactions(limit: int = 20) -> List[Dict]:
    """Get recent normal transactions for the wallet."""
    params = {
        "module": "account",
        "action": "txlist",
        "address": WALLET_ADDRESS,
        "startblock": 0,
        "endblock": 99999999,
        "sort": "desc",
        "page": 1,
        "offset": limit,
    }
    try:
        resp = requests.get(ETHERSCAN_API, params=params, timeout=15)
        data = resp.json()
        if data.get("status") == "1":
            return data.get("result", [])
        return []
    except Exception as e:
        print(f"Error fetching transactions: {e}")
        return []


def format_tx(tx: Dict) -> str:
    """Format a transaction for display."""
    value_eth = int(tx.get("value", 0)) / 1e18
    ts = int(tx.get("timeStamp", 0))
    dt = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S UTC")
    direction = "IN" if tx.get("to", "").lower() == WALLET_ADDRESS.lower() else "OUT"
    return (
        f"  [{direction}] {value_eth:.6f} ETH  |  "
        f"{tx.get('from', '??')[:20]}...  |  {dt}"
    )


def main():
    print("=" * 60)
    print("Q-MOL CRYPTO PAYMENT MONITOR")
    print(f"Wallet: {WALLET_ADDRESS}")
    print("=" * 60)

    print("\n[1] ETH Balance...")
    balance = get_wallet_balance()
    if balance is not None:
        print(f"  Current balance: {balance:.6f} ETH")
    else:
        print("  Could not fetch balance.")

    print("\n[2] Recent transactions...")
    txs = get_recent_transactions(limit=10)
    if not txs:
        print("  No transactions found (or API error).")
    else:
        for tx in txs:
            print(format_tx(tx))

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
