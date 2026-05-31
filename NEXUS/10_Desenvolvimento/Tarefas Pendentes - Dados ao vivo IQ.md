---
tipo: tarefas
status: aberto
data: 2026-05-23
tags:
  - dev/tarefas
  - trading/iqoption
relacionado:
  - "[[2026-05-23 Arquitetura de dados ao vivo IQ Option]]"
  - "[[NEXUS Connector]]"
---

# Tarefas Pendentes — Dados ao vivo IQ Option

Fases 0–5 entregues (ver [[2026-05-23 Arquitetura de dados ao vivo IQ Option]]). O que
falta para fechar produção e robustez está abaixo. Marque com `x` ao concluir.

## 🚀 Produção
- [ ] **Endpoint SSID/credenciais no Worker** — Worker entrega credenciais decifradas ao Connector (fecha o passo 3 da Fase 1). Hoje usa email+senha no `.env` local.
- [ ] **Deploy do Connector no Render** — subir via `connector/render.yaml` (Free) + configurar secrets no painel.
- [ ] **Cron de keep-alive** — cron-job.org batendo `GET /health` a cada ~10 min (evita o sleep do Render Free).
- [ ] **Orquestrador/OpenClaw → `POST /order`** — agente chamando o mesmo endpoint do form, com o gate de risco 2% no caminho.
- [ ] **Render Starter / always-on** — migrar quando for operar dinheiro real 24/7 (sem gaps de WS). Mesmo container.

## 🧪 Validações pendentes
- [ ] Confirmar visualmente o ciclo **aberta → win/loss** de uma ordem no `/mercado` (Realtime).
- [ ] **Backfill de histórico** — rodar `POST /backfill` e conferir `imported > 0`. Se vier 0, ajustar o parse de `get_position_history` ao shape real da lib.
- [ ] Sincronizar `bun.lock` com `bun install` (o `lightweight-charts` foi instalado via npm `--no-save`).

## 🛡️ Robustez / UX
- [ ] Bloquear no front o envio de ordem quando o ativo estiver **fechado** (`is_open=false`).
- [x] Tratar reconexão do Connector no meio de uma ordem aberta → **reconciliação** (`reconcile_open_trades` no startup + `POST /reconcile`) fecha ordens órfãs consultando o resultado na IQ.
- [ ] (Opcional) Persistir candles **M1 fechados** agregados, se quiser histórico de gráfico durável.
- [ ] (Opcional) Refcount no WS de candles para suportar múltiplos clientes no mesmo par.

## ⚠️ Riscos a monitorar
- [ ] API não-oficial da IQ pode quebrar a qualquer atualização; uso **viola o ToS** (risco de ban). Reavaliar periodicamente.
- [ ] SSID/sessão expira → depender do watchdog de reconexão + re-login.
