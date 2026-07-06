---
tipo: decisao
status: aceita
data: 2026-06-07
projeto: NEXUS Trader
tags:
  - dev/decisao
  - dev/bugfix
  - trading/execucao
relacionado:
  - "[[2026-06-07 Snapshot de operacao]]"
  - "[[Dados ao vivo IQ Option]]"
---

# Decisão: tracking de resultado via histórico (fix do "trade fica aberto" em OTC)

## Contexto (bug observado)
Ordem manual executada (EURUSD-OTC PUT, PRACTICE) ficou **eternamente "aberta"** no painel —
nunca virou win/loss. Diagnóstico ao vivo: o acompanhamento (`orders._track`) usava
`iq_client.wait_result` → `check_win_v3` (binário) / `check_win_v4`, e esses **penduram em
OTC**: a chamada não retornou em 30s+ e ainda derrubou a conexão. Com o tracker travado, o
`close_trade` nunca era chamado. (Pegadinha conhecida do iqoptionapi com OTC — ver
[[Dados ao vivo IQ Option]].)

## Opções consideradas
1. Continuar com `check_win_v3/v4` (bloqueante): ❌ pendura em OTC, trava o tracker.
2. **Resolver pelo HISTÓRICO de posições** (`result_from_history`) após a expiração: ✅
   confiável tanto em OTC quanto no real (foi o que resolveu as 2 ordens travadas:
   `result_from_history` retornou `('loss', -1.0)`).
3. Só depender do `/reconcile` no boot: ❌ resolve órfãs, mas o trade ficaria aberto até o
   próximo restart — péssima UX.

## Decisão
Reescrito `orders._track(order_id, option_type, expiration_min)`:
- **não usa mais** `wait_result`/`check_win` (pendura em OTC);
- espera a expiração (`expiration_min*60 + 8s`) e então consulta o resultado pelo
  **histórico** (`result_from_history`), com tentativas a cada 15s numa janela de ~6 min;
- para `digital`, tenta antes o `check_result` rápido não-bloqueante; depois cai no histórico;
- ao resolver, dá `close_trade` (open → win/loss/tie). Se não resolver na janela, loga e
  deixa o `/reconcile` pegar depois (rede de segurança mantida).

`wait_result` segue no `iq_client` (não removido) mas deixou de ser usado pelo tracker.

## Consequências
- **Positivas:** trades OTC passam a fechar sozinhos e mostrar win/loss; o tracker não trava
  mais nem derruba a conexão; reusa `result_from_history` (já usado pelo reconcile).
- **Negativas:** o histórico leva ~15–60s pra publicar o resultado → o fechamento aparece
  alguns segundos/minutos após a expiração (aceitável; antes nunca aparecia). 2 fetches de
  histórico por tentativa em binário (turbo+binary).
- **Aplica-se às próximas ordens após reiniciar o connector** (sem hot-reload). As 2 ordens
  já travadas foram fechadas manualmente pelo histórico (ambas loss −$1).
