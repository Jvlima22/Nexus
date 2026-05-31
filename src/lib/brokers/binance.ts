import { hmacSha256Hex } from "../crypto";
import { BrokerError, type BrokerAdapter, type BrokerTestResult } from "./types";

const BASE = "https://api.binance.com";

interface AccountResponse {
  canTrade: boolean;
  canWithdraw: boolean;
  canDeposit: boolean;
  accountType?: string;
  permissions?: string[];
  balances?: Array<{ asset: string; free: string; locked: string }>;
}

interface BinanceInput {
  apiKey: string;
  apiSecret: string;
}

export const binanceAdapter: BrokerAdapter = {
  id: "binance",
  authMethod: "api_key",

  async test(raw): Promise<BrokerTestResult> {
    const input = raw as Partial<BinanceInput>;
    if (!input.apiKey || !input.apiSecret) {
      throw new BrokerError("apiKey e apiSecret são obrigatórios", "missing_credentials");
    }

    const timestamp = Date.now();
    const query = `timestamp=${timestamp}&recvWindow=5000`;
    const signature = await hmacSha256Hex(input.apiSecret, query);

    const start = performance.now();
    const res = await fetch(`${BASE}/api/v3/account?${query}&signature=${signature}`, {
      headers: { "X-MBX-APIKEY": input.apiKey },
    });
    const latencyMs = Math.round(performance.now() - start);

    if (!res.ok) {
      const body = await res.text().catch(() => "");
      return {
        ok: false,
        latencyMs,
        permissions: {},
        credentials: input,
        error: `Binance respondeu ${res.status}: ${body || res.statusText}`,
      };
    }

    const account = (await res.json()) as AccountResponse;
    const perms = new Set(account.permissions ?? []);

    return {
      ok: true,
      latencyMs,
      accountLabel: account.accountType ?? "SPOT",
      permissions: {
        read: true,
        spot: perms.has("SPOT") || account.canTrade,
        margin: perms.has("MARGIN"),
        futures: perms.has("FUTURES"),
        withdraw: account.canWithdraw,
        hasWithdraw: account.canWithdraw,
      },
      credentials: input,
    };
  },
};
