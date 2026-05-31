// Verificação rápida: lê .dev.vars e lista as fontes em knowledge_sources.
// Uso: node scripts/verify-knowledge.mjs
import { readFileSync } from "node:fs";
import { createClient } from "@supabase/supabase-js";

const vars = Object.fromEntries(
  readFileSync(new URL("../.dev.vars", import.meta.url), "utf8")
    .split(/\r?\n/)
    .filter((l) => l && !l.trimStart().startsWith("#") && l.includes("="))
    .map((l) => {
      const i = l.indexOf("=");
      return [l.slice(0, i).trim(), l.slice(i + 1).trim()];
    }),
);

const url = vars.VITE_SUPABASE_URL;
const key = vars.SUPABASE_SERVICE_ROLE_KEY;
if (!url || !key) {
  console.error("Faltam VITE_SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY no .dev.vars");
  process.exit(1);
}

const supabase = createClient(url, key, { auth: { persistSession: false } });
const { data, error } = await supabase
  .from("knowledge_sources")
  .select("id,kind,title,char_count,token_estimate,status,active,created_at")
  .order("created_at", { ascending: false })
  .limit(10);

if (error) {
  console.error("ERRO:", error.message);
  console.error(
    error.message.includes("does not exist")
      ? "→ A tabela não existe. Rode a migration 2026-05-24_knowledge_rag.sql no Supabase."
      : "",
  );
  process.exit(1);
}

console.log(`Fontes encontradas: ${data.length}\n`);
for (const r of data) {
  console.log(
    `• [${r.kind}] ${r.title}\n  ${r.char_count} chars · ~${r.token_estimate} tokens · status=${r.status} · ativo=${r.active}`,
  );
}
