---
tipo: exclusao
data: 2026-06-07
escopo: ideia/feature (Robô OTC v2 — item 2)
motivo: ausência de edge comprovada empiricamente (OTC = random walk)
tags:
  - exclusao
  - trading/otc
  - trading/automacao
relacionado:
  - "[[Robo OTC - To Do]]"
  - "[[2026-06-07 Gate de evidencia do autotrader Fase 8]]"
  - "[[2026-06-06 Autotrader deterministico Fase 7]]"
---

# Excluído: motor de sinal técnico "mais forte" no OTC

## O que foi removido
A ideia (item 2 do [[Robo OTC - To Do]]) de melhorar o sinal do autotrader **no OTC**
com indicadores ponderados, filtro de tendência H1, padrões de candle e janela horária,
na esperança de cruzar o breakeven. NÃO foi escrita nenhuma lógica nova em produção —
o `indicators.analyze` segue intocado. Excluída a ROTA, não código entregue.

## Quando
2026-06-07 — após o harness de pesquisa `connector/_research.py`.

## Por quê
A regra de ouro do projeto ("nada entra sem re-backtest acima do breakeven com margem")
foi aplicada ANTES de construir. O harness mediu 12 variantes de sinal contra ~15 mil
sinais reais dos 30 pares OTC abertos (exp 1 candle M5, breakeven 54,3%):

| Variante | Acerto | Amostra |
|---|---|---|
| momentum + filtro H1 | 50,3% | 4.949 |
| RSI extremo (<30/>70) | 50,2% | 3.833 |
| momentum (segue últ. candle) | 50,2% | 14.862 |
| reversão (contra últ. candle) | 49,8% | 14.862 |
| baseline (voto maioria) | 49,8% | 13.311 |
| consenso forte (conf≥0,6) | 49,7% | 3.933 |
| EMA cross puro | 49,2% | 14.915 |
| *(todas as 12)* | **47,4%–50,3%** | — |

**Nenhuma** passou do breakeven (54,3%), quanto mais da meta (57%). Por hora UTC, os
melhores horários (20h=53,8%, 23h=53,7%) ainda ficam abaixo do breakeven. Momentum e
reversão dão ~50% simétricos → o preço não tem memória. Confirma autocorrelação ≈ 0:
**o OTC da IQ é random walk** (preço sintético da corretora). Não há sinal técnico com
edge a extrair — investir num motor mais forte seria otimizar ruído.

**Item 3 (expiração adaptativa) também descartado** (`connector/_expiration.py`): medidas
as expirações 1/5/15min (sinal+resolução no TF nativo). Agregado 49–50% em todas; o
melhor par de cada expiração (USDCHF-OTC 53,6% em 1min; USDBDT-OTC 54,0% em 5min;
AUDNZD-OTC 54,2% em 15min) **fica abaixo do breakeven**. Mudar a expiração não cria edge.
Com isso o OTC está provado sem edge em **3 frentes** (gate, variantes de sinal, expiração).

## O que aprendi
- "Sinal mais forte" não vence aleatoriedade. Antes de engenharia de sinal, **medir se
  existe edge a capturar** — o `_research.py` faz isso barato e deve preceder qualquer
  nova estratégia.
- O OTC não é o mercado: é número sintético. Edge técnico, se existir, está no **forex
  real em pregão** (seg–sex), não no OTC. Pivô natural se quisermos retomar a busca.
- O gate de evidência ([[2026-06-07 Gate de evidencia do autotrader Fase 8]]) continua
  valendo: mesmo sem motor novo, ele impede o robô de operar OTC no prejuízo (0/30).

## Como reverter (se precisar)
- Harness preservado: `connector/_research.py` (rodar contra o connector ligado).
- Para retomar com forex REAL: apontar a watchlist/`_research.py` p/ pares sem `-OTC`
  em horário de pregão e re-medir; só promover variante com EDGE marcado (>57%, n≥300).
- Nada a desfazer em produção — a ideia não chegou a virar código.
