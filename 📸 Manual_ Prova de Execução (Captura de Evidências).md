# 📸 Manual: Prova de Execução (Captura de Evidências)

Este documento descreve a implementação da funcionalidade de captura automática de tela para o **NEXUS TRADER**, permitindo o registro visual de cada operação no banco de dados e no Obsidian.

---

## 1. Infraestrutura de Armazenamento (Supabase)

### Passo 1: Atualizar Tabela de Trades
Execute no SQL Editor do Supabase:
```sql
ALTER TABLE public.trades 
ADD COLUMN IF NOT EXISTS screenshot_url TEXT;
```

### Passo 2: Criar Bucket de Imagens
1. Vá em **Storage** no painel do Supabase.
2. Crie um novo bucket chamado `trade-screenshots`.
3. Marque como **Public** (opcional, para facilitar a visualização no frontend).

---

## 2. Automação de Captura (OpenClaw / Python)

Para capturar o gráfico no momento exato, o OpenClaw utilizará a biblioteca `playwright`.

### Script de Exemplo (`capture_trade.py`)
```python
import asyncio
from playwright.async_api import async_playwright

async def capture_market_moment(trade_id, asset):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_api_context().new_page()
        
        # URL do gráfico (ex: TradingView ou o próprio Dashboard NEXUS)
        await page.goto(f"https://www.tradingview.com/chart/?symbol={asset}")
        
        # Caminho do arquivo
        path = f"screenshots/trade_{trade_id}.png"
        await page.screenshot(path=path, full_page=False)
        
        await browser.close()
        return path
```

---

## 3. Integração com Obsidian

O OpenClaw deve formatar a nota de trade incluindo a imagem capturada.

### Template da Nota de Trade
```markdown
# 💹 Trade Executado: {{asset}}
**Data:** {{timestamp}}
**Resultado:** {{result}}

## 📸 Prova de Execução
![[trade_{{trade_id}}.png]]

> **Raciocínio da IA:** Entrada baseada em divergência de RSI e volume acima da média.
```

---

## 4. Visualização no Frontend (Lovable)

No componente de Histórico de Trades, adicione um botão para abrir a imagem:

```tsx
{trade.screenshot_url && (
  <Button onClick={() => window.open(trade.screenshot_url)}>
    Ver Gráfico 📷
  </Button>
)}
```

---

## 5. Benefícios para o Sistema
*   **Backtesting Visual:** Permite revisar se a IA entrou no ponto técnico correto.
*   **Auditoria:** Prova documental de que a ordem foi enviada com os parâmetros corretos.
*   **Memória Evolutiva:** O Claude pode analisar imagens passadas para ajustar sua estratégia futura.

---
*NEXUS Trader - Inteligência, Precisão e Memória.*
