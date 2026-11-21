---
tipo: trade
status: aberto
ativo: TSLA
direcao: BUY
estrategia: Day Trader Suite (Level Breakout + Monte Carlo)
entrada_data: 2026-11-21
entrada_preco: 345.82
saida_data: 
saida_preco: 
stop: 340.00
alvo: 357.46
size: 10
pnl: 0.0
pnl_pct: 0.0
tags:
  - trading/operacao
  - trading/day-trader
  - trading/alpaca-paper
relacionado:
  - "[[2026-11-21 Instalacao Day Trader Skills Opcao A Hibrida]]"
---

# TSLA BUY 2026-11-21

## Setup
Estratégia: Suíte de Day Trade integrada ao NEXUS (`day-trader-skill`).
Ativo: `TSLA` (Tesla Inc.)
Timeframe: 5 minutos
Confluências:
- Preço de fechamento da barra anterior: $345.82.
- Simulação Monte Carlo (`trader-timemachine`): 500 replays sobre dados históricos reais de 5 min dos últimos 59 pregões.
- Filtro de Notícias (`trader-news`): Catalisadores monitorados via Yahoo Finance RSS.

## Plano original
- Entrada: $345.82
- Stop Loss: $340.00 (risco de $5.82 por ação)
- Alvo (Take Profit): $357.46 (2R = 2x o risco)
- Relação Risco/Retorno (R:R): 2.00
- Flat By: 15:55 ET (sem posição overnight)
- Limite de Perda Máxima (Max Loss): $58.20 (1.16% da banca de $5.000 — abaixo do teto de risco de 2% do `CLAUDE.md`).

## Execução real
- Conta: Alpaca Paper (`paper: true`)
- Tipo de Ordem: Bracket Order (Market Buy + Take-Profit Limit 357.46 + Stop-Loss Stop 340.00)
- Quantidade: 10 ações
- Preço Médio de Entrada: $345.82
- Custo Total Alocado: $3.458,20 (dentro do teto de alocação de 75%)
- Caixa Restante: $1.541,80
- ID da Ordem: `sim-ord-001`
- Registro no Portfólio: `trader/portfolio.json` e log de auditoria em `trader/state/broker.json`.

## Regras de Risco Validadas
1. Gate Algorítmico (`trader-risk`): PASS (risco por trade $58.20 < $100.00, R:R 2.00 > 1.20).
2. Aprovação Explícita (`trader-broker`): Registrada com hash e fingerprint no estado imutável.
