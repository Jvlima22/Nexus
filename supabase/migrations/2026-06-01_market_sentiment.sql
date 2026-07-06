-- ──────────────────────────────────────────────────────────────────────────────
-- NEXUS Trader — Migration: Polymarket / sentimento macro (Fase 4)
-- Decisão: NEXUS/10_Desenvolvimento/Decisoes/2026-06-01 Camada de sentimento Polymarket.md
--
-- `market_sentiment`: snapshot do bias macro por mercado da Polymarket (Gamma API).
-- O Connector faz upsert por (user_id, slug); o Risk Judge lê o agregado como regra 0
-- e o dashboard assina via Realtime (PolymarketFeed). Idempotente: pode reexecutar.
-- ──────────────────────────────────────────────────────────────────────────────

create table if not exists public.market_sentiment (
  id           uuid primary key default uuid_generate_v4(),
  user_id      uuid not null references auth.users(id) on delete cascade,
  slug         text not null,
  question     text,
  probability  numeric(6,4) not null,                 -- prob do "Yes" (0–1)
  bias         text not null check (bias in ('bullish', 'bearish', 'neutral')),
  volume       numeric(18,2),
  updated_at   timestamptz not null default now(),
  unique (user_id, slug)
);

create index if not exists market_sentiment_user_idx on public.market_sentiment(user_id, updated_at desc);

alter table public.market_sentiment enable row level security;
drop policy if exists "market_sentiment: owner read" on public.market_sentiment;
create policy "market_sentiment: owner read" on public.market_sentiment for select using (auth.uid() = user_id);

drop trigger if exists touch_market_sentiment on public.market_sentiment;
create trigger touch_market_sentiment before update on public.market_sentiment
  for each row execute function public.touch_updated_at();

-- Realtime: o PolymarketFeed vê as mudanças de probabilidade em tempo real.
alter table public.market_sentiment replica identity full;

do $$
begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'market_sentiment'
  ) then
    alter publication supabase_realtime add table public.market_sentiment;
  end if;
end $$;
