# Research Brief — Edge Backtest

Domínio: backtesting de estratégias de trading e aferição de edge estatístico. Fundamentos
embutidos (sem web search, por economia de tokens — reforçar depois se necessário).

## Frameworks e métodos centrais

1. **Tamanho de amostra manda.** Win rate sobre poucos trades é ruído. Regra prática: abaixo
   de ~30 trades, nada é conclusivo; para inferência mínima buscar 100–200+ trades. Sempre
   reportar N.

2. **Edge real vs. sorte (o teste que importa).** Não basta win rate > 50%. Em opções
   binárias o breakeven depende do payout:
   - `win_rate_breakeven = 1 / (1 + payout)`
   - Ex.: payout 85% → breakeven = 1/1.85 = **54,05%**. Um win rate de 52% com payout 85% é
     **perdedor**, não vencedor.
   Comparar o win rate observado contra o breakeven usando **intervalo de confiança / teste
   binomial**: o limite inferior do IC (95%) precisa ficar acima do breakeven pra falar em edge.

3. **Expectancy por trade** = `win_rate * ganho_medio - (1-win_rate) * perda_media`. É a
   métrica-rainha: positivo e estatisticamente significante = edge.

4. **Look-ahead bias.** A decisão de entrada só pode usar dados disponíveis ATÉ o candle de
   sinal (nunca o fechamento futuro). Bug clássico que fabrica edge inexistente.

5. **Overfitting / p-hacking.** Testar N variantes e escolher a melhor infla o falso-positivo.
   Mitigar com correção de múltiplos testes (Bonferroni) ou reservar janela out-of-sample.

6. **Custos.** Spread, slippage e payout < 100% corroem o edge aparente. Simular com os custos
   reais da corretora.

## Vocabulário do domínio
expectancy, win rate, payoff/payout, breakeven, drawdown máximo, tamanho de amostra,
intervalo de confiança, significância estatística, look-ahead bias, out-of-sample, random walk.

## Referência interna (NEXUS)
OTC já provado **random walk** (gate 0/30 + 12 variantes ~50%). Meta atual: validar edge no
**forex real**, não no OTC. Serve de calibração: se uma estratégia OTC "passar", desconfiar de bug.

## Fonte de dados
Connector IQ Option — `GET /candles` (FastAPI, porta 8010). Requer IQ conectada; sem conexão
devolve 503 (guard de timeout ~9s).
