/**
 * Cliente mínimo da Anthropic Messages API via fetch (roda no Cloudflare Worker,
 * sem SDK). Usa PROMPT CACHING: a base de conhecimento vai como bloco de system
 * com `cache_control: ephemeral` → 1ª chamada grava o cache, as seguintes leem do
 * cache (TTFT muito menor + ~90% mais barato). É a estratégia "RAG só com tokens
 * Claude" — não há embeddings nem vendor externo.
 */
import { getEnv, requireEnv } from "./env";

const API_URL = "https://api.anthropic.com/v1/messages";
const DEFAULT_MODEL = "claude-sonnet-4-6";

interface SystemBlock {
  type: "text";
  text: string;
  cache_control?: { type: "ephemeral" };
}

export interface ClaudeUsage {
  input_tokens: number;
  output_tokens: number;
  cache_creation_input_tokens: number;
  cache_read_input_tokens: number;
}

export interface AskResult {
  answer: string;
  usage: ClaudeUsage;
  model: string;
}

const BASE_SYSTEM =
  "Você é a NEXUS, IA de trading do usuário. Responda em português, conciso e técnico. " +
  "Baseie-se SOMENTE na base de conhecimento fornecida; se a informação não estiver lá, " +
  "diga claramente que não consta no contexto — não invente.";

export async function askClaudeWithContext(opts: {
  question: string;
  knowledge: string; // base concatenada (bloco cacheado)
  system?: string;
  model?: string;
  maxTokens?: number;
}): Promise<AskResult> {
  const apiKey = requireEnv("ANTHROPIC_API_KEY");
  const model = opts.model ?? getEnv("NEXUS_CLAUDE_MODEL") ?? DEFAULT_MODEL;

  const system: SystemBlock[] = [
    { type: "text", text: opts.system ?? BASE_SYSTEM },
  ];
  if (opts.knowledge.trim()) {
    system.push({
      type: "text",
      text: `Base de conhecimento do usuário:\n\n${opts.knowledge}`,
      cache_control: { type: "ephemeral" }, // cacheia tudo até aqui (prefixo estável)
    });
  }

  const res = await fetch(API_URL, {
    method: "POST",
    headers: {
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
      "content-type": "application/json",
    },
    body: JSON.stringify({
      model,
      max_tokens: opts.maxTokens ?? 1024,
      system,
      messages: [{ role: "user", content: opts.question }],
    }),
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`Anthropic ${res.status}: ${detail.slice(0, 500)}`);
  }

  const data = (await res.json()) as {
    content: { type: string; text?: string }[];
    usage: Partial<ClaudeUsage>;
  };

  return {
    model,
    answer: data.content
      .filter((b) => b.type === "text")
      .map((b) => b.text ?? "")
      .join(""),
    usage: {
      input_tokens: data.usage.input_tokens ?? 0,
      output_tokens: data.usage.output_tokens ?? 0,
      cache_creation_input_tokens: data.usage.cache_creation_input_tokens ?? 0,
      cache_read_input_tokens: data.usage.cache_read_input_tokens ?? 0,
    },
  };
}
