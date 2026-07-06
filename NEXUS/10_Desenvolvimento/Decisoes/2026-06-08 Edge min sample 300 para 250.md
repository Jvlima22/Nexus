---
tipo: decisao
data: 2026-06-08
tags: [autotrader, edge-gate, risco]
---

# Gate de evidência: amostra mínima 300 → 250

## Contexto
Pares com edge medido mas amostra pouco abaixo de 300 eram vetados:
`amostra insuficiente (265 < 300)` (ex.: EURCAD-op). Custava oportunidades reais.

## Decisão
`autotrader_edge_min_sample` de **300 → 250** em `connector/config.py` e
`connector/.env.example`. Sem override no `.env`, então o default vale.

## Consequências
- Pares com 250–299 sinais medidos agora entram na watchlist do autotrader.
- Trade-off: amostra menor = intervalo de confiança da taxa medida um pouco mais largo.
  `edge_min_hit` (0.57) inalterado como margem sobre breakeven.
- Requer **restart do Connector** pra aplicar.

## Como reverter
Voltar `autotrader_edge_min_sample` para 300 (config.py + .env.example), ou setar
`AUTOTRADER_EDGE_MIN_SAMPLE=300` no `.env`.
