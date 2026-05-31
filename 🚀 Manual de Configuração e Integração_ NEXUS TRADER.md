# 🚀 Manual de Configuração e Integração: NEXUS TRADER

Este documento consolida todas as etapas necessárias para transformar o protótipo do **NEXUS** em uma plataforma de trading autônoma funcional, integrando Frontend, Banco de Dados (Supabase), Inteligência Artificial (Claude) e Orquestração (OpenClaw).

---

## 1. Configuração do Ambiente de Desenvolvimento

### Pré-requisitos
*   **Node.js v20+** ou **Bun** (Recomendado)
*   **Git**

### Comandos de Inicialização
Execute estes comandos na raiz da pasta `NEXUS`:

```powershell
# Instalar dependências
bun install

# Iniciar servidor local
bun dev
```

---

## 2. Banco de Dados: Supabase (O Coração)

### Passo 1: Criação das Tabelas
Acesse o **SQL Editor** no Supabase e execute o script abaixo para criar a estrutura profissional:

```sql
-- Tabelas Principais
CREATE TABLE profiles (id UUID PRIMARY KEY, api_keys JSONB, risk_profile TEXT);
CREATE TABLE trades (id UUID PRIMARY KEY, asset TEXT, type TEXT, result DECIMAL, time TIMESTAMPTZ);
CREATE TABLE ai_logs (id UUID PRIMARY KEY, icon TEXT, tone TEXT, text TEXT, created_at TIMESTAMPTZ);
CREATE TABLE bankroll_history (id UUID PRIMARY KEY, balance DECIMAL, timestamp TIMESTAMPTZ);
CREATE TABLE memory_notes (id BIGSERIAL PRIMARY KEY, title TEXT, tag TEXT, body TEXT);
```

### Passo 2: Ativar Realtime
Para atualizações instantâneas sem refresh:
```sql
ALTER PUBLICATION supabase_realtime 
ADD TABLE trades, ai_logs, bankroll_history;
```

---

## 3. Variáveis de Ambiente (.env)

Crie um arquivo `.env` na raiz do projeto com as seguintes chaves:

```env
# Supabase (Frontend)
VITE_SUPABASE_URL=https://seu-projeto.supabase.co
VITE_SUPABASE_ANON_KEY=sua-chave-anonima-aqui

# Inteligência Artificial (Orquestrador)
ANTHROPIC_API_KEY=sk-ant-api03-sua-chave-aqui

# Memória (Obsidian)
OBSIDIAN_API_KEY=sua-chave-do-plugin-aqui
OBSIDIAN_PORT=27123
```

---

## 4. Orquestração: OpenClaw + Claude

O OpenClaw atua como o motor que executa as decisões do Claude.

### Estrutura do Agente (`nexus_trader.yaml`)
Configure o comportamento da IA:

```yaml
name: "Nexus Trader"
role: "Estrategista de Trading de Elite"
system_prompt: |
  Você analisa o mercado via Binance/IQ Option.
  Decida entradas baseadas em Price Action e Volume.
  Registre logs no Supabase e insights no Obsidian.
tools:
  - binance_connector
  - iqoption_connector
  - supabase_sync
```

### Comando de Execução
```bash
python main.py --agent nexus_trader --mode autonomous
```

---

## 5. Fluxo de Operação Autônoma

1.  **Monitoramento:** OpenClaw coleta dados em tempo real.
2.  **Análise:** Claude (Cérebro) processa os dados e decide a ação.
3.  **Execução:** OpenClaw valida o risco e envia a ordem para a corretora.
4.  **Feedback:** O resultado aparece instantaneamente no seu Dashboard NEXUS.

---

## 6. Segurança e Melhores Práticas

*   **Paper Trading:** Sempre inicie em contas "Demo" ou "Testnet".
*   **Kill Switch:** Mantenha o botão de emergência do frontend funcional para interromper o OpenClaw instantaneamente.
*   **Gerenciamento de Risco:** Nunca configure o Claude para operar com mais de 2% da banca por trade.

---
*Documento gerado automaticamente para o projeto NEXUS Trader.*
