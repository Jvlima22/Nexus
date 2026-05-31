export type BrokerId = "binance" | "bybit" | "deriv" | "iqoption";
export type AuthMethod = "oauth" | "api_key" | "ssid";

export interface BrokerPermissions {
  read?: boolean;
  spot?: boolean;
  futures?: boolean;
  margin?: boolean;
  withdraw?: boolean;
  /** True se a API key tem permissão de saque (DEVE ser bloqueada por segurança). */
  hasWithdraw?: boolean;
}

export interface BrokerTestResult {
  ok: boolean;
  latencyMs: number;
  accountLabel?: string;
  permissions: BrokerPermissions;
  /** Stored encrypted for later use (e.g., updated SSID, refreshed OAuth token). */
  credentials: Record<string, unknown>;
  error?: string;
}

export interface BrokerAdapter {
  id: BrokerId;
  authMethod: AuthMethod;
  /**
   * Valida credenciais recém-fornecidas e devolve metadados + payload a cifrar.
   * Não persiste nada — a rota de API é quem grava no Supabase.
   */
  test(input: Record<string, unknown>): Promise<BrokerTestResult>;
}

export class BrokerError extends Error {
  constructor(message: string, public readonly code?: string) {
    super(message);
    this.name = "BrokerError";
  }
}
