---
tipo: projeto
status: em-andamento
data: 2026-07-07
tags: [pendente, risk-judge, dashboard, connector, mt5, iq-option]
relacionado: ["[[2026-07-07 Risk Judge unificado e Visao Geral real]]"]
---

# NEXUS — Pendências (2026-07-07)

Lista de tudo que falta depois da sessão que unificou o Risk Judge (IQ+MT5),
trouxe dados reais pra Visão Geral e consertou o connector. Ver a decisão
[[2026-07-07 Risk Judge unificado e Visao Geral real]] pro contexto completo.

## ✅ Já feito nesta sessão
- Risk Judge (`connector/risk.py`) agnóstico de corretora — MT5 real agora tem
  circuit breaker, teto diário, blackout de notícia, bias macro e um gate de
  margem novo (`MARGIN_LEVEL_LOW`, veta abaixo de 150%).
- Visão Geral (`/`) com seletor de conta (MT5 real ↔ IQ Option practice),
  saldo/P&L/operações reais, `AITerminal` mostrando vetos/aprovações de verdade.
- Connector unificado num processo só (porta **8010** — a 8000 é do terminal
  MT5), com as rotas do IQ Option de volta (`/assets`, `/candles`, `/order`,
  `/indicators`, `/sentiment`, `/autotrader/status`) e um guard de timeout
  pras chamadas que travavam quando a IQ não está conectada.
- 2 bugs de dados corrigidos: `user_id` faltando nos inserts do MT5 (trades
  nunca apareciam no Supabase) e o import do `supabase` mascarado pela pasta
  local `NEXUS/supabase/` (silenciosamente quebrado desde sempre).

## ⏳ Falta — ações diretas
### 1. Confirmar a Visão Geral no navegador
`npm run dev` está travando neste ambiente antes de imprimir qualquer log do
Vite — parece ser a "sandbox detection" do `@lovable.dev/vite-tanstack-config`
travando numa chamada de rede (mesma classe do problema de DNS bloqueado já
visto no projeto). Não mexi em `vite.config.ts`. **Rodar `npm run dev` numa
janela normal (fora deste sandbox) e conferir**: seletor de conta, stat cards,
`AITerminal` com dado real, em `/`.

### 2. Deixar o connector rodando
Hoje só sobe manual (`python main.py` dentro de `connector/`, venv `.venv`).
Se quiser ele sempre no ar (pro `/mercado` funcionar sem precisar lembrar de
subir), decidir: tarefa agendada igual ao `nexus_bot_24h.py` (VBS + Task
Scheduler) ou manual mesmo.

### 3. MCP MetaTrader desconectado
Caiu no meio da sessão e não voltou sozinho. Precisa reconectar do seu lado
(reiniciar o `metatrader-mcp-server` ou `/mcp` numa sessão interativa) —
não é algo que eu resolvo por aqui.

## 🔧 Débito técnico (identificado, não corrigido — por escolha)
- **IQ Option sem timeout na lib**: mitiguei com um guard de timeout (8s) nos
  endpoints do connector, mas a causa raiz (a lib `iqoptionapi` trava sem
  limite quando não conectada) continua lá.
- **Autotrader só fala IQ Option**: o motor sofisticado (`autotrader.py`, com
  gate de edge/backtest) nunca foi ligado ao MT5. O MT5 real roda com a
  lógica própria e mais simples do `nexus_bot_24h.py` (EMA20/50 H1). Unificar
  os dois loops de decisão é a "Fase 2" que ficou de fora — decisão de
  arquitetura, não é ajuste pequeno.

## 🧭 Decisões de negócio em aberto (não são código)
- IQ Option ainda em modo **PRACTICE** — nunca validamos login com credencial
  real. Decidir se vale ativar de verdade ou manter o foco 100% em MT5 (que
  já opera dinheiro real).
- Ligar o autotrader determinístico (`AUTOTRADER_ENABLED`, hoje `false`) —
  seja pro IQ Option seja, depois de consolidado, pro MT5.

## Comandos úteis
- Rodar connector: `cd connector && .\.venv\Scripts\python.exe main.py` (porta 8010)
- Rodar frontend: `npm run dev` (porta 5173)
- Testar Risk Judge isolado: `cd connector && .\.venv\Scripts\python.exe -c "import risk; ..."`
- Restart do bot MT5: parar `pythonw` rodando `nexus_bot_24h.py`, relançar via `iniciar_bot.vbs`
