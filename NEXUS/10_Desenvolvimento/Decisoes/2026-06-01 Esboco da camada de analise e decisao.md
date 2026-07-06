---
tipo: decisao
status: rascunho
data: 2026-06-01
projeto: NEXUS Trader
tags:
  - dev/decisao
  - trading/decisao
  - arquitetura
relacionado:
  - "[[2026-05-31 Risk Judge - juiz de risco]]"
  - "[[2026-06-01 Camada de sentimento Polymarket]]"
  - "[[2026-06-01 Gate de sessao Londres-NY]]"
  - "[[2026-06-01 Calendario ForexFactory blackout]]"
---

# Esboço: Camada de Análise & Decisão (Fase 2)

> **Status: RASCUNHO p/ revisão.** Não codar antes de aprovar. Bloqueado pelo billing
> do OpenClaw (ver [[openclaw-integracao]]).

## Onde isto se encaixa
O **funil de proteção já existe e está fechado**: Risk Judge ([[2026-05-31 Risk Judge - juiz de risco]])
com regras 0 (macro), 0b (sessão), 0c (notícia) + 1–5 (confiança/2%/breaker/drawdown). Esse
funil só **valida** um sinal — ele não o **gera**. As camadas 3–6 do doc (Contexto/Supply-Demand,
AMD, Bookmap, gatilho BoS/FVG) são **análise**: produzem o `direction + confidence` que entra no
funil. Hoje isso é mock (`IndicatorsGrid` usa `mock-data`; connector só serve candles crus).

## O contrato (a peça central)
Tudo gira em torno de UM objeto — o **sinal**. Análise produz, Risk Judge consome:

```json
{
  "active": "EURUSD",
  "direction": "call",            // call | put
  "confidence": 0.78,             // 0–1, entra direto na regra 1/2 do juiz
  "timeframe": "M5",
  "rationale": "BoS de alta no M5 + FVG não mitigado; RSI saindo de sobrevenda",
  "features": { "rsi": 28.4, "ema_cross": "bull", "trend_h1": "up", "fvg": true },
  "source": "openclaw" | "rules", // quem gerou
  "ts": "2026-06-01T18:30:00Z"
}
```
Definir este JSON primeiro destrava tudo: a análise vira "qualquer coisa que preencha o
contrato" e o `POST /order` só ganha o campo `confidence` (já tem) + opcional `rationale`.

## Duas fontes de sinal (complementares, não excludentes)

### A) Indicadores determinísticos (`connector/indicators.py`) — FAZER PRIMEIRO
Calcular sobre os candles que o connector já tem (`get_candles`): RSI, EMA cross, MACD,
Bollinger, e heurísticas de estrutura (HH/HL, BoS simples, FVG). Saída: um sinal "rules"
com confidence derivada de quantos indicadores concordam (ex.: 4/6 a favor = 0.67).
- **Prós:** determinístico, testável, sem custo de API, sem depender do OpenClaw/billing.
- **Serve a 2 usos:** (1) sinal autônomo básico; (2) `features` que alimentam o prompt do LLM.
- Substitui o mock do `IndicatorsGrid` por dados reais (novo endpoint `GET /indicators`).

### B) Cérebro LLM (OpenClaw/GPT-5.4) — DEPOIS, precisa de billing
O OpenClaw já analisa read-only (skill Fase 1) e escreve no vault. Evolução p/ Fase 2:
a skill passa a **emitir o sinal JSON** (não só prosa), combinando os `features` dos
indicadores + contexto macro (`/sentiment`) + conhecimento do vault (RAG por prompt caching,
ver [[knowledge-rag-strategy]]). O LLM dá o `confidence` e o `rationale`.
- O LLM **nunca** executa direto: ele propõe o sinal → passa pelo Risk Judge → (Fase 2)
  aprovação humana → (Fase 4) autônomo.

