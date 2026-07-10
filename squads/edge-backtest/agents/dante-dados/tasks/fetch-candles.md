---
task: "Fetch Candles"
order: 1
input: |
  - config: conteúdo de backtest-config.md (estratégia, ativo, timeframe, período, payout)
output: |
  - candles: série histórica de candles (OHLC + timestamp) para o ativo/timeframe/período
  - coverage: N de candles obtidos, primeiro/último timestamp, gaps detectados
---

# Fetch Candles

Puxa o histórico de candles do Connector IQ Option para o ativo, timeframe e período definidos
na config. Verifica cobertura e registra qualquer buraco no histórico antes de simular.

## Process

1. Ler `backtest-config.md` e extrair ativo, timeframe, período (início/fim) e payout.
2. Chamar o Connector `GET /candles` (base `http://127.0.0.1:8010`) com os parâmetros. Se
   responder 503 ou estourar timeout, abortar com mensagem clara "Connector/IQ indisponível".
3. Conferir cobertura: N de candles, primeiro e último timestamp, e gaps (saltos maiores que
   o timeframe). Registrar tudo em `coverage`.

## Output Format

```yaml
ativo: "EURUSD"
timeframe: "M5"
periodo: "2026-01-01 a 2026-06-30"
payout: 0.85
coverage:
  candles: 26280
  primeiro: "2026-01-01T00:00:00Z"
  ultimo: "2026-06-30T23:55:00Z"
  gaps: 3
candles: "<série carregada em memória para a próxima task>"
```

## Output Example

> Referência de qualidade, não template rígido.

```yaml
ativo: "EURUSD"
timeframe: "M5"
periodo: "2026-01-01 a 2026-06-30"
payout: 0.85
coverage:
  candles: 26280
  primeiro: "2026-01-01T00:00:00Z"
  ultimo: "2026-06-30T23:55:00Z"
  gaps: 3          # feriados/fins de semana — esperado no forex
  observacao: "cobertura íntegra; 3 gaps coincidem com finais de semana"
status: "ok"
```

## Quality Criteria

- [ ] N de candles e intervalo temporal reportados.
- [ ] Gaps detectados e explicados (ou confirmados como esperados).
- [ ] Falha do Connector tratada com mensagem clara, sem inventar dados.

## Veto Conditions

Rejeitar e refazer se QUALQUER uma for verdadeira:
1. Nenhum candle obtido (Connector indisponível) e a task reportou sucesso mesmo assim.
2. Período retornado diverge do período pedido sem justificativa registrada.
