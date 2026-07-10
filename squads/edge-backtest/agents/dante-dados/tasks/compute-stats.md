---
task: "Compute Stats"
order: 3
input: |
  - trades: lista de trades simulados (da task run-backtest)
  - payout: payout da corretora (da config)
output: |
  - metrics.md: métricas de performance + teste de significância + flag de edge
---

# Compute Stats

Calcula as métricas de performance sobre os trades e o teste de significância que decide se há
edge: o limite inferior do IC 95% do win rate precisa superar o breakeven do payout.

## Process

1. Calcular N (total de trades), win rate observado e o IC 95% (aprox. normal ou Wilson).
2. Calcular o breakeven do payout (`1/(1+payout)`), a expectancy por trade
   (`win_rate*payout - (1-win_rate)`) e o drawdown máximo da curva de equity.
3. Determinar `edge_flag`: verdadeiro só se (limite inferior do IC > breakeven) E (expectancy > 0)
   E (N >= 30). Escrever tudo em `metrics.md`.

## Output Format

```markdown
# Métricas — {estratégia} — {ativo} {timeframe}
- N (trades): {n}
- Win rate: {wr}% (IC 95%: {lo}%–{hi}%)
- Breakeven (payout {p}%): {be}%
- Expectancy/trade: {exp}
- Drawdown máx: {dd}%
- edge_flag: {true|false}
- confianca_estatistica: {Alta|Média|Baixa}
```

## Output Example

> Referência de qualidade, não template rígido.

```markdown
# Métricas — Breakout London Open — EURUSD M5
- N (trades): 236
- Win rate: 58,9% (IC 95%: 52,6%–65,2%)
- Breakeven (payout 85%): 54,05%
- Expectancy/trade: +0,089
- Drawdown máx: -11,2%
- edge_flag: true          # limite inferior 52,6% < 54,05%? NÃO — 52,6% < 54,05% → revisar
- confianca_estatistica: Média
- nota: limite inferior (52,6%) fica ABAIXO do breakeven (54,05%); edge_flag deve refletir isso
```

## Quality Criteria

- [ ] N, win rate, IC 95%, breakeven, expectancy e drawdown presentes.
- [ ] `edge_flag` derivado corretamente da regra (IC inferior > breakeven E expectancy > 0 E N>=30).
- [ ] Confiança estatística atribuída (Alta/Média/Baixa).

## Veto Conditions

Rejeitar e refazer se QUALQUER uma for verdadeira:
1. `edge_flag = true` mas o limite inferior do IC não supera o breakeven.
2. Win rate reportado sem IC, ou métricas sem N.
