// Testa a ANTHROPIC_API_KEY do .dev.vars com 1 chamada mínima. NÃO imprime a chave.
import { readFileSync } from "node:fs";

const raw = readFileSync(new URL("../.dev.vars", import.meta.url), "utf8");
const line = raw.split(/\r?\n/).find((l) => l.startsWith("ANTHROPIC_API_KEY="));
if (!line) {
  console.error("ANTHROPIC_API_KEY não encontrada no .dev.vars");
  process.exit(1);
}
let key = line.slice("ANTHROPIC_API_KEY=".length);

// Diagnóstico sem vazar a chave
const hadQuotes = /^["'].*["']$/.test(key.trim());
const hadSpace = key !== key.trim();
key = key.trim().replace(/^["']|["']$/g, "");
console.log("comprimento:", key.length);
console.log("prefixo:", key.slice(0, 14) + "…");
console.log("sufixo:", "…" + key.slice(-6));
console.log("tinha espaços nas pontas?", hadSpace);
console.log("tinha aspas?", hadQuotes);
console.log("começa com sk-ant-?", key.startsWith("sk-ant-"));
console.log("---");

const res = await fetch("https://api.anthropic.com/v1/messages", {
  method: "POST",
  headers: {
    "x-api-key": key,
    "anthropic-version": "2023-06-01",
    "content-type": "application/json",
  },
  body: JSON.stringify({
    model: "claude-sonnet-4-6",
    max_tokens: 1,
    messages: [{ role: "user", content: "hi" }],
  }),
});

console.log("HTTP", res.status);
console.log(await res.text());
