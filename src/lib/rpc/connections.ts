import { createServerFn } from "@tanstack/react-start";
import { getSupabaseAdmin } from "@/lib/supabase-admin";
import { encryptJSON, decryptJSON } from "@/lib/crypto";
import { getAdapter, type BrokerId } from "@/lib/brokers";
import { requireUser } from "./auth-guard";
import { logAudit } from "./audit";

interface ConnectInput {
  accessToken: string;
  broker: BrokerId;
  credentials: Record<string, unknown>;
}

interface OperationInput {
  accessToken: string;
  broker: BrokerId;
}

function validateBroker(id: unknown): BrokerId {
  if (typeof id !== "string" || !["binance", "bybit", "deriv", "iqoption"].includes(id)) {
    throw new Error(`broker inválido: ${String(id)}`);
  }
  return id as BrokerId;
}

export const connectBroker = createServerFn({ method: "POST" })
  .inputValidator((data: ConnectInput) => ({
    accessToken: String(data.accessToken),
    broker: validateBroker(data.broker),
    credentials: data.credentials ?? {},
  }))
  .handler(async ({ data }) => {
    const { userId } = await requireUser(data.accessToken);
    const adapter = getAdapter(data.broker);

    const result = await adapter.test(data.credentials).catch((err) => ({
      ok: false as const,
      latencyMs: 0,
      permissions: {},
      credentials: data.credentials,
      error: err instanceof Error ? err.message : String(err),
    }));

    if (!result.ok) {
      await logAudit(userId, data.broker, "error", { stage: "connect", error: result.error });
      return { ok: false, error: result.error ?? "Falha na conexão" };
    }

    if (result.permissions.hasWithdraw) {
      await logAudit(userId, data.broker, "error", { stage: "connect", error: "withdraw_blocked" });
      return {
        ok: false,
        error:
          "Esta API Key permite saque (withdraw). Por segurança, NEXUS bloqueia chaves com essa permissão. Crie uma nova chave SEM a opção 'Enable Withdrawals'.",
      };
    }

    const cipher = await encryptJSON(result.credentials);
    const admin = getSupabaseAdmin();

    const { error } = await admin.from("broker_connections").upsert(
      {
        user_id: userId,
        broker: data.broker,
        auth_method: adapter.authMethod,
        status: "connected",
        account_label: result.accountLabel,
        permissions: result.permissions,
        last_latency_ms: result.latencyMs,
        last_tested_at: new Date().toISOString(),
        last_error: null,
        credentials_ciphertext: cipher.ciphertext,
        credentials_iv: cipher.iv,
      },
      { onConflict: "user_id,broker" },
    );

    if (error) {
      await logAudit(userId, data.broker, "error", { stage: "persist", error: error.message });
      return { ok: false, error: `Falha ao salvar: ${error.message}` };
    }

    await logAudit(userId, data.broker, "connect", {
      latencyMs: result.latencyMs,
      permissions: result.permissions,
    });

    return {
      ok: true,
      accountLabel: result.accountLabel,
      latencyMs: result.latencyMs,
      permissions: result.permissions,
    };
  });

export const testBroker = createServerFn({ method: "POST" })
  .inputValidator((data: OperationInput) => ({
    accessToken: String(data.accessToken),
    broker: validateBroker(data.broker),
  }))
  .handler(async ({ data }) => {
    const { userId } = await requireUser(data.accessToken);
    const admin = getSupabaseAdmin();

    const { data: row, error } = await admin
      .from("broker_connections")
      .select("credentials_ciphertext, credentials_iv")
      .eq("user_id", userId)
      .eq("broker", data.broker)
      .single();

    if (error || !row) {
      return { ok: false, error: "Conexão não encontrada" };
    }

    const creds = await decryptJSON<Record<string, unknown>>({
      ciphertext: row.credentials_ciphertext,
      iv: row.credentials_iv,
    });

    const adapter = getAdapter(data.broker);
    const result = await adapter.test(creds);

    await admin
      .from("broker_connections")
      .update({
        status: result.ok ? "connected" : "error",
        last_latency_ms: result.latencyMs,
        last_tested_at: new Date().toISOString(),
        last_error: result.ok ? null : result.error,
      })
      .eq("user_id", userId)
      .eq("broker", data.broker);

    await logAudit(userId, data.broker, "test", { ok: result.ok, latencyMs: result.latencyMs });

    return { ok: result.ok, latencyMs: result.latencyMs, error: result.error };
  });

export const revokeBroker = createServerFn({ method: "POST" })
  .inputValidator((data: OperationInput) => ({
    accessToken: String(data.accessToken),
    broker: validateBroker(data.broker),
  }))
  .handler(async ({ data }) => {
    const { userId } = await requireUser(data.accessToken);
    const admin = getSupabaseAdmin();

    const { error } = await admin
      .from("broker_connections")
      .delete()
      .eq("user_id", userId)
      .eq("broker", data.broker);

    if (error) return { ok: false, error: error.message };

    await logAudit(userId, data.broker, "revoke", {});
    return { ok: true };
  });
