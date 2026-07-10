---
task: "Write Report"
order: 1
input: |
  - metrics.md: métricas de performance + significância (do Dante)
output: |
  - report.md (parcial): sumário executivo, tabela de métricas, insights, metodologia
---

# Write Report

Transforma as métricas em um relatório de backtest no padrão data-analysis: sumário executivo,
tabela com comparações, insights interpretados e metodologia. O veredito em si é a próxima task.

## Process

1. Ler `metrics.md`. Montar o sumário executivo (3 bullets) resumindo N, win rate vs. breakeven
   e expectancy — legível de forma independente.
2. Montar a tabela de métricas, cada linha com coluna de comparação (breakeven/baseline) e status.
3. Escrever 2–4 insights, cada um terminando com "isso significa…" e um nível de confiança;
   fechar com a seção Metodologia (período, fonte, N, exclusões).

## Output Format

```markdown
# Backtest: {estratégia} — {ativo} {timeframe}
## Sumário Executivo
- {bullet 1}
- {bullet 2}
- {bullet 3}
## Métricas
| Métrica | Valor | Baseline | Status |
|---|---|---|---|
| ... | ... | ... | ... |
## Insights
1. {achado}. Isso significa {implicação}. (Confiança {Alta|Média|Baixa}.)
## Metodologia
- Período / Fonte / N / Custos / Exclusões
```

## Output Example

> Referência de qualidade, não template rígido.

```markdown
# Backtest: Breakout London Open — EURUSD M5
## Sumário Executivo
- Sobre 236 trades, win rate 58,9% (IC 95%: 52,6%–65,2%) contra breakeven de 54,05%.
- Expectancy +0,089/trade, drawdown máx -11,2%.
- Margem apertada: o IC inferior encosta no breakeven — confiança Média.
## Métricas
| Métrica | Valor | Baseline | Status |
|---|---|---|---|
| Trades (N) | 236 | ≥100 | OK |
| Win rate | 58,9% | breakeven 54,05% | Acima |
| IC 95% | 52,6%–65,2% | > breakeven | Limite encosta |
| Expectancy | +0,089 | > 0 | Positiva |
## Insights
1. O IC inferior (52,6%) fica quase no breakeven. Isso significa que o edge não é robusto e
   pode sumir out-of-sample. (Confiança Média.)
## Metodologia
- Período: 2026-01 a 2026-06 (M5). Fonte: Connector IQ. N=236. Payout 85%. Exclui feriados.
```

## Quality Criteria

- [ ] Sumário executivo com 3 bullets independentes.
- [ ] Tabela com coluna de comparação e status por métrica.
- [ ] Cada insight com "isso significa…" e confiança.
- [ ] Metodologia com período, fonte, N e exclusões.

## Veto Conditions

Rejeitar e refazer se QUALQUER uma for verdadeira:
1. Algum número aparece sem interpretação ("isso significa…").
2. Falta a seção Metodologia ou o N não é citado.
