"""Loops de sincronização: IQ Option → Supabase (estado durável)."""
from __future__ import annotations

import logging
import threading
import time

import supabase_sync
from iq_client import client

logger = logging.getLogger("nexus.sync")


def _asset_loop(interval_s: int) -> None:
    while True:
        try:
            assets = client.get_assets()
            supabase_sync.upsert_assets(assets)
            logger.info("assets sincronizados (%d)", len(assets))
        except Exception:  # noqa: BLE001
            logger.exception("Falha no sync de assets")
        time.sleep(interval_s)


def start_asset_sync(interval_s: int = 30) -> None:
    """Poll periódico dos ativos → tabela `assets`. No-op se Supabase não configurado."""
    if not supabase_sync.configured():
        logger.warning("Supabase não configurado (SUPABASE_URL/SERVICE_ROLE_KEY/NEXUS_USER_ID) — sync de assets desligado")
        return
    threading.Thread(target=_asset_loop, args=(interval_s,), daemon=True, name="asset-sync").start()
    logger.info("Sync de assets iniciado (cada %ss)", interval_s)


def _balance_loop(interval_s: int) -> None:
    while True:
        try:
            supabase_sync.insert_balance(client.get_balance())
        except Exception:  # noqa: BLE001
            logger.exception("Falha no sync de saldo")
        time.sleep(interval_s)


def start_balance_sync(interval_s: int = 15) -> None:
    """Snapshot periódico de saldo → bankroll_history."""
    if not supabase_sync.configured():
        return
    threading.Thread(target=_balance_loop, args=(interval_s,), daemon=True, name="balance-sync").start()
    logger.info("Sync de saldo iniciado (cada %ss)", interval_s)


# Tipos de instrumento que a lib aceita no histórico.
_HISTORY_TYPES = ["turbo-option", "binary-option", "digital-option"]


def reconcile_open_trades() -> dict:
    """
    Fecha trades 'open' órfãs (a thread de acompanhamento morreu num restart):
    consulta o resultado real na IQ e dá UPDATE. Retorna checked/closed/unresolved.
    """
    if not supabase_sync.configured():
        return {"checked": 0, "closed": [], "unresolved": []}
    open_trades = supabase_sync.get_open_nexus_trades()
    closed: list[dict] = []
    unresolved: list[str] = []
    for t in open_trades:
        eid = t["external_id"]
        otype = t.get("option_type") or "binary"
        try:
            # 1) mesma sessão (instantâneo); 2) histórico (ordens órfãs de outra sessão)
            status, pnl = client.check_result(eid, otype)
            if not status:
                status, pnl = client.result_from_history(eid, otype)
            if status:
                supabase_sync.close_trade(eid, status, pnl)
                closed.append({"order": eid, "status": status, "pnl": pnl})
                logger.info("reconciliada ordem %s: %s (pnl=%s)", eid, status, pnl)
            else:
                unresolved.append(eid)
                logger.warning("ordem %s ainda sem resultado (não encontrada no histórico)", eid)
        except Exception:  # noqa: BLE001
            unresolved.append(eid)
            logger.exception("falha ao reconciliar ordem %s", eid)
    return {"checked": len(open_trades), "closed": closed, "unresolved": unresolved}


def start_reconcile_on_boot() -> None:
    """Reconcilia ordens órfãs ~3s após o boot (dá tempo da conexão estabilizar)."""
    if not supabase_sync.configured():
        return

    def run() -> None:
        time.sleep(20)  # IQ leva ~10-30s p/ ter o histórico de posições pronto
        res = reconcile_open_trades()
        if res["closed"]:
            logger.info("Reconciliação no boot: %d ordem(ns) fechada(s)", len(res["closed"]))

    threading.Thread(target=run, daemon=True, name="reconcile-boot").start()


def backfill_history(limit_per_type: int = 100) -> int:
    """Importa operações passadas da IQ → trades (source='manual'). Best-effort."""
    if not supabase_sync.configured():
        raise RuntimeError("Supabase não configurado")
    total = 0
    for itype in _HISTORY_TYPES:
        try:
            positions = client.get_position_history(itype, limit_per_type)
            n = supabase_sync.insert_historical_trades(positions)
            total += n
            logger.info("backfill %s: %d posições lidas, %d novas", itype, len(positions), n)
        except Exception:  # noqa: BLE001
            logger.exception("backfill falhou para %s", itype)
    return total
