"""
Backtest da estratégia do autotrader — versão MÓDULO (reutilizável in-process).

Promove a lógica do script exploratório `_backtest.py` a uma função por par que o
robô chama periodicamente para MEDIR o edge (taxa de acerto real) de cada ativo.
É a base do "gate de evidência" (Robô OTC v2): o autotrader só opera um par cujo
edge medido supere o breakeven com margem — nunca por esperança.

Binária: vence se, na expiração (1 candle do timeframe primário), o preço fechou
na direção prevista por `indicators.analyze`. Breakeven com payout p = 1/(1+p).

Roda DENTRO do connector → puxa candles via `client.get_candles` (sem HTTP).
"""
from __future__ import annotations

import logging
from typing import Any

import indicators
from config import settings
from iq_client import client

logger = logging.getLogger("nexus.backtest")

_TF_LABEL = {60: "M1", 300: "M5", 900: "M15", 3600: "H1", 14400: "H4", 86400: "D1"}

# Parâmetros do backtest (espelham o robô): janela passada por analyze e nº de
# candles puxados. Defaults conservadores que rendem amostra estatística.
WINDOW = 200          # candles que cada analyze() enxerga (igual ao robô)
N_PRIMARY = 700       # candles do timeframe primário a puxar (→ ~500 sinais)
N_CONFIRM = 240       # candles do timeframe de confirmação


def _tf(size: int) -> str:
    return _TF_LABEL.get(size, f"{size}s")


def _outcome(c_now: dict, c_next: dict) -> str | None:
    """Direção realizada entre dois candles consecutivos. None em empate (descarta)."""
    if c_next["close"] > c_now["close"]:
        return "call"
    if c_next["close"] < c_now["close"]:
        return "put"
    return None


def _confirm_dir_at(confirm: list[dict], j: int, tf_label: str) -> str | None:
    """Direção do sinal de confirmação considerando candles até o índice j (trailing)."""
    lo = max(0, j - WINDOW + 1)
    return indicators.analyze("x", tf_label, confirm[lo:j + 1])["direction"]


def backtest_pair(
    active: str,
    *,
    timeframe: int | None = None,
    confirm_tf: int | None = None,
    payout: float = 0.84,
) -> dict[str, Any] | None:
    """Backtesta um par e devolve as taxas de acerto medidas, ou None se faltam dados.

    Retorna o "edge" do par em dois recortes:
      - hit_rate/sample: todos os sinais M5 (estratégia crua).
      - confluence_hit_rate/confluence_sample: só sinais onde o TF de confirmação
        concordava (= o que o robô REALMENTE opera quando require_confluence=true).
    """
    timeframe = timeframe or settings.autotrader_timeframe
    confirm_tf = confirm_tf or settings.autotrader_confirm_tf
    confirm_label = _tf(confirm_tf)

    try:
        c5 = client.get_candles(active, timeframe, N_PRIMARY)
        c15 = client.get_candles(active, confirm_tf, N_CONFIRM)
    except Exception:  # noqa: BLE001 — um par sem histórico não derruba a varredura
        logger.debug("backtest: sem candles para %s", active, exc_info=True)
        return None
    if len(c5) < WINDOW + 10 or len(c15) < 40:
        return None

    wins = n = c_wins = c_n = 0
    j = 0  # ponteiro no TF de confirmação (candle cujo time <= t)
    for i in range(WINDOW, len(c5) - 1):
        t = c5[i]["time"]
        while j + 1 < len(c15) and c15[j + 1]["time"] <= t:
            j += 1
        sig = indicators.analyze(active, _tf(timeframe), c5[i - WINDOW + 1:i + 1])
        d5 = sig["direction"]
        if d5 is None:
            continue
        realized = _outcome(c5[i], c5[i + 1])
        if realized is None:
            continue
        won = realized == d5
        n += 1
        wins += won
        if _confirm_dir_at(c15, j, confirm_label) == d5:
            c_n += 1
            c_wins += won

    if n == 0:
        return None
    return {
        "symbol": active,
        "hit_rate": round(wins / n, 4),
        "sample": n,
        "confluence_hit_rate": round(c_wins / c_n, 4) if c_n else None,
        "confluence_sample": c_n,
        "breakeven": round(1 / (1 + payout), 4),
        "payout": payout,
    }


def gate_metric(edge: dict[str, Any]) -> tuple[float | None, int]:
    """Extrai (hit_rate, sample) que o gate deve usar, conforme a config do robô.

    Com confluência ligada, mede o recorte com confluência (o que o robô opera de
    fato); senão, o recorte cru. Centraliza a escolha p/ robô e UI concordarem."""
    if settings.autotrader_require_confluence and settings.autotrader_edge_use_confluence:
        return edge.get("confluence_hit_rate"), int(edge.get("confluence_sample") or 0)
    return edge.get("hit_rate"), int(edge.get("sample") or 0)


def passes_gate(edge: dict[str, Any] | None) -> bool:
    """True se o par tem edge comprovado: amostra suficiente E acerto > limite."""
    if not edge:
        return False
    hit, sample = gate_metric(edge)
    if hit is None or sample < settings.autotrader_edge_min_sample:
        return False
    return hit > settings.autotrader_edge_min_hit
