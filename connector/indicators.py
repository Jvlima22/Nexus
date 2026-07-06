"""
Análise técnica determinística da NEXUS (Fase 2, fonte de sinal "rules").

Calcula indicadores sobre os candles do connector (RSI, EMA cross, MACD, Bollinger)
e heurísticas de estrutura (tendência por HH/HL, BoS simples). Cada indicador vota
bullish/bearish/neutral; o sinal final é o consenso da maioria, com `confidence`
proporcional ao quão unânime foi o voto.

Puro Python (sem numpy/pandas) — entrada é a lista de candles normalizados
{time, open, high, low, close, volume}. Saída segue o "contrato do sinal".
"""
from __future__ import annotations

from typing import Any, Literal

Vote = Literal["bullish", "bearish", "neutral"]


# ── Primitivas ────────────────────────────────────────────────────────────────
def ema(values: list[float], period: int) -> list[float]:
    """EMA; lista do mesmo tamanho (primeiros pontos = SMA acumulada de seed)."""
    if not values:
        return []
    k = 2 / (period + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def rsi(closes: list[float], period: int = 14) -> float | None:
    """RSI clássico (médias simples de ganhos/perdas). None se faltam dados."""
    if len(closes) < period + 1:
        return None
    gains, losses = 0.0, 0.0
    for i in range(-period, 0):
        diff = closes[i] - closes[i - 1]
        if diff >= 0:
            gains += diff
        else:
            losses -= diff
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9) -> dict[str, float] | None:
    """Linha MACD, linha de sinal e histograma. None se faltam dados."""
    if len(closes) < slow + signal:
        return None
    macd_line = [f - s for f, s in zip(ema(closes, fast), ema(closes, slow))]
    signal_line = ema(macd_line, signal)
    return {
        "macd": macd_line[-1],
        "signal": signal_line[-1],
        "hist": macd_line[-1] - signal_line[-1],
    }


def bollinger(closes: list[float], period: int = 20, mult: float = 2.0) -> dict[str, float] | None:
    if len(closes) < period:
        return None
    mid = sum(closes[-period:]) / period
    var = sum((c - mid) ** 2 for c in closes[-period:]) / period
    sd = var ** 0.5
    return {"mid": mid, "upper": mid + mult * sd, "lower": mid - mult * sd}


def atr(candles: list[dict[str, Any]], period: int = 14) -> float | None:
    """Average True Range (média simples das últimas `period` TRs). None se faltam dados.
    TR = max(high-low, |high-close_ant|, |low-close_ant|)."""
    if len(candles) < period + 1:
        return None
    trs: list[float] = []
    for i in range(1, len(candles)):
        h, low, pc = candles[i]["high"], candles[i]["low"], candles[i - 1]["close"]
        trs.append(max(h - low, abs(h - pc), abs(low - pc)))
    return sum(trs[-period:]) / period


def trend_structure(candles: list[dict[str, Any]], lookback: int = 20) -> Vote:
    """Tendência por topos/fundos: HH+HL = alta, LH+LL = baixa, senão lateral."""
    if len(candles) < lookback:
        return "neutral"
    window = candles[-lookback:]
    half = lookback // 2
    prev_hi = max(c["high"] for c in window[:half])
    prev_lo = min(c["low"] for c in window[:half])
    cur_hi = max(c["high"] for c in window[half:])
    cur_lo = min(c["low"] for c in window[half:])
    if cur_hi > prev_hi and cur_lo > prev_lo:
        return "bullish"
    if cur_hi < prev_hi and cur_lo < prev_lo:
        return "bearish"
    return "neutral"


# ── Votos por indicador ───────────────────────────────────────────────────────
def _vote_rsi(value: float | None) -> Vote:
    if value is None:
        return "neutral"
    if value < 30:
        return "bullish"   # sobrevenda → reversão de alta
    if value > 70:
        return "bearish"   # sobrecompra → reversão de baixa
    return "neutral"


def _vote_ema(closes: list[float], fast: int = 9, slow: int = 21) -> Vote:
    if len(closes) < slow:
        return "neutral"
    ef, es = ema(closes, fast)[-1], ema(closes, slow)[-1]
    if ef > es:
        return "bullish"
    if ef < es:
        return "bearish"
    return "neutral"


def _vote_macd(m: dict[str, float] | None) -> Vote:
    if m is None:
        return "neutral"
    if m["hist"] > 0:
        return "bullish"
    if m["hist"] < 0:
        return "bearish"
    return "neutral"


def _vote_bollinger(closes: list[float], b: dict[str, float] | None) -> Vote:
    if b is None or not closes:
        return "neutral"
    price = closes[-1]
    if price <= b["lower"]:
        return "bullish"   # tocou banda inferior → reversão
    if price >= b["upper"]:
        return "bearish"
    return "neutral"


