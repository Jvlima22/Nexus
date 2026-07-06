---
tipo: ferramenta
categoria: dados/sentimento
status: ativa
tags:
  - ferramenta
  - trading/sentimento
criado: 2026-06-01
relacionado:
  - "[[2026-06-01 Camada de sentimento Polymarket]]"
---

# Polymarket (Gamma API)

## O que é
Mercado de previsões. Usado pela NEXUS como **camada de sentimento macro** (filtro
primário de direção): a probabilidade de eventos macro vira bias bullish/bearish/neutral.

## Para que uso
Alimentar a **regra 0 do Risk Judge** (`MACRO_CONFLICT`): uma ordem cuja direção contraria
o bias macro agregado é vetada no servidor. Também exibido no dashboard (`PolymarketFeed`).

## Como acessar
- URL/CLI: `https://gamma-api.polymarket.com/markets?slug=<slug>` (REST público, sem auth)
- Auth: nenhuma (leitura pública)

## Comandos / endpoints frequentes
```
# bias agregado + mercados monitorados (via Connector)
GET http://localhost:8000/sentiment

# mercado cru da Gamma
GET https://gamma-api.polymarket.com/markets?slug=us-recession-in-2026
```
Config no Connector (`.env`): `POLYMARKET_SLUGS` (CSV de slugs), `POLYMARKET_POLL_S`,
`POLYMARKET_BULL_THRESHOLD` / `BEAR_THRESHOLD`, `POLYMARKET_GATE_ENABLED`.

## Pegadinhas
- `outcomes` e `outcomePrices` vêm como **string JSON** (não lista) — `polymarket.py` faz parse.
- Sem `POLYMARKET_SLUGS` a camada fica **inerte** (fail-open intencional, não bloqueia nada).
- Bias é **global** (maioria simples dos mercados), não casa slug↔ativo ainda.
- Falha de rede/leitura = neutral: indisponibilidade nunca trava a operação sozinha.

## Alternativas consideradas
- CLOB API + chave: granular demais p/ leitura de sentimento; descartada por ora.
