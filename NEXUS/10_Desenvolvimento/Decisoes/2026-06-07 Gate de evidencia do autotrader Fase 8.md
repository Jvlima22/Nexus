---
tipo: decisao
status: aceita
data: 2026-06-07
projeto: NEXUS Trader
tags:
  - dev/decisao
  - trading/automacao
  - trading/otc
relacionado:
  - "[[2026-06-06 Autotrader deterministico Fase 7]]"
  - "[[2026-05-31 Risk Judge - juiz de risco]]"
  - "[[Robo OTC - To Do]]"
---

# Decisão: Gate de evidência do autotrader (Fase 8 — Robô OTC v2)

## Contexto
O backtest empírico de 06/06 (9.100 sinais, 30 pares OTC, payout 84% → breakeven
**54,3%**) provou que a estratégia atual em OTC rende **~50% de acerto** — abaixo do
breakeven, perde dinheiro. Conclusão registrada em [[Robo OTC - To Do]]: **sem edge
técnico no OTC com a v1**. Logo, deixar o robô operar todos os pares varridos é operar
no prejuízo por construção.

A v2 inverte a lógica: o robô só pode operar um par cujo **edge esteja medido e acima
do breakeven com margem** — nunca por esperança. "Mede antes de apostar."

## Opções consideradas
1. **Melhorar o sinal primeiro** (indicadores ponderados, H1, padrões de candle):
   descartado como ponto de partida — se o OTC é random walk (autocorrelação ≈ 0,
   como o backtest indicou), nenhum motor técnico acha edge; seria esforço cego.
2. **Gate de evidência primeiro** (medir o edge par a par e só operar quem passa). ✅
   Honra o achado do backtest: se nenhum par passar, o robô corretamente não opera.
3. Edge como **regra do Risk Judge**: descartado. O edge é específico da estratégia
   determinística do autotrader, não um risco universal. Uma ordem **manual** do
   dashboard não deve ser barrada por "a estratégia de regras não tem edge neste par".
   Por isso o gate é **pré-filtro do autotrader**, e o Risk Judge segue só com regras
   universais (sessão, alocação, breaker, teto, macro, notícia).

## Decisão
- **`connector/backtest.py`** (módulo, promovido do script exploratório `_backtest.py`):
  `backtest_pair(symbol)` roda in-process (puxa candles via `client.get_candles`, sem
  HTTP) e devolve o acerto medido em dois recortes — **cru (M5)** e **com confluência
  M5+M15** (= o que o robô de fato opera). `passes_gate(edge)` e `gate_metric(edge)`
  centralizam a escolha da métrica conforme a config (default: recorte com confluência).
- **Persistência:** tabela `asset_edge` (migration `2026-06-07_asset_edge.sql`) com
  hit_rate, sample, recorte de confluência, breakeven e `passes_gate`. RLS owner-read +
  Realtime. `supabase_sync.upsert_asset_edge` / `get_asset_edge`.
- **Loop de edge** (`_edge_loop`): thread independente no autotrader que, a cada
  `AUTOTRADER_EDGE_REFRESH_S` (6h), backtesta a watchlist, persiste e atualiza o cache
  em memória. Roda **mesmo com o robô desligado** (medir é read-only) e o último edge é
  **carregado do Supabase no boot**, então o gate já vale logo após um restart.
- **Gate no `_evaluate` (regra 0 do robô):** antes de gastar trabalho com o sinal, se
  `edge_gate_enabled` e o par não passa (`hit ≤ min` OU `sample < min`), **skip** com
  razão auditável ("edge X% ≤ mínimo", "amostra insuficiente", "sem edge medido ainda").
- **UI** (`AutotraderPanel`): chip `gate N/M com edge` + grade "Edge medido (backtest)"
  com a taxa por par (verde = habilitado).

Parâmetros (`config.py` / `.env`): `AUTOTRADER_EDGE_GATE_ENABLED=true`,
`EDGE_MIN_HIT=0.57` (breakeven 54,3% + margem), `EDGE_MIN_SAMPLE=300`,
`EDGE_USE_CONFLUENCE=true`, `EDGE_REFRESH_S=21600`.

## Consequências
- **Positivas:** o robô deixa de operar no escuro — só toca par com vantagem
  estatística comprovada; se nenhum passar, não opera (resultado correto). Determinístico
  e auditável; reusa a infra da Fase 7; o Risk Judge fica intocado. UI mostra o edge real.
- **Negativas:** backtest é pesado (puxa ~700+240 candles por par) → cadência de 6h e
  warmup de 30s no boot; nas primeiras execuções pós-restart sem dado persistido, tudo é
  `skip` até o 1º backtest fechar (seguro, mas o robô fica inerte). O edge usa candles
  históricos da IQ — se o OTC for de fato random walk, **espera-se que nenhum par passe**,
  e isso é a resposta honesta, não um bug.
- **A revisitar quando:** se nenhum par passar o gate por muitos ciclos, partir para o
  motor de sinal mais forte (item 2 do [[Robo OTC - To Do]]) e/ou expiração adaptativa,
  sempre re-backtestando acima do breakeven antes de habilitar. Migrar o controle de
  "posição aberta" e o edge p/ fora da memória se o robô virar multi-instância.
