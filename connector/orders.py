"""
Execução de ordens da NEXUS com gerenciamento de risco.

Fluxo: valida risco (≤2% da banca, regra do CLAUDE.md) → buy na IQ → grava em
`trades` (open) → thread acompanha o resultado e dá UPDATE (win/loss/tie).
"""
from __future__ import annotations

import logging
import threading

import supabase_sync
from iq_client import client

logger = logging.getLogger("nexus.orders")

RISK_PCT = 0.02  # máximo 2% da banca por operação


class RiskError(Exception):
    """Ordem rejeitada pelo gate de risco."""


def place_order(active: str, direction: str, amount: float, expiration_min: int, option_type: str) -> dict:
    if direction not in ("call", "put"):
        raise ValueError("direction deve ser 'call' ou 'put'")
    if amount <= 0:
        raise ValueError("amount deve ser > 0")
    if not supabase_sync.configured():
        raise RuntimeError("Supabase não configurado — ordem não seria registrada")

    # ── Gate de risco: amount ≤ 2% da banca ──
    balance = client.get_balance()
    limit = round(balance * RISK_PCT, 2)
    if amount > limit:
        raise RiskError(
            f"Ordem de {amount:.2f} excede o limite de risco de 2% da banca "
            f"({limit:.2f} de {balance:.2f}). Reduza o valor."
        )

    payout = client.get_payout(active, option_type)
    order_id = client.buy(active, direction, amount, expiration_min, option_type)
    trade_id = supabase_sync.insert_trade(active, direction, amount, order_id, expiration_min, option_type, payout)
    logger.info("Ordem aberta: %s %s %.2f (order=%s)", active, direction, amount, order_id)

    threading.Thread(target=_track, args=(order_id, option_type), daemon=True, name=f"track-{order_id}").start()
    return {
        "ok": True,
        "order_id": order_id,
        "trade_id": trade_id,
        "balance": balance,
        "risk_limit": limit,
        "payout": payout,
    }


def _track(order_id, option_type: str) -> None:
    try:
        status, pnl = client.wait_result(order_id, option_type)
        if status == "open":
            logger.warning("Resultado da ordem %s expirou sem fechar", order_id)
            return
        supabase_sync.close_trade(order_id, status, pnl)
        logger.info("Ordem %s fechada: %s (pnl=%s)", order_id, status, pnl)
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao acompanhar a ordem %s", order_id)
