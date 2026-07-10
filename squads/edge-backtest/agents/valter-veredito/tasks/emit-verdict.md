---
task: "Emit Verdict"
order: 2
input: |
  - report.md (parcial): relatório sem veredito (da task write-report)
  - metrics.md: métricas + edge_flag (do Dante)
output: |
  - report.md (final): relatório com veredito ATIVAR/DESCARTAR + confiança
  - strategy-spec.json: params da estratégia (SOMENTE se veredito = ATIVAR)
---

# Emit Verdict

Fecha o relatório com o veredito inequívoco e, quando ATIVAR, exporta o `strategy-spec.json`
que o autotrader consumirá. Nenhuma ordem é executada aqui.

## Process

1. Aplicar a regra: **ATIVAR** só se `edge_flag = true` (IC inferior > breakeven E expectancy > 0
   E N ≥ 30) e sem red flag de rigor; caso contrário **DESCARTAR** (inclui inconclusivo).
2. Anexar a seção Veredito ao `report.md` com o resultado e o nível de confiança, mais uma
   linha lembrando que a execução é externa ao squad.
3. Se ATIVAR, gerar `strategy-spec.json` com os params. Se DESCARTAR, NÃO gerar o arquivo e
   registrar o porquê no relatório.

## Output Format

```markdown
## Veredito
**{ATIVAR|DESCARTAR}** — confiança {Alta|Média|Baixa}.
Motivo: {1-2 frases baseadas nas métricas}.
Execução: fora do escopo deste squad (Connector/autotrader).
```
strategy-spec.json (só se ATIVAR):
```json
{ "estrategia": "...", "ativo": "...", "timeframe": "...", "regra_entrada": "...",
  "expiracao": "...", "payout_assumido": 0.85, "edge": { "win_rate": 0.0, "ic95": [0,0],
  "expectancy": 0.0, "n": 0 }, "gerado_em": "YYYY-MM-DD", "status": "candidato" }
```

## Output Example

> Referência de qualidade, não template rígido.

```markdown
## Veredito
**DESCARTAR** — confiança Alta.
Motivo: win rate 51,2% (IC 95%: 46,4%–56,0%) não supera o breakeven de 54,05%; expectancy
negativa (-0,038). Indistinguível de random walk.
Execução: fora do escopo deste squad (Connector/autotrader).
strategy-spec.json: não gerado (veredito DESCARTAR).
```

## Quality Criteria

- [ ] Veredito explícito ATIVAR ou DESCARTAR com confiança.
- [ ] `strategy-spec.json` gerado se e somente se ATIVAR.
- [ ] Linha deixando claro que a execução é externa ao squad.

## Veto Conditions

Rejeitar e refazer se QUALQUER uma for verdadeira:
1. Veredito ATIVAR sem `edge_flag = true` nas métricas.
2. `strategy-spec.json` gerado num veredito DESCARTAR (ou ausente num ATIVAR).
