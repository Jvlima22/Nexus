---
tipo: decisao
data: 2026-06-08
tags: [ui, layout, sidebar]
---

# App-shell fixo: sidebar e topbar não rolam, só o conteúdo

## Contexto
O `AppLayout` era `min-h-screen flex` e crescia com o conteúdo. O `<aside>` (sidebar),
sendo filho flex, esticava até a altura do **documento inteiro** — então o rodapé do
sidebar (email + botão Sair) ia parar no fim da página. Em telas com conteúdo alto
(ex.: `/mercado`), ao rolar, email/sair sumiam pra muito abaixo da viewport. Valia
pra todas as páginas.

## Decisão
Shell de dashboard com viewport travada e scroll só no conteúdo:
- `AppLayout`: outer `min-h-screen` → `h-screen overflow-hidden`. `<main>` virou a
  única área rolável: `flex-1 min-h-0 overflow-y-auto scrollbar-modern`.
- `Topbar`: `+shrink-0` (mantém `h-16` fixo, não comprime).
- `Sidebar`: `+h-full`; `nav` ganhou `overflow-y-auto scrollbar-modern` (rola só a
  lista se crescer). O bloco de email/sair (`flex-1` no nav empurra) fica **travado no
  rodapé da viewport**.

## Consequências
- Sidebar + Topbar 100% fixos; email/sair sempre visíveis, independente de scroll/altura.
- **Scroll mudou em todas as telas**: agora rola dentro do `main`, não no `<body>`.
  Mobile inalterado (`MobileNav` fixo; sidebar é `hidden md:flex`).
- `min-h-0` no main é essencial: sem ele o flex item não encolhe e o overflow vaza.

## Como reverter
`AppLayout` outer volta a `min-h-screen flex`, `main` perde `min-h-0 overflow-y-auto`;
remover `shrink-0` do Topbar e `h-full`/`overflow-y-auto` do Sidebar.

Toca [[AppLayout]] · [[Sidebar]] · [[Topbar]]
