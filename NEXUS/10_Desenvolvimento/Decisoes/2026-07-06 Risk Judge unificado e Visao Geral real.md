---
tipo: decisao
status: aceita
data: 2026-07-06
projeto: NEXUS Trader
tags:
  - dev/decisao
  - risk-judge
  - mt5
  - iq-option
relacionado: ["[[Pendencias - 2026-07-07]]"]
---

# Decisão: unificar o Risk Judge entre IQ Option e MT5, e ligar a Visão Geral a dados reais

## Contexto
O Risk Judge (`connector/risk.py`) — circuit breaker, teto diário, blackout de
notícia, bias macro, alocação — só protegia o fluxo IQ Option. Quem de fato
opera dinheiro real hoje é `nexus_bot_24h.py` (MT5), um script à parte com
regras próprias e mais simples, sem passar pelo juiz. Ao inspecionar a conta
real via MCP, achei margin level em **103%** (quase sem folga) — o position
sizing por stop-loss não considera quanto de margem cada lote consome.

Também descobri que o `connector/main.py` tinha virado uma bridge exclusiva
do MT5 (commit `9492c3c`), derrubando as rotas antigas do IQ Option
(`/assets`, `/candles`, `/order`, etc.) que o frontend (`src/lib/connector.ts`)
ainda chama — e que a porta 8000 padrão já é usada pelo terminal MT5 nesta
máquina, então o serviço nunca conseguia subir.

## Opções consideradas
1. **Construir uma abstração `TradingClient` completa** (interface comum pros
   dois brokers) — descartada: `risk.py` só dependia da IQ por uma única
   chamada (`client.get_balance()`); abstrair tudo seria over-engineering.
2. **Manter dois Risk Judges separados** (um por corretora) — descartada:
   duplicaria a lógica de circuit breaker/teto diário/gates, e o objetivo era
   justamente parar de duplicar.
3. **Tornar `risk.evaluate()` agnóstico de corretora** (receber `balance`,
   `source`, `margin_level` do chamador) + **um único connector** servindo
   IQ e MT5 lado a lado, cada um com seu próprio histórico via `source`. ✅

## Decisão
Opção 3. `risk.evaluate()` deixou de importar o cliente IQ Option
internamente; quem chama (IQ `orders.py`, MT5 `nexus_bot_24h.py`/`main.py`)
fornece `balance`/`source`/`margin_level`. Nova regra `MARGIN_LEVEL_LOW`
(veta abaixo de 150%). `supabase_sync.py` ganhou parâmetro `source` em
`recent_results`/`today_realized_pnl`/`get_open_nexus_trades`, então
circuit breaker e teto diário são **por corretora**, não globais.

O `connector/main.py` voltou a servir os dois: IQ Option (restaurado do
commit anterior + `/indicators`, `/sentiment`, `/autotrader/status` que
nunca tinham sido implementados, só chamados pelo frontend) e MT5, na porta
**8010** (a 8000 ficou reservada pro terminal MT5). Registrado como tarefa
agendada do Windows (`NEXUS_Connector`), mesmo padrão do `nexus_bot_24h.py`.

A Visão Geral (`/`) ganhou seletor de conta (MT5 real ↔ IQ Option practice)
via `validateSearch` do TanStack Router, e o painel `AITerminal` — que
antes era um roteiro fake (`terminalFeed` em `mock-data.ts`) — passou a
mostrar `risk_events` + `trades` reais, filtrados pela conta escolhida.

## Bugs encontrados no caminho (não eram o objetivo, mas bloqueavam tudo)
- `nexus_bot_24h.py` gravava trades sem `user_id` (coluna `NOT NULL`) —
  todo insert falhava silenciosamente; dashboard nunca via os trades MT5.
- `from supabase import create_client` vinha falhando **desde sempre** nesse
  script: a pasta `NEXUS/supabase/` (migrations SQL) na raiz do projeto é
  interpretada como *namespace package* pelo Python, então `import supabase`
  "funcionava" sem nunca ser o pacote de verdade — e o auto-instalador do
  topo do script só testava `import supabase` (sucesso falso), nunca
  instalando o pacote real. Corrigido: probe explícito de `create_client` +
  `pip install --force-reinstall supabase` no Python do sistema.
- `iqoptionapi` não tem timeout — `client.connect()` direto no `lifespan`
  travava o boot inteiro do serviço (MT5 incluso) quando a rede/DNS até a IQ
  está bloqueada. Movido pra thread em background; endpoints de leitura
  (`/assets`, `/candles`, `/indicators`, `/debug/positions`) ganharam um
  guard de timeout (8s) que devolve 503 em vez de pendurar a requisição.

## Consequências
- Positivas: MT5 real agora tem a mesma auditoria/segurança que o IQ Option
  já tinha; dashboard mostra dado de verdade; `/mercado` volta a funcionar
  (endpoints IQ existem de novo, na porta certa).
- Negativas: `bankroll_history.source` agora carrega dois significados
  diferentes (`'tick'`/null = método de captura do IQ; `'nexus_mt5'` = origem
  MT5) — funciona, mas não é limpo. Autotrader determinístico (`autotrader.py`,
  com gate de edge/backtest) continua só falando IQ Option — o MT5 real opera
  com a lógica própria e mais simples do `nexus_bot_24h.py`.
- A revisitar quando: decidir se vale consolidar os dois loops de decisão
  (MT5 e IQ) num autotrader único — ver [[Pendencias - 2026-07-07]].
