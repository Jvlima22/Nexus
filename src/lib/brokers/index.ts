import { binanceAdapter } from "./binance";
import { bybitAdapter } from "./bybit";
import { derivAdapter } from "./deriv";
import { iqoptionAdapter } from "./iqoption";
import type { BrokerAdapter, BrokerId } from "./types";

export const adapters: Record<BrokerId, BrokerAdapter> = {
  binance: binanceAdapter,
  bybit: bybitAdapter,
  deriv: derivAdapter,
  iqoption: iqoptionAdapter,
};

export function getAdapter(id: string): BrokerAdapter {
  const a = adapters[id as BrokerId];
  if (!a) throw new Error(`Adapter desconhecido: ${id}`);
  return a;
}

export type { BrokerAdapter, BrokerId } from "./types";
export { buildDerivAuthorizeUrl } from "./deriv";
