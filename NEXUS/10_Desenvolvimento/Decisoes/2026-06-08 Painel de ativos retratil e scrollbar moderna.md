---
tipo: decisao
data: 2026-06-08
tags: [ui, mercado, ux]
---

# Painel de ativos retrátil + scrollbar moderna (Mercado)

## Contexto
Na rota `/mercado` a lista de Ativos ocupava largura fixa (`grid lg:grid-cols-4`, `col-span-1`) e usava a scrollbar nativa do SO.

## Decisão
- **Scrollbar moderna:** classe `.scrollbar-modern` em `src/styles.css` (fina, arredondada, thumb realça em `--color-primary` no hover; `scrollbar-width: thin` p/ Firefox). Aplicada na lista de ativos.
- **Retrair/expandir:** estado `assetsOpen` em `mercado.tsx`. Botões `PanelLeftClose`/`PanelLeftOpen` (lucide). Retraído vira um rail fino (`lg:w-11`) com label vertical.
- **Layout flex:** topo trocado de `grid lg:grid-cols-4` para `flex lg:flex-row`. Card do gráfico agora é `flex-1 min-w-0` — ao retrair os Ativos, o gráfico **expande a largura** automaticamente.

## Consequências
- Largura do painel de Ativos fixada em `lg:w-72`.
- Sem libs novas (lucide e Tailwind já presentes). Typecheck verde.

## Como reverter
Voltar o container para `grid grid-cols-1 lg:grid-cols-4`, Ativos `lg:col-span-1`, gráfico `lg:col-span-3`; remover `assetsOpen`, os botões e a classe `.scrollbar-modern`.

Toca [[mercado]] · [[CandleChart]]
