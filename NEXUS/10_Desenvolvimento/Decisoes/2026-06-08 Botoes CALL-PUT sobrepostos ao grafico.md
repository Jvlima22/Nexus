---
tipo: decisao
data: 2026-06-08
tags: [ui, mercado, trading, ux]
---

# Entrada de ordem sobreposta ao gráfico (estilo IQ Option)

## Contexto
O formulário de ordem (Valor + Expiração + CALL/PUT) vivia dentro do `LiveTrades`,
que estava no modal de operações. Pedido: mover a entrada pro gráfico, igual IQ Option.

## Decisão
- **Novo componente** `src/components/market/ChartOrderPanel.tsx`: carrega
  `amount`/`expiration`/`sending` + `submit` (`placeOrder` + toast). Render como
  overlay absoluto na **borda direita** do gráfico (`absolute right-3 top-1/2`),
  `w-40`, fundo `bg-card/80 backdrop-blur`, CALL verde (▲) em cima, PUT vermelho (▼).
- **`CandleChart` intocado** — o wrapper em `mercado.tsx` virou `relative` e recebe
  `<ChartOrderPanel active={active} />` como irmão sobreposto.
- **`LiveTrades` enxugado**: removido o form de ordem e props/imports relacionados
  (`placeOrder`, `toast`, ícones, `EXPIRATIONS`, prop `active`). Agora é só a tabela.
- **Modal** mostra apenas a tabela "Operações ao vivo".

## Consequências
- Operar é 1 clique direto no gráfico (UX IQ Option). Backend e gate de risco 2%
  inalterados.
- `LiveTrades` não recebe mais `active` — chamada em `mercado.tsx` atualizada.

## Como reverter
Reintroduzir o form de ordem no `LiveTrades` (ver git), remover `ChartOrderPanel`
e o wrapper `relative`, voltar `<LiveTrades active={active} />`.

Toca [[mercado]] · [[CandleChart]] · [[LiveTrades]]
