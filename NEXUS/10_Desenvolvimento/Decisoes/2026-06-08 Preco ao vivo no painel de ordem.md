---
tipo: decisao
data: 2026-06-08
tags: [ui, mercado, trading]
---

# Painel de ordem à esquerda — preço nativo da linha pontilhada visível

## Contexto
A label do último preço (linha pontilhada / escala direita do lightweight-charts)
ficava atrás do `ChartOrderPanel`, que estava sobreposto na **borda direita**.

## Tentativas descartadas
1. Mostrar o preço *dentro* do painel — recusado (queria o valor da própria linha).
2. Tag de preço custom via `priceToCoordinate`, posicionada à esquerda do painel —
   substituída por solução mais simples.

## Decisão
Mover o `ChartOrderPanel` para a **borda esquerda** (`absolute left-3`). Com isso a
escala/label nativa do preço (lado direito) fica **livre** e o lightweight-charts já
exibe o valor da linha pontilhada sozinho — sem código extra.

- `CandleChart` revertido ao estado original (sem `onPrice`/`priceTag`/subscrições).
- Só mudou `right-3` → `left-3` no `ChartOrderPanel`.

## Consequências
- Menos código, preço nativo sempre visível. Painel à esquerda não cobre a escala.

## Como reverter
Voltar `left-3` → `right-3` no `ChartOrderPanel`.

Toca [[mercado]] · [[CandleChart]]
