/**
 * Contrato do snapshot de operação — retrato do mercado no instante da ordem,
 * gravado pelo connector (connector/snapshot.py) em `trade_snapshots.snapshot`.
 * O front redesenha o gráfico e os detalhes a partir disto (auditoria pós-trade).
 */

export interface SnapshotCandle {
  time: number; // epoch (s)
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface CandlePattern {
  name: string; // "martelo" | "engolfo de alta" | "doji" | …
  bias: "bullish" | "bearish" | "neutral";
}

export interface TradeSnapshot {
  asset: string;
  timeframe: string; // M1 | M5 | M15
  captured_at: string; // ISO UTC
  expiration_min: number;
  payout?: number | null;
  entry: {
    time: number | null; // epoch do candle de entrada
    price: number | null;
    direction: "call" | "put";
  };
  candles: SnapshotCandle[];
  indicators: {
    rsi: number | null;
    ema9: number | null;
    ema21: number | null;
    macd: { macd: number; signal: number; hist: number } | null;
    bollinger: { mid: number; upper: number; lower: number } | null;
    votes: Record<string, "bullish" | "bearish" | "neutral">;
  };
  patterns: CandlePattern[];
  support_resistance: {
    support: number | null;
    resistance: number | null;
    pivots: { time: number; price: number; kind: "support" | "resistance" }[];
  };
  signal: {
    direction: "call" | "put" | null;
    confidence: number;
    rationale: string;
    source: string;
  };
  risk: Record<string, number | null> | null;
}

/** Linha da tabela `trade_snapshots`. */
export interface TradeSnapshotRow {
  trade_id: string;
  asset: string | null;
  timeframe: string | null;
  captured_at: string;
  snapshot: TradeSnapshot;
}
