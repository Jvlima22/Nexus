---
type: checkpoint
outputFile: squads/edge-backtest/output/backtest-config.md
---

# Step 01: Configurar Backtest

Squad **Edge Backtest** (NEXUS Trader) — provar ou refutar o edge de uma estratégia.

Antes de rodar a análise, preciso da configuração do backtest. Colete do usuário:

1. **Estratégia** — a regra de entrada (ex: "Breakout do range 08:00–10:00 GMT", "Reversão quando RSI<30").
2. **Ativo** — par/símbolo (ex: EURUSD, EURUSD-OTC).
3. **Timeframe** — M1, M5, M15…
4. **Período** — datas de início e fim (ex: 2026-01-01 a 2026-06-30).
5. **Payout** — payout da corretora pro ativo (ex: 0.85). Necessário pro breakeven.
6. **Expiração/saída** — como o trade fecha (ex: expiração de 5 candles, stop/alvo).

Grave as respostas em `backtest-config.md` no formato abaixo.

## Output Format
```markdown
# Backtest Config
- estrategia: {texto da regra}
- ativo: {símbolo}
- timeframe: {M1|M5|M15|...}
- periodo: {início} a {fim}
- payout: {0.xx}
- saida: {regra de expiração/saída}
```

## Output Example
```markdown
# Backtest Config
- estrategia: Breakout do range das 08:00–10:00 GMT (London open)
- ativo: EURUSD
- timeframe: M5
- periodo: 2026-01-01 a 2026-06-30
- payout: 0.85
- saida: expiração de 3 candles
```
