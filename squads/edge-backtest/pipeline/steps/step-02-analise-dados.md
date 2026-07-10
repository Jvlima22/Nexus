---
execution: subagent
agent: dante-dados
inputFile: squads/edge-backtest/output/backtest-config.md
outputFile: squads/edge-backtest/output/metrics.md
model_tier: powerful
---

# Step 02: Análise de Dados

## Context Loading

Carregue antes de executar:
- `squads/edge-backtest/output/backtest-config.md` — config do backtest (estratégia, ativo, timeframe, período, payout, saída).
- `squads/edge-backtest/pipeline/data/domain-framework.md` — metodologia de coleta, simulação e estatística.
- `squads/edge-backtest/pipeline/data/anti-patterns.md` — armadilhas a evitar (look-ahead, amostra, custos).

## Instructions

### Process
1. Executar as tarefas do Dante em ordem: `fetch-candles` (puxar candles do Connector `GET /candles`
   em `http://127.0.0.1:8010`), `run-backtest` (simular cronologicamente, sem look-ahead) e
   `compute-stats` (métricas + significância).
2. Se o Connector responder 503 ou estourar timeout, abortar e escrever em `metrics.md` o status
   "Connector/IQ indisponível" — nunca inventar dados.
3. Gravar `metrics.md` com N, win rate + IC 95%, breakeven do payout, expectancy, drawdown e
   `edge_flag` (true só se IC inferior > breakeven E expectancy > 0 E N ≥ 30).

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
- fonte: Connector IQ /candles | período | N candles
```

## Output Example
```markdown
# Métricas — Breakout London Open — EURUSD M5
- N (trades): 236
- Win rate: 58,9% (IC 95%: 52,6%–65,2%)
- Breakeven (payout 85%): 54,05%
- Expectancy/trade: +0,089
- Drawdown máx: -11,2%
- edge_flag: false   # IC inferior 52,6% NÃO supera breakeven 54,05% → sem edge robusto
- confianca_estatistica: Média
- fonte: Connector IQ /candles | 2026-01-01 a 2026-06-30 | 26.280 candles
- look_ahead_check: ausente (entrada usa candle <= sinal)
```

## Veto Conditions
Rejeitar e refazer se QUALQUER uma for verdadeira:
1. `metrics.md` reporta métricas mas o Connector estava indisponível (dados fabricados).
2. `edge_flag = true` sem o IC inferior superar o breakeven.

## Quality Criteria
- [ ] N (trades e candles) presente.
- [ ] Win rate com IC 95% e comparação ao breakeven.
- [ ] Expectancy e drawdown presentes.
- [ ] `edge_flag` coerente com a regra.
- [ ] Check de look-ahead registrado.
- [ ] Fonte e período dos dados citados.

## Notas de Execução
- Base do Connector: `http://127.0.0.1:8010` (porta 8010). Guard de timeout ~9s → 503 se a IQ
  não estiver conectada; nesse caso o passo falha com status de erro, sem inventar métricas.
- Referência de calibração: OTC é random walk (gate 0/30 + 12 variantes ~50%). Um `edge_flag=true`
  em ativo OTC deve ser tratado como suspeito (provável look-ahead) antes de comemorado.
- Este passo apenas mede — nenhuma ordem é enviada em hipótese alguma.
