---
tipo: decisao
status: aceita
data: 2026-05-24
projeto: NEXUS Trader
tags:
  - dev/decisao
  - ia/rag
  - ia/knowledge
relacionado:
  - "[[2026-05-23 Custo da IA - API pay-as-you-go vs assinatura]]"
  - "[[2026-05-23 Documentacao obrigatoria no Obsidian]]"
---

# Decisão: como dar contexto (RAG) à IA a partir de upload/URL no Knowledge

## Contexto
A interface `/knowledge` tinha (no scaffold antigo) upload de arquivos e link de URL
para alimentar contexto da IA — recurso removido, agora reativado. Requisito do
usuário: ao subir um arquivo ou colar um link, o conteúdo vira contexto que a IA
recupera "em milissegundos".

Restrição forte trazida pelo usuário: **gastar apenas tokens da Claude** — sem um
segundo vendor pago.

## Opções consideradas
1. **Embeddings + pgvector (RAG clássico)** — Workers AI (bge-m3), Voyage ou OpenAI.
   Busca semântica de verdade, escala. Contras: a Anthropic **não tem endpoint de
   embeddings** (recomenda Voyage), então exigiria outro provedor/binding. Voyage/OpenAI
   = novo vendor + hop externo na query (contraria "milissegundos" e "só Claude").
2. **Prompt Caching (escolhida)** — guarda o texto extraído em `knowledge_sources` e
   injeta a base inteira como **prefixo `system` cacheado** (`cache_control: ephemeral`).
   1ª chamada grava o cache; as seguintes leem do cache (TTFT bem menor, ~90% mais
   barato). **Só tokens Claude**, zero embeddings, zero vendor.
3. **Full-Text Search (Postgres `tsvector`/BM25) + Contextual Retrieval (Haiku)** —
   recuperação por palavra-chave em ms, de graça no Supabase; Claude só na resposta.

## Decisão
**Opção 2 (Prompt Caching) como v1**, com a **camada de dados já pronta para a 2**:
a tabela `knowledge_sources` tem coluna gerada `tsv` (tsvector PT) + índice GIN, então
ligar FTS/BM25 quando a base passar do tamanho do contexto **não exige nova migration**.

Por quê: melhor encaixe com "só tokens Claude" + "milissegundos" + simplicidade, e dá a
**melhor qualidade** (o Claude vê a base inteira, sem perda por chunking/recuperação).
Limite: vale enquanto a base ativa couber no contexto (~150K tokens no Sonnet/Opus;
mais no modelo de 1M). Acima disso → evoluir para FTS (opção 3).

## Implementação
- **Migration** `supabase/migrations/2026-05-24_knowledge_rag.sql`: tabela
  `knowledge_sources` (kind file|url|text, content, char/token, status, active), RLS
  por dono (INSERT via service_role), `tsv` gerada + GIN, Realtime.
- **`src/lib/anthropic.ts`**: client da Messages API via `fetch` (sem SDK), com
  `cache_control` no bloco da base. Modelo padrão `claude-sonnet-4-6` (`NEXUS_CLAUDE_MODEL`).
- **`src/lib/rpc/knowledge.ts`**: `ingestKnowledge` (extrai URL via strip-HTML, PDF via
  `unpdf`, texto/arquivos-texto direto) e `askNexus` (monta base ativa + pergunta cacheada).
- **`src/components/ai/KnowledgeContext.tsx`** + aba em `src/routes/knowledge.tsx`:
  adicionar URL/arquivo/texto, lista com toggle ativo/excluir, caixa de pergunta que
  mostra latência e se foi cache HIT.
- **Dep nova:** `unpdf` (parser de PDF que roda no Worker). **Env nova:** `ANTHROPIC_API_KEY`
  (secret do Worker — `.dev.vars` em dev / `wrangler secret put` em prod).

## Consequências
- Positivas: contexto "instantâneo" via cache; custo só na Anthropic; sem infra de
  vetores; qualidade máxima (base inteira no contexto); FTS pré-cabeado.
- Negativas / riscos:
  - Cache `ephemeral` expira (~5 min sem uso) → 1ª pergunta após ocioso re-grava (mais
    cara/lenta). Mitigável com TTL estendido depois.
  - Não escala para base gigante (estoura contexto) → gatilho para opção 3.
  - Extração de URL é strip-HTML simples (sem readability) → páginas pesadas trazem ruído.
  - `unpdf` no Worker: PDFs escaneados (imagem) não extraem texto.
- A revisitar quando: base ativa > ~100K tokens, ou se a recuperação ficar imprecisa
  (ligar FTS/Contextual Retrieval), ou se quiser busca semântica (embeddings + pgvector).
