# NEXUS Connector

Serviço Python persistente que faz a ponte entre **IQ Option** (API não-oficial,
WS por SSID) **e MetaTrader 5** (forex real) e o NEXUS — um único processo, uma
única porta (**8010**; a 8000 é do próprio terminal MT5 na máquina). Arquitetura
**Híbrida**: serve candles ao vivo direto via WS e grava estado durável
(assets/trades/saldo) no Supabase.

> ⚠️ A API da IQ Option **não é oficial**, pode quebrar a qualquer atualização e
> seu uso **viola o ToS** (risco de ban da conta). Use ciente.

## Status por fase
- [x] **Fase 1** — base: login SSID, reconexão + heartbeat, `GET /health` `/assets` `/candles`.
- [x] **Fase 2** — WS `/ws/candles` (candle em formação) + gráfico `lightweight-charts` no front (rota `/mercado`).
- [x] **Fase 3** — poll de ativos → upsert em `assets` (Supabase) + warm-up digital (silencia o thread). Front lista via Realtime. Exige `SUPABASE_*` + `NEXUS_USER_ID`.
- [x] **Fase 4** — `POST /order` com gate de risco 2% → `iq.buy` → grava `trades` (`source='nexus'`, open) → thread acompanha resultado e dá UPDATE (win/loss). Front: form de ordem + tabela ao vivo no `/mercado`.
- [x] **Fase 5** — sync de saldo (`get_balance`/15s → `bankroll_history`) no dashboard; `POST /backfill` importa histórico (`get_position_history` → `trades` source='manual'); `/historico` lê trades reais via Realtime.

## Endpoints

**IQ Option:**
```
GET  /health
GET  /assets
GET  /candles?active=&size=&count=
GET  /indicators?active=&size=&count=     sinal determinístico (RSI/EMA/MACD/Bollinger)
GET  /sentiment                           bias macro agregado (Polymarket)
POST /order      body: {active, direction(call|put), amount, expiration(min), option_type}
GET  /autotrader/status
POST /autotrader/toggle   body: {enabled}
POST /backfill   importa operações passadas (rodar uma vez)
POST /reconcile  fecha ordens 'open' órfãs (consulta resultado na IQ)
GET  /vault/tree           lista todos os .md do vault Obsidian
GET  /vault/file?path=     markdown cru de uma nota (sandbox no vault)
WS   /ws/candles?active=&size=
```

**MetaTrader 5:** ver `/mt5/*` no topo de `main.py` (session, account, candles,
positions, analyze, signal, order, close, stats, summary, `/ws/mt5/candles`).

## Rodar local (Windows / PowerShell)
Requer **git** instalado (a lib da IQ vem do GitHub). Use o python do venv direto
(evita o erro de ExecutionPolicy do Activate.ps1):
```powershell
cd connector
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env        # preencha IQ_EMAIL + IQ_PASSWORD
.\.venv\Scripts\python.exe main.py
```
Teste: `GET http://localhost:8010/health` → `{"ok":true,"iq_connected":true,"mt5_connected":true}`.

## Autenticação
- **Recomendado:** `IQ_EMAIL` + `IQ_PASSWORD` no `.env` — a lib loga e gerencia o
  SSID internamente (mais confiável neste fork).
- **Fallback SSID:** `IQ_SSID` (dev) ou `SSID_ENDPOINT`+`SSID_TOKEN` via Worker (prod).
  Best-effort — o fork não injeta SSID de forma estável.

## Deploy no Render (Free + keep-alive)
1. New > Blueprint, aponte para este repo (`render.yaml` já configura `rootDir: connector`).
2. Defina os secrets no painel (`IQ_SSID` ou `SSID_ENDPOINT`/`SSID_TOKEN`, `SUPABASE_*`, `NEXUS_USER_ID`, `ALLOWED_ORIGINS`).
3. **Keep-alive:** o Free dorme após ~15 min ocioso. Crie um cron grátis em
   [cron-job.org](https://cron-job.org) batendo `GET https://<seu-app>.onrender.com/health`
   a cada 10 min. Não é 100% — cold starts ainda derrubam o WS, e o watchdog reconecta.
4. Para trading real 24/7 sem gaps, troque `plan: free` por `starter` (~US$7/mês).

## Verificado
- Instalação no Python 3.13 OK (`iqoptionapi-7.1.1` via git + `websocket-client==0.56.0`).
- Import de `iqoptionapi.stable_api` e de `main` OK no 3.13.

## Pendente (precisa de credenciais reais)
- `connect()` de fato logar na IQ — testar com `IQ_EMAIL`/`IQ_PASSWORD` no 1º run.
