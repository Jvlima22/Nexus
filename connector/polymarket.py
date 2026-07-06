"""
Polymarket (Gamma API pública) — camada de sentimento macro da NEXUS.

A Polymarket é o filtro PRIMÁRIO de direção (Fase 4 do Master Plan): a probabilidade
real de um evento macro vira um **bias direcional** (bullish/bearish/neutral) que o
Risk Judge usa como regra 0. Sem auth/chave — só leitura de mercados públicos.

Mapa de bias (configurável em config.py):
  prob YES > bull_threshold (0.65)  -> bullish (risk-on)
  prob YES < bear_threshold (0.35)  -> bearish (risk-off)
  entre os dois                     -> neutral (ficar fora / não bloqueia)
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

import doh
from config import settings

logger = logging.getLogger("nexus.polymarket")

GAMMA_HOST = "gamma-api.polymarket.com"
GAMMA_URL = f"https://{GAMMA_HOST}/markets"

# Provedores no Brasil forjam NXDOMAIN p/ polymarket.com → resolve via DoH (Cloudflare),
# sem exigir troca de DNS no SO. Escopado só a este host.
doh.enable_for(GAMMA_HOST)


def _parse_json_field(value: Any) -> list:
    """outcomes/outcomePrices vêm como string JSON na Gamma; às vezes já como lista."""
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return []
    return []


def _yes_probability(market: dict[str, Any]) -> float | None:
    """Extrai a probabilidade do desfecho 'Yes' (0–1) de um mercado da Gamma."""
    outcomes = _parse_json_field(market.get("outcomes"))
    prices = _parse_json_field(market.get("outcomePrices"))
    if not prices:
        return None
    # Procura o índice de "Yes"; default no primeiro desfecho.
    idx = 0
    for i, o in enumerate(outcomes):
        if str(o).strip().lower() in ("yes", "sim"):
            idx = i
            break
    try:
        return float(prices[idx])
    except (ValueError, IndexError, TypeError):
        return None


def classify_bias(probability: float) -> str:
    if probability >= settings.polymarket_bull_threshold:
        return "bullish"
    if probability <= settings.polymarket_bear_threshold:
        return "bearish"
    return "neutral"


def fetch_market(slug: str) -> dict[str, Any] | None:
    """Lê um mercado da Gamma por slug e devolve o sentimento normalizado, ou None."""
    if not slug:
        return None
    try:
        resp = httpx.get(GAMMA_URL, params={"slug": slug}, timeout=10.0)
        resp.raise_for_status()
        data = resp.json()
    except Exception:  # noqa: BLE001 — rede instável não pode derrubar o loop
        logger.exception("Falha ao consultar a Gamma API (slug=%s)", slug)
        return None

    markets = data if isinstance(data, list) else data.get("data", [])
    if not markets:
        logger.warning("Nenhum mercado retornado para slug=%s", slug)
        return None

    market = markets[0]
    prob = _yes_probability(market)
    if prob is None:
        logger.warning("Mercado %s sem probabilidade utilizável", slug)
        return None

    volume = market.get("volume") or market.get("volumeNum")
    try:
        volume = float(volume) if volume is not None else None
    except (ValueError, TypeError):
        volume = None

    return {
        "slug": slug,
        "question": market.get("question") or market.get("title") or slug,
        "probability": round(prob, 4),
        "bias": classify_bias(prob),
        "volume": volume,
    }
