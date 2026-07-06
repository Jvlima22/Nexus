"""
ForexFactory (feed JSON faireconomy) — calendário econômico da NEXUS.

Camada 2 do funil: identifica janelas de alta volatilidade (notícias de alto impacto)
para suspender operações minutos antes/depois. O feed semi-oficial é estável e sem auth:
  https://nfs.faireconomy.media/ff_calendar_thisweek.json

Cada item: {title, country, date (ISO 8601 c/ offset), impact: High|Medium|Low, ...}.
"""
from __future__ import annotations

import hashlib
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

import doh
from config import settings

logger = logging.getLogger("nexus.forexfactory")

FF_HOST = "nfs.faireconomy.media"
FF_URL = f"https://{FF_HOST}/ff_calendar_thisweek.json"

# Insurance de DNS (mesmo contorno da Polymarket; inócuo se o host não for bloqueado).
doh.enable_for(FF_HOST)

# Cache em memória dos eventos da semana (o gate consulta isto, sem ir à rede por ordem).
_events: list[dict[str, Any]] = []
_lock = threading.Lock()


def set_cache(events: list[dict[str, Any]]) -> None:
    with _lock:
        global _events
        _events = events


def get_cache() -> list[dict[str, Any]]:
    with _lock:
        return list(_events)


def _event_id(title: str, when_iso: str) -> str:
    return hashlib.sha1(f"{title}|{when_iso}".encode()).hexdigest()[:16]


def fetch_events() -> list[dict[str, Any]]:
    """Lê o calendário da semana e devolve eventos normalizados. [] em caso de falha."""
    try:
        resp = httpx.get(FF_URL, timeout=15.0, headers={"user-agent": "nexus-trader/1.0"})
        resp.raise_for_status()
        raw = resp.json()
    except Exception:  # noqa: BLE001 — rede instável não derruba o loop
        logger.exception("Falha ao consultar o feed do ForexFactory")
        return []

    items = raw if isinstance(raw, list) else raw.get("events", [])
    out: list[dict[str, Any]] = []
    for ev in items:
        when = ev.get("date") or ev.get("timestamp")
        title = ev.get("title") or ev.get("event")
        if not when or not title:
            continue
        when_iso = _to_iso(when)
        if when_iso is None:
            continue
        out.append(
            {
                "event_id": _event_id(title, when_iso),
                "title": title,
                "country": ev.get("country"),
                "impact": (ev.get("impact") or "").strip().capitalize() or "Unknown",
                "event_time": when_iso,
            }
        )
    return out


def _to_iso(value: Any) -> str | None:
    """Normaliza date (ISO string ou epoch) para ISO 8601 UTC-aware."""
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
        # ff usa "2026-06-02T14:30:00-04:00" (já com offset)
        dt = datetime.fromisoformat(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except (ValueError, TypeError):
        return None


def active_blackout(now: datetime | None = None) -> dict[str, Any] | None:
    """Evento de alto impacto cuja janela de blackout cobre `now` (UTC). None se livre.

    Janela = [event_time - before, event_time + after], só p/ impactos configurados.
    """
    now = now or datetime.now(timezone.utc)
    impacts = settings.calendar_impacts_list
    before = timedelta(minutes=settings.calendar_blackout_before_min)
    after = timedelta(minutes=settings.calendar_blackout_after_min)
    for ev in get_cache():
        if ev.get("impact") not in impacts:
            continue
        try:
            when = datetime.fromisoformat(ev["event_time"])
        except (ValueError, TypeError, KeyError):
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        if when - before <= now <= when + after:
            return ev
    return None
