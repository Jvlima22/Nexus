import { hmacSha256Hex } from "../crypto";
import { BrokerError, type BrokerAdapter, type BrokerTestResult } from "./types";

const BASE = "https://api.bybit.com";

interface BybitInput {
  apiKey: string;
  apiSecret: string;
}

interface ApiKeyInfoResponse {
  retCode: number;
  retMsg: string;
  result?: {
    id: string;
    apiKey: string;
    readOnly: number;
    permissions?: Record<string, string[]>;
  };
}

export const bybitAdapter: BrokerAdapter = {
  id: "bybit",
  authMethod: "api_key",

  async test(raw): Promise<BrokerTestResult> {
    const input = raw as Partial<BybitInput>;
    if (!input.apiKey || !input.apiSecret) {
      throw new BrokerError("apiKey e apiSecret são obrigatórios", "missing_credentials");
    }

    const timestamp = Date.now().toString();
    const recvWindow = "5000";
    const queryString = "";
    const signaturePayload = `${timestamp}${input.apiKey}${recvWindow}${queryString}`;
    const signature = await hmacSha256Hex(input.apiSecret, signaturePayload);

    const start = performance.now();
    const res = await fetch(`${BASE}/v5/user/query-api`, {
      headers: {
        "X-BAPI-API-KEY": input.apiKey,
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-RECV-WINDOW": recvWindow,
        "X-BAPI-SIGN": signature,
      },
    });
    const latencyMs = Math.round(performance.now() - start);

    const body = (await res.json().catch(() => ({}))) as ApiKeyInfoResponse;

    if (!res.ok || body.retCode !== 0 || !body.result) {
      return {
        ok: false,
        latencyMs,
        permissions: {},
        credentials: input,
        error: `Bybit respondeu ${res.status}: ${body.retMsg || res.statusText}`,
      };
    }

    const perms = body.result.permissions ?? {};
    const flat = new Set<string>(Object.values(perms).flat());

    return {
      ok: true,
      latencyMs,
      accountLabel: `API ${body.result.apiKey.slice(-6)}`,
      permissions: {
        read: true,
        spot: flat.has("SpotTrade"),
        futures: flat.has("ContractTrade") || flat.has("DerivativesTrade"),
        margin: flat.has("Margin"),
        withdraw: flat.has("Withdraw"),
        hasWithdraw: flat.has("Withdraw"),
      },
      credentials: input,
    };
  },
};
