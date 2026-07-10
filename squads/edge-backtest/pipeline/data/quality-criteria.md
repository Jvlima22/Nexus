# Quality Criteria — Edge Backtest

Rubrica de aceitação. Um relatório só é liberado se cumprir TODOS os itens.

## Estatística
- [ ] N (número de trades) reportado explicitamente. Se N < 30, o relatório declara "inconclusivo".
- [ ] Win rate acompanhado do intervalo de confiança 95%.
- [ ] Breakeven do payout calculado e comparado ao win rate (não basta > 50%).
- [ ] Expectancy por trade calculada com payout e custos.
- [ ] Drawdown máximo reportado.
- [ ] Veredito de edge baseado em: limite inferior do IC > breakeven E expectancy > 0.

## Rigor
- [ ] Confirmado que a entrada não usa dados futuros (sem look-ahead bias).
- [ ] Se várias variantes foram testadas, o risco de p-hacking é declarado e mitigado.
- [ ] Custos (payout < 100%, spread/slippage) considerados na expectancy.
- [ ] Período e regime de mercado do teste declarados (evitar generalizar de janela curta).

## Apresentação (padrão data-analysis)
- [ ] Sumário executivo com 3 bullets, legível de forma independente.
- [ ] Toda métrica tem coluna de comparação (breakeven/baseline).
- [ ] Todo insight termina com "isso significa…".
- [ ] Nível de confiança (Alta/Média/Baixa) em cada achado e no veredito.
- [ ] Metodologia ao final: período, fonte, tamanho de amostra, exclusões.
- [ ] Zero qualificadores vagos ("bom", "significativo", "forte") sem número.
- [ ] Veredito final explícito: **ATIVAR** ou **DESCARTAR**.

## Handoff
- [ ] Se ATIVAR, `strategy-spec.json` gerado com params completos e válidos.
- [ ] Nenhuma ordem executada; relatório deixa claro que execução é externa ao squad.
