-- ──────────────────────────────────────────────────────────────────────────────
-- NEXUS Trader — Migration: Trade Snapshots (auditoria pós-trade)
-- Decisão: NEXUS/10_Desenvolvimento/Decisoes/2026-06-07 Snapshot de operacao.md
--
-- `trade_snapshots`: retrato do mercado no instante de cada ordem (candles +
-- indicadores + padrão de candle + suporte/resistência), como JSON. Gravado pelo
-- connector (orders._capture_snapshot) e lido SOB DEMANDA quando o usuário clica
-- numa operação. Sem Realtime de propósito (não infla o feed de trades).
-- Execute no SQL Editor do Supabase, uma vez. Idempotente: pode reexecutar.
-- ──────────────────────────────────────────────────────────────────────────────

create table if not exists public.trade_snapshots (
  id           uuid primary key default uuid_generate_v4(),
  user_id      uuid not null references auth.users(id) on delete cascade,
  trade_id     uuid references public.trades(id) on delete cascade,
  external_id  text,                 -- order_id da IQ (join alternativo)
  asset        text,
  timeframe    text,                 -- M1 | M5 | M15 (derivado da expiração)
  captured_at  timestamptz not null default now(),
  snapshot     jsonb not null,       -- candles, indicators, patterns, support_resistance, signal, risk
  unique (user_id, trade_id)
);

create index if not exists trade_snapshots_trade_idx on public.trade_snapshots(user_id, trade_id);
create index if not exists trade_snapshots_ext_idx on public.trade_snapshots(user_id, external_id);

alter table public.trade_snapshots enable row level security;
drop policy if exists "trade_snapshots: owner read" on public.trade_snapshots;
create policy "trade_snapshots: owner read" on public.trade_snapshots for select using (auth.uid() = user_id);
