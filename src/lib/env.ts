/**
 * Acesso a variáveis de ambiente do Worker em qualquer runtime suportado:
 *   - Cloudflare Worker dev (Miniflare via @cloudflare/vite-plugin)
 *   - Cloudflare Worker prod
 *   - Node.js (se algum dia rodar fora do Worker)
 *
 * Em produção / dev no Cloudflare, os vars vêm via `env` do fetch handler
 * (NÃO via process.env). Stashamos no globalThis no entry para que os módulos
 * de lib consigam ler.
 */

const ENV_GLOBAL_KEY = "__NEXUS_WORKER_ENV__" as const;

type EnvBag = Record<string, string | undefined>;

interface GlobalWithEnv {
  [ENV_GLOBAL_KEY]?: EnvBag;
}

export function setWorkerEnv(env: unknown): void {
  if (env && typeof env === "object") {
    (globalThis as GlobalWithEnv)[ENV_GLOBAL_KEY] = env as EnvBag;
  }
}

export function getEnv(key: string): string | undefined {
  const fromGlobal = (globalThis as GlobalWithEnv)[ENV_GLOBAL_KEY]?.[key];
  if (fromGlobal !== undefined) return fromGlobal;

  // Fallback: Node / Workers com nodejs_compat
  if (typeof process !== "undefined" && process.env) {
    return process.env[key];
  }
  return undefined;
}

export function requireEnv(key: string): string {
  const v = getEnv(key);
  if (!v) {
    throw new Error(
      `Variável de ambiente ${key} ausente. Verifique .dev.vars (dev) ou wrangler secret (prod).`,
    );
  }
  return v;
}
