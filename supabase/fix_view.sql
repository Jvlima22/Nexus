-- ──────────────────────────────────────────────────────────────────────────────
-- Fix da view broker_connections_safe
-- Execute no SQL Editor do Supabase se a /conexoes estiver retornando 404
-- ao buscar a view.
-- ──────────────────────────────────────────────────────────────────────────────

-- Garante que a view existe (idempotente)
create or replace view public.broker_connections_safe as
select
  id, user_id, broker, auth_method, status,
  account_label, permissions, last_latency_ms, last_tested_at, last_error,
  expires_at, created_at, updated_at
from public.broker_connections;

-- security_invoker faz a view respeitar as RLS policies da tabela base
-- (sem isso, a view roda como owner e Supabase pode bloquear o acesso).
alter view public.broker_connections_safe set (security_invoker = on);

-- Concede SELECT explícito para roles do Supabase
grant select on public.broker_connections_safe to authenticated, anon;

-- Força o PostgREST a recarregar o schema cache (resolve 404 fantasma)
notify pgrst, 'reload schema';