# ── Agregação → sinal ─────────────────────────────────────────────────────────
def analyze(active: str, timeframe: str, candles: list[dict[str, Any]]) -> dict[str, Any]:
    """Roda os indicadores e devolve um sinal no contrato da NEXUS.

    direction: call (bullish) | put (bearish) | None (sem consenso/neutral).
    confidence: |bull - bear| / total_de_votos_direcionais_possiveis.
    """
    closes = [c["close"] for c in candles]
    rsi_v = rsi(closes)
    macd_v = macd(closes)
    boll_v = bollinger(closes)
    regime = detect_regime(candles)

    votes: dict[str, Vote] = {
        "rsi": _vote_rsi(rsi_v),
        "ema_cross": _vote_ema(closes),
        "macd": _vote_macd(macd_v),
        "bollinger": _vote_bollinger(closes, boll_v),
        "trend": trend_structure(candles),
    }

    bulls = sum(1 for v in votes.values() if v == "bullish")
    bears = sum(1 for v in votes.values() if v == "bearish")
    total = len(votes)

    if bulls > bears:
        direction: str | None = "call"
        bias: Vote = "bullish"
    elif bears > bulls:
        direction = "put"
        bias = "bearish"
    else:
        direction = None
        bias = "neutral"

    confidence = round(abs(bulls - bears) / total, 4) if total else 0.0

    rationale = (
        f"{bulls} bull / {bears} bear de {total} indicadores. "
        + ", ".join(f"{k}={v}" for k, v in votes.items())
    )

    return {
        "active": active,
        "timeframe": timeframe,
        "direction": direction,
        "bias": bias,
        "confidence": confidence,
        "rationale": rationale,
        "source": "rules",
        "regime": regime,
        "features": {
            "rsi": round(rsi_v, 2) if rsi_v is not None else None,
            "macd": {k: round(x, 6) for k, x in macd_v.items()} if macd_v else None,
            "bollinger": {k: round(x, 6) for k, x in boll_v.items()} if boll_v else None,
            "votes": votes,
        },
        "candles_used": len(candles),
    }


# ── Padrões de candle (martelo, engolfo, doji…) ───────────────────────────────
def _anatomy(c: dict[str, Any]) -> dict[str, float]:
    """Corpo, amplitude e sombras de um candle. Amplitude 0 → tudo 0 (candle plano)."""
    rng = c["high"] - c["low"]
    body = abs(c["close"] - c["open"])
    return {
        "range": rng,
        "body": body,
        "upper": c["high"] - max(c["open"], c["close"]),
        "lower": min(c["open"], c["close"]) - c["low"],
        "bullish": c["close"] > c["open"],
    }


