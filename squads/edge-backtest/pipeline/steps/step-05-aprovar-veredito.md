---
type: checkpoint
---

# Step 05: Aprovar Veredito

Ponto de decisão humano — só depois da sua aprovação a nota é gravada no vault Obsidian.

Apresente ao usuário um resumo com:
1. **Veredito** — ATIVAR ou DESCARTAR + nível de confiança.
2. **Selo da revisão** — APROVADO / APROVADO com ressalva / REPROVADO (de `review.md`).
3. **Métricas-chave** — N, win rate + IC, breakeven, expectancy.
4. **strategy-spec.json** — se foi gerado (só em ATIVAR).

Pergunte se o usuário aprova gravar a nota final em `NEXUS/30_Trading/` do vault.

- **Aprovar** → gravar a nota no vault (`NEXUS/30_Trading/`) e atualizar `_memory/runs.md`.
- **Rejeitar** → não gravar no vault; devolver ao passo 3 (`relatorio-veredito`) com o motivo.

Lembrete: este squad NÃO executa ordens. Um veredito ATIVAR só significa que a estratégia é
candidata a ser ligada no autotrader (stack persistente) — decisão e execução seguem externas.
