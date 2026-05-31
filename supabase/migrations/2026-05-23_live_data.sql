-- ──────────────────────────────────────────────────────────────────────────────
-- NEXUS Trader — Migration: dados ao vivo da IQ Option (arquitetura Híbrida)
-- Decisão: NEXUS/10_Desenvolvimento/Decisoes/2026-05-23 Arquitetura de dados ao vivo IQ Option.md
--
-- IMPORTANTE: `trades` e `bankroll_history` JÁ EXISTEM (scaffold Lovable) com um
-- design próprio. Esta migration NÃO recria — apenas ADICIONA o que falta e liga
-- RLS/Realtime. Mapa de colunas reusadas em `trades`:
--   asset=símbolo · type=direção(Call/Put) · result=PnL($) · time=abertura
--   external_id=id da ordem IQ · status=estado(open/win/loss) · note_url=link Obsidian
--
-- Candles ao vivo NÃO ficam no banco — vão direto pelo WS do Connector.
-- Execute no SQL Editor do Supabase, uma vez. Idempotente: pode reexecutar.
-- ──────────────────────────────────────────────────────────────────────────────

-- Garante a função de updated_at (definida no schema.sql; recriada por segurança).
create or replace function public.touch_updated_at()
returns trigger language plpgsql as $$
begin new.updated_at = now(); return new; end;
$$;

-- Backfill de profiles: `trades.user_id` referencia `profiles(id)`. Contas criadas
-- antes do trigger handle_new_user não têm profile → FK quebra. Cria os faltantes
-- profiles do scaffold tem `id` (PK→auth.users) E `user_id` NOT NULL; setamos ambos
-- com o id do auth. (Sem coluna `email`.)
insert into public.profiles (id, user_id)
select id, id from auth.users
on conflict (id) do nothing;

-- ══════════════════════════════════════════════════════════════════════════════
-- assets: NOVA — espelho dos "ativos disponíveis" da IQ por usuário
-- ══════════════════════════════════════════════════════════════════════════════
create table if not exists public.assets (
  id            uuid primary key default uuid_generate_v4(),
  user_id       uuid not null references auth.users(id) on delete cascade,
  symbol        text not null,
  name          text,
  type          text not null check (type in ('binary','digital','forex','crypto','stock','commodity')),
  is_open       boolean not null default false,
  payout        numeric(5,2),
  iq_active_id  integer,
  updated_at    timestamptz not null default now(),
  unique (user_id, symbol, type)
);

create index if not exists assets_user_idx on public.assets(user_id, is_open);

alter table public.assets enable row level security;
drop policy if exists "assets: owner read" on public.assets;
create policy "assets: owner read" on public.assets for select using (auth.uid() = user_id);

drop trigger if exists touch_assets on public.assets;
create trigger touch_assets before update on public.assets
  for each row execute function public.touch_updated_at();

-- ══════════════════════════════════════════════════════════════════════════════
-- trades: EXISTENTE — adiciona colunas do fluxo ao vivo (sem tocar nas atuais)
-- ══════════════════════════════════════════════════════════════════════════════
alter table public.trades add column if not exists source             text not null default 'manual';
alter table public.trades add column if not exists amount             numeric(14,2);
alter table public.trades add column if not exists payout             numeric(5,2);
alter table public.trades add column if not exists option_type        text;       -- binary|digital (type já guarda Call/Put)
alter table public.trades add column if not exists expiration_seconds integer;
alter table public.trades add column if not exists expires_at         timestamptz;
alter table public.trades add column if not exists closed_at          timestamptz;
alter table public.trades add column if not exists strategy           text;
alter table public.trades add column if not exists updated_at         timestamptz not null default now();

-- CHECK do source (drop+add para ser idempotente).
alter table public.trades drop constraint if exists trades_source_chk;
alter table public.trades add  constraint trades_source_chk check (source in ('nexus','manual'));

-- `result` (PnL em $) só existe ao fechar a operação → precisa ser nullable.
-- O scaffold Lovable a criou NOT NULL; relaxamos para permitir ordens abertas.
alter table public.trades alter column result drop not null;

create index if not exists trades_user_time_idx   on public.trades(user_id, time desc);
create index if not exists trades_user_status_idx on public.trades(user_id, status);

alter table public.trades enable row level security;
drop policy if exists "trades: owner read" on public.trades;
create policy "trades: owner read" on public.trades for select using (auth.uid() = user_id);

drop trigger if exists touch_trades on public.trades;
create trigger touch_trades before update on public.trades
  for each row execute function public.touch_updated_at();

-- ══════════════════════════════════════════════════════════════════════════════
-- bankroll_history: EXISTENTE (id,user_id,balance,timestamp) — adiciona metadados
-- ══════════════════════════════════════════════════════════════════════════════
alter table public.bankroll_history add column if not exists currency     text not null default 'USD';
alter table public.bankroll_history add column if not exists account_type text not null default 'practice';
alter table public.bankroll_history add column if not exists source       text;

alter table public.bankroll_history drop constraint if exists bankroll_account_type_chk;
alter table public.bankroll_history add  constraint bankroll_account_type_chk check (account_type in ('real','practice'));

create index if not exists bankroll_history_user_idx on public.bankroll_history(user_id, "timestamp" desc);

alter table public.bankroll_history enable row level security;
drop policy if exists "bankroll_history: owner read" on public.bankroll_history;
create policy "bankroll_history: owner read" on public.bankroll_history for select using (auth.uid() = user_id);

-- ══════════════════════════════════════════════════════════════════════════════
-- Realtime: replica identity full (payload completo em UPDATE) + add à publicação
-- (guardado contra "já é membro" para ser idempotente).
-- ══════════════════════════════════════════════════════════════════════════════
alter table public.assets           replica identity full;
alter table public.trades           replica identity full;
alter table public.bankroll_history replica identity full;

do $$
declare t text;
begin
  foreach t in array array['assets','trades','bankroll_history'] loop
    if not exists (
      select 1 from pg_publication_tables
      where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = t
    ) then
      execute format('alter publication supabase_realtime add table public.%I', t);
    end if;
  end loop;
end $$;
