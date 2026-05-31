# NEXUS Trader

Plataforma de trading autônoma integrada com Inteligência Artificial (Claude), Orquestração (OpenClaw), Banco de Dados (Supabase) e Memória de Aprendizado (Obsidian).

---

## 🚀 Diretrizes de Economia de Tokens (CRÍTICO)
Para minimizar o consumo de tokens e otimizar o custo de contexto em cada mensagem:
- **Estilo Conciso-First:** Vá direto ao ponto técnico. Pule introduções, saudações, conclusões e explicações óbvias.
- **Apenas Diffs:** Quando sugerir alterações de código, **nunca** reescreva arquivos inteiros. Envie apenas a alteração pontual (formato git diff ou trecho isolado com linhas de início/fim).
- **Sem Boilerplate:** Evite gerar explicações extensas sobre o que o código faz, a menos que solicitado.
- **Decisões Diretas:** Se houver ambiguidade no design, proponha alternativas diretas (Ex: Opção A ou Opção B) para resposta rápida.

---

## 🛠️ Stack Tecnológica & Comandos
- **Ambiente:** Bun (Recomendado) ou Node.js (v20+)
- **Frontend:** React + TypeScript + Vite + Tailwind CSS + Shadcn/ui
- **Banco de Dados & Realtime:** Supabase (tabelas `trades`, `ai_logs`, `bankroll_history`, `profiles`, `memory_notes`)
- **Integração IA:** Anthropic API (Claude 3.5 Sonnet / Claude 3 Haiku)
- **Orquestração:** OpenClaw (Agente `nexus_trader.yaml` operando via Python)
- **Memória:** Obsidian via Local REST API (porta 27124)

### Comandos de Terminal
*   **Instalação:** `bun install` ou `npm install`
*   **Iniciar Frontend (Dev):** `bun dev` ou `npm run dev`
*   **Build:** `bun run build` ou `npm run build`
*   **Linting:** `bun run lint` ou `npm run lint`
*   **Testar Conexão Claude:** `powershell -ExecutionPolicy Bypass -File test-claude.ps1`

---

## 📂 Estrutura de Pastas e Componentes
- `src/components/` - Componentes reutilizáveis de UI (Shadcn)
- `src/pages/` - Páginas principais (Dashboard, Operações, Configurações)
- `src/lib/` - Clientes de integração (Supabase, API Obsidian, etc.)
- `.env` - Chaves de ambiente (Supabase URL/Anon Key, Anthropic API Key)

---

## 📌 Padrões de Desenvolvimento
- **TypeScript Estrito:** Tipagem explícita para todas as funções. Proibido o uso de `any`.
- **UI Consistente:** Dark mode nativo usando tons de Zinc/Slate. Emerald/Green para lucros e Rose/Red para prejuízos.
- **Atualização Realtime:** Use as assinaturas em tempo real do Supabase para manter painéis atualizados sem refresh.
- **Autonomia & Segurança:** O orquestrador deve validar o gerenciamento de risco (ex: limite de 2% de alocação por operação) antes de encaminhar qualquer sinal de compra/venda vindo da IA.

---

## 📓 Registro no Obsidian (OBRIGATÓRIO)
Vault: `./NEXUS/` (índice em `./NEXUS/Bem-vindo.md`). Toda inserção, alteração ou exclusão que o Claude fizer deve ser documentada lá:
- **Novo projeto/arquivo/feature/dependência:** nota no diretório certo a partir de `_Sistema/Templates/` (Projeto, Ferramenta, Estratégia, Trade).
- **Decisão técnica:** nota em `10_Desenvolvimento/Decisoes/` (contexto, opções, escolha, consequências).
- **Exclusão de código/feature/ideia:** nota em `50_Exclusoes/` com motivo real (não "limpeza") e como reverter.
- **Trade executado/fechado:** nota em `30_Trading/Operacoes/` usando o template Trade.
- **Toda sessão:** entrada em `40_Registros/Diario/YYYY-MM-DD.md` com wikilinks para o que foi tocado.

Regra de ouro: se não está no vault, não aconteceu. O diário do dia é o índice autoritativo da sessão.
