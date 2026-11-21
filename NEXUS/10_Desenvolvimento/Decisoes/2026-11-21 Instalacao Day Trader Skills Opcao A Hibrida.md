---
tipo: decisao
status: aceita
data: 2026-11-21
projeto: NEXUS Trader
tags:
  - dev/decisao
  - skills
  - day-trader
  - risk-management
  - alpaca
  - mt5
relacionado: ["[[CLAUDE.md]]", "[[2026-07-06 Risk Judge unificado e Visao Geral real]]"]
---

# Decisão: Instalação da Suíte Day Trader Skills (Opção A Híbrida)

## Contexto
O NEXUS Trader operava com foco em estratégias automatizadas em MetaTrader 5 (forex/ouro) e IQ Option (binárias). Identificou-se a oportunidade de enriquecer o stack com a suíte de 11 Claude skills do repositório `Jakeschincariol/day-trader-skill` (versão 2 do Trader skill), especializada em day trading sistemático, análise de notícias de última hora, simulação de Monte Carlo com dados reais da sessão (Time Machine) e triplo gate de risco algorítmico sem custo de API paga.

Para integrar a suíte ao NEXUS, duas abordagens foram avaliadas:
- **Opção A (Híbrida):** Instalação nativa das 11 skills cobrindo Ações US via Alpaca Paper e criação de aliases para ativos Forex e Ouro (`EURUSD=X`, `GC=F`) operados no MT5.
- **Opção B (Exclusiva MT5):** Adaptação imediata e restritiva de todos os módulos apenas para o ecossistema MetaTrader 5.

O usuário selecionou formalmente a **Opção A**.

## Decisão
1. **Instalação Multi-Ambiente:**
   - As 11 skills (`trader-scanner`, `trader-news`, `trader-entry`, `trader-exit`, `trader-timemachine`, `trader-risk`, `trader-budget`, `trader-broker`, `trader-alerts`, `trader-analyst`, `trader-pelosi`) foram instaladas em:
     - `.claude/skills/trader-*`: Disponíveis nativamente para execução via Claude Code.
     - `skills/trader-*` e `skills/day-trader/`: Integradas à biblioteca do projeto NEXUS.
     - `.agent/skills/trader-*`: Mapeadas para o runner e assistentes Antigravity.
2. **Configuração de Risco Unificada (`trader/config.json`):**
   - Rigorosamente alinhada à política de risco de 2% do `CLAUDE.md`:
     - Banca base: `$5.000` USD
     - Risco por trade (`max_loss_per_trade_usd`): `$100` USD (exatos 2%)
     - Teto de perda diária (`max_daily_loss_usd`): `$200` USD (4%, alinhado ao `nexus_bot_24h.py`)
     - Posições simultâneas: `3`
     - R/R mínimo: `1.2`
     - Broker default: `alpaca` em modo `paper: true`.
3. **Mapeamento Híbrido de Símbolos (`symbol_aliases`):**
   - Criação de `trader/alias_helper.py` permitindo que símbolos do MT5 (`EURUSD`, `XAUUSD`, `GOLD`, etc.) sejam automaticamente resolvidos para seus correspondentes do Yahoo Finance (`EURUSD=X`, `GC=F`).

## Consequências e Próximos Passos
- Os 315 testes unitários da suíte executam com sucesso.
- O time ganha acesso instantâneo a ferramentas de simulação Monte Carlo (10.000 replays) antes de arriscar capital real.
- Próxima etapa: Conectar o output de planos (`trader/plan.json`) e execuções (`trader/orders.json`) ao log automático do Supabase e às notas de trade no Obsidian.
