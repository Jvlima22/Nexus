---
tipo: ferramenta
categoria: dados/calendario
status: ativa
tags:
  - ferramenta
  - trading/noticias
criado: 2026-06-01
relacionado:
  - "[[2026-06-01 Calendario ForexFactory blackout]]"
---

# ForexFactory (feed faireconomy)

## O que é
Calendário econômico (notícias macro com horário e nível de impacto). Usado pela NEXUS
como **camada de blackout**: pausa ordens em torno de eventos de alto impacto.

## Para que uso
Alimentar a **regra 0c do Risk Judge** (`NEWS_BLACKOUT`): se a hora atual cai em ±15min de
um evento High, a ordem é vetada no servidor.

## Como acessar
- URL: `https://nfs.faireconomy.media/ff_calendar_thisweek.json` (feed semi-oficial, sem auth)
- Auth: nenhuma

## Comandos / endpoints frequentes
```
# eventos em cache + blackout ativo (via Connector)
GET http://localhost:8000/calendar
```
Config no `.env`: `CALENDAR_GATE_ENABLED`, `CALENDAR_POLL_S`,
`CALENDAR_BLACKOUT_BEFORE_MIN`/`AFTER_MIN`, `CALENDAR_IMPACTS` (CSV: `High` ou `High,Medium`).

## Pegadinhas
- Campo `date` vem **com offset** (ex: `2026-06-02T14:30:00-04:00`) — `forexfactory.py` normaliza p/ UTC-aware.
- Cobre só a **semana corrente** (`thisweek`).
- Blackout é **global** (qualquer High pausa tudo, não filtra por país/par).
- Cache em memória (não Supabase); zera no restart, repovoa no boot. DoH ligado por precaução.

## Alternativas consideradas
- Scraping do HTML do ForexFactory: frágil, descartado.
