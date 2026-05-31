---
tipo: decisao
status: aceita
data: 2026-05-23
projeto: NEXUS Trader
tags:
  - dev/decisao
  - processo
  - automacao
relacionado:
  - "[[2026-05-23 Documentacao obrigatoria no Obsidian]]"
---

# Decisão: Hooks de auto-log no diário do Obsidian

## Contexto
A regra "tudo deve ser documentado no Obsidian" ([[2026-05-23 Documentacao obrigatoria no Obsidian]]) depende do Claude lembrar de atualizar o diário a cada sessão. Mesmo com `CLAUDE.md` reforçando, isso é instrução — não execução. Para ser **100% automático**, o harness do Claude Code precisa executar a ação, não o modelo.

## Opções consideradas
1. **Só instrução textual** (`CLAUDE.md` + memórias): confiável, mas não garantido. Se o Claude esquecer numa sessão longa, fica buraco no diário.
2. **Hooks do Claude Code** (`PostToolUse`, `SessionStart`): o harness executa scripts shell em pontos do ciclo de vida. Independe da disciplina do modelo.
3. **MCP server custom + Obsidian REST API** (porta 27124, já habilitada): mais flexível e estruturado, mas overkill para o objetivo atual de auto-log.

## Decisão
Opção 2 — hooks. Mantém a opção 1 ativa (defesa em profundidade) e adia a opção 3 para quando volume justificar.

Configuração em `.claude/settings.json` (project-level, vale para qualquer Claude rodando no diretório):
- **`SessionStart`** → `ensure-diary.ps1` cria `40_Registros/Diario/YYYY-MM-DD.md` se não existir, com frontmatter e seções do template.
- **`PostToolUse` em `Write|Edit`** → `log-activity.ps1` injeta uma linha `- HH:mm \`[Tool]\` \`path\`` na seção "## Tocado hoje" do diário.

Exclusões automáticas: arquivos dentro do próprio vault (evita ruído/recursão), `.claude/`, `node_modules/`, `memory/`.

## Consequências
- **Positivas:** zero esforço manual para registrar arquivos tocados; o diário fica completo mesmo se o Claude esquecer; funciona para qualquer Claude/agente que rodar no projeto.
- **Negativas:** hooks rodam via PowerShell — qualquer mudança nos paths quebra. Exit code é silencioso (`try/catch` engole erros) para nunca travar uma sessão; em troca, falhas precisam ser detectadas inspecionando o diário.
- **Caveat conhecido:** quando `.claude/` é criado pela primeira vez no meio de uma sessão (como hoje), o watcher do Claude Code não pega — só vale na próxima sessão ou após abrir `/hooks` no menu.
- **A revisitar quando:** quisermos auto-log também para `Bash` (commits, instalações), ou quando o volume justificar push direto via Obsidian REST API.

## Arquivos
- `.claude/settings.json` — declaração dos hooks
- `.claude/hooks/ensure-diary.ps1`
- `.claude/hooks/log-activity.ps1`
