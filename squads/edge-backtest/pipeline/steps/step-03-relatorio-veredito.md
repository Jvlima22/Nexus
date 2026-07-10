---
execution: inline
agent: valter-veredito
inputFile: squads/edge-backtest/output/metrics.md
outputFile: squads/edge-backtest/output/report.md
---

# Step 03: Relatório + Veredito

## Context Loading

Carregue antes de executar:
- `squads/edge-backtest/output/metrics.md` — métricas + `edge_flag` (do Dante).
- `squads/edge-backtest/pipeline/data/quality-criteria.md` — rubrica de aceitação do relatório.
- `squads/edge-backtest/pipeline/data/output-examples.md` — exemplos de relatório ATIVAR e DESCARTAR.

## Instructions

### Process
1. Executar `write-report`: montar sumário executivo (3 bullets), tabela de métricas com coluna
   de comparação, insights com "isso significa…" + confiança, e metodologia.
2. Executar `emit-verdict`: aplicar a regra (ATIVAR só se `edge_flag=true` e sem red flag) e
   anexar a seção Veredito com confiança; incluir a linha "execução é externa ao squad".
3. Se o veredito for ATIVAR, gerar `strategy-spec.json` no output. Se DESCARTAR, não gerar e
   registrar o motivo no relatório.

## Output Format
```markdown
# Backtest: {estratégia} — {ativo} {timeframe}
## Sumário Executivo
- ... (3 bullets)
## Métricas
| Métrica | Valor | Baseline | Status |
## Insights
1. {achado}. Isso significa {implicação}. (Confiança {nível}.)
## Metodologia
- Período / Fonte / N / Custos / Exclusões
## Veredito
**{ATIVAR|DESCARTAR}** — confiança {nível}. Motivo: {...}. Execução: externa ao squad.
```

## Output Example
```markdown
# Backtest: Reversão RSI<30 — EURUSD-OTC M1
## Sumário Executivo
- 412 trades, win rate 51,2% (IC 95%: 46,4%–56,0%) contra breakeven 54,05%.
- Expectancy -0,038/trade; indistinguível de random walk.
- Veredito DESCARTAR (confiança Alta).
## Métricas
| Métrica | Valor | Baseline | Status |
|---|---|---|---|
| Trades (N) | 412 | ≥100 | OK |
| Win rate | 51,2% | breakeven 54,05% | Abaixo |
| Expectancy | -0,038 | > 0 | Negativa |
## Insights
1. Win rate abaixo do breakeven. Isso significa que perde no líquido apesar de acertar 51%. (Confiança Alta.)
## Metodologia
- Período 2026-05 a 2026-06 (M1). Fonte Connector IQ. N=412. Payout 85%.
## Veredito
**DESCARTAR** — confiança Alta. Motivo: sem edge; IC cruza o breakeven. Execução: externa ao squad.
```

## Veto Conditions
Rejeitar e refazer se QUALQUER uma for verdadeira:
1. Veredito ATIVAR sem `edge_flag=true` no metrics.md.
2. Algum número sem "isso significa…" ou falta a Metodologia.

## Quality Criteria
- [ ] Sumário executivo com 3 bullets independentes.
- [ ] Veredito explícito com confiança.
- [ ] `strategy-spec.json` gerado se e somente se ATIVAR.
- [ ] Metodologia presente.
