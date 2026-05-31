---
tipo: ferramenta
categoria: orquestracao
status: ativa
tags:
  - ferramenta
  - ia/orquestrador
criado: 2026-05-24
relacionado:
  - "[[2026-05-24 RAG do Knowledge - Prompt Caching]]"
  - "[[2026-05-23 Custo da IA - API pay-as-you-go vs assinatura]]"
---

# OpenClaw

## O que é
Framework open-source de orquestração de agentes de IA (gateway self-hosted) que vai
ser o **orquestrador** do NEXUS — o cérebro (LLM) decide, o OpenClaw executa/supervisiona.

## Para que uso
Loop de trading autônomo: alimenta o LLM com dados de mercado, recebe a decisão, valida
risco e (no futuro) executa via Connector, registrando tudo no Obsidian. **Fase 1 atual:
análise read-only** (sem ordens).

## Como acessar
- CLI: `openclaw` (instalado via npm em `AppData\Roaming\npm\openclaw.ps1`) — v2026.3.28.
- Gateway local: `http://127.0.0.1:18789/` (Control UI). `bind: loopback`, auth por token.
- Workspace: `C:\Users\TGL Solutions\.openclaw\workspace` (skills, AGENTS.md, TOOLS.md, HEARTBEAT.md).
- Auth/LLM: perfil **`openai:default`** → modelo **`openai/gpt-5.4`** (fallback `gpt-4o`).
  **Decisão (2026-05-24): cérebro = GPT-5.4 agora; migrar p/ Claude quando houver crédito
  de API Anthropic.** Migração = `openclaw configure` (add provider anthropic) ou editar
  `openclaw.json` → `agents.defaults.model.primary` p/ `anthropic/claude-sonnet-4-6` + perfil
  de auth anthropic. Mudança de ~1 linha; a skill não muda.
- Canal **WhatsApp** ativo (allowlist do número do usuário) — usável p/ notificação.

## Comandos / endpoints frequentes
```
openclaw --version
# Skills do NEXUS: ~/.openclaw/workspace/skills/nexus_trader/SKILL.md
# Ambiente: ~/.openclaw/workspace/TOOLS.md (seção NEXUS)
# Loop: ~/.openclaw/workspace/HEARTBEAT.md (DESATIVADO por padrão)
```

## Integração com o NEXUS (Fase 1 — read-only)
- Skill `nexus_trader`: lê `GET /candles`,`/assets`,`/health` do Connector, analisa e
  grava nota em `30_Trading/Analises/` via **`POST /vault/note`** (endpoint novo no Connector,
  sandbox + allowlist de subpasta em `connector/vault.py`).
- **Barreira dura de risco fica no Connector** (gate 2% + bloqueio de saque). O LLM nunca
  recebe poder de furá-la. `POST /order` é proibido na Fase 1.
- Loop = `HEARTBEAT.md` (poll periódico do OpenClaw). Deixado **desativado** p/ não queimar
  tokens sem ordem explícita; cadência típica é de minutos (não tick-a-tick).

## Pegadinhas
- **Cérebro = OpenAI GPT-5.4 (decidido p/ agora).** "OpenClaw + Claude" fica p/ quando
  houver crédito de API Anthropic — exige add perfil de auth Anthropic + trocar o modelo.
  Pressupõe que a chave OpenAI tem crédito; se a Fase 1 não rodar, checar saldo OpenAI.
- Heartbeat não é tick-a-tick; "loop por candle" em alta frequência custa caro e foge do
  design do heartbeat (use cron p/ timing exato). Começar espaçado.
- Connector precisa estar rodando (`python main.py`) e a IQ conectada p/ a skill funcionar.

## Alternativas consideradas
- Construir o loop dentro do próprio Connector Python (sem framework) — mais controle,
  menos recursos prontos (multi-agente, canais, governança). Preterido a favor do OpenClaw,
  que já está instalado e traz orquestração + WhatsApp + limites de passos/tokens.