def detect_patterns(candles: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Padrões clássicos no ÚLTIMO candle (engolfo olha o penúltimo). Lista de
    {name, bias}. Nomes em PT-BR p/ exibir direto na UI. Vazio = sem padrão claro."""
    if len(candles) < 2:
        return []
    c = candles[-1]
    p = candles[-2]
    a = _anatomy(c)
    out: list[dict[str, str]] = []
    if a["range"] <= 0:
        return out

    # Doji: corpo desprezível ante a amplitude → indecisão.
    if a["body"] <= 0.1 * a["range"]:
        out.append({"name": "doji", "bias": "neutral"})

    # Marubozu: corpo domina a amplitude (sombras mínimas) → continuação forte.
    if a["body"] >= 0.9 * a["range"]:
        out.append({"name": "marubozu de alta" if a["bullish"] else "marubozu de baixa",
                    "bias": "bullish" if a["bullish"] else "bearish"})

    # Martelo: sombra inferior longa (≥2× corpo), sombra superior curta → reversão de alta.
    if a["body"] > 0 and a["lower"] >= 2 * a["body"] and a["upper"] <= a["body"]:
        out.append({"name": "martelo", "bias": "bullish"})

    # Sombra superior longa: estrela cadente (em alta) ou martelo invertido (em baixa).
    if a["body"] > 0 and a["upper"] >= 2 * a["body"] and a["lower"] <= a["body"]:
        if trend_structure(candles) == "bullish":
            out.append({"name": "estrela cadente", "bias": "bearish"})
        else:
            out.append({"name": "martelo invertido", "bias": "bullish"})

    # Engolfo: corpo atual cobre o corpo anterior de cor oposta.
    pa = _anatomy(p)
    if a["bullish"] and not pa["bullish"] and c["close"] >= p["open"] and c["open"] <= p["close"]:
        out.append({"name": "engolfo de alta", "bias": "bullish"})
    if not a["bullish"] and pa["bullish"] and c["close"] <= p["open"] and c["open"] >= p["close"]:
        out.append({"name": "engolfo de baixa", "bias": "bearish"})

    return out


# ── Suporte / Resistência por pivôs de swing ──────────────────────────────────
def support_resistance(candles: list[dict[str, Any]], lookback: int = 50, k: int = 2) -> dict[str, Any]:
    """Suporte/resistência por pivôs: um swing-high é um candle cujo high é o maior
    dos ±k vizinhos (idem swing-low). Resistência = swing-high mais próximo ACIMA do
    preço; suporte = swing-low mais próximo ABAIXO. Fallback p/ max/min recentes."""
    window = candles[-lookback:] if len(candles) > lookback else candles
    if len(window) < 2 * k + 1:
        if not window:
            return {"support": None, "resistance": None, "pivots": []}
        hi = max(c["high"] for c in window)
        lo = min(c["low"] for c in window)
        return {"support": lo, "resistance": hi, "pivots": []}

    pivots: list[dict[str, Any]] = []
    highs: list[float] = []
    lows: list[float] = []
    for i in range(k, len(window) - k):
        seg = window[i - k:i + k + 1]
        c = window[i]
        if c["high"] == max(s["high"] for s in seg):
            highs.append(c["high"])
            pivots.append({"time": c["time"], "price": c["high"], "kind": "resistance"})
        if c["low"] == min(s["low"] for s in seg):
            lows.append(c["low"])
            pivots.append({"time": c["time"], "price": c["low"], "kind": "support"})

    price = window[-1]["close"]
    above = [h for h in highs if h > price]
    below = [low for low in lows if low < price]
    resistance = min(above) if above else (max(highs) if highs else max(c["high"] for c in window))
    support = max(below) if below else (min(lows) if lows else min(c["low"] for c in window))
    return {"support": support, "resistance": resistance, "pivots": pivots[-12:]}


# ── Detecção de regime de mercado (prompt #4 do playbook quant) ────────────────
def detect_regime(candles: list[dict[str, Any]], lookback: int = 50) -> dict[str, Any]:
    """Classifica o REGIME atual: tendência, volatilidade e volume — e recomenda o
    tipo de estratégia que funciona nesse ambiente (e o que evitar).

    `suitable_for_trend` resume tudo num booleano: o autotrader é seguidor de
    tendência por confluência, então só deve operar quando este é True. Chop
    lateral de baixa volatilidade é onde ele sangra → False.
    """
    undef = {
        "trend": "indefinido", "volatility": "indefinido", "volume": "indefinido",
        "atr_pct": None, "suitable_for_trend": False,
        "recommend": "Dados insuficientes para classificar o regime.",
        "avoid": "Operar sem leitura de regime.",
    }
    if len(candles) < 30:
        return undef

    win = candles[-lookback:] if len(candles) > lookback else candles
    closes = [c["close"] for c in candles]
    price = closes[-1]
    if not price:
        return undef

    # ── Tendência: estrutura HH/HL + sinal da separação EMA9/EMA21 ──
    struct = trend_structure(candles, min(lookback, len(candles)))
    ef, es = ema(closes, 9)[-1], ema(closes, 21)[-1]
    sep = (ef - es) / price
    if struct == "bullish" and sep > 0:
        trend = "alta"
    elif struct == "bearish" and sep < 0:
        trend = "baixa"
    else:
        trend = "lateral"

    # ── Volatilidade: TR% recente (últimas 5) vs mediana do lookback ──
    trs_pct: list[float] = []
    for i in range(1, len(win)):
        h, low, pc = win[i]["high"], win[i]["low"], win[i - 1]["close"]
        c = win[i]["close"]
        if c:
            trs_pct.append(max(h - low, abs(h - pc), abs(low - pc)) / c)
    if trs_pct:
        base = sorted(trs_pct)[len(trs_pct) // 2]  # mediana
        recent = sum(trs_pct[-5:]) / min(5, len(trs_pct))
        ratio = recent / base if base else 1.0
        volatility = "alta" if ratio > 1.3 else "baixa" if ratio < 0.7 else "normal"
    else:
        volatility = "indefinido"

    cur_atr = atr(candles, 14)
    atr_pct = round(cur_atr / price * 100, 4) if cur_atr else None

    # ── Volume: média recente vs média do lookback (0 = corretora não envia) ──
    vols = [float(c.get("volume") or 0) for c in win]
    if sum(vols) <= 0:
        volume = "indisponível"
    else:
        recent_v = sum(vols[-5:]) / min(5, len(vols))
        base_v = sum(vols) / len(vols)
        volume = "alto" if recent_v > 1.3 * base_v else "baixo" if recent_v < 0.7 * base_v else "normal"

    # ── Recomendação por combinação tendência × volatilidade ──
    suitable = trend in ("alta", "baixa") and volatility in ("normal", "alta")
    if trend == "lateral" and volatility == "baixa":
        recommend = "Chop: sem direção e sem amplitude — melhor ficar fora."
        avoid = "Estratégias de tendência (EMA/MACD): geram sinais falsos no range."
    elif trend == "lateral":
        recommend = "Range volátil: reversão nas bandas (Bollinger) opera melhor que tendência."
        avoid = "Romper o range no susto — espere confirmação do rompimento."
    elif suitable:
        recommend = f"Tendência de {trend} com volatilidade {volatility}: ambiente de continuação (EMA/MACD a favor)."
        avoid = "Contra-tendência (pegar topo/fundo) — surfe a favor."
    else:
        recommend = f"Tendência de {trend} mas volatilidade {volatility}: movimento fraco, confluência pede cautela."
        avoid = "Stake cheio — reduza a exposição até a volatilidade voltar."

    return {
        "trend": trend,
        "volatility": volatility,
        "volume": volume,
        "atr_pct": atr_pct,
        "suitable_for_trend": suitable,
        "recommend": recommend,
        "avoid": avoid,
    }
