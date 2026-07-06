---
tipo: decisao
status: aceita
data: 2026-06-01
projeto: NEXUS Trader
tags:
  - dev/decisao
  - trading/sentimento
relacionado:
  - "[[2026-05-31 Risk Judge - juiz de risco]]"
---

# Decisão: Camada de Sentimento Macro (Polymarket) — Fase 4

## Contexto
O documento [[NEXUS TRADER Estratégia Definitiva e Arquitetura de Integração]] define a
Polymarket como o **filtro primário de direção** (Camada 1 do funil de 8 camadas): se a
probabilidade real de um evento macro não sustenta o trade, a operação é descartada. A
Fase 3 ([[2026-05-31 Risk Judge - juiz de risco]]) já criou o juiz inegociável; faltava
ligar o sentimento macro a ele.

## Opções consideradas
**Como o sentimento age sobre a ordem:**
1. **Gate no Risk Judge (regra 0)** — bias macro que contradiz a direção da ordem = VETO
   `MACRO_CONFLICT`, determinístico e auditado em `risk_events`. ✅
2. Só compor a `confidence` que o OpenClaw/GPT envia — mais flexível, menos rígido.
3. Só exibir no dashboard — informativo, não bloqueia.

**Fonte de dados:**
1. **Gamma API pública** (`gamma-api.polymarket.com/markets`) — sem auth, lê mercados,
   volume e `outcomePrices`. Suficiente p/ bias macro. ✅
2. CLOB API + chave — granular demais p/ leitura de sentimento agora.
3. Mock primeiro.

## Decisão
Escolhidas **1 + 1**: gate no Risk Judge com dados da Gamma pública.

- `connector/polymarket.py`: lê um mercado por slug, extrai prob do "Yes" (campos
  `outcomes`/`outcomePrices` vêm como string JSON na Gamma) e classifica o bias
  (`≥0.65` bullish, `≤0.35` bearish, entre = neutral).
- `connector/sync.py` `start_sentiment_sync()`: loop de poll (default 120s) por slug →
  upsert em `market_sentiment`. No-op se `POLYMARKET_SLUGS` vazio.
- `connector/risk.py` **regra 0** (`MACRO_CONFLICT`): `_macro_bias()` agrega a maioria
  não-neutra; PUT contra bullish ou CALL contra bearish = veto. Empate/sem dados/falha
  de leitura = neutral (NÃO bloqueia — indisponibilidade nunca trava a operação sozinha).
- Migration `2026-06-01_market_sentiment.sql` (tabela + RLS + Realtime).
- Front: `useSentiment.ts` (realtime + bias agregado), `PolymarketFeed.tsx` montado na
  rota `/mercado`, endpoint `GET /sentiment` no Connector.
- Params em `config.py` (thresholds, poll, `polymarket_gate_enabled`).

## Consequências
- **Positivas:** direção macro entra no funil de forma determinística e auditável; base
  pronta p/ as próximas camadas (calendário, sessões). Gate desligável por env sem mexer
  no código (`POLYMARKET_GATE_ENABLED=false`).
- **Negativas:** o bias é agregado simples por maioria — não pondera por volume nem casa
  slug↔ativo (um bias macro global vale p/ todas as ordens). A Gamma pode mudar o shape
  do payload. Sem slugs configurados, a camada fica inerte (fail-open, intencional).
- **A revisitar quando:** mapear sentimento por ativo/classe (forex vs cripto), ponderar
  por volume/liquidez, e quando a `confidence` do OpenClaw passar a compor bias macro +
  gatilho técnico (em vez de número solto).
