-- ──────────────────────────────────────────────────────────────────────────────
-- NEXUS Trader — Schema de bootstrap
-- Execute no SQL Editor do Supabase (uma vez, na criação do projeto).
-- ──────────────────────────────────────────────────────────────────────────────

-- Extensões
create extension if not exists "uuid-ossp";

-- ──────────────────────────────────────────────────────────────────────────────
-- profiles: 1 linha por usuário do Supabase Auth
-- ──────────────────────────────────────────────────────────────────────────────
create table if not exists public.profiles (
  id              uuid primary key references auth.users(id) on delete cascade,
  email           text,
  display_name    text,
  risk_profile    text default 'conservative',
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

alter table public.profiles enable row level security;

drop policy if exists "profiles: owner read"  on public.profiles;
drop policy if exists "profiles: owner write" on public.profiles;
create policy "profiles: owner read"  on public.profiles for select using (auth.uid() = id);
create policy "profiles: owner write" on public.profiles for update using (auth.uid() = id);

-- Trigger: criar profile automaticamente quando um usuário se registra
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  insert into public.profiles (id, email)
  values (new.id, new.email)
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ──────────────────────────────────────────────────────────────────────────────
-- broker_connections: 1 linha por (user, broker)
-- credentials_ciphertext guarda payload AES-GCM cifrado no Worker.
-- O service_role lê para uso server-side; o usuário só lê metadados via view.
-- ──────────────────────────────────────────────────────────────────────────────
create table if not exists public.broker_connections (
  id                      uuid primary key default uuid_generate_v4(),
  user_id                 uuid not null references auth.users(id) on delete cascade,
  broker                  text not null check (broker in ('binance','bybit','deriv','iqoption','coinbase','kraken')),
  auth_method             text not null check (auth_method in ('oauth','api_key','ssid')),
  status                  text not null default 'pending' check (status in ('pending','connected','error','revoked')),
  account_label           text,
  permissions             jsonb default '{}'::jsonb,
  last_latency_ms         integer,
  last_tested_at          timestamptz,
  last_error              text,
  credentials_ciphertext  text not null,
  credentials_iv          text not null,
  expires_at              timestamptz,
  created_at              timestamptz not null default now(),
  updated_at              timestamptz not null default now(),
  unique (user_id, broker)
);

create index if not exists broker_connections_user_idx on public.broker_connections(user_id);

alter table public.broker_connections enable row level security;

-- O usuário pode LER seu registro (sem credenciais — campos sensíveis ficam na view)
drop policy if exists "broker_connections: owner read"   on public.broker_connections;
drop policy if exists "broker_connections: owner delete" on public.broker_connections;
create policy "broker_connections: owner read"   on public.broker_connections for select using (auth.uid() = user_id);
create policy "broker_connections: owner delete" on public.broker_connections for delete using (auth.uid() = user_id);

-- INSERT/UPDATE acontecem via service_role (rotas server-side); RLS bloqueia escrita direta do client.

-- View pública sem credenciais cifradas — segura para o frontend ler
create or replace view public.broker_connections_safe as
select
  id, user_id, broker, auth_method, status,
  account_label, permissions, last_latency_ms, last_tested_at, last_error,
  expires_at, created_at, updated_at
from public.broker_connections;

-- security_invoker = on faz a view respeitar as RLS da tabela base.
-- Sem isso, a view roda como owner e o Supabase bloqueia o acesso via PostgREST.
alter view public.broker_connections_safe set (security_invoker = on);
grant select on public.broker_connections_safe to authenticated, anon;

-- ──────────────────────────────────────────────────────────────────────────────
-- broker_audit_log: histórico imutável de operações sensíveis
-- ──────────────────────────────────────────────────────────────────────────────
create table if not exists public.broker_audit_log (
  id          uuid primary key default uuid_generate_v4(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  broker      text not null,
  action      text not null check (action in ('connect','test','revoke','error')),
  detail      jsonb default '{}'::jsonb,
  ip_address  text,
  user_agent  text,
  created_at  timestamptz not null default now()
);

create index if not exists broker_audit_log_user_idx on public.broker_audit_log(user_id, created_at desc);

alter table public.broker_audit_log enable row level security;

drop policy if exists "broker_audit_log: owner read" on public.broker_audit_log;
create policy "broker_audit_log: owner read" on public.broker_audit_log for select using (auth.uid() = user_id);

-- Escritas só via service_role.

-- ──────────────────────────────────────────────────────────────────────────────
-- updated_at automático
-- ──────────────────────────────────────────────────────────────────────────────
create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end;
$$;

drop trigger if exists touch_profiles            on public.profiles;
drop trigger if exists touch_broker_connections  on public.broker_connections;
create trigger touch_profiles            before update on public.profiles            for each row execute function public.touch_updated_at();
create trigger touch_broker_connections  before update on public.broker_connections  for each row execute function public.touch_updated_at();
