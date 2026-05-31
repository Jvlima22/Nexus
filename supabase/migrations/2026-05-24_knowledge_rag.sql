-- ──────────────────────────────────────────────────────────────────────────────
-- NEXUS Trader — Migration: Knowledge / Contexto da IA (RAG via Prompt Caching)
-- Decisão: NEXUS/10_Desenvolvimento/Decisoes/2026-05-24 RAG do Knowledge - Prompt Caching.md
--
-- Recurso: o usuário sobe arquivos / cola texto / adiciona URLs em /knowledge.
-- O texto extraído fica aqui e é injetado como PREFIXO CACHEADO no Claude
-- (cache_control ephemeral) → contexto "em milissegundos" sem vendor de embeddings.
--
-- A coluna `tsv` já deixa a Fase 2 (busca full-text / BM25) pronta sem migration nova.
-- Execute no SQL Editor do Supabase, uma vez. Idempotente.
-- ──────────────────────────────────────────────────────────────────────────────

create table if not exists public.knowledge_sources (
  id              uuid primary key default uuid_generate_v4(),
  user_id         uuid not null references auth.users(id) on delete cascade,
  kind            text not null check (kind in ('file','url','text')),
  title           text not null,
  source_url      text,                 -- preenchido quando kind='url'
  storage_path    text,                 -- reservado: original no Storage (futuro)
  mime            text,
  content         text not null default '',
  char_count      integer not null default 0,
  token_estimate  integer not null default 0,  -- ~ char_count/4
  status          text not null default 'ready' check (status in ('processing','ready','error')),
  error           text,
  active          boolean not null default true,  -- entra no contexto da IA?
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

create index if not exists knowledge_sources_user_idx on public.knowledge_sources(user_id, created_at desc);

-- Fase 2 (FTS): coluna gerada + índice GIN. Pré-pronto, não usado ainda.
alter table public.knowledge_sources
  add column if not exists tsv tsvector
  generated always as (to_tsvector('portuguese', coalesce(title,'') || ' ' || coalesce(content,''))) stored;
create index if not exists knowledge_sources_tsv_idx on public.knowledge_sources using gin(tsv);

alter table public.knowledge_sources enable row level security;

-- Leitura/edição/exclusão só do dono. INSERT acontece via service_role (server fn de ingestão).
drop policy if exists "knowledge: owner read"   on public.knowledge_sources;
drop policy if exists "knowledge: owner update" on public.knowledge_sources;
drop policy if exists "knowledge: owner delete" on public.knowledge_sources;
create policy "knowledge: owner read"   on public.knowledge_sources for select using (auth.uid() = user_id);
create policy "knowledge: owner update" on public.knowledge_sources for update using (auth.uid() = user_id);
create policy "knowledge: owner delete" on public.knowledge_sources for delete using (auth.uid() = user_id);

drop trigger if exists touch_knowledge_sources on public.knowledge_sources;
create trigger touch_knowledge_sources before update on public.knowledge_sources
  for each row execute function public.touch_updated_at();

-- Realtime: lista de fontes atualiza sem refresh.
alter table public.knowledge_sources replica identity full;
do $$
begin
  if not exists (
    select 1 from pg_publication_tables
    where pubname = 'supabase_realtime' and schemaname = 'public' and tablename = 'knowledge_sources'
  ) then
    execute 'alter publication supabase_realtime add table public.knowledge_sources';
  end if;
end $$;
