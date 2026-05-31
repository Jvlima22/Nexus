# Prompt de Evolução: Nexus Trader - Inteligência e Memória

## Objetivo
Melhorar a dashboard atual para incluir funcionalidades avançadas de monitoramento de IA, integração visual com a "Memória Obsidian" e detalhamento de gerenciamento de risco profissional.

## Novas Seções e Componentes

### 1. Terminal de Pensamento da IA (Claude Feed)
*   **Interface:** Crie um componente que simule um terminal de log moderno, mas com uma estética de "chat de sistema".
*   **Conteúdo:** Deve exibir o fluxo de raciocínio do Claude:
    *   "🕒 [10:45:01] Analisando par BTC/USDT no timeframe de 5min..."
    *   "🧠 [10:45:05] RSI em 72 (Sobrecompra). Aguardando confirmação de Price Action."
    *   "✅ [10:45:10] Padrão Estrela da Noite identificado. Calculando risco via Kelly Criterion..."
*   **Visual:** Fonte mono-espaçada, texto com cores suaves (dimmed), e animação de digitação.

### 2. Módulo de Memória e Know-how (Obsidian Bridge)
*   **Componente:** Uma aba ou seção chamada "Base de Conhecimento".
*   **Funcionalidade:** Exiba cards que representam "Notas de Memória" que a IA acabou de salvar ou consultar.
*   **Exemplo:** "Nota #452: Padrão de reversão em alta volatilidade. Resultado: Sucesso. Ajuste de parâmetro sugerido: +2% de margem."
*   **Estética:** Ícone de arquivo/documento, indicando que a IA está "escrevendo" no Obsidian em tempo real.

### 3. Visualizador de Gerenciamento de Risco (Pro)
*   **Gráfico de Alocação:** Um gráfico circular ou barra de progresso mostrando quanto da banca está em risco na operação atual.
*   **Calculadora Kelly:** Exiba o cálculo dinâmico: "Banca: $1000 | Probabilidade: 60% | Payback: 80% -> Sugestão Kelly: $25.00".
*   **Painel de Alavancagem:** Um slider visual que mostra o nível de alavancagem atual e o "Risco de Ruína" associado.

### 4. Seção de Sinais e Indicadores Ativos
*   **Grid de Indicadores:** Pequenos widgets para RSI, Médias Móveis (9/21), MACD e Volume.
*   **Status:** Cada indicador deve ter um badge de "Bullish", "Bearish" ou "Neutral" baseado na análise da IA.

### 5. Controle de Autonomia (Mode Selector)
*   **Botões de Estado:**
    *   **Manual:** Apenas sinais, você executa.
    *   **Híbrido:** IA sugere, você confirma no dashboard.
    *   **Full Auto:** IA orquestra tudo (Claude no comando).

## Melhorias de UX/UI
*   **Micro-interações:** Adicione um efeito de "Glow" verde ao redor do saldo quando uma operação é fechada com lucro.
*   **Notificações Toast:** Use toasts para avisar quando a IA "Aprendeu algo novo" ou "Atualizou a memória no Obsidian".
*   **Layout:** Garanta que o terminal de pensamento da IA tenha destaque, pois é o coração da plataforma.

---
**Instrução Técnica:** Continue usando Shadcn/ui e Tailwind. Mantenha o código modular para que eu possa conectar as APIs reais facilmente depois.
