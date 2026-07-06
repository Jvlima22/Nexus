-- ──────────────────────────────────────────────────────────────────────────────
-- NEXUS Trader — Migration: Asset Edge (Robô OTC v2 — gate de evidência)
-- Projeto: NEXUS/10_Desenvolvimento/Projetos/Robo OTC - To Do.md
--
-- `asset_edge`: taxa de acerto MEDIDA (backtest) por par. O autotrader só opera
-- um par cujo edge supere o breakeven com margem — nunca por esperança. Alimentado
-- pelo loop de edge do robô (connector/backtest.py) e lido como pré-filtro.
-- Execute no SQL Editor do Supabase, uma vez. Idempotente: pode reexecutar.
-- ──────────────────────────────────────────────────────────────────────────────

create table if not exists public.asset_edge (
  id                    uuid primary key default uuid_generate_v4(),
  user_id               uuid not null references auth.users(id) on delete cascade,
  symbol                text not null,
  hit_rate              numeric(5,4),   -- acerto de TODOS os sinais M5 (estratégia crua)
  sample                integer not null default 0,
  confluence_hit_rate   numeric(5,4),   -- acerto só com confluência (o que o robô opera)
  confluence_sample     integer not null default 0,
  breakeven             numeric(5,4),   -- 1/(1+payout) — limiar de lucro
  passes_gate           boolean not null default false,  -- snapshot do veredito do gate
  updated_at            timestamptz not null default now(),
  unique (user_id, symbol)
);

create index if not exists asset_edge_user_idx on public.asset_edge(user_id, symbol);

alter table public.asset_edge enable row level security;
drop policy if exists "asset_edge: owner read" on public.asset_edge;
create policy "asset_edge: owner read" on public.asset_edge for select using (auth.uid() = user_id);

-- Realtime: o painel do autotrader vê quais pares ganharam/perderam edge ao vivo.
alter table public.asset_edge replica identity full;

do $$
begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'asset_edge'
  ) then
    alter publication supabase_realtime add table public.asset_edge;
  end if;
end $$;
