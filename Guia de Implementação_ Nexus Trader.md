# Guia de Implementação: Nexus Trader

Este guia detalha o passo a passo para construir e integrar todos os componentes da plataforma Nexus Trader.

## Fase 1: Infraestrutura de Dados (Supabase)

1.  **Criação do Projeto:** Acesse o [Supabase](https://supabase.com/) e crie um novo projeto chamado "Nexus Trader".
2.  **Configuração do Banco de Dados:** No editor SQL do Supabase, execute os scripts para criar as tabelas:
    *   `profiles` (ID, user_id, api_keys, settings)
    *   `trades` (ID, asset, type, entry_price, exit_price, result, strategy_id)
    *   `ai_logs` (ID, timestamp, thought_process, action_taken)
    *   `bankroll_history` (ID, timestamp, balance)
3.  **Configuração do Storage:** Crie dois buckets: `context-files` (público para leitura) e `backups`.
4.  **Habilitar Realtime:** Vá em *Database > Replication* e habilite a replicação para as tabelas `trades` e `ai_logs` para que o frontend atualize instantaneamente.

## Fase 2: Frontend (Lovable + Supabase)

1.  **Conexão com Supabase:** No Lovable, use a integração nativa com o Supabase para conectar seu projeto.
2.  **Lógica de Autenticação:** Configure o login/signup usando o Supabase Auth.
3.  **Vinculação de Dados:**
    *   Substitua os dados fictícios dos gráficos por consultas à tabela `bankroll_history`.
    *   Conecte a tabela de operações à tabela `trades`.
    *   Vincule o terminal de logs à tabela `ai_logs`.
4.  **Central de Conhecimento:** Implemente a lógica de upload para que os arquivos sejam enviados diretamente para o bucket `context-files` do Supabase.

## Fase 3: Orquestração e IA (OpenClaw + Claude)

1.  **Instalação do OpenClaw:** Recomendamos rodar o OpenClaw em um servidor Linux (Ubuntu) via Docker ou instalação direta.
2.  **Configuração do Claude:** Insira sua `ANTHROPIC_API_KEY` nas configurações do OpenClaw.
3.  **Desenvolvimento de "Skills" (Scripts Python):**
    *   Crie um script `market_data.py` para ler WebSockets da Binance/IQ Option.
    *   Crie um script `order_execution.py` para enviar ordens de compra/venda.
    *   Crie um script `obsidian_sync.py` para ler/escrever arquivos Markdown.
4.  **Criação do Agente no OpenClaw:** Configure um agente chamado "Nexus Strategy" com as instruções (System Prompt) que definem sua estratégia de trading e gerenciamento de risco.

## Fase 4: Integração da Memória (Obsidian)

1.  **Estrutura de Pastas:** No seu computador (ou servidor), crie um vault do Obsidian com as pastas: `/Operacoes`, `/Aprendizados`, `/Estrategias`.
2.  **Instalação do Local REST API:** Instale este plugin no Obsidian para que o OpenClaw possa se comunicar com ele via HTTP.
3.  **Configuração de Sincronização:** Configure o OpenClaw para salvar um resumo de cada dia de trading na pasta `/Aprendizados`.

## Fase 5: O Loop de Automação

1.  **Webhooks de Comando:** Configure o Lovable para enviar um sinal (webhook) para o OpenClaw quando você clicar em "Iniciar Automação".
2.  **Loop de Decisão:**
    *   OpenClaw coleta dados -> Claude analisa -> Claude decide -> OpenClaw valida risco -> OpenClaw executa trade -> OpenClaw registra no Supabase e Obsidian.
3.  **Monitoramento:** Acompanhe tudo pelo dashboard do Lovable em tempo real.

## Fase 6: Testes e Refinamento

1.  **Paper Trading:** Antes de usar dinheiro real, configure as APIs das corretoras para o modo "Testnet" ou "Demo".
2.  **Backtesting:** Use o Claude para analisar os dados históricos salvos no Obsidian e refinar as estratégias.
3.  **Otimização de Prompt:** Ajuste o System Prompt do Claude conforme você observa o comportamento dele no mercado.

---
Este roteiro transforma a visão teórica em uma plataforma operacional. Cada fase concluída é um passo em direção a um sistema de trading verdadeiramente autônomo e inteligente.
