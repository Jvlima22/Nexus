-- ──────────────────────────────────────────────────────────────────────────────
-- NEXUS Trader — Migration: Risk Judge (Fase 3)
-- Decisão: NEXUS/10_Desenvolvimento/Decisoes/2026-05-31 Risk Judge - juiz de risco.md
--
-- `risk_events`: trilha de auditoria de TODO veredito do juiz de risco (aprovação
-- ou veto), com o código da regra e o motivo. Alimenta o painel de risco no front.
-- Execute no SQL Editor do Supabase, uma vez. Idempotente: pode reexecutar.
-- ──────────────────────────────────────────────────────────────────────────────

create table if not exists public.risk_events (
  id          uuid primary key default uuid_generate_v4(),
  user_id     uuid not null references auth.users(id) on delete cascade,
  created_at  timestamptz not null default now(),
  decision    text not null check (decision in ('approved', 'rejected')),
  -- OK | LOW_CONFIDENCE | NEUTRAL | ALLOC_EXCEEDED | CIRCUIT_BREAKER | DAILY_LOSS_CAP
  code        text not null,
  asset       text,
  direction   text,
  confidence  numeric(4,3),
  amount      numeric(14,2),
  balance     numeric(14,2),
  reason      text,
  details     jsonb not null default '{}'::jsonb
);

create index if not exists risk_events_user_idx on public.risk_events(user_id, created_at desc);

alter table public.risk_events enable row level security;
drop policy if exists "risk_events: owner read" on public.risk_events;
create policy "risk_events: owner read" on public.risk_events for select using (auth.uid() = user_id);

-- Realtime: o painel de risco vê os vetos em tempo real.
alter table public.risk_events replica identity full;

do $$
begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'risk_events'
  ) then
    alter publication supabase_realtime add table public.risk_events;
  end if;
end $$;
