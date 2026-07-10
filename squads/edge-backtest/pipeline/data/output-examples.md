# Output Examples — Edge Backtest

Exemplos completos do entregável final. Referência de qualidade, não template rígido.

## Exemplo 1 — Veredito DESCARTAR (sem edge)

```
# Backtest: Estratégia "Reversão RSI<30" — EURUSD-OTC M1

## Sumário Executivo
- Sobre 412 trades simulados, o win rate foi de 51,2% (IC 95%: 46,4%–56,0%), abaixo do
  breakeven de 54,05% exigido pelo payout de 85%. Isso significa que a estratégia perde
  dinheiro no líquido apesar de "acertar mais da metade".
- A expectancy por trade foi de -R$0,038 por real arriscado — negativa e consistente com
  ruído (o IC do win rate cruza o breakeven).
- Veredito: DESCARTAR (confiança Alta).

## Métricas
| Métrica | Valor | Baseline | Status |
|---|---|---|---|
| Trades (N) | 412 | ≥100 | OK |
| Win rate | 51,2% | breakeven 54,05% | Abaixo |
| IC 95% win rate | 46,4%–56,0% | — | Cruza breakeven |
| Expectancy/trade | -0,038 | > 0 | Negativa |
| Drawdown máx | -18,4% | — | — |

## Insights
1. O win rate não supera o breakeven do payout. Isso significa que "acertar 51%" é
   irrelevante — com payout 85% seria preciso >54% só pra empatar. (Confiança Alta.)
2. O IC cruza o breakeven, então nem podemos afirmar edge positivo. Isso significa que o
   resultado é indistinguível de random walk. (Confiança Alta.)

## Metodologia
- Período: 2026-05-01 a 2026-06-30 (M1). Fonte: Connector IQ /candles. N=412 trades.
- Custos: payout 85% aplicado. Exclusões: fins de semana sem OTC.
```

## Exemplo 2 — Veredito ATIVAR (edge plausível)

```
# Backtest: Estratégia "Breakout London Open" — EURUSD M5

## Sumário Executivo
- Sobre 236 trades, win rate 58,9% (IC 95%: 52,6%–65,2%), com limite inferior acima do
  breakeven de 54,05% (payout 85%). Isso significa edge estatisticamente plausível.
- Expectancy +0,089 por real arriscado; drawdown máximo -11,2%. Isso significa retorno
  positivo com risco controlado na janela testada.
- Veredito: ATIVAR (confiança Média — N moderado, validar out-of-sample).

## Métricas
| Métrica | Valor | Baseline | Status |
|---|---|---|---|
| Trades (N) | 236 | ≥100 | OK |
| Win rate | 58,9% | breakeven 54,05% | Acima |
| IC 95% win rate | 52,6%–65,2% | — | Inferior > breakeven |
| Expectancy/trade | +0,089 | > 0 | Positiva |
| Drawdown máx | -11,2% | — | — |

## Insights
1. O limite inferior do IC (52,6%) fica acima do breakeven. Isso significa que, mesmo no
   cenário pessimista da amostra, a estratégia empata ou ganha. (Confiança Média — N=236.)
2. Edge concentrado na janela 08:00–10:00 GMT. Isso significa que a hora é parte da estratégia,
   não incidental. (Confiança Média.)

## Metodologia
- Período: 2026-01-01 a 2026-06-30 (M5). Fonte: Connector IQ /candles. N=236 trades.
- Custos: payout 85%. Exclusões: feriados. Ressalva: sem janela out-of-sample ainda.
```
