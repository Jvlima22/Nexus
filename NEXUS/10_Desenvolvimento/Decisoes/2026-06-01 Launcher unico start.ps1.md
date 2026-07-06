---
tipo: decisao
status: aceita
data: 2026-06-01
projeto: NEXUS Trader
tags:
  - dev/decisao
  - dev/tooling
relacionado:
  - "[[OpenClaw]]"
---

# Decisão: launcher único `start.ps1` (`npm start`)

## Contexto
Rodar a plataforma completa exigia abrir 3 terminais e lembrar 3 comandos diferentes:
- **Frontend** (Vite/TanStack/CF Worker) — `npm run dev` → `:8080`
- **Connector** (FastAPI/uvicorn, ponte IQ Option) — `.venv\Scripts\python.exe main.py` → `:8000`
- **OpenClaw** (gateway WS, orquestrador) — `openclaw gateway` → `:18789`

Pedido: subir tudo com **um comando só**, incluindo o OpenClaw.

## Opções consideradas
1. **`concurrently` (devDep) + script `dev:all`**: exige `npm install` de dep nova e
   mata processos-filho de forma menos limpa no Windows (deixa órfãos node/python).
2. **`start.ps1` nativo (PowerShell) + script `npm start`**: zero dependência nova,
   nativo Windows, output prefixado/colorido por serviço, `Ctrl+C` derruba a árvore
   inteira via `taskkill /T /F`. ✅

## Decisão
Criado `start.ps1` na raiz. Lança os 3 serviços como `System.Diagnostics.Process`
(`UseShellExecute=$false`, stdout/stderr redirecionados e prefixados via
`Register-ObjectEvent`). `npm`/`openclaw` (.cmd) são chamados por `cmd.exe /c`; o
python pelo exe do venv direto. Loop principal vigia `HasExited` — se **qualquer**
serviço cai, o `finally` chama `Stop-All` e encerra os demais (mata a árvore por PID).
Flags `-SkipOpenClaw` / `-SkipConnector` para subir subconjuntos. Script `"start"`
adicionado ao `package.json` → **`npm start`**.

Escrito em **ASCII puro** de propósito: PowerShell 5.1 lê `.ps1` UTF-8-sem-BOM como
ANSI e acentos/travessões quebram o parser (aprendido na 1ª tentativa).

Subir o gateway do OpenClaw **não** liga o loop autônomo de trading — o `HEARTBEAT.md`
(skill `nexus_trader`) continua desativado; é só o daemon de orquestração no ar.

## Consequências
- **Positivas:** onboarding trivial (`npm start`); sem órfãos no Ctrl+C; logs unificados.
- **Negativas / a saber:**
  - Pré-requisitos continuam manuais: `npm install`, `connector/.venv`, `.env`/`.dev.vars`
    e `connector/.env` precisam existir (o script avisa, não cria).
  - O canal **WhatsApp** do OpenClaw está deslogado (401) e fica em auto-restart no log —
    ruído inofensivo; resolver com `openclaw channels login` se for usar.
  - Específico de Windows/PowerShell. Para Linux/CI seria preciso um `start.sh` equivalente.
- **A revisitar quando:** definir o cérebro final do OpenClaw (GPT-5.4 → Claude) ou
  quando o heartbeat de trading for ativado — aí o launcher vira o ponto de partida do loop.
