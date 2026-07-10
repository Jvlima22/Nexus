# Anti-Patterns — Edge Backtest

Erros que fabricam edge inexistente ou enganam a decisão. Cada um destrói a credibilidade do backtest.

## Nunca fazer

1. **Declarar edge só porque win rate > 50%.** Em binárias o breakeven é `1/(1+payout)`.
   Com payout 85%, precisa de >54,05%. Ignorar isso transforma perdedor em "vencedor".

2. **Concluir com amostra pequena.** Win rate sobre 15 trades é sorte. Sem N suficiente
   (mín. ~100 pra inferência mínima), o único veredito honesto é "inconclusivo".

3. **Look-ahead bias.** Usar o fechamento do candle de decisão (ou qualquer dado futuro) na
   regra de entrada. Fabrica um edge que não existe no ao vivo.

4. **P-hacking silencioso.** Testar 20 variantes, reportar só a melhor como se fosse a única.
   Infla o falso-positivo. Se testou N, declare e corrija (Bonferroni) ou valide out-of-sample.

5. **Ignorar custos.** Simular com payout 100%/sem spread. O edge aparente evapora quando os
   custos reais entram.

6. **Generalizar de uma janela curta.** Um mês de bull market não prova edge perene. Declarar
   o período e o regime; não vender "funciona sempre".

## Sempre fazer

1. **Reportar N e o IC do win rate.** Sem tamanho de amostra e intervalo de confiança, o número
   é opinião, não evidência.

2. **Comparar contra o breakeven do payout.** Toda métrica de acerto sai ao lado do breakeven.

3. **Preferir "inconclusivo" a um veredito otimista.** Falso ATIVAR custa dinheiro real; falso
   DESCARTAR custa uma oportunidade. Na dúvida, DESCARTAR e pedir mais dados.

4. **Deixar claro que o squad não executa ordens.** A execução é externa (Connector/autotrader);
   o squad só prova/refuta e emite a spec.
