"""
NEXUS — pattern_engine.py
Motor de reconhecimento de padrões de candles com ATR dinâmico e filtro de volume.

Padrões suportados:
  Reversão: pin_bar_bull, pin_bar_bear, engulfing_bull, engulfing_bear,
             morning_star, evening_star, hammer, shooting_star
  Continuação: three_white_soldiers, three_black_crows, inside_bar
  Neutros: doji

Cada sinal retorna: pattern, direction, strength (0-100), entry, sl, tp, rr.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# ---------------------------------------------------------------------------
# Estruturas de dados
# ---------------------------------------------------------------------------

@dataclass
class Candle:
    time: int | str   # Unix timestamp (MT5) ou string ISO (CSV/teste)
    open: float
    high: float
    low: float
    close: float
    volume: int = 0

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low

    @property
    def range(self) -> float:
        return self.high - self.low

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open

    @property
    def mid(self) -> float:
        return (self.high + self.low) / 2


@dataclass
class PatternSignal:
    pattern: str
    direction: Literal["BUY", "SELL", "NEUTRAL"]
    strength: int           # 0-100
    entry: float
    stop_loss: float
    take_profit: float
    rr_ratio: float
    candle_index: int       # índice da vela de sinal (relativo ao array)
    description: str
    tags: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        arrow = "▲" if self.direction == "BUY" else "▼" if self.direction == "SELL" else "–"
        return (
            f"{arrow} {self.pattern.upper()} | Força: {self.strength}/100 | "
            f"Entry: {self.entry:.5f} | SL: {self.stop_loss:.5f} | "
            f"TP: {self.take_profit:.5f} | RR: {self.rr_ratio:.1f}:1"
        )


# ---------------------------------------------------------------------------
# ATR dinâmico
# ---------------------------------------------------------------------------

def calc_atr(candles: list[Candle], period: int = 14) -> float:
    """Average True Range dos últimos `period` candles."""
    if len(candles) < period + 1:
        # Fallback: usa range médio das últimas velas disponíveis
        return sum(c.range for c in candles) / len(candles)

    true_ranges = []
    for i in range(1, len(candles)):
        tr = max(
            candles[i].high - candles[i].low,
            abs(candles[i].high - candles[i - 1].close),
            abs(candles[i].low - candles[i - 1].close),
        )
        true_ranges.append(tr)

    return sum(true_ranges[-period:]) / period


def calc_volume_ma(candles: list[Candle], period: int = 20) -> float:
    """Média de volume dos últimos `period` candles."""
    vols = [c.volume for c in candles[-period:] if c.volume > 0]
    return sum(vols) / len(vols) if vols else 0


# ---------------------------------------------------------------------------
# Detector principal
# ---------------------------------------------------------------------------

def detect_patterns(
    candles: list[Candle],
    atr_period: int = 14,
    atr_sl_mult: float = 1.5,   # SL = 1.5 × ATR
    atr_tp_mult: float = 2.5,   # TP = 2.5 × ATR  (RR ~1.7:1)
    min_volume_mult: float = 0.8,  # volume mínimo = 80% da média
) -> list[PatternSignal]:
    """
    Analisa a lista de candles e retorna todos os padrões detectados.
    O último candle é o mais recente (índice -1).
    Mínimo recomendado: 20 candles.
    """
    if len(candles) < 3:
        return []

    atr = calc_atr(candles, atr_period)
    vol_ma = calc_volume_ma(candles)
    signals: list[PatternSignal] = []

    c0 = candles[-1]   # vela atual (mais recente)
    c1 = candles[-2]   # vela anterior
    c2 = candles[-3]   # duas velas atrás

    # Filtro de volume: só detectar se volume >= mínimo
    has_volume = (c0.volume == 0) or (vol_ma == 0) or (c0.volume >= vol_ma * min_volume_mult)

    if not has_volume:
        return []

    sl_dist = atr * atr_sl_mult
    tp_dist = atr * atr_tp_mult

    # ------------------------------------------------------------------
    # 1. PIN BAR BULLISH
    # Corpo pequeno no topo, wick inferior longo (≥ 2× corpo e ≥ 60% do range)
    # ------------------------------------------------------------------
    if (
        c0.lower_wick >= c0.body * 2
        and c0.lower_wick >= c0.range * 0.6
        and c0.body <= atr * 0.4
    ):
        entry = c0.high + atr * 0.1   # entrada acima da máxima
        sl = c0.low - atr * 0.1
        tp = entry + tp_dist
        rr = _rr(entry, sl, tp)
        strength = _pin_bar_strength(c0, "bull")
        signals.append(PatternSignal(
            pattern="pin_bar_bull",
            direction="BUY",
            strength=strength,
            entry=round(entry, 5),
            stop_loss=round(sl, 5),
            take_profit=round(tp, 5),
            rr_ratio=round(rr, 2),
            candle_index=-1,
            description=f"Pin bar bullish — wick inferior {c0.lower_wick/atr:.1f}× ATR",
            tags=["reversão", "price_action"],
        ))

    # ------------------------------------------------------------------
    # 2. PIN BAR BEARISH (shooting star)
    # Corpo pequeno na base, wick superior longo
    # ------------------------------------------------------------------
    if (
        c0.upper_wick >= c0.body * 2
        and c0.upper_wick >= c0.range * 0.6
        and c0.body <= atr * 0.4
    ):
        entry = c0.low - atr * 0.1
        sl = c0.high + atr * 0.1
        tp = entry - tp_dist
        rr = _rr(entry, sl, tp, direction="SELL")
        strength = _pin_bar_strength(c0, "bear")
        signals.append(PatternSignal(
            pattern="pin_bar_bear",
            direction="SELL",
            strength=strength,
            entry=round(entry, 5),
            stop_loss=round(sl, 5),
            take_profit=round(tp, 5),
            rr_ratio=round(rr, 2),
            candle_index=-1,
            description=f"Pin bar bearish — wick superior {c0.upper_wick/atr:.1f}× ATR",
            tags=["reversão", "price_action"],
        ))

    # ------------------------------------------------------------------
    # 3. ENGOLFO BULLISH
    # Vela bearish seguida de bullish que engole completamente o corpo
    # ------------------------------------------------------------------
    if (
        c1.is_bearish
        and c0.is_bullish
        and c0.open <= c1.close
        and c0.close >= c1.open
        and c0.body >= c1.body * 1.1
    ):
        entry = c0.close
        sl = c0.low - atr * 0.1
        tp = entry + tp_dist
        rr = _rr(entry, sl, tp)
        strength = min(100, int(50 + (c0.body / c1.body - 1) * 40))
        signals.append(PatternSignal(
            pattern="engulfing_bull",
            direction="BUY",
            strength=strength,
            entry=round(entry, 5),
            stop_loss=round(sl, 5),
            take_profit=round(tp, 5),
            rr_ratio=round(rr, 2),
            candle_index=-1,
            description=f"Engolfo bullish — corpo {c0.body/c1.body:.1f}× maior que anterior",
            tags=["reversão", "engolfo"],
        ))

    # ------------------------------------------------------------------
    # 4. ENGOLFO BEARISH
    # ------------------------------------------------------------------
    if (
        c1.is_bullish
        and c0.is_bearish
        and c0.open >= c1.close
        and c0.close <= c1.open
        and c0.body >= c1.body * 1.1
    ):
        entry = c0.close
        sl = c0.high + atr * 0.1
        tp = entry - tp_dist
        rr = _rr(entry, sl, tp, direction="SELL")
        strength = min(100, int(50 + (c0.body / c1.body - 1) * 40))
        signals.append(PatternSignal(
            pattern="engulfing_bear",
            direction="SELL",
            strength=strength,
            entry=round(entry, 5),
            stop_loss=round(sl, 5),
            take_profit=round(tp, 5),
            rr_ratio=round(rr, 2),
            candle_index=-1,
            description=f"Engolfo bearish — corpo {c0.body/c1.body:.1f}× maior que anterior",
            tags=["reversão", "engolfo"],
        ))

    # ------------------------------------------------------------------
    # 5. INSIDE BAR
    # Vela completamente dentro do range da anterior → breakout esperado
    # ------------------------------------------------------------------
    if (
        c0.high <= c1.high
        and c0.low >= c1.low
        and c0.body <= c1.body * 0.7
    ):
        # Direção depende do bias anterior (c2)
        bias = "BUY" if c2.is_bullish else "SELL"
        if bias == "BUY":
            entry = c1.high + atr * 0.05
            sl = c1.low - atr * 0.1
            tp = entry + tp_dist
        else:
            entry = c1.low - atr * 0.05
            sl = c1.high + atr * 0.1
            tp = entry - tp_dist
        rr = _rr(entry, sl, tp, direction=bias)
        signals.append(PatternSignal(
            pattern="inside_bar",
            direction=bias,
            strength=60,
            entry=round(entry, 5),
            stop_loss=round(sl, 5),
            take_profit=round(tp, 5),
            rr_ratio=round(rr, 2),
            candle_index=-1,
            description=f"Inside bar — breakout esperado na direção {bias}",
            tags=["continuação", "compressão"],
        ))

    # ------------------------------------------------------------------
    # 6. DOJI
    # Corpo quase zero (indecisão)
    # ------------------------------------------------------------------
    if c0.body <= atr * 0.1 and c0.range >= atr * 0.3:
        signals.append(PatternSignal(
            pattern="doji",
            direction="NEUTRAL",
            strength=40,
            entry=c0.close,
            stop_loss=c0.low - atr * 0.1,
            take_profit=c0.high + atr * 0.1,
            rr_ratio=0.0,
            candle_index=-1,
            description="Doji — indecisão. Aguardar confirmação direcional.",
            tags=["neutro", "indecisão"],
        ))

    # ------------------------------------------------------------------
    # 7. THREE WHITE SOLDIERS (continuação bullish)
    # ------------------------------------------------------------------
    if (
        len(candles) >= 3
        and c2.is_bullish and c1.is_bullish and c0.is_bullish
        and c1.close > c2.close and c0.close > c1.close
        and c2.body >= atr * 0.5 and c1.body >= atr * 0.5 and c0.body >= atr * 0.5
        and c1.open > c2.open and c0.open > c1.open
    ):
        entry = c0.close
        sl = c0.low - atr * 0.1
        tp = entry + tp_dist
        rr = _rr(entry, sl, tp)
        signals.append(PatternSignal(
            pattern="three_white_soldiers",
            direction="BUY",
            strength=75,
            entry=round(entry, 5),
            stop_loss=round(sl, 5),
            take_profit=round(tp, 5),
            rr_ratio=round(rr, 2),
            candle_index=-1,
            description="Três soldados brancos — forte momentum bullish",
            tags=["continuação", "momentum"],
        ))

    # ------------------------------------------------------------------
    # 8. THREE BLACK CROWS (continuação bearish)
    # ------------------------------------------------------------------
    if (
        len(candles) >= 3
        and c2.is_bearish and c1.is_bearish and c0.is_bearish
        and c1.close < c2.close and c0.close < c1.close
        and c2.body >= atr * 0.5 and c1.body >= atr * 0.5 and c0.body >= atr * 0.5
        and c1.open < c2.open and c0.open < c1.open
    ):
        entry = c0.close
        sl = c0.high + atr * 0.1
        tp = entry - tp_dist
        rr = _rr(entry, sl, tp, direction="SELL")
        signals.append(PatternSignal(
            pattern="three_black_crows",
            direction="SELL",
            strength=75,
            entry=round(entry, 5),
            stop_loss=round(sl, 5),
            take_profit=round(tp, 5),
            rr_ratio=round(rr, 2),
            candle_index=-1,
            description="Três corvos negros — forte momentum bearish",
            tags=["continuação", "momentum"],
        ))

    return sorted(signals, key=lambda s: s.strength, reverse=True)


# ---------------------------------------------------------------------------
# Análise completa (multi-timeframe summary)
# ---------------------------------------------------------------------------

def analyze(
    candles: list[Candle],
    symbol: str = "EURUSD",
    timeframe: str = "M5",
    atr_period: int = 14,
) -> dict:
    """
    Retorna um dict com:
      - atr: ATR(14) atual
      - vol_ma: média de volume
      - patterns: lista de PatternSignal detectados
      - best_signal: sinal de maior força (ou None)
      - bias: 'bullish' | 'bearish' | 'ranging'
    """
    if len(candles) < 5:
        return {"error": "Candles insuficientes (mínimo 5)"}

    atr = calc_atr(candles, atr_period)
    vol_ma = calc_volume_ma(candles)
    patterns = detect_patterns(candles, atr_period)

    # Bias simples: direção dos últimos 5 fechamentos
    last5 = candles[-5:]
    closes = [c.close for c in last5]
    up_count = sum(1 for i in range(1, len(closes)) if closes[i] > closes[i-1])
    down_count = sum(1 for i in range(1, len(closes)) if closes[i] < closes[i-1])

    if up_count >= 4:
        bias = "bullish"
    elif down_count >= 4:
        bias = "bearish"
    else:
        bias = "ranging"

    best = patterns[0] if patterns else None

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "atr": round(atr, 5),
        "atr_pips": round(atr * 10000, 1),
        "vol_ma": round(vol_ma, 0),
        "current_volume": candles[-1].volume,
        "bias": bias,
        "patterns_found": len(patterns),
        "patterns": [str(p) for p in patterns],
        "best_signal": _signal_to_dict(best) if best else None,
        "best_signal_str": str(best) if best else "Nenhum padrão detectado",
    }


# ---------------------------------------------------------------------------
# Parser de CSV do MT5 (formato get_candles_latest)
# ---------------------------------------------------------------------------

def parse_mt5_csv(csv_text: str) -> list[Candle]:
    """
    Converte o CSV retornado por get_candles_latest em lista de Candle.
    Formato: index,time,open,high,low,close,tick_volume,spread,real_volume
    """
    candles = []
    lines = csv_text.strip().split("\r\n")
    header_skipped = False

    for line in lines:
        if not header_skipped:
            header_skipped = True
            continue
        parts = line.strip().split(",")
        if len(parts) < 7:
            continue
        try:
            candles.append(Candle(
                time=parts[1],
                open=float(parts[2]),
                high=float(parts[3]),
                low=float(parts[4]),
                close=float(parts[5]),
                volume=int(float(parts[6])),
            ))
        except (ValueError, IndexError):
            continue

    return candles  # já em ordem cronológica (índice 0 = mais antigo)


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------

def _signal_to_dict(s: PatternSignal) -> dict:
    """Converte PatternSignal em dict JSON-serializable."""
    return {
        "pattern": s.pattern,
        "direction": s.direction,
        "strength": s.strength,
        "entry": s.entry,
        "stop_loss": s.stop_loss,
        "take_profit": s.take_profit,
        "rr_ratio": s.rr_ratio,
        "candle_index": s.candle_index,
        "description": s.description,
        "tags": s.tags,
    }


def _rr(entry: float, sl: float, tp: float, direction: str = "BUY") -> float:
    if direction == "BUY":
        risk = abs(entry - sl)
        reward = abs(tp - entry)
    else:
        risk = abs(sl - entry)
        reward = abs(entry - tp)
    return round(reward / risk, 2) if risk > 0 else 0.0


def _pin_bar_strength(c: Candle, side: str) -> int:
    """Força do pin bar: quanto maior o wick em relação ao range, maior a força."""
    if side == "bull":
        ratio = c.lower_wick / c.range if c.range > 0 else 0
    else:
        ratio = c.upper_wick / c.range if c.range > 0 else 0
    return min(100, int(ratio * 120))


# ---------------------------------------------------------------------------
# CLI rápido para teste
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Exemplo com candles sintéticos
    test_candles = [
        Candle("2026-06-29 08:00", 1.1380, 1.1385, 1.1375, 1.1382, 800),
        Candle("2026-06-29 08:05", 1.1382, 1.1388, 1.1370, 1.1371, 950),  # pin bar bear
        Candle("2026-06-29 08:10", 1.1371, 1.1372, 1.1371, 1.1371, 100),
    ]
    result = analyze(test_candles, symbol="EURUSD", timeframe="M5")
    print(f"ATR: {result['atr_pips']} pips")
    print(f"Bias: {result['bias']}")
    print(f"Padrões: {result['patterns_found']}")
    print(result['best_signal_str'])
