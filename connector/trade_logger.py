"""
NEXUS — trade_logger.py
Grava cada operação MT5 no Supabase com racional da IA, padrão e resultado.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Literal, Optional

from supabase import create_client, Client


# ---------------------------------------------------------------------------
# Cliente Supabase
# ---------------------------------------------------------------------------

def _get_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


# ---------------------------------------------------------------------------
# Tipos
# ---------------------------------------------------------------------------

Session = Literal["asian", "london", "new_york", "overlap", "off"]
Direction = Literal["BUY", "SELL"]


def detect_session(utc_hour: int) -> Session:
    """Classifica a sessão com base na hora UTC."""
    if 22 <= utc_hour or utc_hour < 7:
        return "asian"
    if 7 <= utc_hour < 12:
        return "london"
    if 12 <= utc_hour < 16:
        return "overlap"
    if 16 <= utc_hour < 21:
        return "new_york"
    return "off"


# ---------------------------------------------------------------------------
# Log de sinal (antes de entrar)
# ---------------------------------------------------------------------------

def log_signal(
    *,
    symbol: str,
    direction: Direction,
    timeframe: str,
    pattern: str,
    session: Session,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    rr_ratio: float,
    ai_reasoning: str,
    h1_bias: str,
    m5_structure: str,
    confidence: int,           # 0-100
) -> str:
    """
    Insere um sinal na tabela ai_signals antes da execução.
    Retorna o ID gerado para linkar ao trade.
    """
    client = _get_client()
    now = datetime.now(timezone.utc).isoformat()

    row = {
        "created_at": now,
        "symbol": symbol,
        "direction": direction,
        "timeframe": timeframe,
        "pattern": pattern,
        "session": session,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "rr_ratio": rr_ratio,
        "ai_reasoning": ai_reasoning,
        "h1_bias": h1_bias,
        "m5_structure": m5_structure,
        "confidence": confidence,
        "outcome": "pending",
    }

    result = client.table("ai_signals").insert(row).execute()
    return result.data[0]["id"]


# ---------------------------------------------------------------------------
# Log de entrada (após place_market_order)
# ---------------------------------------------------------------------------

def log_trade_open(
    *,
    signal_id: Optional[str] = None,
    position_id: int,
    symbol: str,
    direction: Direction,
    volume: float,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    timeframe: str,
    pattern: str,
    session: Session,
    ai_reasoning: str,
) -> str:
    """
    Insere a operação aberta na tabela trades.
    Retorna o ID do registro.
    """
    client = _get_client()
    now = datetime.now(timezone.utc).isoformat()

    row = {
        "created_at": now,
        "source": "nexus_mt5",
        "position_id": str(position_id),
        "symbol": symbol,
        "direction": direction,
        "volume": volume,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "timeframe": timeframe,
        "pattern": pattern,
        "session": session,
        "ai_reasoning": ai_reasoning,
        "signal_id": signal_id,
        "status": "open",
        "result": None,
        "pnl": None,
        "closed_at": None,
    }

    result = client.table("trades").insert(row).execute()
    return result.data[0]["id"]


# ---------------------------------------------------------------------------
# Log de fechamento (após TP/SL/manual)
# ---------------------------------------------------------------------------

def log_trade_close(
    *,
    position_id: int,
    close_price: float,
    pnl: float,
    close_reason: Literal["tp", "sl", "manual"],
) -> None:
    """
    Atualiza o registro do trade com resultado e fecha.
    Também atualiza o outcome na tabela ai_signals.
    """
    client = _get_client()
    now = datetime.now(timezone.utc).isoformat()
    result_label = "win" if pnl > 0 else "loss"

    # Atualiza trades
    update = {
        "status": "closed",
        "close_price": close_price,
        "pnl": pnl,
        "result": result_label,
        "close_reason": close_reason,
        "closed_at": now,
    }

    trade = (
        client.table("trades")
        .update(update)
        .eq("position_id", str(position_id))
        .execute()
    )

    # Propaga outcome para ai_signals
    if trade.data and trade.data[0].get("signal_id"):
        signal_id = trade.data[0]["signal_id"]
        client.table("ai_signals").update({"outcome": result_label}).eq("id", signal_id).execute()


# ---------------------------------------------------------------------------
# Consulta de histórico (para a IA aprender)
# ---------------------------------------------------------------------------

def get_pattern_stats(
    symbol: str = "EURUSD",
    min_samples: int = 5,
) -> list[dict]:
    """
    Retorna win rate agrupado por padrão + sessão.
    Usado pelo Claude antes de analisar para calibrar confiança.
    """
    client = _get_client()

    rows = (
        client.table("ai_signals")
        .select("pattern, session, outcome")
        .eq("symbol", symbol)
        .neq("outcome", "pending")
        .execute()
    )

    stats: dict[str, dict] = {}
    for row in rows.data:
        key = f"{row['pattern']}|{row['session']}"
        if key not in stats:
            stats[key] = {"pattern": row["pattern"], "session": row["session"], "wins": 0, "total": 0}
        stats[key]["total"] += 1
        if row["outcome"] == "win":
            stats[key]["wins"] += 1

    result = []
    for s in stats.values():
        if s["total"] >= min_samples:
            s["win_rate"] = round(s["wins"] / s["total"] * 100, 1)
            result.append(s)

    return sorted(result, key=lambda x: x["win_rate"], reverse=True)


# ---------------------------------------------------------------------------
# Resumo da sessão atual (para o diário Obsidian)
# ---------------------------------------------------------------------------

def get_session_summary(date_str: str) -> dict:
    """
    Retorna estatísticas da sessão de um dia específico (YYYY-MM-DD).
    """
    client = _get_client()

    trades = (
        client.table("trades")
        .select("*")
        .gte("created_at", f"{date_str}T00:00:00Z")
        .lte("created_at", f"{date_str}T23:59:59Z")
        .eq("source", "nexus_mt5")
        .execute()
    )

    rows = trades.data
    total = len(rows)
    wins = sum(1 for r in rows if r.get("result") == "win")
    losses = sum(1 for r in rows if r.get("result") == "loss")
    total_pnl = sum(r.get("pnl") or 0 for r in rows)

    return {
        "date": date_str,
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / total * 100, 1) if total > 0 else 0,
        "total_pnl": round(total_pnl, 2),
        "trades": rows,
    }
