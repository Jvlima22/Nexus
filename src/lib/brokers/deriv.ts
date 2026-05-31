import { BrokerError, type BrokerAdapter, type BrokerTestResult } from "./types";
import { getEnv } from "../env";

/**
 * Deriv OAuth 2.0 — fluxo de redirect.
 *
 * 1. /api/connections/deriv/start  → redireciona p/ oauth.deriv.com com app_id
 * 2. Deriv volta com ?token1=...&acct1=...&cur1=...
 * 3. /api/connections/deriv/callback chama adapter.test({ token, account, currency })
 *
 * O "token" devolvido pela Deriv é um API token longa-vida — guardamos ele cifrado.
 */

const WS_URL = "wss://ws.derivws.com/websockets/v3";

interface DerivInput {
  token: string;
  account?: string;
  currency?: string;
}

interface AuthorizeResponse {
  authorize?: {
    loginid: string;
    balance: number;
    currency: string;
    email: string;
    scopes?: string[];
  };
  error?: { code: string; message: string };
}

export function buildDerivAuthorizeUrl(state: string): string {
  const appId = getEnv("DERIV_APP_ID");
  if (!appId) throw new BrokerError("DERIV_APP_ID não configurado", "config_missing");
  const url = new URL("https://oauth.deriv.com/oauth2/authorize");
  url.searchParams.set("app_id", appId);
  url.searchParams.set("state", state);
  return url.toString();
}

export const derivAdapter: BrokerAdapter = {
  id: "deriv",
  authMethod: "oauth",

  async test(raw): Promise<BrokerTestResult> {
    const input = raw as Partial<DerivInput>;
    if (!input.token) {
      throw new BrokerError("token OAuth ausente", "missing_credentials");
    }

    const appId = getEnv("DERIV_APP_ID");
    if (!appId) throw new BrokerError("DERIV_APP_ID não configurado", "config_missing");

    const start = performance.now();
    const ws = new WebSocket(`${WS_URL}?app_id=${appId}`);

    const result = await new Promise<AuthorizeResponse>((resolve, reject) => {
      const timeout = setTimeout(() => {
        try { ws.close(); } catch {}
        reject(new BrokerError("Timeout autorizando com Deriv (10s)", "timeout"));
      }, 10_000);

      ws.addEventListener("open", () => {
        ws.send(JSON.stringify({ authorize: input.token }));
      });
      ws.addEventListener("message", (evt) => {
        clearTimeout(timeout);
        try {
          resolve(JSON.parse(evt.data as string) as AuthorizeResponse);
        } catch (e) {
          reject(e);
        } finally {
          try { ws.close(); } catch {}
        }
      });
      ws.addEventListener("error", () => {
        clearTimeout(timeout);
        reject(new BrokerError("WebSocket da Deriv falhou", "ws_error"));
      });
    });

    const latencyMs = Math.round(performance.now() - start);

    if (result.error || !result.authorize) {
      return {
        ok: false,
        latencyMs,
        permissions: {},
        credentials: input,
        error: result.error?.message ?? "Authorize sem dados",
      };
    }

    const scopes = new Set(result.authorize.scopes ?? []);
    return {
      ok: true,
      latencyMs,
      accountLabel: `${result.authorize.loginid} (${result.authorize.currency})`,
      permissions: {
        read: scopes.has("read") || scopes.size === 0,
        spot: scopes.has("trade"),
        withdraw: scopes.has("payments"),
        hasWithdraw: scopes.has("payments"),
      },
      credentials: input,
    };
  },
};
