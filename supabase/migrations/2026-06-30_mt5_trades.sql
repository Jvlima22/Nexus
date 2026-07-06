-- ──────────────────────────────────────────────────────────────────────────────
-- NEXUS Trader — Migration: suporte MT5 na tabela trades
-- Execute no SQL Editor do Supabase Dashboard
-- ──────────────────────────────────────────────────────────────────────────────

-- 1. Colunas MT5 (seguro: ADD COLUMN IF NOT EXISTS)
alter table public.trades add column if not exists position_id   text;
alter table public.trades add column if not exists symbol        text;
alter table public.trades add column if not exists direction     text;        -- BUY | SELL
alter table public.trades add column if not exists volume        numeric(10,2);
alter table public.trades add column if not exists entry_price   numeric(18,6);
alter table public.trades add column if not exists stop_loss     numeric(18,6);
alter table public.trades add column if not exists take_profit   numeric(18,6);
alter table public.trades add column if not exists close_price   numeric(18,6);
alter table public.trades add column if not exists pnl           numeric(14,2);
alter table public.trades add column if not exists close_reason  text;        -- tp | sl | manual
alter table public.trades add column if not exists timeframe     text;
alter table public.trades add column if not exists pattern       text;
alter table public.trades add column if not exists session       text;
alter table public.trades add column if not exists signal_id     uuid;
alter table public.trades add column if not exists ai_reasoning  text;
alter table public.trades add column if not exists magic         bigint;

-- 2. Corrige constraint source para aceitar nexus_mt5
alter table public.trades drop constraint if exists trades_source_chk;
alter table public.trades add  constraint trades_source_chk
  check (source in ('nexus', 'manual', 'nexus_mt5'));

-- 3. Index para busca por position_id (ticket MT5)
create index if not exists trades_position_id_idx on public.trades(position_id);
create index if not exists trades_symbol_idx      on public.trades(symbol);

-- 4. ai_signals (cria se não existir)
create table if not exists public.ai_signals (
  id            uuid primary key default uuid_generate_v4(),
  created_at    timestamptz not null default now(),
  symbol        text not null,
  direction     text not null,
  timeframe     text,
  pattern       text,
  session       text,
  entry_price   numeric(18,6),
  stop_loss     numeric(18,6),
  take_profit   numeric(18,6),
  rr_ratio      numeric(5,2),
  ai_reasoning  text,
  h1_bias       text,
  m5_structure  text,
  confidence    integer,
  outcome       text not null default 'pending'  -- pending | win | loss
);

alter table public.ai_signals enable row level security;
drop policy if exists "ai_signals: service role all" on public.ai_signals;
create policy "ai_signals: service role all" on public.ai_signals
  using (true) with check (true);

-- Realtime para ai_signals
alter table public.ai_signals replica identity full;
do $$
begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime'
      and schemaname = 'public'
      and tablename = 'ai_signals'
  ) then
    alter publication supabase_realtime add table public.ai_signals;
  end if;
end $$;
