# Squad Memory: Edge Backtest

## Estilo de Escrita

## Design Visual

## Estrutura de Conteúdo

## Proibições Explícitas
- Nunca executar ordens (POST /order) — o squad é análise pura.
- Nunca declarar edge sem comparar contra o breakeven do payout.

## Técnico (específico do squad)
- Fonte de dados: Connector IQ Option, GET /candles, porta 8010. Requer IQ conectada (senão 503).
- Referência de calibração: OTC = random walk (gate 0/30 + 12 variantes ~50%).
