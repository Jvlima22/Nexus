"""
Execução de ordens da NEXUS com gerenciamento de risco.

Fluxo: Risk Judge (risk.evaluate, o juiz inegociável) → buy na IQ → grava em
`trades` (open) → thread acompanha o resultado e dá UPDATE (win/loss/tie).
"""
from __future__ import annotations

import logging
import threading
import time

import risk
import snapshot
import supabase_sync
from iq_client import client
from risk import RiskError  # re-exportado p/ compatibilidade (main.py captura orders.RiskError)

logger = logging.getLogger("nexus.orders")

__all__ = ["place_order", "RiskError"]


def place_order(
    active: str,
    direction: str,
    amount: float,
    expiration_min: int,
    option_type: str,
    confidence: float | None = None,
) -> dict:
    if direction not in ("call", "put"):
        raise ValueError("direction deve ser 'call' ou 'put'")
    if amount <= 0:
        raise ValueError("amount deve ser > 0")
    if not supabase_sync.configured():
        raise RuntimeError("Supabase não configurado — ordem não seria registrada")

    # ── Risk Judge: todo sinal passa por aqui antes de executar ──
    verdict = risk.evaluate(active, direction, amount, confidence)

    payout = client.get_payout(active, option_type)
    order_id = client.buy(active, direction, amount, expiration_min, option_type)
    trade_id = supabase_sync.insert_trade(active, direction, amount, order_id, expiration_min, option_type, payout)
    logger.info("Ordem aberta: %s %s %.2f (order=%s)", active, direction, amount, order_id)

    threading.Thread(
        target=_track, args=(order_id, option_type, expiration_min),
        daemon=True, name=f"track-{order_id}",
    ).start()
    # Snapshot de auditoria (gráfico/padrão/indicadores/S-R do instante) — fora do caminho
    # crítico: roda em thread e qualquer falha é engolida, nunca afeta a ordem.
    threading.Thread(
        target=_capture_snapshot,
        args=(trade_id, order_id, active, direction, confidence, expiration_min, payout, verdict),
        daemon=True, name=f"snapshot-{order_id}",
    ).start()
    return {
        "ok": True,
        "order_id": order_id,
        "trade_id": trade_id,
        "balance": verdict["balance"],
        "risk_limit": verdict["risk_limit"],
        "payout": payout,
        "risk": verdict,
    }


def _capture_snapshot(
    trade_id: str,
    order_id,
    active: str,
    direction: str,
    confidence: float | None,
    expiration_min: int,
    payout: float | None,
    verdict: dict,
) -> None:
    """Puxa a janela de candles do instante, monta o snapshot e persiste. Best-effort."""
    try:
        size = snapshot.tf_for_expiration(expiration_min)
        candles = client.get_candles(active, size, 80)  # ~80 p/ warm-up dos indicadores
        if not candles:
            return
        snap = snapshot.build(
            active, size, candles,
            direction=direction, confidence=confidence,
            entry_price=candles[-1]["close"], expiration_min=expiration_min,
            risk_verdict=verdict,
        )
        snap["payout"] = payout
        supabase_sync.insert_trade_snapshot(trade_id, order_id, active, snap["timeframe"], snap)
        logger.info("Snapshot gravado p/ %s (trade=%s, %d candles)", active, trade_id, len(snap["candles"]))
    except Exception:  # noqa: BLE001 — auditoria nunca derruba a ordem
        logger.exception("Falha ao capturar snapshot da ordem %s", order_id)


def _track(order_id, option_type: str, expiration_min: int) -> None:
    """Acompanha o resultado e dá UPDATE em `trades` (open → win/loss/tie).

    NÃO usa check_win_v3/v4: em OTC esses bloqueiam/penduram e a ordem nunca fechava.
    Em vez disso espera a expiração e resolve pelo HISTÓRICO de posições (confiável p/
    OTC e real), com tentativas. Para digital tenta primeiro o check rápido não-bloqueante.
    """
    try:
        time.sleep(expiration_min * 60 + 8)  # deixa a opção fechar antes de consultar
        deadline = time.time() + 360  # ~6 min de janela p/ o histórico publicar o resultado
        while time.time() < deadline:
            status = pnl = None
            try:
                if option_type == "digital":
                    status, pnl = client.check_result(order_id, option_type)  # rápido p/ digital
                if not status:
                    status, pnl = client.result_from_history(order_id, option_type)
            except Exception:  # noqa: BLE001 — uma tentativa que falha não derruba o tracker
                logger.debug("tentativa de resultado falhou p/ %s", order_id, exc_info=True)
            if status:
                supabase_sync.close_trade(order_id, status, pnl)
                logger.info("Ordem %s fechada: %s (pnl=%s)", order_id, status, pnl)
                return
            time.sleep(15)
        logger.warning("Resultado da ordem %s não resolveu na janela; o reconcile pega depois", order_id)
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao acompanhar a ordem %s", order_id)
