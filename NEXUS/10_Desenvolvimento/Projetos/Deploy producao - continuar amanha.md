---
tipo: projeto
status: em-andamento
data: 2026-07-06
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
