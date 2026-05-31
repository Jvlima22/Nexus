import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { getEnv } from "./env";

let cached: SupabaseClient | undefined;

/**
 * Cliente Supabase com service_role — uso APENAS em server functions (Worker).
 * Não importar em código que roda no browser.
 */
export function getSupabaseAdmin(): SupabaseClient {
  if (cached) return cached;

  const url = getEnv("VITE_SUPABASE_URL") ?? getEnv("SUPABASE_URL");
  const key = getEnv("SUPABASE_SERVICE_ROLE_KEY");

  if (!url || !key) {
    const g = globalThis as Record<string, unknown>;
    const stashed = g.__NEXUS_WORKER_ENV__ as Record<string, unknown> | undefined;
    const stashedKeys = stashed ? Object.keys(stashed) : [];
    const procKeys = typeof process !== "undefined" && process.env ? Object.keys(process.env).filter((k) => /supabase|deriv|broker|vite_/i.test(k)) : [];
    console.error("[supabase-admin] env não encontrado.", {
      url: !!url,
      key: !!key,
      stashedKeys,
      procKeys,
    });
    throw new Error(
      "Supabase admin não configurado: defina VITE_SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY em .dev.vars.",
    );
  }

  cached = createClient(url, key, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
  return cached;
}
