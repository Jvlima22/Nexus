---
tipo: decisao
data: 2026-07-06
tags: [deploy, cloudflare, vercel, infra]
---

# Deploy do frontend na Cloudflare Workers (e não Vercel)

## Contexto
Pedido inicial foi "deploy na Vercel". Fiz o deploy, mas todas as URLs davam **404**.

## Causa raiz
O frontend é **TanStack Start** (`@tanstack/react-start`) com SSR, e a `@lovable.dev/vite-tanstack-config` embute o `@cloudflare/vite-plugin` (build-only). O build gera um **Cloudflare Worker** (`dist/server/index.js` + `dist/server/wrangler.json`), não output estático. O Vercel detecta "Vite" e serve como site estático → 404 em tudo. Não é ajustável por env/config no Vercel sem reescrever o build fora do plugin Cloudflare.

## Opções
- **A) Cloudflare Workers** (alvo nativo): `wrangler.jsonc` + `src/server.ts` já configurados. Escolhida.
- **B) Forçar Vercel**: reescrever build p/ preset Node/Vercel (Nitro), brigando com a lovable-config. Rejeitada (frágil).

## Escolha / execução
- Renomeado worker `tanstack-start-app` → `nexustrader` em `wrangler.jsonc`.
- Registrado subdomínio workers.dev `nexustrader` (via API CF).
- `wrangler deploy` → **https://nexustrader.nexustrader.workers.dev** (HTTP 200).
- Secrets no Worker: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` (`wrangler secret put`).

## Consequências / pendências
- Vercel (`nexus-trader`, aliases `nexxustrader.vercel.app` etc.) fica órfão — remover depois.
- Faltam server secrets p/ features: connector URL (Render), `VITE_DERIV_APP_ID`, `ANTHROPIC_API_KEY`. Dados ao vivo dependem do connector Python público.
- DNS local bloqueado: verificar URL nova exige DoH (`curl --doh-url`). Ver [[Funil de risco/decisão]] contorno DoH.

## Como reverter
`git revert` do nome em `wrangler.jsonc`; `wrangler delete` do worker `nexustrader`.
