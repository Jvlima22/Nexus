"""
NEXUS — session_filter.py
Valida se o horário atual é adequado para operar no Forex.
Bloqueia: Asian session, fins de semana, horários de baixa liquidez.
Libera: London (08-12h UTC), Overlap London+NY (12-16h UTC), NY (16-21h UTC).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

# ---------------------------------------------------------------------------
# Tipos
# ---------------------------------------------------------------------------

Session = Literal["london", "overlap", "new_york", "asian", "off", "weekend"]


@dataclass
class SessionStatus:
    allowed: bool
    session: Session
    utc_hour: int
    reason: str
    best_pairs: list[str]

    def __str__(self) -> str:
        status = "✅ LIBERADO" if self.allowed else "🚫 BLOQUEADO"
        return (
            f"{status} | Sessão: {self.session.upper()} "
            f"| {self.utc_hour:02d}h UTC | {self.reason}"
        )


# ---------------------------------------------------------------------------
# Janelas de sessão (UTC)
# ---------------------------------------------------------------------------

SESSIONS: dict[Session, dict] = {
    "london": {
        "start": 7,
        "end": 12,
        "allowed": True,
        "best_pairs": ["EURUSD", "GBPUSD", "EURGBP", "USDJPY"],
        "description": "Maior liquidez europeia. Melhor sessão para scalping.",
    },
    "overlap": {
        "start": 12,
        "end": 16,
        "allowed": True,
        "best_pairs": ["EURUSD", "GBPUSD", "USDJPY", "USDCAD"],
        "description": "Sobreposição Londres + Nova York. Volume máximo do dia.",
    },
    "new_york": {
        "start": 16,
        "end": 21,
        "allowed": True,
        "best_pairs": ["EURUSD", "USDJPY", "USDCAD", "XAUUSD"],
        "description": "Sessão americana. Boa liquidez, atenção a dados USD.",
    },
    "asian": {
        "start": 22,  # até 7 (wrap around)
        "end": 7,
        "allowed": False,
        "best_pairs": ["USDJPY", "AUDUSD", "NZDUSD"],
        "description": "Baixa liquidez. Spreads largos. Alto risco de whipsaw.",
    },
    "off": {
        "start": 21,
        "end": 22,
        "allowed": False,
        "best_pairs": [],
        "description": "Janela morta entre NY e Asian. Liquidez mínima.",
    },
}

# Horários de alta volatilidade a evitar (dados econômicos frequentes)
HIGH_IMPACT_WINDOWS: list[tuple[int, int]] = [
    (12, 30),  # NFP, CPI USA (12:30 UTC)
    (13, 30),  # dados secundários USA
    (14, 00),  # dados ISM, PMI
    (8, 30),   # dados UK / BOE
]

# Minutos de buffer antes/após evento de alto impacto
EVENT_BUFFER_MINUTES = 15


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------

def check_session(dt: datetime | None = None) -> SessionStatus:
    """
    Avalia se o momento atual é adequado para operar.

    Args:
        dt: datetime com timezone. Se None, usa UTC agora.

    Returns:
        SessionStatus com allowed, session, reason e best_pairs.
    """
    if dt is None:
        dt = datetime.now(timezone.utc)

    # Fim de semana: sexta 21h UTC → domingo 22h UTC
    weekday = dt.weekday()  # 0=Mon, 4=Fri, 5=Sat, 6=Sun
    utc_hour = dt.hour
    utc_minute = dt.minute

    if weekday == 5:  # Sábado inteiro
        return SessionStatus(
            allowed=False,
            session="weekend",
            utc_hour=utc_hour,
            reason="Mercado fechado — sábado.",
            best_pairs=[],
        )

    if weekday == 6 and utc_hour < 22:  # Domingo até 22h
        return SessionStatus(
            allowed=False,
            session="weekend",
            utc_hour=utc_hour,
            reason="Mercado ilíquido — domingo antes da abertura de Sydney (22h UTC).",
            best_pairs=[],
        )

    if weekday == 4 and utc_hour >= 21:  # Sexta após 21h
        return SessionStatus(
            allowed=False,
            session="weekend",
            utc_hour=utc_hour,
            reason="Mercado fechando — sexta após 21h UTC. Risco de gap na segunda.",
            best_pairs=[],
        )

    # Detectar sessão pelo horário
    session = _detect_session(utc_hour)
    meta = SESSIONS[session]

    if not meta["allowed"]:
        return SessionStatus(
            allowed=False,
            session=session,
            utc_hour=utc_hour,
            reason=meta["description"],
            best_pairs=meta["best_pairs"],
        )

    # Verificar janela de eventos de alto impacto
    for event_hour, event_minute in HIGH_IMPACT_WINDOWS:
        event_total = event_hour * 60 + event_minute
        current_total = utc_hour * 60 + utc_minute
        if abs(current_total - event_total) <= EVENT_BUFFER_MINUTES:
            return SessionStatus(
                allowed=False,
                session=session,
                utc_hour=utc_hour,
                reason=f"Janela de dados econômicos — buffer de {EVENT_BUFFER_MINUTES}min ao redor de {event_hour:02d}:{event_minute:02d} UTC.",
                best_pairs=meta["best_pairs"],
            )

    return SessionStatus(
        allowed=True,
        session=session,
        utc_hour=utc_hour,
        reason=meta["description"],
        best_pairs=meta["best_pairs"],
    )


def _detect_session(utc_hour: int) -> Session:
    if 7 <= utc_hour < 12:
        return "london"
    if 12 <= utc_hour < 16:
        return "overlap"
    if 16 <= utc_hour < 21:
        return "new_york"
    if 21 <= utc_hour < 22:
        return "off"
    return "asian"  # 22-23 e 0-6


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------

def next_allowed_session(dt: datetime | None = None) -> dict:
    """Retorna quando começa a próxima sessão permitida."""
    if dt is None:
        dt = datetime.now(timezone.utc)

    utc_hour = dt.hour
    weekday = dt.weekday()

    # Se for fim de semana, próxima sessão é London de segunda
    if weekday in (5, 6) or (weekday == 4 and utc_hour >= 21):
        days_until_monday = (7 - weekday) % 7 or 7
        return {
            "session": "london",
            "utc_time": f"Segunda-feira às 07:00 UTC (em ~{days_until_monday} dias)",
            "local_brt": f"Segunda-feira às 04:00 BRT",
        }

    # Próxima abertura de London hoje ou amanhã
    if utc_hour < 7:
        return {"session": "london", "utc_time": "Hoje às 07:00 UTC", "local_brt": "Hoje às 04:00 BRT"}
    if utc_hour >= 21:
        return {"session": "london", "utc_time": "Amanhã às 07:00 UTC", "local_brt": "Amanhã às 04:00 BRT"}

    # Já está em sessão permitida
    status = check_session(dt)
    return {"session": status.session, "utc_time": "Agora", "local_brt": "Agora"}


# ---------------------------------------------------------------------------
# CLI rápido para teste
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    status = check_session()
    print(status)
    print(f"Melhores pares: {', '.join(status.best_pairs) or 'N/A'}")
    if not status.allowed:
        next_s = next_allowed_session()
        print(f"Próxima sessão: {next_s['session'].upper()} — {next_s['utc_time']}")
