import { createServerFn } from "@tanstack/react-start";
import { getSupabaseAdmin } from "@/lib/supabase-admin";
import { askClaudeWithContext } from "@/lib/anthropic";
import { requireUser } from "./auth-guard";

/**
 * Knowledge / Contexto da IA.
 * - ingestKnowledge: extrai texto de URL / arquivo / texto colado e grava em
 *   `knowledge_sources` (INSERT via service_role; o client não tem permissão).
 * - askNexus: monta a base ativa do usuário e pergunta ao Claude com prompt caching.
 * Listagem, toggle e delete são feitos direto no client via RLS (owner policies).
 */

// ── Extração ──────────────────────────────────────────────────────────────────

function htmlToText(html: string): string {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<noscript[\s\S]*?<\/noscript>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/gi, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'")
    .replace(/[ \t]{2,}/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

async function extractUrl(
  url: string,
): Promise<{ title: string; content: string }> {
  let res: Response;
  try {
    res = await fetch(url, {
      headers: { "user-agent": "Mozilla/5.0 (compatible; NEXUS/1.0)" },
    });
  } catch {
    throw new Error("Não consegui acessar a URL.");
  }
  if (!res.ok) throw new Error(`Falha ao buscar URL (HTTP ${res.status}).`);
  const html = await res.text();
  const title =
    html.match(/<title[^>]*>([\s\S]*?)<\/title>/i)?.[1]?.trim() || url;
  return { title, content: htmlToText(html) };
}

function b64ToBytes(b64: string): Uint8Array {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}

async function extractPdf(bytes: Uint8Array): Promise<string> {
  // import dinâmico + specifier indireto: se `unpdf` não estiver instalado, só o PDF
  // falha (URL/texto seguem) e o typecheck não quebra antes do `npm install`.
  const specifier = "unpdf";
  const mod = (await import(/* @vite-ignore */ specifier)) as {
    getDocumentProxy: (b: Uint8Array) => Promise<unknown>;
    extractText: (
      pdf: unknown,
      o: { mergePages: boolean },
    ) => Promise<{ text: string | string[] }>;
  };
  const pdf = await mod.getDocumentProxy(bytes);
  const { text } = await mod.extractText(pdf, { mergePages: true });
  return Array.isArray(text) ? text.join("\n\n") : text;
}

// ── ingestKnowledge ─────────────────────────────────────────────────────────

interface IngestInput {
  accessToken: string;
  kind: "file" | "url" | "text";
  title?: string;
  url?: string;
  text?: string;
  dataBase64?: string;
  mime?: string;
}

export const ingestKnowledge = createServerFn({ method: "POST" })
  .inputValidator((d: IngestInput) => {
    if (!["file", "url", "text"].includes(d.kind))
      throw new Error("kind inválido");
    return {
      accessToken: String(d.accessToken),
      kind: d.kind,
      title: d.title ? String(d.title) : "",
      url: d.url ? String(d.url) : "",
      text: d.text ? String(d.text) : "",
      dataBase64: d.dataBase64 ? String(d.dataBase64) : "",
      mime: d.mime ? String(d.mime) : "",
    };
  })
  .handler(async ({ data }) => {
    const { userId } = await requireUser(data.accessToken);

    let title = data.title.trim();
    let content = "";
    let sourceUrl: string | null = null;

    if (data.kind === "url") {
      if (!data.url) throw new Error("URL ausente.");
      const ex = await extractUrl(data.url);
      title = title || ex.title;
      content = ex.content;
      sourceUrl = data.url;
    } else if (data.text) {
      content = data.text;
      title = title || "Texto colado";
    } else if (data.dataBase64) {
      const bytes = b64ToBytes(data.dataBase64);
      const isPdf =
        data.mime.includes("pdf") || title.toLowerCase().endsWith(".pdf");
      content = isPdf
        ? await extractPdf(bytes)
        : new TextDecoder().decode(bytes);
      title = title || "Arquivo";
    } else {
      throw new Error("Nada para ingerir.");
    }

    content = content.trim();
    if (!content)
      throw new Error("Não consegui extrair texto legível da fonte.");

    const admin = getSupabaseAdmin();
    const { data: row, error } = await admin
      .from("knowledge_sources")
      .insert({
        user_id: userId,
        kind: data.kind,
        title: title.slice(0, 200),
        source_url: sourceUrl,
        mime: data.mime || null,
        content,
        char_count: content.length,
        token_estimate: Math.ceil(content.length / 4),
        status: "ready",
      })
      .select(
        "id,kind,title,char_count,token_estimate,status,active,created_at",
      )
      .single();

    if (error) throw new Error(error.message);
    return row;
  });

// ── askNexus ──────────────────────────────────────────────────────────────────

interface AskInput {
  accessToken: string;
  question: string;
}

export const askNexus = createServerFn({ method: "POST" })
  .inputValidator((d: AskInput) => ({
    accessToken: String(d.accessToken),
    question: String(d.question),
  }))
  .handler(async ({ data }) => {
    const { userId } = await requireUser(data.accessToken);
    if (!data.question.trim()) throw new Error("Pergunta vazia.");

    const admin = getSupabaseAdmin();
    const { data: rows, error } = await admin
      .from("knowledge_sources")
      .select("title,content")
      .eq("user_id", userId)
      .eq("active", true)
      .eq("status", "ready")
      .order("created_at", { ascending: true });
    if (error) throw new Error(error.message);

    const kb = (rows ?? [])
      .map((r) => `## ${r.title}\n\n${r.content}`)
      .join("\n\n---\n\n");

    const started = Date.now();
    const result = await askClaudeWithContext({
      question: data.question,
      knowledge: kb,
    });

    return {
      answer: result.answer,
      model: result.model,
      usage: result.usage,
      sources: rows?.length ?? 0,
      elapsedMs: Date.now() - started,
      cached: result.usage.cache_read_input_tokens > 0,
    };
  });
