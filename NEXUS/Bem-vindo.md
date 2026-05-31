---
tipo: indice
tags:
  - indice
---

# NEXUS — Índice do Vault

Vault central para tudo: desenvolvimento, ferramentas, trading, registros e exclusões.

## Áreas

- [[00_Inbox]] — captura rápida, triagem depois
- [[10_Desenvolvimento]] — projetos, decisões técnicas, snippets
- [[20_Ferramentas]] — APIs, CLIs, SaaS, como uso cada uma
- [[30_Trading]] — estratégias, operações, mercados, pesquisa
- [[40_Registros]] — diário de bordo (o que aconteceu por dia)
- [[50_Exclusoes]] — o que foi removido e por quê
- [[90_Arquivo]] — concluído/obsoleto mas vale guardar
- [[_Sistema]] — templates e Bases

## Bases (views dinâmicas)

- ![[_Sistema/Bases/Trades-Abertos.base]]
- ![[_Sistema/Bases/Projetos-Ativos.base]]

## Convenções

- **Frontmatter obrigatório**: toda nota tem `tipo`, `tags`, e os campos do seu template
- **Pastas numeradas**: ordem fixa (00 → 90)
- **Sem acentos nos nomes de pastas** (compatibilidade com scripts/CLI)
- **Wikilinks** sempre que houver relação entre notas
- **Diário** é o registro autoritativo do que foi feito em cada dia

## Tipos de nota e templates

| Tipo | Template | Pasta destino |
|------|----------|---------------|
| Projeto | [[_Sistema/Templates/Projeto]] | `10_Desenvolvimento/Projetos/` |
| Decisão | [[_Sistema/Templates/Decisao]] | `10_Desenvolvimento/Decisoes/` |
| Ferramenta | [[_Sistema/Templates/Ferramenta]] | `20_Ferramentas/` |
| Estratégia | [[_Sistema/Templates/Estrategia]] | `30_Trading/Estrategias/` |
| Trade | [[_Sistema/Templates/Trade]] | `30_Trading/Operacoes/` |
| Diário | [[_Sistema/Templates/Diario]] | `40_Registros/Diario/` |
| Exclusão | [[_Sistema/Templates/Exclusao]] | `50_Exclusoes/` |
