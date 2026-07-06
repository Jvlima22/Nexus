---
tipo: decisao
data: 2026-06-08
tags: [ui, mercado, ux]
---

# Operações ao vivo em modal + painéis de decisão lado a lado

## Contexto
Na rota `/mercado` o rodapé era um grid 2+1: `LiveTrades` (ordem + tabela "Operações
ao vivo") ocupava 2 colunas e os 3 painéis de decisão (Autotrader, Sinal Técnico,
Sentimento Macro) ficavam empilhados em 1 coluna estreita à direita.

## Decisão
- **LiveTrades → modal:** botão "Operações" (ícone `Activity`) no header do gráfico
  abre um `Dialog` (shadcn) com o `LiveTrades` dentro. Estado `tradesOpen`.
  `DialogContent` em `max-w-4xl`, corpo com scroll `scrollbar-modern`.
- **Painéis lado a lado:** rodapé virou `grid md:grid-cols-3 items-start` com
  `AutotraderPanel`, `SignalPanel`, `PolymarketFeed` — abaixo do gráfico de moedas.

## Consequências
- Tela mais limpa; gráfico e decisões ganham foco. Operar/ver trades agora é
  ação deliberada (abrir modal).
- `LiveTrades` mantém form de ordem + tabela juntos (componente não foi dividido).

## Como reverter
Voltar o rodapé para `grid lg:grid-cols-3` com `LiveTrades` em `col-span-2` e os 3
painéis em `col-span-1 space-y-4`; remover `tradesOpen`, o botão e o `Dialog`.

Toca [[mercado]] · [[LiveTrades]]
