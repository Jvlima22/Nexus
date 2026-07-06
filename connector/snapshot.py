"""
Snapshot de operação — retrato do mercado no instante exato de uma ordem.

Captura, no momento da execução (manual ou autotrader), o que justificava a entrada:
candles, indicadores (RSI/EMA/MACD/Bollinger + votos), padrão de candle identificado
(martelo, engolfo, doji…) e suporte/resistência. Guardado como JSON em `trade_snapshots`
e redesenhado no front ao clicar na operação (auditoria pós-trade).

Reusa indicators.analyze + indicators.detect_patterns + indicators.support_resistance.
Não toca no caminho crítico da ordem — o chamador roda isto em thread de fundo.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import indicators

_TF_LABEL = {60: "M1", 300: "M5", 900: "M15", 3600: "H1", 14400: "H4", 86400: "D1"}
DISPLAY_CANDLES = 60  # quantos candles guardar p/ desenhar o gráfico


def tf_for_expiration(expiration_min: int) -> int:
    """Timeframe (s) do snapshot a partir da expiração da ordem (1m→M1, 5m→M5, 15m→M15)."""
    return {1: 60, 5: 300, 15: 900}.get(expiration_min, 300)


def _label(size: int) -> str:
    return _TF_LABEL.get(size, f"{size}s")


def build(
    active: str,
    size: int,
    candles: list[dict[str, Any]],
    *,
    direction: str,
    confidence: float | None,
    entry_price: float | None,
    expiration_min: int,
    risk_verdict: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Monta o snapshot da operação. `candles` = janela do timeframe (mais recente no fim)."""
    timeframe = _label(size)
    sig = indicators.analyze(active, timeframe, candles)
    feat = sig["features"]
    patterns = indicators.detect_patterns(candles)
    sr = indicators.support_resistance(candles)

    last = candles[-1] if candles else None
    entry = {
        "time": last["time"] if last else None,
        "price": entry_price if entry_price is not None else (last["close"] if last else None),
        "direction": direction,
    }

    closes = [c["close"] for c in candles]
    ema9 = round(indicators.ema(closes, 9)[-1], 6) if len(closes) >= 9 else None
    ema21 = round(indicators.ema(closes, 21)[-1], 6) if len(closes) >= 21 else None

    return {
        "asset": active,
        "timeframe": timeframe,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "expiration_min": expiration_min,
        "entry": entry,
        "candles": [
            {"time": c["time"], "open": c["open"], "high": c["high"], "low": c["low"], "close": c["close"]}
            for c in candles[-DISPLAY_CANDLES:]
        ],
        "indicators": {
            "rsi": feat["rsi"],
            "ema9": ema9,
            "ema21": ema21,
            "macd": feat["macd"],
            "bollinger": feat["bollinger"],
            "votes": feat["votes"],
        },
        "patterns": patterns,
        "support_resistance": sr,
        "signal": {
            "direction": sig["direction"],
            "confidence": sig["confidence"],
            "rationale": sig["rationale"],
            "source": sig["source"],
        },
        "risk": _risk_subset(risk_verdict),
    }


def _risk_subset(verdict: dict[str, Any] | None) -> dict[str, Any] | None:
    """Recorte do veredito do Risk Judge p/ exibir (sem dados sensíveis extras)."""
    if not verdict:
        return None
    keys = ("balance", "risk_limit", "confidence", "consecutive_losses", "pnl_today")
    return {k: verdict.get(k) for k in keys if k in verdict}
