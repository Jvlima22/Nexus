# Domain Framework — Backtest de Edge

Metodologia operacional que o squad segue, do dado bruto ao veredito.

## 1. Coleta
- Ler a config (estratégia, ativo, timeframe, período) de `backtest-config.md`.
- Puxar candles do Connector (`GET /candles`). Verificar cobertura do período e gaps.
- Registrar N de candles obtidos e qualquer buraco no histórico.

## 2. Simulação (sem look-ahead)
- Percorrer os candles em ordem cronológica.
- Em cada candle de sinal, avaliar a regra de entrada usando SÓ dados até aquele candle.
- Registrar cada trade: timestamp, direção (call/put ou buy/sell), preço de entrada,
  candle de expiração/saída, resultado (win/loss), retorno considerando o payout.

## 3. Estatística
- N de trades (tamanho de amostra). Se N < 30 → inconclusivo por construção.
- Win rate observado + intervalo de confiança 95% (aprox. normal ou Wilson).
- Breakeven pelo payout: `1/(1+payout)`.
- Expectancy por trade, considerando payout e custos.
- Drawdown máximo da curva de equity simulada.
- Veredito estatístico: há edge SÓ se o limite inferior do IC do win rate > breakeven
  E expectancy > 0.

## 4. Interpretação e veredito
- Traduzir métricas em insights (cada um com "isso significa…").
- Confiança: Alta (N grande, IC folgado, sem red flags), Média (N moderado ou margem apertada),
  Baixa (N pequeno, margem no limite, ou red flag de rigor).
- Veredito: **ATIVAR** (edge com confiança ≥ Média) ou **DESCARTAR** (sem edge / inconclusivo).

## 5. Revisão de rigor (gate)
- Antes de liberar: checar amostra, look-ahead, overfitting/p-hacking, custos, período.
- Qualquer red flag rebaixa a confiança ou reprova o relatório (volta pro redator).

## 6. Handoff
- Se ATIVAR: exportar `strategy-spec.json` com os params da estratégia pro autotrader consumir.
- Gravar relatório no output do squad E nota no vault `30_Trading/`.
- **Nenhuma ordem é executada aqui** — execução vive no stack persistente (Connector/autotrader).
