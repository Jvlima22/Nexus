---
tipo: decisao
status: aceita
data: 2026-05-23
projeto: NEXUS Trader
tags:
  - dev/decisao
  - ia/custo
  - ia/anthropic
relacionado:
  - "[[2026-05-23 Arquitetura de dados ao vivo IQ Option]]"
  - "[[Tarefas Pendentes - Dados ao vivo IQ]]"
---

# Decisão: Custo da IA — API pay-as-you-go, não assinatura

## Contexto
A NEXUS roda Claude em loop (triagem de setup → decisão de trade). Antes de
ligar isso em produção 24/7 é preciso saber **quanto custa por dia** e **qual
modelo de billing** sustenta um bot contínuo. Conclusão curta: **orce API
pré-paga, não plano de assinatura.**

## Preços por milhão de tokens (Claude 4.x atual)
| Modelo | Input | Output |
|---|---|---|
| Haiku 4.5 | ~$1 | ~$5 |
| Sonnet 4.6 | ~$3 | ~$15 |

## Estimativa diária
Assumindo o mix típico de um loop de trading: **~85% input / 15% output**.

| Cenário | Tokens/dia | Haiku 4.5/dia | Sonnet 4.6/dia |
|---|---|---|---|
| Conservador | ~8,6M | ~$13 | ~$40 |
| Moderado | ~26M | ~$40 | ~$120 |
| Agressivo | ~104M | ~$160 | ~$480 |

> Mensal: multiplique por ~30. Moderado em Sonnet ≈ **$3.600/mês**.

## Opções consideradas
1. **Assinatura (Max, até $200/mês)**: limites de uso pensados para sessões
   **interativas**; os Termos **vedam** usar a assinatura para automação /
   serviço de fundo contínuo. ❌ Não é caminho suportado para bot 24/7.
2. **API pay-as-you-go (créditos pré-pagos)**: cobra por token usado, sem teto
   artificial, é o caminho suportado para automação. ✅

## Decisão
**API pay-as-you-go (opção 2).** Nenhum plano de assinatura sustenta um bot
contínuo de forma suportada — Max é para uso interativo e o ToS proíbe usá-lo
como serviço de fundo. O loop da NEXUS roda na API com créditos pré-pagos.

### Alavancas reais de redução de custo
- **Haiku para triagem, Sonnet só na decisão final** → corta ~70% do gasto.
- **Prompt caching do contexto fixo** (regras, system prompt) → desconto grande
  em chamadas repetidas — exatamente o padrão de um loop.
- **Reduzir frequência:** chamar Claude só em sinal/setup, não a cada candle.
  Pré-filtrar com **regras determinísticas (sem IA)** e acionar o Claude apenas
  quando há candidato.
- **Enxugar contexto:** mandar candles agregados / indicadores, não tick a tick.

## Consequências
- Positivas:
  - Com arquitetura enxuta (Haiku + caching + acionamento por setup) o dia
    realista cai para a faixa de **~$5–20/dia**.
  - Billing previsível e dimensionável; sem risco de violar ToS de assinatura.
- Negativas / riscos:
  - Sem otimização, Sonnet em alta frequência passa fácil de **$100–400/dia**.
  - Exige disciplina no design do loop (gating determinístico + caching) — se o
    pré-filtro falhar, o custo escala linear com o número de chamadas.
- A revisitar quando: definir o modelo final de produção, medir o custo real
  por chamada, ou se a Anthropic mudar preços / tabela de modelos.

## Confirmação empírica (2026-05-24)
Ao ligar o RAG do Knowledge ([[2026-05-24 RAG do Knowledge - Prompt Caching]]),
testei a `ANTHROPIC_API_KEY` real direto contra a Messages API:

- A chave **é válida** (autentica; formato `sk-ant-api03-…`; modelo `claude-sonnet-4-6`
  aceito). O `401` que apareceu no app era **chave desatualizada na memória do dev**
  (Worker lê `.dev.vars` no boot → precisa **reiniciar `npm run dev`** após editar).
- Resposta real da API: **HTTP 400 — "Your credit balance is too low to access the
  Anthropic API."** → conta **sem créditos**.

**Pergunta do usuário:** "uso o plano Pro, não consigo usar aqui?" → **Não.**
Assinatura **Claude Pro/Max (claude.ai)** e **Claude Code** NÃO dão acesso à API e
NÃO compartilham saldo. Chamadas programáticas (o `fetch` do Worker) só rodam sobre
a **API pré-paga** — billing separado. Reforça a decisão acima.

**Pendência aberta:** comprar crédito de API (console.anthropic.com → Plans & Billing;
mínimo ~US$ 5). Com contexto ~2.853 tokens + prompt caching, US$ 5 rendem milhares de
perguntas — custo irrisório, não é segunda mensalidade.

**Verificadores deixados:** `scripts/verify-knowledge.mjs` (lista fontes no Supabase) e
`scripts/verify-anthropic.mjs` (testa a chave sem vazá-la).
