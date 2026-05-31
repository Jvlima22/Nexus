---
tipo: decisao
status: aceita
data: 2026-05-23
projeto: NEXUS Trader
tags:
  - dev/decisao
  - trading/iqoption
relacionado:
  - "[[2026-05-23 Documentacao obrigatoria no Obsidian]]"
  - "[[Tarefas Pendentes - Dados ao vivo IQ]]"
---

# Decisão: Arquitetura de dados ao vivo da IQ Option no NEXUS

## Contexto
O NEXUS já autentica na IQ Option — `src/lib/brokers/iqoption.ts` faz o POST de
login em `auth.iqoption.com/api/v2/login` e guarda o **SSID cifrado** (AES-GCM)
em `broker_connections.credentials_ciphertext`. Isso é **só sessão**: não abre
WebSocket nem traz dados. Objetivo agora: exibir no NEXUS, em tempo real,
candles, ativos disponíveis, histórico, saldo e as operações feitas pela própria
NEXUS — "como se eu estivesse dentro da IQ Option".

Premissa técnica: a API da IQ **não é oficial** e usa WS proprietário autenticado
por SSID. O browser não consegue falar esse protocolo direto (CORS + expor SSID
no cliente). Logo, em qualquer desenho existe um **Connector Python persistente**.

## Opções consideradas
1. **A — Com ponte (IQ → Connector → Supabase → NEXUS)**: Supabase como fonte
   única de verdade. Prós: histórico persistido, Realtime multi-device, front
   simples. Contras: latência extra (ruim p/ candles ao vivo), custo de escrita.
2. **B — Direto sem ponte (IQ → Connector → NEXUS via WS)**: front consome WS do
   Connector. Prós: latência mínima. Contras: sem persistência (refresh = perde
   histórico), sem multi-device, Connector vira ponto único cego.
3. **Híbrido**: cada canal no que é bom. Candles/ticks ao vivo direto via WS do
   Connector; estado durável (trades, saldo, ativos) via Supabase Realtime.

## Decisão
**Híbrido (opção 3).** Candles/ticks → WS do Connector → `lightweight-charts`.
Trades, saldo (`bankroll_history`) e ativos (`assets`) → gravados pelo Connector
no Supabase, lidos no front por Realtime.

**Hospedagem do Connector:** Render — plano **Free + keep-alive** (cron externo
batendo `GET /health` a cada ~10 min). Migração trivial p/ Render Starter (~US$7/mês,
always-on) ou Oracle Always Free quando for trading real 24/7.

**SSID p/ o Connector:** o Connector roda fora do Cloudflare Worker, então **não**
pode decifrar o ciphertext sozinho. Decisão: o Worker expõe um endpoint
server-side autenticado que devolve o SSID decifrado para o Connector (evita
espalhar a chave AES). A definir na Fase 1.

## Consequências
- Positivas:
  - Tempo real fluido nos candles + histórico durável e auditável.
  - Distinção operação NEXUS vs manual via coluna `source` em `trades`.
  - Front desacoplado: Supabase Realtime já em uso no projeto.
- Negativas / riscos (API não-oficial):
  - Pode quebrar a qualquer atualização da IQ; **viola o ToS** deles → risco de
    ban da conta. Usar ciente.
  - SSID expira → Connector precisa de reconexão + re-login automáticos.
  - Render Free dorme após ~15 min ocioso → cold start derruba o WS; keep-alive
    mitiga mas não elimina. Em operação aberta, uma reconexão é risco real.
  - Connector é ponto único de falha → exige health-check + restart.
  - Faltam tabelas no schema: `trades`, `assets`, `bankroll_history` (migration).
- A revisitar quando: for operar com dinheiro real (subir p/ always-on) ou se a
  IQ quebrar o endpoint de login/WS.

## Adaptação ao schema existente (descoberto na Fase 1)
`trades` e `bankroll_history` JÁ existiam (scaffold Lovable). Decisão: **não recriar**
— adaptar o fluxo aos nomes existentes e só adicionar colunas faltantes.
Mapa de colunas reusadas em `trades` (o Connector grava nesses nomes na Fase 4):

| Conceito | Coluna existente |
|---|---|
| símbolo | `asset` |
| direção (Call/Put) | `type` |
| PnL em $ | `result` (numeric) |
| abertura | `time` |
| id da ordem IQ | `external_id` (text) |
| estado (open/win/loss) | `status` |
| link Obsidian | `note_url` |

Colunas adicionadas: `source`, `amount`, `payout`, `option_type`, `expiration_seconds`,
`expires_at`, `closed_at`, `strategy`, `updated_at`. `assets` foi criada nova.
`bankroll_history` usa `timestamp` (não `recorded_at`) + ganhou `currency`,`account_type`,`source`.

## Fases de implementação
0. Auditoria + registro no vault (esta nota). ✅
1. Connector base: SSID + reconexão + heartbeat; REST `GET /assets`, `GET /candles`; `GET /health`.
2. Candles ao vivo: WS Connector → `lightweight-charts`.
3. Ativos: poll → tabela `assets` → lista no front (Realtime).
4. Operações NEXUS: gravar `trades` (`source='nexus'`) + UPDATE resultado; gate de risco 2% antes do buy.
5. Histórico + saldo: backfill `get_position_history`, sync `bankroll_history`.
