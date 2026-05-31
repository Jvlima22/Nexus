---
tipo: trade
status: fechado
ativo: AIG-OTC
direcao: PUT
estrategia: teste manual (form do /mercado)
entrada_data: 2026-05-23
entrada_preco: 78.2205
saida_data: 2026-05-23
saida_preco: 78.2835
stop:
alvo:
size: 1
pnl: -1
pnl_pct: -100
tags:
  - trading/operacao
  - trading/iqoption
relacionado:
  - "[[NEXUS Connector]]"
  - "[[2026-05-23 Arquitetura de dados ao vivo IQ Option]]"
---

# AIG-OTC PUT 2026-05-23

## Setup
Estratégia: teste manual — **primeira operação real disparada pela NEXUS** (form CALL/PUT do `/mercado`), validando a Fase 4 ponta a ponta.
Timeframe: opção binária/turbo, expiração 1 min.
Conta: PRACTICE (demo).

## Execução real
- Entrada: 78.2205 (PUT, $1) · order `13923733460` · ~20:15
- Saída: 78.2835 · ~20:16 (expiração)
- Motivo de saída: expiração da opção. Preço **subiu** contra um PUT → perda.

## Resultado
- PnL: **−$1,00** (`close_reason: loose`, payout era 185%/85%)
- Resultado recuperado do histórico da IQ (`get_position_history_v2`) e gravado na marra no Supabase.

## Lição
- A operação em si foi um teste; o valor de aprendizado foi **de engenharia**: descobrimos que o `close_trade` escrevia numa coluna `pnl` inexistente (schema reusa `result`) — corrigido, senão nenhuma ordem fecharia.
- Falta validar o ciclo automático **aberta→win/loss** em sessão (sem precisar de reconcile manual). Ver [[Tarefas Pendentes - Dados ao vivo IQ]].
