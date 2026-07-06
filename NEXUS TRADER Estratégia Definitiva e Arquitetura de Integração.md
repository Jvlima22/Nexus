# NEXUS TRADER: Estratégia Definitiva e Arquitetura de Integração

Este documento consolida o **Master Plan** estratégico do Projeto Nexus, unindo a infraestrutura técnica do repositório GitHub, a inteligência preditiva da **Polymarket** e a metodologia profissional de **Price Action/Orderflow**.

---

## 1. Visão Geral do Ecossistema Nexus

O Nexus não é apenas um bot, mas uma plataforma de decisão orquestrada por IA (Claude 3.5 via OpenClaw) que utiliza dados em tempo real para executar operações de alta probabilidade.

### Stack Tecnológica Integrada
*   **Frontend**: React + Vite (Dashboard com Realtime Subscriptions).
*   **Backend**: Supabase (PostgreSQL + Realtime + Auth).
*   **Inteligência**: Polymarket API (Sentimento Macro) + Claude 3.5 (Análise de Cenários).
*   **Execução**: Python Connector (IQ Option / Binance) com Gate de Risco de 2%.
*   **Memória**: Obsidian Vault (Registro de diários e estratégias evolutivas).

---

## 2. A Camada de Inteligência Preditiva (Polymarket)

A Polymarket atua como o filtro primário de direção. Se a probabilidade real de um evento macro não sustenta o trade, a operação é descartada.

### Fluxo de Sentimento em Tempo Real
1.  **Coleta**: O `polymarket_connector.py` extrai dados de eventos com alto volume/volatilidade.
2.  **Processamento**: As probabilidades são convertidas em **Bias Direcional**:
    *   **Bullish**: Eventos favoráveis > 65%.
    *   **Bearish**: Eventos desfavoráveis > 65%.
    *   **Neutral**: Incerteza entre 40-60% (Ficar fora do mercado).
3.  **Exibição**: O componente `PolymarketFeed.tsx` mostra alertas, notícias e mudanças de probabilidade diretamente na tela principal do Nexus via Supabase Realtime.

---

## 3. Fluxo Operacional Profissional (As 8 Camadas)

Cada operação executada pelo Nexus deve passar por este funil de validação:

| Camada | Ferramenta | Ação Técnica |
| :--- | :--- | :--- |
| **1. Sentimento** | **Polymarket** | Define o Bias Macro (Compra/Venda). |
| **2. Calendário** | **ForexFactory** | Identifica janelas de volatilidade (Notícias de alto impacto). |
| **3. Contexto** | **TradingView** | Mapeamento de H4: Supply & Demand + Liquidity Sweeps. |
| **4. Estratégia** | **AMD Model** | Identifica Acumulação, Manipulação e Distribuição. |
| **5. Confirmação** | **Bookmap** | Valida se há ordens reais protegendo a zona de entrada. |
| **6. Gatilho** | **LTF (1m/5m)** | Busca por Break of Structure (BoS) e Fair Value Gap (FVG). |
| **7. Timing** | **Sessões** | Execução restrita às aberturas de Londres e Nova York. |
| **8. Registro** | **FXReplay/Obsidian** | Log automático da operação para backtesting e auditoria. |

---

## 4. Segurança e Automação de Rede (VPN-as-Code)

Dado o bloqueio geográfico no Brasil, o Nexus utiliza uma arquitetura de segurança em camadas para proteger a conta e garantir o acesso aos dados.

### Protocolo de Conexão
*   **Gatekeeper**: O script verifica a localização do IP via `ipapi.co` antes de qualquer chamada. Se detectar Brasil, o sistema trava.
*   **Automação VPN**:
    *   **Desenvolvimento**: Uso de Proton VPN CLI (`protonvpn-cli c --cc CA`).
    *   **Produção**: Docker Sidecar com **Gluetun** para roteamento obrigatório via Canadá/Japão.
*   **Privacidade**: Desativação de iCloud Private Relay e Localização do Safari no iOS para evitar vazamentos de WebRTC.

---

## 5. Implementação no Repositório Nexus

Para consolidar esta estratégia no seu código atual, siga esta estrutura de diretórios:

```text
Nexus/
├── connector/
│   ├── polymarket_connector.py    # Coleta e envia dados ao Supabase
│   ├── iq_client.py               # Execução na corretora
│   └── orders.py                  # Lógica de decisão (Bias Polymarket + Risco)
├── src/
│   ├── components/
│   │   └── market/
│   │       └── PolymarketFeed.tsx # Visualização em tempo real no Dashboard
├── NEXUS/
│   └── _Sistema/
│       └── Templates/
│           └── Sentimento.md      # Registro de análise macro no Obsidian
```

---

## 6. Próximos Passos de Evolução

1.  **Finalizar o SQL**: Criar a tabela `market_sentiment` no Supabase e ativar o Realtime.
2.  **Deploy do Connector**: Rodar o `polymarket_connector.py` em uma VPS internacional ou com VPN ativa.
3.  **Ajuste do Dashboard**: Integrar o `PolymarketFeed.tsx` na rota principal para monitoramento visual constante.
4.  **Escalabilidade**: Utilizar o histórico de acertos do Nexus para buscar financiamento na **@lvl.funding**.

---
**NEXUS: Onde a probabilidade encontra a precisão.**
