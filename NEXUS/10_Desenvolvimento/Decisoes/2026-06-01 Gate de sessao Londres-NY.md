---
tipo: decisao
status: aceita
data: 2026-06-01
projeto: NEXUS Trader
tags:
  - dev/decisao
  - trading/risco
relacionado:
  - "[[2026-05-31 Risk Judge - juiz de risco]]"
  - "[[2026-06-01 Camada de sentimento Polymarket]]"
---

# Decisão: Gate de Sessão Londres/NY (Camada 7)

## Contexto
A Camada 7 do funil de 8 camadas do doc [[NEXUS TRADER Estratégia Definitiva e Arquitetura de Integração]]
("Timing") restringe a execução às aberturas de Londres e Nova York — janelas de maior
liquidez e movimento direcional. As Fases 3 ([[2026-05-31 Risk Judge - juiz de risco]]) e
4 ([[2026-06-01 Camada de sentimento Polymarket]]) já consolidaram o Risk Judge; esta é só
mais uma regra no mesmo funil.

## Opções consideradas
1. **Regra temporal no Risk Judge** (`OUTSIDE_SESSION`), horários em UTC, env-overridable. ✅
   Determinístico, sem API externa, 100% testável, encaixa no padrão das regras existentes.
2. Gate no front (UI desabilita botões fora do horário) — descartado: o LLM/connector
   contornaria; a barreira tem que ser no servidor.
3. Agendador externo (cron liga/desliga o connector) — descartado: complexo e perde a
   auditoria unificada em `risk_events`.

## Decisão
Nova regra **0b** em `connector/risk.py`, logo após o gate de macro e antes da confiança:
- `_in_session(hour_utc)`: True se a hora UTC cai em Londres `[8,17)` OU NY `[13,22)` →
  janela combinada efetiva **08:00–22:00 UTC**.
- Fora da janela → veto `OUTSIDE_SESSION` (auditado em `risk_events`).
- Params em `config.py` (`session_gate_enabled`, `session_london_start/end`,
  `session_ny_start/end`), todos env-overridable. `SESSION_GATE_ENABLED=false` = opera 24h.
- Vale p/ ordem manual e da IA (a barreira protege os dois). Testado: veta 03h/22h, aprova
  08h/15h; bordas `[start, end)` corretas.

## Consequências
- **Positivas:** evita operar na madrugada/baixa liquidez (asiática), de forma determinística
  e auditável; zero dependência externa (ao contrário de Polymarket/ForexFactory).
- **Negativas:** horários em **UTC fixo** — não ajustam a horário de verão (DST) de
  Londres/NY automaticamente; a "janela" é por hora cheia (não minuto). Bias é global,
  não por ativo (mesma limitação das outras camadas). Mercados 24h (cripto/OTC de fim de
  semana) também ficam restritos à janela — pode não ser o desejado p/ todos os ativos.
- **A revisitar quando:** quiser DST real (pytz/zoneinfo por sessão), granularidade de
  minuto, ou janelas por classe de ativo (forex só em sessão; cripto 24h).
