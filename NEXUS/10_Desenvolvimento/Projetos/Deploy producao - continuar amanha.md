---
tipo: projeto
status: em-andamento
data: 2026-07-06
<<<<<<< HEAD
tags: [deploy, cloudflare, render, deriv, infra, pendente]
---

# Deploy de produção — continuar amanhã (2026-07-07)

Retomada do deploy iniciado em 2026-07-06. Ver decisão [[2026-07-06 Deploy do frontend na Cloudflare Workers]].

## ✅ Já feito hoje
- Frontend no ar: **https://nexustrader.nexustrader.workers.dev** (Cloudflare Workers, HTTP 200).
- Subdomínio workers.dev `nexustrader` registrado.
- Vercel Authentication desligada (era o "pede login").
- Secrets no Worker: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `ANTHROPIC_API_KEY`, `DERIV_APP_ID`.
- Deriv: app web "Nexus Trader" criado. **App ID = `33KZNJRhS5hZKTrgReR6I`** (formato alfanumérico novo). Redirect: `https://nexustrader.nexustrader.workers.dev/api/connections/deriv/callback`.
- `VITE_DERIV_APP_ID` assado no bundle (build-time).

## ⏳ Falta (pra dados ao vivo)
### 1. Deployar o connector Python no Render → obter `VITE_CONNECTOR_URL`
- **render.com → New → Blueprint** → apontar repo `Jvlima22/Nexus`. O `connector/render.yaml` configura tudo (rootDir `connector`).
- Preencher secrets no painel Render: `IQ_SSID`, `SSID_ENDPOINT`, `SSID_TOKEN`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `NEXUS_USER_ID`, `POLYMARKET_SLUGS`.
- `ALLOWED_ORIGINS` = `https://nexustrader.nexustrader.workers.dev`
- Render dá URL tipo `https://nexus-connector.onrender.com` → esse é o `VITE_CONNECTOR_URL`.
- ⚠️ Plano free do Render **dorme após ~15 min** ocioso (ver keep-alive no `connector/README.md`).

### 2. Setar connector no Worker + rebuild
```bash
# adicionar em .env:  VITE_CONNECTOR_URL=https://<url-render>
npm run build
npx wrangler deploy
```
(WS é derivado da HTTP se `VITE_CONNECTOR_WS_URL` ficar vazio.)

## ⚠️ Riscos a verificar amanhã
- **Deriv WS + App ID alfanumérico**: o código usa endpoint legado `wss://ws.derivws.com/websockets/v3?app_id=`. Se a conexão ao vivo falhar, o App ID novo (alfanumérico) pode não ser aceito pelo WS legado — investigar. OAuth em si está correto. Ver [[Corretoras e OAuth]].
- DNS local bloqueado: verificar URLs exige DoH (`curl --doh-url https://cloudflare-dns.com/dns-query`). Ver [[Funil de risco/decisão]].

## Limpeza pendente
- Projeto órfão no **Vercel** (`nexus-trader`, aliases `nexxustrader.vercel.app`, `nexxus-trader.vercel.app`) — remover.

## Comandos úteis
- Deploy: `npx wrangler deploy`
- Listar secrets: `npx wrangler secret list`
- Setar secret: `printf "%s" "<valor>" | npx wrangler secret put <NOME>`
=======
atualizado: 2026-07-07
tags: [deploy, cloudflare, render, deriv, infra, pendente]
---

# Deploy de produção — connector no Render

Retomada do deploy de 2026-07-06. Ver [[2026-07-06 Deploy do frontend na Cloudflare Workers]]
e [[2026-07-07 MT5 opcional para deploy do connector no Render]].

## ✅ Já feito
- Frontend no ar: **https://nexustrader.nexustrader.workers.dev** (Cloudflare Workers, 200).
- Secrets no Worker (Supabase, Anthropic, Deriv App ID).
- **2026-07-07:** connector agora **deployável em Linux/Render** — MT5 virou opcional
  (import guardado + marcador de plataforma no requirements). Testado sem e com MT5.

## ⚠️ Bloqueios NOVOS descobertos em 2026-07-07 (ordem de resolução)

### 0. `git push` do código pro GitHub (PRÉ-REQUISITO de tudo)
`origin/main` estava em `bf63f91` (connector **antigo**). O connector atual está em
`9492c3c` + `7451564`, **não pushados**. O fix do MT5 está numa branch/PR
(`worktree-connector-render-deploy`). **Sem push, o Render Blueprint deploya a versão velha.**
→ Revisar o PR, mergear e `git push origin main`.

### 1. Deployar o connector no Render → obter `VITE_CONNECTOR_URL`
- **render.com → New → Blueprint** → repo `Jvlima22/Nexus`. `connector/render.yaml`
  configura tudo (rootDir `connector`, healthCheck `/health`).
- Secrets no painel (agora com auth recomendada por email+senha):
  `IQ_EMAIL`+`IQ_PASSWORD` (ou fallback `IQ_SSID` / `SSID_ENDPOINT`+`SSID_TOKEN`),
  `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `NEXUS_USER_ID`, `POLYMARKET_SLUGS`.
- `ALLOWED_ORIGINS` = `https://nexustrader.nexustrader.workers.dev`
- Render dá `https://nexus-connector.onrender.com` → esse é o `VITE_CONNECTOR_URL`.
- ⚠️ No Render (Linux) o connector sobe **só com IQ Option**; MT5/forex real exige
  máquina Windows. Ver [[2026-07-07 MT5 opcional para deploy do connector no Render]].
- ⚠️ Free dorme após ~15 min ocioso → keep-alive (cron-job.org batendo `/health`).

### 2. Setar connector no Worker + rebuild
```bash
# .env:  VITE_CONNECTOR_URL=https://<url-render>
npm run build && npx wrangler deploy
```
(WS derivado do HTTP se `VITE_CONNECTOR_WS_URL` vazio.)

### 3. Deriv App ID está INVÁLIDO — corrigir
`33KZNJRhS5hZKTrgReR6I` **não é** app_id da Deriv (ela usa **numérico**, ex. `1089`).
OAuth **e** WS falham com esse valor. → Registrar app em **api.deriv.com**, pegar o
**app_id numérico**, e setar em `DERIV_APP_ID` (Worker) e `VITE_DERIV_APP_ID` (build).
Ver [[Corretoras e OAuth]].

## Limpeza pendente
- Remover projeto órfão no **Vercel** (`nexus-trader`).

## Comandos úteis
- Deploy Worker: `npx wrangler deploy`
- Secrets: `npx wrangler secret list` / `printf "%s" "<v>" | npx wrangler secret put <N>`
>>>>>>> b5690aa39079454527d7071a85047de18aa5aa5a
