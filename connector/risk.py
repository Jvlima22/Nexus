"""
Risk Judge da NEXUS — o juiz inegociável por onde TODO sinal passa antes de
virar ordem na IQ. Nenhuma decisão da IA pula esta porta.

Regras (todas precisam passar; o primeiro veto interrompe e é auditado):
  0. Bias macro (Polymarket) vs. direção.     -> MACRO_CONFLICT
  0b. Sessão de mercado (Londres/NY).         -> OUTSIDE_SESSION
  0c. Blackout de notícia (ForexFactory).     -> NEWS_BLACKOUT
  1. Confiança ≥ MIN_CONFIDENCE.              -> LOW_CONFIDENCE
  2. Zona neutra (NEUTRAL_LOW–NEUTRAL_HIGH).  -> NEUTRAL  (ficar fora do mercado)
  3. Alocação ≤ RISK_PCT da banca (recalc).   -> ALLOC_EXCEEDED
  4. Circuit breaker: stops seguidos.         -> CIRCUIT_BREAKER
  5. Teto de prejuízo do dia.                 -> DAILY_LOSS_CAP

Confiança é opcional: ordens manuais (dashboard, sem sinal de IA) pulam as
regras 1–2, mas SEMPRE obedecem 0b e 3–5 (sessão, alocação, circuit breaker e
teto diário protegem humano e máquina por igual).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import forexfactory
import supabase_sync
from config import settings
from iq_client import client

logger = logging.getLogger("nexus.risk")


class RiskError(Exception):
    """Ordem vetada pelo Risk Judge. `code` identifica a regra violada."""

    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


def evaluate(active: str, direction: str, amount: float, confidence: float | None) -> dict:
    """Roda o funil de risco. Levanta RiskError no primeiro veto; senão devolve o veredito.

    O veto e a aprovação são gravados em `risk_events` para auditoria.
    """
    if confidence is not None and not (0.0 <= confidence <= 1.0):
        raise ValueError("confidence deve estar entre 0 e 1")

    def veto(code: str, message: str, details: dict) -> RiskError:
        supabase_sync.insert_risk_event(
            "rejected", code, active, direction, confidence, amount, details.get("balance"), message, details
        )
        logger.warning("Risk Judge VETOU (%s): %s", code, message)
        return RiskError(code, message, details)

    # ── Regra 0: sentimento macro (Polymarket) contradiz a direção? ──
    if settings.polymarket_gate_enabled:
        bias = _macro_bias()
        if bias == "bullish" and direction == "put":
            raise veto(
                "MACRO_CONFLICT",
                "Bias macro bullish (Polymarket) contradiz uma ordem PUT.",
                {"macro_bias": bias},
            )
        if bias == "bearish" and direction == "call":
            raise veto(
                "MACRO_CONFLICT",
                "Bias macro bearish (Polymarket) contradiz uma ordem CALL.",
                {"macro_bias": bias},
            )

    # ── Regra 0b: janela de sessão (Londres/NY) — só opera na liquidez ──
    if settings.session_gate_enabled:
        hour = datetime.now(timezone.utc).hour
        if not _in_session(hour):
            raise veto(
                "OUTSIDE_SESSION",
                f"Fora das sessões de Londres/NY (hora atual {hour:02d}:00 UTC). "
                f"Londres {settings.session_london_start:02d}–{settings.session_london_end:02d}h, "
                f"NY {settings.session_ny_start:02d}–{settings.session_ny_end:02d}h UTC.",
                {"hour_utc": hour},
            )

    # ── Regra 0c: blackout de notícia de alto impacto (ForexFactory) ──
    if settings.calendar_gate_enabled:
        ev = forexfactory.active_blackout()
        if ev:
            raise veto(
                "NEWS_BLACKOUT",
                f"Blackout de notícia de alto impacto: '{ev['title']}' "
                f"({ev.get('country') or '?'} {ev['event_time']}). "
                f"Sem operar ±{settings.calendar_blackout_before_min}min do evento.",
                {"event": ev["title"], "event_time": ev["event_time"], "impact": ev.get("impact")},
            )

    # ── Regras 1 & 2: confiança do sinal (só quando há sinal de IA) ──
    if confidence is not None:
        if settings.neutral_low <= confidence <= settings.neutral_high:
            raise veto(
                "NEUTRAL",
                f"Confiança {confidence:.0%} na zona neutra "
                f"({settings.neutral_low:.0%}–{settings.neutral_high:.0%}): ficar fora do mercado.",
                {"confidence": confidence},
            )
        if confidence < settings.min_confidence:
            raise veto(
                "LOW_CONFIDENCE",
                f"Confiança {confidence:.0%} abaixo do mínimo de {settings.min_confidence:.0%}.",
                {"confidence": confidence},
            )

    # ── Regra 3: alocação ≤ 2% da banca (saldo recalculado agora) ──
    balance = client.get_balance()
    limit = round(balance * settings.risk_pct, 2)
    if amount > limit:
        raise veto(
            "ALLOC_EXCEEDED",
            f"Ordem de {amount:.2f} excede o limite de {settings.risk_pct:.0%} da banca "
            f"({limit:.2f} de {balance:.2f}). Reduza o valor.",
            {"balance": balance, "risk_limit": limit},
        )

    # ── Regra 4: circuit breaker de stops seguidos ──
    streak = _consecutive_losses(supabase_sync.recent_results(settings.max_consecutive_losses))
    if streak >= settings.max_consecutive_losses:
        raise veto(
            "CIRCUIT_BREAKER",
            f"{streak} perdas seguidas (limite {settings.max_consecutive_losses}). "
            f"Trading travado até reset manual.",
            {"balance": balance, "consecutive_losses": streak},
        )

    # ── Regra 5: teto de prejuízo diário ──
    pnl_today = supabase_sync.today_realized_pnl()
    daily_cap = round(balance * settings.daily_loss_cap_pct, 2)
    if pnl_today <= -daily_cap:
        raise veto(
            "DAILY_LOSS_CAP",
            f"Prejuízo do dia {pnl_today:.2f} atingiu o teto de {settings.daily_loss_cap_pct:.0%} "
            f"da banca (-{daily_cap:.2f}). Trading travado por hoje.",
            {"balance": balance, "pnl_today": pnl_today, "daily_cap": daily_cap},
        )

    verdict = {
        "balance": balance,
        "risk_limit": limit,
        "confidence": confidence,
        "consecutive_losses": streak,
        "pnl_today": pnl_today,
    }
    supabase_sync.insert_risk_event(
        "approved", "OK", active, direction, confidence, amount, balance, "Aprovado pelo Risk Judge", verdict
    )
    logger.info("Risk Judge APROVOU %s %s %.2f (conf=%s)", active, direction, amount, confidence)
    return verdict


def _macro_bias() -> str:
    """Bias macro agregado dos mercados da Polymarket: maioria entre os não-neutros.

    Sem dados ou empate → 'neutral' (não bloqueia). Falha de leitura também é neutra:
    a indisponibilidade do sentimento nunca pode travar a operação por si só.
    """
    try:
        rows = supabase_sync.get_sentiment()
    except Exception:  # noqa: BLE001
        logger.exception("Falha ao ler sentimento; tratando como neutro")
        return "neutral"
    bulls = sum(1 for r in rows if r.get("bias") == "bullish")
    bears = sum(1 for r in rows if r.get("bias") == "bearish")
    if bulls > bears:
        return "bullish"
    if bears > bulls:
        return "bearish"
    return "neutral"


def _in_session(hour_utc: int) -> bool:
    """True se a hora UTC cai na janela de Londres OU de NY (intervalos [start, end))."""
    in_london = settings.session_london_start <= hour_utc < settings.session_london_end
    in_ny = settings.session_ny_start <= hour_utc < settings.session_ny_end
    return in_london or in_ny


def _consecutive_losses(results: list[str]) -> int:
    """Conta perdas seguidas a partir da mais recente. 'win'/'tie' quebram a sequência."""
    streak = 0
    for status in results:
        if status == "loss":
            streak += 1
        else:
            break
    return streak
