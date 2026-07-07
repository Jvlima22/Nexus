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


def get_open_assets() -> list[dict[str, Any]]:
    """Ativos atualmente abertos (alimentados pelo loop de asset-sync). Base da watchlist
    dinâmica do autotrader — leitura rápida no Supabase em vez de bater na IQ a cada ciclo."""
    res = (
        get_sb()
        .table("assets")
        .select("symbol,type,payout")
        .eq("user_id", settings.nexus_user_id)
        .eq("is_open", True)
        .execute()
    )
    return res.data or []


def upsert_asset_edge(rows: list[dict[str, Any]]) -> None:
    """Upsert do edge medido (backtest) por (user_id, symbol). Alimenta o gate de
    evidência do autotrader e o painel. service_role bypassa RLS."""
    if not rows:
        return
    now = datetime.now(timezone.utc).isoformat()
    payload = [
        {
            "user_id": settings.nexus_user_id,
            "symbol": r["symbol"],
            "hit_rate": r.get("hit_rate"),
            "sample": r.get("sample") or 0,
            "confluence_hit_rate": r.get("confluence_hit_rate"),
            "confluence_sample": r.get("confluence_sample") or 0,
            "breakeven": r.get("breakeven"),
            "passes_gate": bool(r.get("passes_gate")),
            "updated_at": now,
        }
        for r in rows
    ]
    get_sb().table("asset_edge").upsert(payload, on_conflict="user_id,symbol").execute()


def get_asset_edge() -> dict[str, dict[str, Any]]:
    """Edge medido por símbolo (mapa symbol → linha). Base do gate de evidência."""
    res = (
        get_sb()
        .table("asset_edge")
        .select("symbol,hit_rate,sample,confluence_hit_rate,confluence_sample,breakeven,passes_gate,updated_at")
        .eq("user_id", settings.nexus_user_id)
        .execute()
    )
    return {r["symbol"]: r for r in (res.data or [])}


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


def insert_trade_snapshot(
    trade_id: str,
    external_id: Any,
    asset: str,
    timeframe: str,
    snapshot: dict[str, Any],
) -> None:
    """Grava o retrato do mercado no instante da ordem em `trade_snapshots` (1 por trade).
    Upsert por (user_id, trade_id) — reexecução não duplica. Lido sob demanda no clique."""
    get_sb().table("trade_snapshots").upsert(
        {
            "user_id": settings.nexus_user_id,
            "trade_id": trade_id,
            "external_id": str(external_id) if external_id is not None else None,
            "asset": asset,
            "timeframe": timeframe,
            "snapshot": snapshot,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="user_id,trade_id",
    ).execute()


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


def get_open_nexus_trades(source: str = "nexus") -> list[dict[str, Any]]:
    """Trades ainda 'open' de uma origem (p/ reconciliar resultado após restart)."""
    res = (
        get_sb()
        .table("trades")
        .select("external_id,option_type")
        .eq("user_id", settings.nexus_user_id)
        .eq("source", source)
        .eq("status", "open")
        .execute()
    )
    return [r for r in res.data if r.get("external_id")]


# ──────────────────────────────────────────────────────────────────────────────
# Polymarket (Fase 4): snapshot de sentimento macro + leitura p/ o Risk Judge.
# ──────────────────────────────────────────────────────────────────────────────
def upsert_sentiment(snapshot: dict[str, Any]) -> None:
    """Upsert do bias de um mercado em `market_sentiment` por (user_id, slug)."""
    get_sb().table("market_sentiment").upsert(
        {
            "user_id": settings.nexus_user_id,
            "slug": snapshot["slug"],
            "question": snapshot.get("question"),
            "probability": snapshot["probability"],
            "bias": snapshot["bias"],
            "volume": snapshot.get("volume"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="user_id,slug",
    ).execute()


def get_sentiment() -> list[dict[str, Any]]:
    """Snapshots de sentimento do usuário (p/ o Risk Judge agregar o bias macro)."""
    res = (
        get_sb()
        .table("market_sentiment")
        .select("slug,question,probability,bias,volume,updated_at")
        .eq("user_id", settings.nexus_user_id)
        .execute()
    )
    return res.data or []


# ──────────────────────────────────────────────────────────────────────────────
# Risk Judge (Fase 3): estado para circuit breaker / teto diário + auditoria.
# ──────────────────────────────────────────────────────────────────────────────
def recent_results(limit: int = 10, source: str = "nexus") -> list[str]:
    """Status das últimas ordens fechadas de uma origem (mais recente primeiro). Base do circuit breaker."""
    res = (
        get_sb()
        .table("trades")
        .select("status,closed_at")
        .eq("user_id", settings.nexus_user_id)
        .eq("source", source)
        .in_("status", ["win", "loss", "tie"])
        .order("closed_at", desc=True)
        .limit(limit)
        .execute()
    )
    return [r["status"] for r in res.data]


def today_realized_pnl(source: str = "nexus") -> float:
    """Soma do PnL (`result`) das ordens de uma origem fechadas desde 00:00 UTC. Negativo = prejuízo."""
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    res = (
        get_sb()
        .table("trades")
        .select("result")
        .eq("user_id", settings.nexus_user_id)
        .eq("source", source)
        .gte("closed_at", start.isoformat())
        .not_.is_("result", "null")
        .execute()
    )
    return float(sum((r.get("result") or 0) for r in res.data))


def insert_risk_event(
    decision: str,
    code: str,
    active: str,
    direction: str,
    confidence: float | None,
    amount: float,
    balance: float | None,
    reason: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Audita o veredito do Risk Judge (aprovação ou veto) em `risk_events`."""
    try:
        get_sb().table("risk_events").insert(
            {
                "user_id": settings.nexus_user_id,
                "decision": decision,
                "code": code,
                "asset": active,
                "direction": direction,
                "confidence": confidence,
                "amount": amount,
                "balance": balance,
                "reason": reason,
                "details": details or {},
            }
        ).execute()
    except Exception:  # noqa: BLE001 — auditoria não pode derrubar a decisão de risco
        logger.exception("Falha ao gravar risk_event (%s/%s)", decision, code)


def close_trade(order_id: Any, status: str, pnl: float | None) -> None:
    """Atualiza o resultado da ordem → o front vê open→win/loss via Realtime."""
    get_sb().table("trades").update(
        {
            "status": status,
            "result": pnl,  # `result` é o PnL em $ (schema legado); não há coluna `pnl`
            "closed_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("user_id", settings.nexus_user_id).eq("external_id", str(order_id)).execute()
