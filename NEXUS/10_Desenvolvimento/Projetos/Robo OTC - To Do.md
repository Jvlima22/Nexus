---
tipo: projeto
status: pausado
stack: [Python, FastAPI, indicators, Risk Judge]
tags:
  - dev/projeto
  - trading/automacao
  - trading/otc
criado: 2026-06-06
atualizado: 2026-06-07
relacionado:
  - "[[2026-06-06 Autotrader deterministico Fase 7]]"
  - "[[2026-06-07 Gate de evidencia do autotrader Fase 8]]"
---

# Robô OTC — To Do (concluir depois)

## Objetivo
Ter um robô que opera **dias úteis + OTC** com **vantagem estatística comprovada** —
nunca por esperança. Autonomia amarrada à evidência (backtest), não ao achismo.

## 🛑 VEREDITO FINAL DO OTC (07/06) — sem edge, provado em 3 frentes
1. **Gate de evidência** (`backtest.py`): 0/30 pares passam (melhor EURUSD-OTC 54,4%).
2. **12 variantes de sinal** (`_research.py`): faixa 47,4%–50,3%, nenhuma > breakeven.
3. **3 expirações** (`_expiration.py`): 1/5/15min agregam ~49–50%; melhor par por
   expiração (53,6%–54,2%) ainda abaixo do breakeven 54,3%.

→ O OTC da IQ é **random walk** (preço sintético). **Nenhuma estratégia técnica
automatizada tem edge ali.** Próximo passo real = **forex REAL em pregão (seg–sex)**,
reusando toda a infra. O gate fica ligado como guarda-corpo (robô não opera OTC no
prejuízo). Ver [[2026-06-07 Motor de sinal tecnico mais forte no OTC]].

## ⚠️ Ponto de partida (achado do backtest 2026-06-06)
Backtest real (9.100 sinais, 30 pares OTC, expiração 5min, payout 84% → breakeven **54,3%**):
- Estratégia atual em OTC = **~50% de acerto** → **abaixo do breakeven = perde dinheiro**.
- Confiança **não discrimina** (0.2/0.4/0.6 ≈ 50%); `conf ≥ 0.8` **nunca ocorre** (por isso `min_confidence=0.70` nunca dispara em OTC).
- Confluência M5+M15 ajuda pouco (melhor caso 51,7%, ainda perde).
- **Autocorrelação ≈ 0** → OTC da IQ é estatisticamente **random walk** (preço sintético da corretora).
- **Conclusão:** não há edge técnico no OTC com a estratégia atual. "100% de acerto" é impossível.

Scripts de apoio (reaproveitáveis): `connector/_backtest.py`, `connector/_report.py`.

## Estado atual
- [x] Autotrader determinístico (laço, Risk Judge, UI, scanner de moedas) — ver [[2026-06-06 Autotrader deterministico Fase 7]]
- [x] Backtest empírico do OTC (provou ausência de edge na v1)
- [x] Robô v2 com gate de evidência — ver [[2026-06-07 Gate de evidencia do autotrader Fase 8]]
- [x] Validação em PRACTICE — gate validado ao vivo (0/30, 0 ordens). OTC sem edge confirmado.
- [x] OTC investigado a fundo (sinal + expiração) — **descartado por evidência**.
- [ ] **Pivô p/ forex REAL em pregão** — **tudo pronto** (`AUTOTRADER_EXCLUDE_OTC=true`, robô se pivota sozinho na 2ª). Passos em [[Pivo Forex Real - runbook]].

## To Do — Robô v2 "gate de evidência"
### 1. Gate de backtest (o mais importante) — ✅ FEITO (Fase 8)
- [x] Promover `_backtest.py` a módulo (`backtest.py`) com função reutilizável por par.
- [x] Loop periódico que backtesta cada par da watchlist e calcula a taxa de acerto recente.
- [x] Persistir o resultado (tabela `asset_edge` no Supabase: symbol, hit_rate, sample, confluência, breakeven, passes_gate, updated_at).
- [x] **Pré-filtro do autotrader** (regra 0 do robô, NÃO no Risk Judge): só opera par com `hit_rate > 0.57` e amostra ≥ 300 sinais.
- [x] UI: painel mostra quais pares estão "habilitados por edge" e a taxa de cada um.
- [x] Migration `2026-06-07_asset_edge.sql` rodada + **validado ao vivo (07/06)**: 30 pares
      -OTC medidos → **0 habilitados** (melhor = EURUSD-OTC 54,4%, abaixo de 57%). 0 ordens.
      **Confirma: sem edge técnico no OTC.** Gate funciona como guarda-corpo.

### 2. Motor de sinal mais forte — ❌ DESCARTADO NO OTC por evidência (07/06)
Harness `connector/_research.py` mediu 12 variantes em ~15 mil sinais reais. **Nenhuma
passou do breakeven** (faixa 47,4%–50,3%; melhor = momentum+H1 50,3%). Por hora UTC, o
melhor (20h) = 53,8%, ainda abaixo. Momentum≈reversão≈50% → preço sem memória.
Ver [[2026-06-07 Motor de sinal tecnico mais forte no OTC]].
- [x] Indicadores ponderados / consenso forte — testado, 49,7%. Sem edge.
- [x] Filtro de tendência H1 como contexto — testado em todas as variantes. Não ajuda.
- [x] Padrões/hora do dia — testado. Nenhuma hora cruza o breakeven.
- [x] Regra de ouro **honrada**: medido antes de construir, nada promovido (era ruído).
- **Conclusão:** edge técnico, se existir, está no **forex REAL em pregão**, não no OTC.

### 3. Expiração adaptativa — ❌ DESCARTADO NO OTC por evidência (07/06)
Harness `connector/_expiration.py` mediu 1/5/15min nos 30 pares (sinal+resolução no TF
nativo). Agregado: 1min=49,7%, 5min=49,7%, 15min=49,0% — todas abaixo. **Melhor par de
cada expiração** ainda fica abaixo do breakeven: USDCHF-OTC 53,6% (1min), USDBDT-OTC
54,0% (5min), AUDNZD-OTC 54,2% (15min). Expiração não cria edge no OTC.
- [x] Backtestar expirações 1/5/15min por par — feito, nenhuma cruza o breakeven.

### 4. Segurança / REAL
- [ ] Trava: REAL só liberado para par com edge comprovado em backtest **e** em PRACTICE ao vivo.
- [ ] Período mínimo de validação em PRACTICE com taxa de acerto real acompanhada.

## Decisões-chave
- [[2026-06-06 Autotrader deterministico Fase 7]] — base (v1) já feita.
- [[2026-06-07 Gate de evidencia do autotrader Fase 8]] — gate de edge como pré-filtro,
  min 0.57 / amostra 300, loop de backtest persistindo em `asset_edge`. ✅

## Próximos passos
1. Rodar a migration `2026-06-07_asset_edge.sql` no Supabase e subir o connector com o gate.
2. Deixar 1 ciclo de edge fechar e ver quantos pares passam (`GET /autotrader/status`).
3. **Se ~nenhum passar** (esperado se OTC = random walk): partir para o item 2 (motor de
   sinal mais forte) e/ou expiração adaptativa, sempre re-backtestando acima do breakeven.
4. **Se algum passar**: validar em PRACTICE ao vivo antes de qualquer cogitação de REAL.

## Links
- Código v1: `connector/autotrader.py`, `connector/indicators.py`, `connector/risk.py`
- Gate v2: `connector/backtest.py`, `supabase/migrations/2026-06-07_asset_edge.sql`
- Análise: `connector/_backtest.py`, `connector/_report.py`
