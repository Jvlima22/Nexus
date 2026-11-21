# NEXUS Trader — Day Trader Skills Suite (Opção A Híbrida)

Esta pasta centraliza os artefatos de configuração e execução da suíte de 11 skills do `day-trader-skill` integradas ao ecossistema **NEXUS**.

## Estrutura da Integração

- **Configuração:** `trader/config.json`
- **Aliases Forex/MT5:** `trader/alias_helper.py`
- **Skills instaladas em:**
  - `.claude/skills/trader-*` (Claude Code)
  - `skills/trader-*` e `skills/day-trader/` (NEXUS Local)
  - `.agent/skills/trader-*` (Antigravity CLI)

## Escopo Híbrido de Ativos (Opção A)

1. **Ações US (Nativas via Alpaca Paper):**
   - Ativos: `TSLA`, `NVDA`, `AAPL`, `SPY`, `MSFT`, `AMZN`, `META`, `QQQ`
   - Execução: Alpaca Paper Trading via MCP (`trader-broker`)

2. **Forex & Commodities (Aliases para MT5 / Yahoo Finance):**
   - Forex: `EURUSD` -> `EURUSD=X`, `GBPUSD` -> `GBPUSD=X`, `USDJPY` -> `USDJPY=X`
   - Ouro: `XAUUSD` / `GOLD` -> `GC=F`
   - Dados analíticos públicos de candle e volatilidade via endpoints v8 Yahoo Finance sem custo de API.

## Parâmetros de Risco (Alinhados com CLAUDE.md)

- **Banca base (`budget`):** $5.000,00 USD
- **Risco Máximo por Operação (`max_loss_per_trade_usd`):** $100,00 USD (**2,0%** da banca)
- **Teto Diário de Perda (`max_daily_loss_usd`):** $200,00 USD (**4,0%** da banca)
- **Máximo de Trades Simultâneos (`max_trades_per_day`):** 3 posições
- **Relação Retorno/Risco Mínima (`min_reward_risk`):** 1.2
- **Stop Loss Obrigatório (`require_stop`):** Sim (`true`)
