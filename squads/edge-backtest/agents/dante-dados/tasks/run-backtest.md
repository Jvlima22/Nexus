---
task: "Run Backtest"
order: 2
input: |
  - candles: série histórica carregada pela task fetch-candles
  - config: regra da estratégia (entrada, direção, expiração/saída)
output: |
  - trades: lista de trades simulados (timestamp, direção, entrada, saída, resultado, retorno)
---

# Run Backtest

Simula a estratégia sobre os candles em ordem cronológica estrita, sem look-ahead, gerando a
lista completa de trades com resultado e retorno considerando o payout.

## Process

1. Percorrer os candles do mais antigo ao mais recente. Em cada candle de sinal, avaliar a
   regra de entrada usando SOMENTE dados até aquele candle (nunca o fechamento futuro).
2. Ao disparar uma entrada, registrar direção (call/put ou buy/sell) e preço; determinar a
   saída pela regra (expiração de N candles ou stop/alvo) e o resultado (win/loss).
3. Calcular o retorno de cada trade: em win, `+payout` do valor arriscado; em loss, `-1`.
   Acumular a curva de equity. Montar a lista `trades`.

## Output Format

```yaml
total_trades: 236
trades:
  - ts: "2026-01-02T08:05:00Z"
    direcao: "call"
    entrada: 1.10240
    saida: 1.10281
    resultado: "win"
    retorno: 0.85
  - ts: "2026-01-02T09:15:00Z"
    direcao: "put"
    entrada: 1.10410
    saida: 1.10395
    resultado: "win"
    retorno: 0.85
equity_final: 1.21
```

## Output Example

> Referência de qualidade, não template rígido.

```yaml
total_trades: 236
janela_sinal: "08:00-10:00 GMT (London open)"
trades:
  - ts: "2026-01-02T08:05:00Z"
    direcao: "call"
    entrada: 1.10240
    saida: 1.10281
    resultado: "win"
    retorno: 0.85
  - ts: "2026-01-02T09:15:00Z"
    direcao: "put"
    entrada: 1.10410
    saida: 1.10460
    resultado: "loss"
    retorno: -1.00
look_ahead_check: "ok — entrada usa apenas candles <= candle de sinal"
equity_final: 1.21
```

## Quality Criteria

- [ ] Simulação estritamente cronológica (declara o check de look-ahead).
- [ ] Cada trade tem timestamp, direção, entrada, saída, resultado e retorno.
- [ ] Retorno usa o payout da config (win = +payout, loss = -1).

## Veto Conditions

Rejeitar e refazer se QUALQUER uma for verdadeira:
1. Qualquer trade usa dado posterior ao candle de sinal (look-ahead bias).
2. Retorno de win não bate com o payout informado na config.
