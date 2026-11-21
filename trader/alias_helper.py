"""
NEXUS Trader — Symbol Alias Helper
Resolves MetaTrader 5 / Forex / Commodity symbols to Yahoo Finance symbols
based on the configurations in trader/config.json.
"""
from __future__ import annotations

import json
from pathlib import Path


def load_aliases(config_path: str = "trader/config.json") -> dict[str, str]:
    path = Path(config_path)
    if not path.exists():
        return {
            "EURUSD": "EURUSD=X",
            "GBPUSD": "GBPUSD=X",
            "USDJPY": "USDJPY=X",
            "USDCHF": "USDCHF=X",
            "AUDUSD": "AUDUSD=X",
            "NZDUSD": "NZDUSD=X",
            "USDCAD": "USDCAD=X",
            "EURJPY": "EURJPY=X",
            "GBPJPY": "GBPJPY=X",
            "XAUUSD": "GC=F",
            "GOLD": "GC=F",
        }
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("symbol_aliases", {})
    except Exception:
        return {}


def resolve_symbol(symbol: str, config_path: str = "trader/config.json") -> str:
    sym = symbol.strip().upper()
    aliases = load_aliases(config_path)
    return aliases.get(sym, sym)


def reverse_resolve(yahoo_symbol: str, config_path: str = "trader/config.json") -> str:
    sym = yahoo_symbol.strip()
    aliases = load_aliases(config_path)
    inv = {v: k for k, v in aliases.items()}
    return inv.get(sym, sym)


if __name__ == "__main__":
    import sys
    test_symbols = sys.argv[1:] if len(sys.argv) > 1 else ["EURUSD", "XAUUSD", "TSLA", "GC=F"]
    for s in test_symbols:
        resolved = resolve_symbol(s)
        print(f"{s} -> {resolved}")