## Fluxo proposto (Fase 2 — paper c/ aprovação humana)
```
candles (IQ) ──► indicators.py ──► features + sinal "rules"
                                        │
sentiment (/sentiment) ─────────────────┤
vault (RAG) ────────────────────────────┤
                                        ▼
                              OpenClaw/GPT ──► sinal JSON (confidence, rationale)
                                        │
                                        ▼
                              Risk Judge (risk.evaluate)  ◄── já existe
                                        │ aprovado?
                                        ▼
                         Dashboard: card "Sinal pendente" ──► [Aprovar] humano
                                        │
                                        ▼
                                  POST /order (executa em PRACTICE)
```

## Ordem de implementação sugerida (incremental, cada passo entrega valor)
1. ✅ **Contrato do sinal** — `Signal` em `src/lib/connector.ts` + dict em `indicators.analyze`.
2. ✅ **`indicators.py` + `GET /indicators`** — RSI/EMA/MACD/Bollinger/estrutura, puro Python.
3. ✅ **Sinal "rules"** — consenso por maioria; `confidence = |bull-bear|/total`. Testado.
4. ✅ **Painel de aprovação** — `SignalPanel.tsx` na rota `/mercado`: mostra o sinal real
   (direção, confidence, votos, rationale) + botão **Aprovar** → `placeOrder` com a confidence
   pelo Risk Judge. Aprovação humana obrigatória; erro de veto mostra o `code` (ex. MACRO_CONFLICT).
5. **OpenClaw emite o sinal JSON** (precisa billing) — substitui/complementa o "rules". ← PRÓXIMO
6. **Autônomo** (Fase 4): aprovação automática quando confidence alta + todos os gates ok.

## Implementado em 2026-06-01 (passos 1–3)
- `connector/indicators.py`: primitivas (ema/sma/rsi/macd/bollinger/trend_structure), votos por
  indicador, `analyze()` → contrato do sinal. Sem numpy/pandas.
- `GET /indicators?active&size&count` em `main.py` (+ `_tf_label`).
- `Signal` + `fetchIndicators()` em `src/lib/connector.ts`. `tsc --noEmit` limpo.
- **Limitação observada (a revisitar):** mistura osciladores (RSI/Bollinger = mean-reversion)
  com trend-following (EMA/MACD/trend) — em tendência muito forte o RSI satura e vota CONTRA,
  podendo zerar o consenso. Maioria simples é ingênua. Evoluir p/ pesos por regime ou separar
  "contexto" (trend) de "gatilho" (oscilador). Funciona bem em tendência suave.
- **Passo 4 (2026-06-01):** `src/components/ai/SignalPanel.tsx` montado em `/mercado` (usa o
  `active`+`size` da página). Botão Aprovar → `placeOrder({...confidence})`. `detailError` em
  `connector.ts` ajustado p/ ler `detail` objeto do Risk Judge (`{code,message}`); `OrderInput`
  ganhou `confidence`. Run real EURUSD M5: put conf 0.20 (RSI 53 neutro) — coerente. `tsc` limpo.
  Mock `IndicatorsGrid` (em `/` e `/inteligencia`) ainda existe; o SignalPanel é o caminho novo.

## Decisões em aberto (precisam de você)
- **Quem é a autoridade do sinal?** Indicadores determinísticos, LLM, ou consenso dos dois?
- **Confidence do "rules":** fórmula por consenso simples (N/total) ou ponderada por indicador?
- **Aprovação humana** obrigatória na Fase 2 (recomendado) ou já mira autônomo?
- **Timeframe(s)** de análise: M1/M5 (gatilho) + H1/H4 (contexto)?

## Consequências
- **Positivas:** começar pelos indicadores determinísticos entrega análise real JÁ (sem
  esperar billing do OpenClaw), e gera os `features` que o LLM vai usar depois. O contrato
  isola análise de execução — o Risk Judge não muda.
- **Negativas/riscos:** heurísticas de SMC (BoS/FVG/order blocks) são difíceis de acertar
  em código simples — começar com RSI/EMA/MACD (sólidos) e evoluir. O LLM custa tokens por
  sinal (mitigar com prompt caching e baixa frequência). Billing do OpenClaw é pré-requisito
  da fonte B.
