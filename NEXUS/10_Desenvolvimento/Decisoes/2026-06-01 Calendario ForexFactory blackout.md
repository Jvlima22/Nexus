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
  - "[[2026-06-01 Gate de sessao Londres-NY]]"
---

# Decisão: Calendário ForexFactory — blackout de notícias (Camada 2)

## Contexto
A Camada 2 do funil ([[NEXUS TRADER Estratégia Definitiva e Arquitetura de Integração]])
identifica janelas de alta volatilidade (notícias de alto impacto) para **suspender
operações** minutos antes/depois. Risco real: spreads explodem e a direção fica imprevisível
em CPI, NFP, decisões de juros.

## Opções consideradas
**Fonte de dados:**
1. **Feed JSON faireconomy** (`nfs.faireconomy.media/ff_calendar_thisweek.json`) — semi-oficial,
   sem auth, estável. ✅ Validado: 114 eventos/semana, campo `impact` (High/Medium/Low/Holiday).
2. Scraping do HTML do ForexFactory — frágil, quebra com mudança de layout, timezone chato.
3. Mock primeiro.

**Onde guardar:** cache em memória no connector (não Supabase) — o gate consulta a cada
ordem, não precisa de persistência nem RLS; recarrega o feed a cada 30 min.

## Decisão
- `connector/forexfactory.py`: `fetch_events()` lê o feed, normaliza (`event_id`, `title`,
  `country`, `impact`, `event_time` ISO UTC-aware). `set_cache`/`get_cache` (thread-safe).
  `active_blackout(now)` = evento de impacto configurado cuja janela
  `[event - before, event + after]` cobre agora.
- `sync.py` `start_calendar_sync()`: loop de poll (30 min) → atualiza o cache.
- `risk.py` **regra 0c** (`NEWS_BLACKOUT`), após sessão e antes da confiança: se há blackout
  ativo, veta (auditado em `risk_events`).
- `main.py` `GET /calendar`: eventos em cache + blackout ativo.
- Params em `config.py` (`calendar_gate_enabled`, `calendar_poll_s`,
  `calendar_blackout_before_min`/`after_min`, `calendar_impacts`=CSV). DoH ligado no host
  por precaução (DNS BR). Testado: pega High em ±15min, ignora Low, libera fora da janela,
  borda inclusiva; feed real parseia 13 High/semana.

## Consequências
- **Positivas:** evita operar no caos de notícias de forma determinística e auditável;
  fonte estável sem scraping; janela e impactos configuráveis por env.
- **Negativas:** blackout é **global** (qualquer evento High pausa tudo) — não filtra por
  país/par afetado (um CPI dos EUA pausa até trade de par sem USD). Feed cobre só a
  **semana corrente** (`thisweek`). Cache em memória zera no restart (repovoa no boot).
- **A revisitar quando:** filtrar evento por moeda do ativo operado (CPI USD só pausa pares
  com USD); cobrir além da semana; expor o blackout no dashboard.
