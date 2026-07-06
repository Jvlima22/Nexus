---
tipo: decisao
status: aceita
data: 2026-06-08
projeto: NEXUS Trader
tags:
  - dev/decisao
  - connector
  - trading/analise
  - trading/risco
relacionado:
  - "[[2026-06-07 Indicadores no grafico ao vivo]]"
  - "[[2026-06-07 Gate de evidencia do autotrader Fase 8]]"
  - "[[2026-06-06 Autotrader deterministico Fase 7]]"
---

# Decisão: detecção de regime de mercado como gate do autotrader

## Contexto
Origem: carrossel da **Claude Cowork** (Instagram, post DZQMSSFE0eS) com 12 prompts-template
para usar o Claude como "quant de hedge fund". Cruzando os 12 com a arquitetura atual, três
encaixavam sem inventar módulo novo: #4 (detecção de regime), #2+#9 (backtest + Monte Carlo,
já cobertos pela Fase 8) e #8 (geração de setup, já no SignalPanel). Implementado aqui o **#4**,
que era o buraco entre `indicators.py` (calcula indicadores) e `risk.py`/autotrader (decide):
não havia leitura de **em que ambiente** o sinal está sendo gerado.

O autotrader (Fase 7) é **seguidor de tendência por confluência** (M5+M15 concordando). Esse tipo
de lógica sangra em **chop lateral de baixa volatilidade** — gera sinais que viram pó. Faltava
um filtro que reconhecesse o regime e pulasse esses ambientes.

## Opções consideradas
1. Regra nova no Risk Judge (`risk.py`): ❌ o Risk Judge é o juiz **universal** (vale p/ ordem
   manual também). Regime é específico do robô seguidor de tendência — não deve vetar ordem
   manual de quem opera reversão de propósito.
2. **Função determinística em `indicators.py` + gate suave no autotrader** ✅ — reusa os candles e
   primitivas (EMA, estrutura HH/HL) que já existem; vira mais um campo do contrato do sinal;
   o robô consulta `regime.suitable_for_trend` antes de operar. Espelha a separação que já
   adotamos no gate de evidência (pré-filtro do robô ≠ regra do Risk Judge).
3. Chamar o Claude com o prompt #4 a cada tick: ❌ custo/latência e não-determinismo num laço de
   60s. A stack do robô é determinística por decisão da Fase 7.

## Decisão
- **`indicators.atr()`** (novo): Average True Range (TR clássico, média simples). Puro Python.
- **`indicators.detect_regime(candles, lookback=50)`** (novo): classifica
  - **tendência** — `alta` / `baixa` / `lateral` (estrutura HH/HL via `trend_structure` +
    sinal da separação EMA9/EMA21 normalizada pelo preço; precisa dos dois concordarem p/ não ser lateral);
  - **volatilidade** — `alta` / `normal` / `baixa` (TR% das últimas 5 vs **mediana** do lookback,
    razão >1.3 / <0.7);
  - **volume** — `alto` / `normal` / `baixo` / `indisponível` (a IQ às vezes manda volume 0 → degrada limpo);
  - **`atr_pct`**, **`recommend`** (estratégia que funciona no ambiente) e **`avoid`** (o que evitar);
  - **`suitable_for_trend`** (booleano-resumo): `True` só quando tendência ∈ {alta,baixa} **e**
    volatilidade ∈ {normal,alta}. É o que o robô lê.
- **`analyze()`** passa a devolver `regime` no contrato do sinal (top-level) → aparece de graça em
  `/indicators` e em qualquer consumidor do sinal.
- **`/regime`** (novo endpoint em `main.py`): tendência/vol/volume/recomendação on-demand p/ um ativo.
- **Autotrader `_evaluate`**: novo passo **2b** após o sinal primário — se
  `AUTOTRADER_REGIME_GATE_ENABLED` e `not regime.suitable_for_trend`, registra `skip` auditável
  (`regime desfavorável (lateral/vol baixa): …`) e não opera. Fica **antes** da confluência (barato).
- **Config**: `autotrader_regime_gate_enabled: bool = True` (+ `.env.example`).
- **UI** (`src/lib/connector.ts` + `SignalPanel.tsx`): tipo `Regime` no contrato `Signal`; chip
  "Regime" no SignalPanel logo após a barra de confiança — borda verde quando `suitable_for_trend`,
  âmbar quando não; badges tend./vol/volume/ATR% + linha de `recommend`. Typecheck limpo.

Smoke (candles sintéticos): tendência de alta → `suitable_for_trend=True`; chop lateral →
`lateral`, `suitable_for_trend=False` (gate pula). `analyze().regime` carrega os 7 campos.

## Consequências
- **Positivas:** o robô deixa de operar onde a lógica de tendência não tem chance; `regime` fica
  disponível pra UI (futuro selo "ambiente" no SignalPanel/gráfico) sem rede extra; determinístico,
  sem custo de token; separação limpa robô-vs-Risk-Judge preservada.
- **Negativas:** thresholds (1.3/0.7 de vol, EMA 9/21, lookback 50) são fixos e calibrados no olho —
  podem precisar de ajuste por ativo/timeframe; o gate reduz frequência de trades (menos sinais,
  mais seletivo) — esperado, mas é menos amostra pro gate de evidência.
- **A revisitar quando:** calibrar thresholds (1.3/0.7 vol, EMA 9/21, lookback) com dados reais;
  ou medir se o gate melhora o win-rate medido (`asset_edge`) o suficiente p/ justificar a queda de
  frequência. (Expor na UI ✅ feito — chip no SignalPanel.) Outros prompts do carrossel
  (#5 multifatorial, #7 portfólio, #1 geração livre)
  ficam fora por ora — pressupõem portfólio multi-ativo e estratégia gerada por IA, contra o desenho
  determinístico single-asset atual (Fase 9+ se for pra portfólio de forex).
