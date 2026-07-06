/**
 * Cliente do NEXUS Connector (serviço Python que faz a ponte com a IQ Option).
 * Candles ao vivo vêm DIRETO daqui (arquitetura Híbrida) — não passam pelo Supabase.
 */

const HTTP_URL = (import.meta.env.VITE_CONNECTOR_URL as string | undefined) ?? "http://localhost:8000";
const WS_URL =
  (import.meta.env.VITE_CONNECTOR_WS_URL as string | undefined) ??
  HTTP_URL.replace(/^http/, "ws");

export interface Candle {
  time: number; // epoch (segundos) — formato do lightweight-charts
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Asset {
  symbol: string;
  type: string;
  is_open: boolean;
  payout: number | null;
}

async function detailError(res: Response, fallback: string): Promise<Error> {
  // FastAPI usa `detail`; o Risk Judge devolve um objeto {code, message, ...} nos vetos.
  const body = (await res.json().catch(() => ({}))) as {
    detail?: string | { code?: string; message?: string };
  };
  const d = body.detail;
  if (typeof d === "string") return new Error(d);
  if (d && typeof d === "object") {
    const err = new Error(d.message ?? fallback) as Error & { code?: string };
    if (d.code) err.code = d.code;
    return err;
  }
  return new Error(fallback);
}

/** fetch que converte falha de rede (Connector parado) numa mensagem clara. */
async function connectorFetch(path: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(`${HTTP_URL}${path}`, init);
  } catch {
    throw new Error("Connector offline — inicie o serviço (python main.py em localhost:8000)");
  }
}

export async function fetchCandles(active: string, size: number, count = 200): Promise<Candle[]> {
  const res = await connectorFetch(`/candles?active=${encodeURIComponent(active)}&size=${size}&count=${count}`);
  if (!res.ok) throw await detailError(res, `Connector /candles ${res.status}`);
  const json = (await res.json()) as { candles: Candle[] };
  return json.candles;
}

export async function fetchAssets(): Promise<Asset[]> {
  const res = await connectorFetch(`/assets`);
  if (!res.ok) throw new Error(`Connector /assets ${res.status}`);
  const json = (await res.json()) as { assets: Asset[] };
  return json.assets;
}

export interface OrderInput {
  active: string;
  direction: "call" | "put";
  amount: number;
  expiration: number; // minutos
  option_type?: "binary" | "digital";
  confidence?: number; // 0–1, do sinal; sujeito às regras 1–2 do Risk Judge
}

export interface OrderResult {
  ok: boolean;
  order_id: number | string;
  trade_id: string;
  balance: number;
  risk_limit: number;
  payout: number | null;
}

export async function placeOrder(o: OrderInput): Promise<OrderResult> {
  const res = await connectorFetch(`/order`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(o),
  });
  if (!res.ok) throw await detailError(res, `Connector /order ${res.status}`);
  return (await res.json()) as OrderResult;
}

export type MacroBias = "bullish" | "bearish" | "neutral";

export interface SentimentMarket {
  slug: string;
  question: string | null;
  probability: number; // 0–1
  bias: MacroBias;
  volume: number | null;
  updated_at?: string;
}

export interface SentimentResult {
  count: number;
  macro_bias: MacroBias;
  markets: SentimentMarket[];
}

export async function fetchSentiment(): Promise<SentimentResult> {
  const res = await connectorFetch(`/sentiment`);
  if (!res.ok) throw await detailError(res, `Connector /sentiment ${res.status}`);
  return (await res.json()) as SentimentResult;
}

export type Vote = "bullish" | "bearish" | "neutral";

/** Regime de mercado (prompt #4): ambiente em que o sinal foi gerado. */
export interface Regime {
  trend: "alta" | "baixa" | "lateral" | "indefinido";
  volatility: "alta" | "normal" | "baixa" | "indefinido";
  volume: "alto" | "normal" | "baixo" | "indisponível" | "indefinido";
  atr_pct: number | null;
  suitable_for_trend: boolean;
  recommend: string;
  avoid: string;
}

