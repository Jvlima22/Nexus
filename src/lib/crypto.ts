/**
 * Cifra de credenciais de corretora.
 *
 * Algoritmo: AES-256-GCM via WebCrypto (nativo no Cloudflare Worker e no browser,
 * mas só chamamos do server — nunca cifrar/decifrar credenciais no client).
 *
 * Formato de armazenamento:
 *   credentials_ciphertext = base64( ciphertext + auth_tag )
 *   credentials_iv         = base64( IV de 12 bytes, único por mensagem )
 */

import { getEnv } from "./env";

let keyPromise: Promise<CryptoKey> | undefined;

function base64Decode(b64: string): Uint8Array<ArrayBuffer> {
  const bin = atob(b64);
  const buf = new ArrayBuffer(bin.length);
  const out = new Uint8Array(buf);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

function base64Encode(bytes: Uint8Array): string {
  let bin = "";
  for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
  return btoa(bin);
}

async function getKey(): Promise<CryptoKey> {
  if (keyPromise) return keyPromise;

  const raw = getEnv("BROKER_ENCRYPTION_KEY");
  if (!raw) {
    throw new Error(
      "BROKER_ENCRYPTION_KEY ausente em .dev.vars. Gere com: node -e \"console.log(require('crypto').randomBytes(32).toString('base64'))\"",
    );
  }

  const bytes = base64Decode(raw);
  if (bytes.length !== 32) {
    throw new Error(`BROKER_ENCRYPTION_KEY deve ter 32 bytes (got ${bytes.length}). Use uma chave AES-256 em base64.`);
  }

  keyPromise = crypto.subtle.importKey("raw", bytes, { name: "AES-GCM" }, false, ["encrypt", "decrypt"]);
  return keyPromise;
}

export interface CipherPayload {
  ciphertext: string;
  iv: string;
}

export async function encryptJSON(payload: unknown): Promise<CipherPayload> {
  const key = await getKey();
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const plaintext = new TextEncoder().encode(JSON.stringify(payload));
  const ciphertext = await crypto.subtle.encrypt({ name: "AES-GCM", iv }, key, plaintext);
  return {
    ciphertext: base64Encode(new Uint8Array(ciphertext)),
    iv: base64Encode(iv),
  };
}

export async function decryptJSON<T = unknown>({ ciphertext, iv }: CipherPayload): Promise<T> {
  const key = await getKey();
  const plaintext = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: base64Decode(iv) },
    key,
    base64Decode(ciphertext),
  );
  return JSON.parse(new TextDecoder().decode(plaintext)) as T;
}

/** Assinatura HMAC-SHA256 (Binance, Bybit). Devolve hex lowercase. */
export async function hmacSha256Hex(secret: string, message: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(message));
  const bytes = new Uint8Array(sig);
  let hex = "";
  for (let i = 0; i < bytes.length; i++) hex += bytes[i].toString(16).padStart(2, "0");
  return hex;
}
