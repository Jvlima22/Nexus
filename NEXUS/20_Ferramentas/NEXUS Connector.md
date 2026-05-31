---
tipo: ferramenta
categoria: integracao
status: ativa
tags:
  - ferramenta
  - trading/iqoption
criado: 2026-05-23
relacionado:
  - "[[2026-05-23 Arquitetura de dados ao vivo IQ Option]]"
---

# NEXUS Connector

## O que é
Serviço Python (FastAPI) persistente que faz a ponte entre a IQ Option (API
não-oficial, WS por SSID) e o NEXUS. Vive em `connector/` no repo.

## Para que uso
Trazer candles, ativos, saldo, histórico e operações da IQ em tempo real para o
NEXUS — base de toda a arquitetura Híbrida. Candles ao vivo via WS direto; estado
durável gravado no Supabase.

## Como acessar
- CLI local: `cd connector && python main.py` → `http://localhost:8000`
- Deploy: Render (Blueprint `connector/render.yaml`), plano Free + keep-alive
- Auth: SSID da IQ — em dev no `.env` (`IQ_SSID`); em prod via endpoint do Worker
  (`SSID_ENDPOINT`/`SSID_TOKEN`). SSID cifrado mora em `broker_connections`.

## Comandos / endpoints frequentes
```
GET /health                       -> {ok, iq_connected}   (alvo do keep-alive)
GET /assets                       -> ativos + is_open + payout
GET /candles?active=EURUSD&size=60&count=100
```

## Pegadinhas
- `iqoptionapi` é fork não-oficial; método de anexar SSID varia por versão
  (`[VERIFICAR-FORK]` em `iq_client.connect()`). Confirmar no 1º run com SSID real.
- Render Free dorme após ~15 min → cold start derruba o WS; watchdog reconecta.
- SSID expira → reconexão + re-login automáticos (watchdog a cada 30s).
- Viola ToS da IQ → risco de ban. Ponto único de falha → precisa health-check.

## Alternativas consideradas
- Opção A (tudo via Supabase) e B (tudo direto): descartadas em favor do Híbrido.
  Ver [[2026-05-23 Arquitetura de dados ao vivo IQ Option]].
- Hospedagem: Railway/Fly/Oracle — Render Free escolhido p/ começar sem custo.
