-- ══════════════════════════════════════════════════════════════════════════════
-- bankroll_history: colunas de conta com margem (MT5). Aditivo, idempotente.
-- Habilita snapshot de equity/margin_level junto do saldo já existente, pro
-- card de conta MT5 na Visão Geral (source='nexus_mt5' via nexus_bot_24h.py).
-- ══════════════════════════════════════════════════════════════════════════════
alter table public.bankroll_history add column if not exists equity       numeric(14,2);
alter table public.bankroll_history add column if not exists margin_level numeric(8,2);
