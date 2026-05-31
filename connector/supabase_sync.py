"""Cliente Supabase (service_role) — escreve estado durável (assets/trades/saldo)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from config import settings

logger = logging.getLogger("nexus.supabase")

_sb: Any = None


def configured() -> bool:
    return bool(settings.supabase_url and settings.supabase_service_role_key and settings.nexus_user_id)


def get_sb() -> Any:
    global _sb
    if _sb is None:
        from supabase import create_client  # import tardio

        _sb = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _sb


def upsert_assets(assets: list[dict[str, Any]]) -> None:
    """Upsert na tabela `assets` por (user_id, symbol, type). service_role bypassa RLS."""
    if not assets:
        return
    now = datetime.now(timezone.utc).isoformat()

    # Dedup por (symbol, type): turbo+binary mapeiam pro mesmo type → linhas
    # duplicadas no mesmo upsert violam o ON CONFLICT. Merge: is_open por OR,
    # payout pelo maior.
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for a in assets:
        key = (a["symbol"], a["type"])
        cur = merged.get(key)
        if cur is None:
            merged[key] = {"is_open": a["is_open"], "payout": a["payout"]}
        else:
            cur["is_open"] = cur["is_open"] or a["is_open"]
            if a["payout"] is not None and (cur["payout"] is None or a["payout"] > cur["payout"]):
                cur["payout"] = a["payout"]

    rows = [
        {
            "user_id": settings.nexus_user_id,
            "symbol": symbol,
            "name": symbol,
            "type": atype,
            "is_open": v["is_open"],
            "payout": v["payout"],
            "updated_at": now,
        }
        for (symbol, atype), v in merged.items()
    ]
    get_sb().table("assets").upsert(rows, on_conflict="user_id,symbol,type").execute()


def insert_trade(
    active: str,
    direction: str,
    amount: float,
    order_id: Any,
    expiration_min: int,
    option_type: str,
    payout: float | None,
) -> str:
    """Grava a ordem aberta em `trades` (reusa colunas existentes). Retorna o id."""
    now = datetime.now(timezone.utc)
    row = {
        "user_id": settings.nexus_user_id,
        "asset": active,
        "type": "Call" if direction == "call" else "Put",  # convenção do front
        "option_type": option_type,
        "amount": amount,
        "payout": payout,
        "expiration_seconds": expiration_min * 60,
        "time": now.isoformat(),
        "expires_at": (now + timedelta(minutes=expiration_min)).isoformat(),
        "external_id": str(order_id),
        "status": "open",
        "source": "nexus",
    }
    res = get_sb().table("trades").insert(row).execute()
    return res.data[0]["id"]


def insert_balance(balance: float) -> None:
    """Snapshot de saldo em bankroll_history (append-only)."""
    acct = "real" if settings.iq_balance_mode.upper() == "REAL" else "practice"
    get_sb().table("bankroll_history").insert(
        {
            "user_id": settings.nexus_user_id,
            "balance": balance,
            "account_type": acct,
            "source": "tick",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()


def _existing_external_ids() -> set[str]:
    res = (
        get_sb()
        .table("trades")
        .select("external_id")
        .eq("user_id", settings.nexus_user_id)
        .execute()
    )
    return {r["external_id"] for r in res.data if r.get("external_id")}


def insert_historical_trades(positions: list[dict[str, Any]]) -> int:
    """Grava operações passadas (source='manual'), pulando as já existentes. Retorna nº inseridas."""
    if not positions:
        return 0
    existing = _existing_external_ids()
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for p in positions:
        if p["external_id"] in existing:
            continue
        rows.append(
            {
                "user_id": settings.nexus_user_id,
                "asset": p["asset"],
                "type": p["type"],
                "amount": p["amount"],
                "result": p["pnl"],  # `result` guarda o PnL (não há coluna `pnl`)
                "status": p["status"],
                "option_type": p["option_type"],
                "external_id": p["external_id"],
                "source": "manual",
                "time": now,
                "closed_at": now,
            }
        )
    if not rows:
        return 0
    get_sb().table("trades").insert(rows).execute()
    return len(rows)


def get_open_nexus_trades() -> list[dict[str, Any]]:
    """Trades da NEXUS ainda 'open' (p/ reconciliar resultado após restart)."""
    res = (
        get_sb()
        .table("trades")
        .select("external_id,option_type")
        .eq("user_id", settings.nexus_user_id)
        .eq("source", "nexus")
        .eq("status", "open")
        .execute()
    )
    return [r for r in res.data if r.get("external_id")]


def close_trade(order_id: Any, status: str, pnl: float | None) -> None:
    """Atualiza o resultado da ordem → o front vê open→win/loss via Realtime."""
    get_sb().table("trades").update(
        {
            "status": status,
            "result": pnl,  # `result` é o PnL em $ (schema legado); não há coluna `pnl`
            "closed_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("user_id", settings.nexus_user_id).eq("external_id", str(order_id)).execute()
