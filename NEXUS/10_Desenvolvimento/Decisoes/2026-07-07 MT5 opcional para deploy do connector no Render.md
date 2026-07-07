---
tipo: decisao
data: 2026-07-07
tags: [deploy, render, mt5, connector, infra]
---

# 2026-07-07 — MT5 opcional para o connector rodar no Render (Linux)

Retomada de [[Deploy producao - continuar amanha]]. Ao preparar o deploy do
connector no Render, apareceu um **bloqueador que a nota de ontem não pegou**.

## Contexto / problema
- Render roda **Linux**. O `MetaTrader5` (pip) é **Windows x64 only** — não tem
  wheel pra Linux. Dois pontos de falha:
  1. `pip install -r requirements.txt` **quebra o build** (pacote não instala).
  2. `main.py` fazia `import MetaTrader5 as mt5` **rígido no topo** → mesmo sem o
     pacote, o import derruba o processo no boot do uvicorn.
- Ou seja, o connector como estava **não subia no Render** de jeito nenhum.

## Opções
- **A — desacoplar MT5 (escolhida):** import opcional + marcador de plataforma no
  requirements. Render sobe **só com IQ Option**; rotas `/mt5/*` respondem 503.
- **B — VPS Windows:** hospedar numa máquina Windows com terminal MT5. Caro/complexo
  e desnecessário pro objetivo (dados ao vivo IQ).
- **C — connector só local:** sem endpoint público → sem dados ao vivo no front
  deployado. Derrota o propósito.

## Escolha: A
MT5 é **intrinsecamente local-Windows** — precisa do terminal MT5 rodando na
mesma máquina (ver [[Corretoras e OAuth]] / arquitetura híbrida). Nunca rodaria
no Render de qualquer forma. Forex real via MT5 continua exigindo o connector
numa máquina Windows; o Render cobre IQ (candles/trades/autotrader/sentimento).

## Como (arquivo → mudança)
- `connector/requirements.txt`: `MetaTrader5>=5.0.45; sys_platform == "win32"`
  (pip pula em Linux, instala no Windows).
- `connector/main.py`:
  - import em `try/except ImportError` → `mt5 = None`.
  - `TIMEFRAME_MAP = {...} if mt5 is not None else {}`.
  - bloco MT5 do `lifespan` e o `mt5.shutdown()` guardados por `if mt5 is not None`.
  - `/health` devolve `mt5_error: "MetaTrader5 indisponível neste ambiente"` quando
    a lib falta (antes chamava `mt5.last_error()` sem guarda → crash).
  - Rotas `/mt5/*` já eram protegidas por `_require_mt5()`/`_mt5_connected` → 503.
- `connector/render.yaml`: adicionado `IQ_EMAIL`/`IQ_PASSWORD` (auth recomendada;
  mais confiável que SSID no fork).

## Verificado
- Import **sem** MetaTrader5 (bloqueado via meta_path): OK, `TIMEFRAME_MAP == {}`,
  `/health` → `ok:true, mt5_connected:false`.
- Import **com** MetaTrader5 (Windows): OK, 7 timeframes carregados.

## Consequências
- Render = **IQ Option only**. MT5 (forex real) só quando o connector roda em
  Windows com terminal. Sem regressão local.

## Descobertas laterais (viram bloqueios em [[Deploy producao - continuar amanha]])
- **Deriv App ID inválido:** `33KZNJRhS5hZKTrgReR6I` (21 chars alfanuméricos) **não
  é** um app_id da Deriv — a Deriv usa **app_id numérico** (o de teste é `1089`).
  Tanto o OAuth (`oauth.deriv.com/oauth2/authorize?app_id=`) quanto o WS vão falhar.
  Corrigir: registrar app em **api.deriv.com** e usar o **ID numérico**. Ver [[Corretoras e OAuth]].
- **Código não estava no GitHub:** `origin/main` estava em `bf63f91` (connector
  antigo). O commit `9492c3c` + o WIP do connector (commitado como `7451564`
  durante esta sessão) ainda **precisam de `git push`** — senão o Render Blueprint
  deploya a versão velha.
