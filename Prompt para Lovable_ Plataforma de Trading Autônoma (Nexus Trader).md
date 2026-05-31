# Prompt para Lovable: Plataforma de Trading Autônoma (Nexus Trader)

## Objetivo
Crie uma dashboard de trading profissional, moderna e minimalista para uma plataforma de trading autônoma orquestrada por IA. A interface deve transmitir confiança, clareza e controle técnico.

## Estilo Visual
*   **Tema:** Dark Mode profissional (Slate/Zinc) com acentos em Emerald (ganhos) e Rose (perdas).
*   **Estética:** Minimalista, estilo SaaS moderno (inspirado em Linear ou Stripe).
*   **Componentes:** Use bibliotecas como Shadcn/ui e Lucide React para ícones.

## Estrutura da Interface (Páginas/Seções)

### 1. Dashboard Principal (Visão Geral)
*   **Cards de Status:** Saldo Atual, Lucro/Prejuízo Diário (%), Operações Hoje, e Status do Agente (Online/Analisando/Operando).
*   **Gráfico de Performance:** Um gráfico de linha (Recharts) mostrando a evolução da banca ao longo do tempo.
*   **Monitor em Tempo Real:** Uma seção que exibe o "Pensamento da IA" (ex: "Analisando par BTC/USDT... Padrão de reversão identificado... Aguardando confirmação").

### 2. Painel de Controle (Gerenciamento)
*   **Configurações de Banca:** Inputs para Stop Loss Diário, Take Profit, e multiplicador de Alavancagem.
*   **Seleção de Estratégia:** Um dropdown para escolher entre "Conservadora (Kelly 0.5)", "Moderada" ou "Agressiva".
*   **Toggle de Operação:** Um botão grande e destacado para "Iniciar/Pausar Automação".

### 3. Histórico e Memória (Integração Obsidian)
*   **Tabela de Operações:** Lista com Ativo, Tipo (Call/Put), Resultado, Horário e um link para a "Nota de Memória" (simulando a integração com Obsidian).
*   **Log de Know-how:** Uma área de texto estilizada que mostra os últimos insights aprendidos pela IA (ex: "Aprendizado: Alta volatilidade em horários de notícias reduz assertividade da estratégia X").

### 4. Conexões (Corretoras)
*   Cards simples indicando o status da conexão com Binance e IQ Option (Conectado/Desconectado).

## Funcionalidades de UI/UX
*   **Feedback Visual:** Animações sutis de "pulsação" quando a IA está processando uma análise.
*   **Responsividade:** A plataforma deve ser totalmente funcional em desktop e mobile.
*   **Simulação de Dados:** Inicialmente, preencha com dados fictícios realistas para que eu possa ver a interface em funcionamento.

---

**Instrução Adicional:** Foque em uma arquitetura de código limpa usando React + Tailwind CSS, preparada para futuras integrações via API.
