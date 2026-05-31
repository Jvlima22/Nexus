import { BrokerError, type BrokerAdapter, type BrokerTestResult } from "./types";

/**
 * IQ Option — não tem API oficial.
 *
 * Usamos o endpoint HTTPS de login interno (mesmo do site) para obter o cookie SSID,
 * que serve como token de sessão. O SSID é o que precisamos guardar cifrado para
 * abrir conexões WebSocket posteriores em wss://iqoption.com/echo/websocket.
 *
 * Atenção: este fluxo é reverso, sem garantia de estabilidade — quebra se a IQ
 * Option mexer no endpoint. Pode também violar o TOS deles. Use ciente.
 */

const LOGIN_URL = "https://auth.iqoption.com/api/v2/login";

interface IQInput {
  email: string;
  password: string;
}

interface IQLoginResponse {
  code?: string;
  data?: {
    ssid?: string;
  };
  message?: string;
}

export const iqoptionAdapter: BrokerAdapter = {
  id: "iqoption",
  authMethod: "ssid",

  async test(raw): Promise<BrokerTestResult> {
    const input = raw as Partial<IQInput>;
    if (!input.email || !input.password) {
      throw new BrokerError("email e password são obrigatórios", "missing_credentials");
    }

    const start = performance.now();
    const res = await fetch(LOGIN_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier: input.email, password: input.password }),
    });
    const latencyMs = Math.round(performance.now() - start);

    // O SSID vem em cookies (Set-Cookie: ssid=...) OU no body, dependendo da versão.
    let ssid: string | undefined;
    const setCookie = res.headers.get("set-cookie") ?? "";
    const m = setCookie.match(/ssid=([^;]+)/i);
    if (m) ssid = m[1];

    const body = (await res.json().catch(() => ({}))) as IQLoginResponse;
    if (!ssid && body.data?.ssid) ssid = body.data.ssid;

    if (!res.ok || !ssid) {
      return {
        ok: false,
        latencyMs,
        permissions: {},
        credentials: { email: input.email },
        error: body.message ?? `IQ Option respondeu ${res.status}`,
      };
    }

    return {
      ok: true,
      latencyMs,
      accountLabel: input.email,
      permissions: {
        read: true,
        spot: true,
        withdraw: false,
        hasWithdraw: false,
      },
      credentials: { email: input.email, password: input.password, ssid },
    };
  },
};
