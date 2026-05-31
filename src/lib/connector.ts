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
  const body = (await res.json().catch(() => ({}))) as { detail?: string };
  return new Error(body.detail ?? fallback);
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
