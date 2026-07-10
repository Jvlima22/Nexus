---
tipo: ferramenta
categoria: orquestracao
status: em-teste
tags:
  - ferramenta
  - ia/orquestrador
criado: 2026-07-07
relacionado:
  - "[[OpenClaw]]"
  - "[[2026-07-07 Testar OpenSquad ao lado do OpenClaw]]"
---

# OpenSquad

## O que é
Framework open-source (MIT) de orquestração multi-agente que roda **dentro do IDE**
(Claude Code, Cursor, Antigravity). Você descreve um "squad" em linguagem natural, o agente
**Architect** desenha o time e monta um pipeline com checkpoints de aprovação humana.
Repo: https://github.com/renatoasse/opensquad

## Para que uso (no NEXUS)
**Em teste** ao lado do OpenClaw. Foco realista: **produção de conteúdo** (relatórios,
threads/posts sobre performance de trading), pesquisa e automações com humano no loop —
**não** o core de trading. Ver pegadinha abaixo.

## Como acessar
- Instalado via `npx opensquad init` na raiz do projeto (2026-07-07). Node 22.19 (precisa 20+).
- Comando: `/opensquad` no Claude Code (skill em `.claude/skills/opensquad/SKILL.md`).
  **Só funciona com o IDE aberto a partir da raiz do projeto.**
- Motor: `_opensquad/core/` (Architect + prompts Discovery→Design→Build).
- Squads gerados: `squads/<nome>/`. Memória da empresa: `_opensquad/_memory/company.md`.
- Dashboard "Virtual Office" (React/Phaser): `dashboard/` — `npm run dev` dentro da pasta.
- MCP: adicionou **Playwright MCP** em `.mcp.json` na raiz (navegação/publicação dos agentes).

## Fluxo básico
```
/opensquad                 # menu (1ª vez cai no onboarding: pede empresa + URL)
/opensquad create "..."    # Architect monta um squad novo
/opensquad run <nome>      # executa o pipeline (consome tokens PAGOS)
/opensquad list            # lista squads
/opensquad skills          # gerencia skills
```

## Skills que já vêm
Todas de **conteúdo/marketing**: blog/SEO, copywriting, Instagram (feed/reels/stories),
LinkedIn, YouTube, Twitter, email (sales/newsletter), image-ai-generator, canva, resend,
apify, blotato, instagram-publisher, template-designer. Criar custom: `opensquad-agent-creator`
e `opensquad-skill-creator`.

## Pegadinhas
- **Zero tooling de trading/finanças/risco out-of-the-box.** O framework é de squad de
  **conteúdo**. Pro core do NEXUS (funil de risco, decisão de trade, backtest) não ajuda
  direto — teria que construir agentes do zero. **Não substitui o [[OpenClaw]]** no papel
  operacional 24h (OpenSquad é sob demanda no IDE, não processo persistente).
- **Consome tokens pagos** a cada `run` — monitorar consumo.
- `install` puxou deps com vulnerabilidades (11 no root, 6 no dashboard) e Playwright reclamou
  de instalar browser sem deps do projeto. Aceitável p/ teste; revisar antes de prod.
- `git push` desta sessão deu 403 (credencial `comercialtglsolutions-dev` sem acesso ao repo)
  — problema separado, não relacionado ao OpenSquad.

## Como reverter
Apagar `_opensquad/`, `squads/`, `dashboard/`, `skills/`, `.claude/skills/opensquad/`,
`.agent/`, `.cursor/`, `.cursorignore` e o `.mcp.json` (ou remover só o server playwright).
Religar o OpenClaw. Nada disso foi commitado ainda no momento do teste.

## Alternativa considerada
Continuar só com o [[OpenClaw]] (já é o orquestrador do NEXUS). OpenSquad entrou apenas
como **teste paralelo**, sem desativar o OpenClaw.
