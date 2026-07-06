---
tipo: decisao
status: aceita
data: 2026-06-07
projeto: NEXUS Trader
tags:
  - dev/decisao
  - frontend
  - trading/analise
relacionado:
  - "[[2026-06-07 Snapshot de operacao]]"
---

# Decisão: indicadores configuráveis no gráfico ao vivo (/mercado)

## Contexto
O `CandleChart` do `/mercado` só desenhava candles. O fundador quer ligar/desligar
indicadores sobre o gráfico (Bollinger "e entre outros"). Escopo escolhido: **pacote
completo + persistência** — sobreposições de preço (Bollinger, EMA9, EMA21, SMA) +
osciladores (RSI, MACD) num painel inferior, togláveis por chip e lembrados entre sessões.

## Opções consideradas
1. Buscar os indicadores do connector (`/indicators`): ❌ devolve só os valores escalares
   mais recentes (não a série), e adicionaria round-trips a cada tick.
2. **Calcular no cliente a partir dos candles já recebidos** ✅ — desenha a série inteira,
   recalcula de graça quando o stream atualiza o último candle, sem rede extra. A matemática
   já existia inline no `SnapshotChart` (EMA/Bollinger).
3. Osciladores em gráfico separado sincronizado: ❌ mais código (sincronizar eixo de tempo).
   Optado por **escala overlay no mesmo chart** (técnica do lightweight-charts v4).

## Decisão
- **`src/lib/indicators.ts`** (novo): `ema/sma/bollinger/rsi/macd` puros, retornando série por
  ponto (null no warm-up), espelhando `connector/indicators.py`. O `SnapshotChart` foi
  **refatorado** p/ importar daqui (DRY — fim da duplicação).
- **`useChartIndicators`** (novo hook): estado `{bollinger,ema9,ema21,sma,rsi,macd}` persistido
  em `localStorage["nexus.chart.indicators"]`. Default: Bollinger ligado, resto desligado.
- **`IndicatorBar`** (novo): chips de liga/desliga (BB·EMA9·EMA21·SMA·RSI·MACD) no header do card.
- **`CandleChart`** reescrito: mantém os candles num ref; **efeito principal** (deps active/size)
  cria chart+stream e, a cada candle do stream, recomputa as séries ativas; **efeito de
  reconciliação** (dep indicators) cria/remove séries no toggle **sem refetch**. Sobreposições
  na escala de preço; RSI/MACD em escalas overlay (`priceScaleId`) com `scaleMargins` calculadas
  p/ 0/1/2 osciladores (candles sobem, osciladores ocupam o rodapé). MACD com histograma colorido.

Períodos fixos por ora: BB 20/2, EMA 9 e 21, SMA 50, RSI 14, MACD 12/26/9.

## Consequências
- **Positivas:** indicadores ao vivo sem custo de rede; uma única fonte de verdade da matemática
  (front e snapshot batem com o connector); toggles instantâneos e lembrados; reusa a stack
  (lightweight-charts). 
- **Negativas:** recomputo da série inteira a cada tick (barato p/ ≤200 candles, mas é O(n));
  com **2 osciladores** ligados o rodapé fica dividido em faixas finas (aceitável; default é 0).
  Períodos não editáveis pela UI ainda.
- **A revisitar quando:** quiser editar períodos/cores pela UI, mais indicadores (ATR, Stoch,
  VWAP) — é só estender o `REGISTRY` no `CandleChart` e a lib; ou desenhos manuais (trendlines).
