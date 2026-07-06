---
tipo: decisao
status: aceita
data: 2026-05-31
projeto: NEXUS Trader
tags:
  - dev/decisao
  - trading/risco
relacionado: []
---

# Decisão: Risk Judge — juiz de risco inegociável (Fase 3)

## Contexto
O documento [[NEXUS TRADER Estratégia Definitiva e Arquitetura de Integração]] define um
funil profissional de 8 camadas e um "Gate de Risco de 2%". O código tinha apenas um
gate fraco em `connector/orders.py`: checava só `amount ≤ 2% do saldo`. Qualquer sinal
da IA que coubesse nos 2% executava — sem piso de confiança, sem proteção contra
sequência de perdas, sem teto de prejuízo diário.

Cérebro de decisão definido como **GPT-5.4 via OpenClaw** (ver [[2026-05-31-cerebro-orquestrador-openclaw]]).
O Risk Judge é a autoridade final: o OpenClaw orquestra e sugere, mas nenhuma ordem
passa sem o veredito do juiz.

## Opções consideradas
1. **Manter o gate inline em orders.py**: simples, mas mistura risco com execução e
   não cobre confiança/circuit breaker/drawdown.
2. **Risk Judge como módulo dedicado (`risk.py`)** com funil multi-regra, veredito
   estruturado e auditoria em Supabase: testável, isolado, expansível para as demais
   camadas do funil. ✅
3. **Mover a lógica para o OpenClaw (GPT)**: descartado — o juiz precisa ser
   determinístico e inegociável, fora do alcance do raciocínio probabilístico da IA.

## Decisão
Criado `connector/risk.py` com `evaluate()` rodando 5 regras, na ordem (primeiro veto
interrompe e é auditado):
1. **Confiança ≥ 70%** (`min_confidence`) → `LOW_CONFIDENCE`
2. **Zona neutra 40–60%** (`neutral_low`/`neutral_high`) → `NEUTRAL` (ficar fora)
3. **Alocação ≤ 2% da banca** (`risk_pct`, saldo recalculado) → `ALLOC_EXCEEDED`
4. **Circuit breaker: ≤ 3 stops seguidos** (`max_consecutive_losses`) → `CIRCUIT_BREAKER`
5. **Teto de prejuízo diário 6%** (`daily_loss_cap_pct`, PnL desde 00:00 UTC) → `DAILY_LOSS_CAP`

Confiança é opcional: ordens manuais (dashboard, sem sinal de IA) pulam 1–2 mas sempre
obedecem 3–5. Parâmetros ficam em `config.py` (env-overridable). Todo veredito (aprovação
e veto) é gravado em `public.risk_events` (migration `2026-05-31_risk_judge.sql`, com RLS
e Realtime). `orders.place_order` agora recebe `confidence` e delega ao juiz; `/order`
devolve 422 com `{code, message, ...}` no veto.

## Consequências
- **Positivas:** risco centralizado, determinístico e auditável; base pronta para as
  próximas camadas do funil (Polymarket/sentimento, calendário, sessões); painel de
  risco do front pode assinar `risk_events` via Realtime.
- **Negativas:** circuit breaker e teto diário dependem de `trades.closed_at`/`result`
  estarem corretos (já garantidos pelo fluxo de reconciliação). Teto diário usa
  **00:00 UTC** como corte — pode não casar com a virada de sessão local.
- **A revisitar quando:** integrar a camada de sentimento (Polymarket) — a confiança
  passará a compor bias macro + gatilho técnico, não um número solto; e ao definir
  reset do circuit breaker (hoje é manual/implícito por win).
