---
tipo: decisao
status: aceita
data: 2026-05-23
projeto: NEXUS Trader
tags:
  - dev/decisao
  - processo
relacionado:
  - "[[Bem-vindo]]"
---

# Decisão: Documentação obrigatória no Obsidian

## Contexto
O projeto NEXUS Trader integra Claude (IA), OpenClaw (orquestração), Supabase e Obsidian como camada de memória. Para que a memória cumpra seu papel, todo trabalho feito pelo Claude precisa ter rastro consultável depois — sem isso, o vault desatualiza e perde valor.

## Opções consideradas
1. **Confiar na memória do Claude Code** (arquivos em `.claude/memory/`): suficiente para preferências, mas invisível ao usuário no dia a dia e fragmentado por conversa.
2. **Registrar tudo no vault Obsidian**: índice único, navegável, com Bases dinâmicas e wikilinks. Custa o esforço de manter notas atualizadas.
3. **Híbrido**: memória do Claude para preferências de colaboração; Obsidian para artefatos de trabalho (decisões, exclusões, trades, projetos, ferramentas).

## Decisão
Opção 3 (híbrido), com a regra forte de que toda **inserção, alteração ou exclusão** que o Claude fizer deve gerar/atualizar uma nota no vault. A regra está codificada em:
- `CLAUDE.md` (seção "📓 Registro no Obsidian (OBRIGATÓRIO)") — vista por toda sessão do Claude no projeto
- Memórias `registro-obsidian` e `vault-nexus-estrutura` em `.claude/memory/`

## Consequências
- **Positivas:** o vault vira a fonte única de verdade do histórico; futuras conversas com Claude entram com contexto completo; trades, decisões e exclusões ficam queryáveis via Bases.
- **Negativas:** mais escrita de notas por sessão (overhead controlado pelos templates); risco de fricção se a regra for vista como burocrática.
- **A revisitar quando:** notarmos que notas estão sendo criadas mas não consultadas (sinal de overhead sem retorno), ou quando o volume justificar automação via Obsidian Local REST API (já habilitada na porta 27124).