/** Sinal técnico determinístico (fonte "rules"). Contrato compartilhado com o Risk Judge. */
export interface Signal {
  active: string;
  timeframe: string;
  direction: "call" | "put" | null; // null = sem consenso
  bias: Vote;
  confidence: number; // 0–1
  rationale: string;
  source: "rules" | "openclaw";
  regime: Regime;
  features: {
    rsi: number | null;
    macd: { macd: number; signal: number; hist: number } | null;
    bollinger: { mid: number; upper: number; lower: number } | null;
    votes: Record<string, Vote>;
  };
  candles_used: number;
}

export async function fetchIndicators(active: string, size: number, count = 200): Promise<Signal> {
  const res = await connectorFetch(
    `/indicators?active=${encodeURIComponent(active)}&size=${size}&count=${count}`,
  );
  if (!res.ok) throw await detailError(res, `Connector /indicators ${res.status}`);
  return (await res.json()) as Signal;
}

/** Uma decisão recente do autotrader (ring buffer do /autotrader/status). */
export interface AutotraderDecision {
  time: string; // ISO UTC
  action: "executed" | "skip" | "vetoed" | "error";
  asset: string | null;
  direction: "call" | "put" | null;
  confidence: number | null;
  detail: string;
}

/** Edge medido (backtest) de um par — a taxa/amostra que o gate de fato usa. */
export interface AutotraderEdge {
  hit_rate: number | null; // 0–1
  sample: number;
  passes_gate: boolean; // habilitado a operar?
}

export interface AutotraderStatus {
  enabled: boolean;
  balance_mode: string; // PRACTICE | REAL
  scan_open: boolean; // true = watchlist dinâmica (ativos abertos)
  universe: string; // currencies | all | fixed
  exclude_otc: boolean; // OTC fora da watchlist (random walk) → só forex real
  watchlist_count: number;
  assets: string[]; // amostra da watchlist (até 50)
  min_payout: number;
  max_open: number; // máx. posições simultâneas
  timeframe: string;
  confirm_timeframe: string;
  confluence: boolean;
  poll_s: number;
  stake_pct: number; // 0–1
  ticks: number;
  edge_gate: boolean; // gate de evidência ligado?
  edge_min_hit: number; // 0–1 — acerto mínimo p/ habilitar
  edge_min_sample: number; // amostra mínima
  edge_measured_count: number; // pares já medidos
  edge_enabled_count: number; // pares habilitados pelo edge
  edge: Record<string, AutotraderEdge>; // por ativo da watchlist mostrada
  holding: Record<string, string>; // ativo → ISO até quando está segurado
  recent: AutotraderDecision[];
}

export async function fetchAutotraderStatus(): Promise<AutotraderStatus> {
  const res = await connectorFetch(`/autotrader/status`);
  if (!res.ok) throw await detailError(res, `Connector /autotrader/status ${res.status}`);
  return (await res.json()) as AutotraderStatus;
}

export async function toggleAutotrader(enabled: boolean): Promise<{ enabled: boolean }> {
  const res = await connectorFetch(`/autotrader/toggle`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
  if (!res.ok) throw await detailError(res, `Connector /autotrader/toggle ${res.status}`);
  return (await res.json()) as { enabled: boolean };
}

export interface VaultFile {
  path: string;
  name: string;
  folder: string;
  modified: number;
  size: number;
}

export async function fetchVaultTree(): Promise<VaultFile[]> {
  const res = await connectorFetch(`/vault/tree`);
  if (!res.ok) throw await detailError(res, `Connector /vault/tree ${res.status}`);
  const json = (await res.json()) as { files: VaultFile[] };
  return json.files;
}

export async function fetchVaultFile(path: string): Promise<string> {
  const res = await connectorFetch(`/vault/file?path=${encodeURIComponent(path)}`);
  if (!res.ok) throw await detailError(res, `Connector /vault/file ${res.status}`);
  const json = (await res.json()) as { content: string };
  return json.content;
}

/** Abre o stream do candle em formação. Retorna função de cleanup. */
export function openCandleStream(
  active: string,
  size: number,
  onCandle: (c: Candle) => void,
  onError?: (msg: string) => void,
): () => void {
  const ws = new WebSocket(`${WS_URL}/ws/candles?active=${encodeURIComponent(active)}&size=${size}`);
  ws.onmessage = (ev) => {
    const data = JSON.parse(ev.data as string) as Candle & { error?: string };
    if (data.error) onError?.(data.error);
    else onCandle(data);
  };
  ws.onerror = () => onError?.("Falha na conexão WebSocket com o Connector");
  return () => ws.close();
}
