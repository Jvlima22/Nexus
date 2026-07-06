---
tipo: projeto
status: pronto-para-executar
stack: [Python, FastAPI, indicators, Risk Judge, backtest]
tags:
  - dev/projeto
  - trading/automacao
  - trading/forex
criado: 2026-06-07
atualizado: 2026-06-07
relacionado:
  - "[[Robo OTC - To Do]]"
  - "[[2026-06-07 Motor de sinal tecnico mais forte no OTC]]"
  - "[[2026-06-07 Gate de evidencia do autotrader Fase 8]]"
---

# Pivô p/ Forex REAL — Runbook (executar na segunda, mercado aberto)

OTC encerrado (random walk provado em 3 frentes — ver [[Robo OTC - To Do]]). A partir
de agora o robô mira **forex real em pregão**. **Tudo já está pronto**: a config exclui
OTC por padrão, então quando o mercado abrir o sistema se pivota sozinho. Este runbook é
só pra disparar a medição manualmente e ler o resultado.

## O que já ficou pronto (07/06, fim de semana)
- `AUTOTRADER_EXCLUDE_OTC=true` (default no `config.py`): a watchlist passa a ignorar
  pares `-OTC`. Em fim de semana (só OTC aberto) a watchlist fica **vazia** → o robô não
  opera nada (correto). Na segunda, com forex real aberto, ela se preenche sozinha.
- O **loop de edge** (a cada 6h) vai backtestar os pares reais automaticamente e
  popular `asset_edge`; o **gate** habilita sozinho qualquer par que cruzar 57% (n≥300).
- Harnesses de medição manual prontos: `_research.py`, `_expiration.py`, `_backtest.py`.

## Passos (segunda, após Londres abrir ~08:00 UTC = ~05:00 BRT)
1. **Reiniciar o connector** p/ carregar `AUTOTRADER_EXCLUDE_OTC` (e qualquer env nova):
   ```
   npm start            # sobe os 3, ou:
   powershell -File start.ps1 -SkipOpenClaw   # só web + connector
   ```
2. **Conferir a watchlist** (deve listar pares REAIS, sem `-OTC`):
   ```
   curl http://localhost:8000/autotrader/status
   ```
   Olhar `exclude_otc:true`, `watchlist_count` > 0 e `assets` sem sufixo `-OTC`.
3. **Medir o edge dos pares reais** (manual, não precisa esperar o loop de 6h):
   ```
   connector/.venv/Scripts/python.exe connector/_research.py      # variantes de sinal
   connector/.venv/Scripts/python.exe connector/_expiration.py    # 1/5/15min
   ```
   (rodam contra o connector ligado; usam a watchlist já filtrada)

## Critério de decisão (a regra de ouro continua valendo)
- **Algum par cruza 57% com amostra ≥ 300?**
  - SIM → o gate habilita esse par sozinho; validar em PRACTICE ao vivo antes de cogitar
    REAL. Registrar decisão + nota de estratégia no vault.
  - NÃO → o problema não é o mercado (real ≠ sorteio), é a **estratégia de regras**. Aí
    sim faz sentido evoluir o `indicators.analyze` (pesos, contexto H1, etc.) e
    **re-medir** — só promover o que passar o gate. Nada entra sem backtest > breakeven.

## Notas
- Manter `AUTOTRADER_ENABLED=false` e `IQ_BALANCE_MODE=PRACTICE` até ver edge real +
  validação ao vivo. O kill switch (`POST /autotrader/toggle`) liga/desliga sem reiniciar.
- Forex real tem sessão: o Risk Judge já veta fora de Londres/NY (`OUTSIDE_SESSION`) e em
  blackout de notícia (ForexFactory) — o robô só vai operar nas janelas líquidas.
- Para reativar OTC algum dia (não recomendado): `AUTOTRADER_EXCLUDE_OTC=false`.
