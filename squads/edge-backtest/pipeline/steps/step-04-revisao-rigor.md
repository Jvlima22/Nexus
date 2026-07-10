---
execution: inline
agent: rita-rigor
inputFile: squads/edge-backtest/output/report.md
outputFile: squads/edge-backtest/output/review.md
---

# Step 04: Revisão de Rigor

## Context Loading

Carregue antes de executar:
- `squads/edge-backtest/output/report.md` — relatório + veredito (do Valter).
- `squads/edge-backtest/output/metrics.md` — métricas subjacentes (do Dante).
- `squads/edge-backtest/pipeline/data/anti-patterns.md` — armadilhas de backtest.
- `squads/edge-backtest/pipeline/data/quality-criteria.md` — rubrica de aceitação.

## Instructions

### Process
1. Auditar o relatório contra as red flags: amostra (N≥30/≥100), look-ahead bias, overfitting/
   p-hacking, custos na expectancy, período/regime, e consistência entre `edge_flag` e o texto.
2. Se houver red flag crítico (look-ahead, ATIVAR com N<30, edge_flag inconsistente), marcar
   REPROVADO e devolver ao passo 3. Red flag leve (janela curta) → APROVADO com ressalva e
   confiança rebaixada.
3. Gravar `review.md` com o selo (APROVADO/REPROVADO), as checagens e, se reprovado, o que
   precisa mudar.

## Output Format
```markdown
# Revisão de Rigor — {estratégia} — {ativo} {timeframe}
Selo: {APROVADO|APROVADO (com ressalva)|REPROVADO}
Checagens:
- Amostra: ...
- Look-ahead: ...
- Overfitting: ...
- Custos: ...
- Consistência edge_flag ↔ veredito: ...
{Red flags / Ação, se houver}
```

## Output Example
```markdown
# Revisão de Rigor — Breakout London Open — EURUSD M5
Selo: APROVADO (com ressalva)
Checagens:
- Amostra: N=236 (≥100) ok.
- Look-ahead: ausente (entrada usa candle <= sinal) ok.
- Overfitting: 1 variante testada; sem p-hacking declarado ok.
- Custos: payout 85% na expectancy ok.
- Consistência: edge_flag=false e veredito DESCARTAR batem ok.
Ressalva: IC inferior encosta no breakeven; se reemitir como ATIVAR, exigir out-of-sample
e confiança no máximo Média.
```

## Veto Conditions
Rejeitar e refazer se QUALQUER uma for verdadeira:
1. O `review.md` não traz selo explícito (APROVADO/REPROVADO).
2. Uma red flag crítica presente no relatório passou sem ser apontada.

## Quality Criteria
- [ ] Selo explícito presente.
- [ ] Todas as checagens (amostra, look-ahead, overfitting, custos, consistência) cobertas.
- [ ] Red flag, se houver, cita item e número exatos.
- [ ] Confiança do veredito coerente com as red flags encontradas.

## Notas de Execução
- Red flags críticos (reprovação automática): look-ahead bias, ATIVAR com N<30, `edge_flag`
  inconsistente com o texto do veredito, ou win rate comparado a 50% em vez do breakeven.
- Red flags leves (aprovar com ressalva + confiança rebaixada): janela curta/regime único,
  p-hacking não fatal mas não mitigado, ausência de out-of-sample num ATIVAR.
- Ao REPROVAR, o pipeline volta ao passo 3 (`relatorio-veredito`) com os motivos — a Rita não
  reescreve o relatório, só aponta o que corrigir.
