---
tipo: decisao
status: aceita
data: 2026-06-07
projeto: NEXUS Trader
tags:
  - dev/decisao
  - trading/auditoria
relacionado:
  - "[[2026-05-31 Risk Judge - juiz de risco]]"
  - "[[2026-06-01 Esboco da camada de analise e decisao]]"
---

# Decisão: Snapshot de operação (auditoria pós-trade)

## Contexto
A tabela `trades` só guarda asset/tipo/valor/resultado — nada do "porquê" do instante da
entrada. O fundador quer **clicar numa operação já feita** e ver o retrato do mercado naquele
momento: gráfico de candles com o ponto da entrada, padrão de candle identificado (martelo,
engolfo, doji…), indicadores usados (RSI/EMA/MACD/Bollinger) e suporte/resistência.

## Opções consideradas
1. **Imagem PNG capturada** (render server-side com mplfinance ou headless, salva no Supabase
   Storage): fiel a um "screenshot", mas pesado (render no connector Python), estático (sem
   zoom/crosshair) e consome storage. ❌
2. **Gráfico reconstruído de dados** ✅ — no instante da ordem salvamos os candles + indicadores
   + padrão + S/R como JSON; ao clicar, o front redesenha com `lightweight-charts` (já usado no
   `CandleChart`) e oferece "exportar PNG" (`chart.takeScreenshot`). Leve, interativo, 100%
   reproduzível e auditável.
3. **Gate de aprovação pré-ordem** (robô pausa e pede permissão antes de cada ordem): fora de
   escopo — o pedido é auditoria pós-trade; manteria o autotrader autônomo. ❌ (revisitar depois)

## Decisão
- **Ponto único de captura:** `connector/orders.py::place_order` — por onde passam TODAS as
  ordens (manuais via `/order` e do autotrader). A captura roda em **thread de fundo**
  (`_capture_snapshot`) com try/except total: é auditoria, nunca pode atrasar/derrubar a ordem.
- **Indicadores novos** (`connector/indicators.py`): `detect_patterns` (martelo, estrela cadente,
  martelo invertido, engolfo de alta/baixa, doji, marubozu — nomes PT-BR p/ a UI) e
  `support_resistance` (pivôs de swing; resistência mais próxima acima / suporte abaixo do preço).
- **Montador** (`connector/snapshot.py`): reusa `indicators.analyze` + as 2 funções novas, guarda
  os últimos 60 candles + indicadores + padrões + S/R + sinal + recorte do veredito do Risk Judge.
  Timeframe do snapshot derivado da expiração (1m→M1, 5m→M5, 15m→M15).
- **Persistência:** tabela própria `trade_snapshots` (migration `2026-06-08_trade_snapshots.sql`),
  1 linha por trade, **sem Realtime** (não infla o feed de `trades`), lida SOB DEMANDA no clique.
  RLS owner-read.
- **Front:** `useTradeSnapshot` (fetch lazy), `SnapshotChart` (candles + EMA9/21 + Bollinger +
  linhas de S/R + marcador da entrada + export PNG), `TradeDetailDialog` (reusa o `dialog` shadcn)
  com padrão/indicadores/S-R/risco. Linha de `LiveTrades` vira clicável.

## Consequências
- **Positivas:** todo trade passa a ter um retrato auditável do mercado; reusa a stack
  (lightweight-charts, dialog shadcn, padrão dos hooks Supabase); captura desacoplada (thread)
  não afeta latência nem risco. Serve igual p/ ordens manuais e do robô.
- **Negativas:** EMA/Bollinger das linhas são recomputados no cliente a partir dos candles salvos
  (não guardamos a série inteira) — fiel à fórmula do connector, mas é recomputo. Trades antigas
  (anteriores à feature) não têm snapshot → o modal mostra aviso. O snapshot fotografa o instante
  da ENTRADA; não acompanha a evolução até a expiração (poderia, numa v2, anexar o candle de saída).
- **A revisitar quando:** quiser o candle/resultado de SAÍDA no mesmo gráfico; ou um gate de
  aprovação pré-ordem reusando este mesmo detalhe (opção 3 adiada).
