# NEXUS — Setup das Conexões com Corretoras

Este documento lista o que falta fazer para ativar as conexões em produção.
Todo o código já está implementado — só faltam as configurações externas.

## 1. Criar projeto Supabase

1. Vá em https://supabase.com → novo projeto
2. SQL Editor → cole e execute `supabase/schema.sql`
3. Settings → API → copie:
   - `Project URL` → `VITE_SUPABASE_URL`
   - `anon public` → `VITE_SUPABASE_ANON_KEY`
   - `service_role` → `SUPABASE_SERVICE_ROLE_KEY` (**nunca expor no frontend**)

## 2. Habilitar Google OAuth (opcional)

Supabase → Authentication → Providers → Google → habilitar
e configurar Client ID/Secret do Google Cloud Console.

## 3. Registrar app Deriv

1. https://api.deriv.com → registre uma conta de dev
2. Crie um app com:
   - Redirect URL: `http://localhost:5173/api/connections/deriv/callback` (ou seu domínio em produção)
3. Copie o `app_id` para:
   - `DERIV_APP_ID` (server, validação WS)
   - `VITE_DERIV_APP_ID` (client, montar URL de autorização)

## 4. Gerar a chave de cifra

```powershell
node -e "console.log(require('crypto').randomBytes(32).toString('base64'))"
```

Cole em `BROKER_ENCRYPTION_KEY`.

> **Importante:** se você perder essa chave, **todas as credenciais cifradas
> ficam ilegíveis**. Guarde uma cópia em local seguro.

## 5. Configurar variáveis de ambiente

**Atenção:** o NEXUS roda em Cloudflare Worker via `@cloudflare/vite-plugin`.
Em dev, **dois arquivos** são necessários:

```bash
cp .env.example .env             # carregado pelo Vite → bundle do client (VITE_*)
cp .dev.vars.example .dev.vars   # carregado pelo Worker (Miniflare) → process.env no server
```

| Arquivo       | Quem lê                    | Variáveis                                                      |
|---------------|----------------------------|----------------------------------------------------------------|
| `.env`        | Vite (client + build)      | `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_DERIV_APP_ID` |
| `.dev.vars`   | Cloudflare Worker dev      | `SUPABASE_SERVICE_ROLE_KEY`, `BROKER_ENCRYPTION_KEY`, `DERIV_APP_ID`, `VITE_SUPABASE_URL` (precisa duplicar aqui pro server resolver) |

Para deploy em produção, replicar todas as variáveis do `.dev.vars` em
`wrangler secret put NOME`. As `VITE_*` entram no bundle do client durante `npm run build`.

## 6. Testar localmente

```powershell
npm run dev
# abrir http://localhost:5173
# 1. Criar conta em /login (ou Google)
# 2. Ir em /conexoes e conectar uma corretora
```

## Fluxos por corretora

### Binance / Bybit (API Key)

1. Vá no painel da corretora e crie uma API Key
2. **DESMARQUE "Enable Withdrawals"** — NEXUS bloqueia chaves com saque ativo
3. Marque apenas as permissões que você quer usar (Read, Spot, Futures...)
4. Restrinja IP se possível
5. Cole `API Key` e `API Secret` no modal do NEXUS

### Deriv (OAuth 2.0)

1. Clique "Conectar" → "Autorizar com Deriv"
2. Você será redirecionado para `oauth.deriv.com`
3. Autorize → volta para `/api/connections/deriv/callback`
4. NEXUS guarda o token cifrado

### IQ Option (SSID, não-oficial)

> **Aviso:** este fluxo usa o endpoint interno da IQ Option, sem API oficial.
> Pode quebrar a qualquer momento se a IQ Option mudar o endpoint, e pode
> violar o TOS deles. Use ciente.

1. Cole email + senha no modal
2. NEXUS autentica server-side, captura o cookie SSID
3. SSID fica cifrado no Supabase para usar em conexões WebSocket futuras

## Arquitetura de segurança

```
Client (browser)
  │  Supabase JS (anon key, session cookie)
  ▼
TanStack Start server fns  (Cloudflare Worker)
  │  - requireUser(accessToken)  ← valida JWT do Supabase
  │  - getAdapter(broker).test(creds)  ← fala com a corretora
  │  - encryptJSON(creds)  ← AES-256-GCM
  ▼
Supabase Postgres
  - broker_connections (credenciais cifradas, service_role only)
  - broker_connections_safe (view sem credenciais, RLS = owner)
  - broker_audit_log (RLS = owner read, service_role write)
```

Cliente nunca toca em credenciais cifradas: o `select` no front é feito sobre a
view `broker_connections_safe` que não inclui `credentials_ciphertext`.

## Próximos passos sugeridos

- [ ] Substituir o `mock-data.ts` por queries reais no Supabase (trades, ai_logs)
- [ ] Implementar `getBalance` em cada adapter
- [ ] Realtime subscriptions para o terminal de logs
- [ ] Rate limit nas rotas server-side (Cloudflare KV ou Durable Objects)
- [ ] Refresh automático do token Deriv (Deriv tokens expiram)
- [ ] Reconectar WebSocket da IQ Option periodicamente para manter SSID quente
