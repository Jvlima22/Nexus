---
tipo: decisao
data: 2026-07-07
status: em-teste
tags:
  - decisao
  - ia/orquestrador
relacionado:
  - "[[OpenSquad]]"
  - "[[OpenClaw]]"
---

# 2026-07-07 Testar OpenSquad ao lado do OpenClaw

## Contexto
NEXUS já tem o [[OpenClaw]] como orquestrador (cérebro GPT-5.4, skill read-only, loop 24h
via `nexus_bot_24h.py`). O usuário quis **testar** o [[OpenSquad]] — outro framework
multi-agente, mas que roda dentro do IDE com checkpoints humanos.

## Opções
- **A — Trocar OpenClaw por OpenSquad.** Descartada: OpenSquad é sob demanda no IDE, não é
  processo persistente; não cobre operação autônoma 24h.
- **B — Rodar OpenSquad em paralelo (teste), sem desativar o OpenClaw.** ✅ Escolhida.
- **C — Ignorar o OpenSquad.** Descartada: usuário quer testar.

## Escolha
**B.** `npx opensquad init` na raiz (2026-07-07). OpenClaw permanece intacto. OpenSquad
tratado como camada de **conteúdo/pesquisa** com humano no loop, não como substituto do
orquestrador operacional.

## Consequências
- Novos diretórios no repo: `_opensquad/`, `squads/`, `dashboard/`, `skills/`, `.agent/`,
  `.cursor/`, `.mcp.json` (Playwright MCP), skill `.claude/skills/opensquad/`.
- `.gitignore` atualizado p/ não versionar deps e outputs do OpenSquad.
- **Descoberta:** skills nativas são só de conteúdo/marketing — zero trading. Encaixe real
  no NEXUS = relatórios/posts sobre performance, não decisão de trade.
- Cada `run` gasta tokens pagos.
- Reversível: ver seção "Como reverter" em [[OpenSquad]].

## Pendente
- Rodar `/opensquad` (onboarding: perfil da empresa) e criar 1º squad de teste (conteúdo).
- Resolver 403 do `git push` (credencial sem acesso a `Jvlima22/Nexus.git`) — separado.
