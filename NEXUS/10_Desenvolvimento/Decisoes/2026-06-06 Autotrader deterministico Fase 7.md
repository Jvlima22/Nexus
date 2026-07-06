---
tipo: decisao
status: aceita
data: 2026-06-06
projeto: NEXUS Trader
tags:
  - dev/decisao
  - trading/automacao
relacionado:
  - "[[2026-05-31 Risk Judge - juiz de risco]]"
  - "[[2026-06-01 Esboco da camada de analise e decisao]]"
---

# Decisão: Autotrader determinístico (Fase 7)

## Contexto
O funil já tem todas as camadas: coleta (candles/sentimento/calendário), interpretação
determinística ([[2026-06-01 Esboco da camada de analise e decisao]] → `indicators.analyze`),
o juiz de risco ([[2026-05-31 Risk Judge - juiz de risco]] → `risk.evaluate`) e a execução
(`orders.place_order`). A única peça que faltava era o **laço de decisão autônomo** — o que
hoje seria o par OpenClaw+IA "olhando os dados e agindo".

O fundador pediu um robô que opere sozinho **sem OpenClaw e sem IA**, mas se comportando
como eles: coletar → interpretar → comprar/vender. Como a interpretação determinística já
existe (`source="rules"`), o robô não precisa de LLM: basta um agendador que ligue
`indicators.analyze` ao `orders.place_order`. Vantagem: zero custo de token e 100%
reproduzível/auditável.

## Opções consideradas
1. **Robô no OpenClaw (GPT-5.4)**: o caminho originalmente desenhado; depende de billing e
   introduz não-determinismo. Adiado, não descartado — os dois caminhos coexistem (ambos
   passam pelo mesmo Risk Judge).
2. **Laço determinístico em Python (`autotrader.py`)** reusando `indicators` + Risk Judge. ✅
3. Reescrever a lógica de risco dentro do robô: descartado — duplicaria o juiz e quebraria a
   regra de ouro de que **nenhuma ordem pula o Risk Judge**.

## Decisão
Criado `connector/autotrader.py` (instância única `engine`) com um thread que, a cada
`AUTOTRADER_POLL_S` (60s), para cada ativo da watchlist:
1. **Coleta+interpreta:** `indicators.analyze` no timeframe primário (M5).
2. **Confluência:** se `AUTOTRADER_REQUIRE_CONFLUENCE=true`, o timeframe de confirmação
   (M15) precisa apontar a mesma direção; usa a **menor** confiança das duas (conservador).
3. **Stake = % fixo da banca** (`risk_pct`, 2%) — espelha o teto do Risk Judge, então não
   estoura a regra de alocação.
4. **Executa** via `orders.place_order(..., confidence)` — o **Risk Judge é a porta
   inegociável**: confiança baixa/neutra, fora de sessão, blackout, macro contrário,
   alocação, circuit breaker e teto diário vetam sozinhos (cada veto já auditado em
   `risk_events`). O robô **não duplica nenhuma regra de risco**.

Controle: `engine.start()` no `lifespan` do `main.py` (sobe sempre, mas o laço respeita o
flag). `GET /autotrader/status` (estado + últimas 15 decisões) e `POST /autotrader/toggle`
(kill switch em runtime). Cooldown por ativo (`AUTOTRADER_COOLDOWN_S`) evita metralhar o
mesmo sinal e re-vetar todo tick. Posições abertas seguram o ativo até expirar.

**Segurança:** `AUTOTRADER_ENABLED=false` por padrão; opera no modo da conta
(`IQ_BALANCE_MODE`, manter PRACTICE até validar).

## Atualização — varredura multi-ativo (scanner de moedas)
A pedido do fundador, o robô deixou de vigiar 1 par fixo e passou a **descobrir
dinamicamente os ativos abertos**. Decisões tomadas:
- **Universo `currencies`** (`AUTOTRADER_UNIVERSE`): só pares de DUAS moedas ISO
  (`_is_currency_pair` valida contra `_ISO_CCY`). Exclui cripto (LTCUSD), ação (NVDA),
  índice (US30) e compostos com `/`. `all` libera tudo.
- **Fonte da watchlist:** lê os ativos abertos do Supabase (`get_open_assets`, alimentado
  pelo asset-sync de 30s) — **não bate na IQ a cada ciclo** (o `GET /assets` direto leva
  15–60s). Cache com TTL `AUTOTRADER_ASSETS_REFRESH_S` (300s).
- **Filtros/perf:** `AUTOTRADER_MIN_PAYOUT` (70%) e `AUTOTRADER_MAX_ASSETS` (30, ordenado
  por payout desc) limitam o trabalho por ciclo. Confluência é lazy (só busca o M15 se o M5
  já deu direção), o que mantém o tick barato mesmo varrendo dezenas de pares.
- **Trava de risco `AUTOTRADER_MAX_OPEN` (3):** nº de posições abertas é a verdade do
  Supabase (`get_open_nexus_trades`) no início do tick; ao atingir o teto o robô para de
  abrir novas até alguma fechar. Sem isso, varrer N ativos abriria N×2% de exposição de uma
  vez — o circuit breaker/teto diário só agem após o resultado fechar.

Validado ao vivo (sáb, fora de sessão): watchlist resolveu 30 pares de moeda `-OTC`
(cripto/ação/índice corretamente excluídos), varredura completa, maioria `skip` por
confluência e o que chegou ao juiz foi `vetoed OUTSIDE_SESSION`.

## Consequências
- **Positivas:** robô autônomo sem custo de token, determinístico e auditável; reusa 90% da
  infra existente; coexiste com o caminho OpenClaw+IA (mesmo juiz); liga/desliga sem reiniciar.
- **Negativas:** a qualidade do robô = qualidade do `indicators.analyze` (maioria simples de
  votos — ingênua em tendência forte, ver limitação já anotada na Fase 2). Sem aprendizado:
  não adapta parâmetros sozinho. Controle de "posição aberta" é em memória (resetado em
  restart; o `reconcile` no boot cobre o lado dos `trades`).
- **A revisitar quando:** validar em PRACTICE e decidir REAL; afinar confluência/expiração
  por ativo; eventualmente plugar o sinal do OpenClaw como fonte alternativa de `confidence`.
