export const equityCurve = Array.from({ length: 30 }, (_, i) => {
  const base = 10000;
  const drift = i * 85;
  const noise = Math.sin(i / 2) * 220 + Math.cos(i / 1.3) * 180;
  return {
    day: `D${i + 1}`,
    value: Math.round(base + drift + noise),
  };
});

export const trades = [
  { id: "T-1042", asset: "BTC/USDT", type: "Call", result: 142.5, time: "14:32", note: "obsidian://btc-reversao-h1" },
  { id: "T-1041", asset: "ETH/USDT", type: "Put", result: -38.2, time: "14:08", note: "obsidian://eth-falha-suporte" },
  { id: "T-1040", asset: "EUR/USD", type: "Call", result: 78.0, time: "13:47", note: "obsidian://eurusd-breakout" },
  { id: "T-1039", asset: "SOL/USDT", type: "Call", result: 215.7, time: "13:21", note: "obsidian://sol-momentum" },
  { id: "T-1038", asset: "BTC/USDT", type: "Put", result: -52.1, time: "12:55", note: "obsidian://btc-fake-rejection" },
  { id: "T-1037", asset: "XRP/USDT", type: "Call", result: 64.3, time: "12:30", note: "obsidian://xrp-acumulacao" },
  { id: "T-1036", asset: "EUR/USD", type: "Put", result: 91.4, time: "11:58", note: "obsidian://eurusd-noticias" },
];

export const insights = [
  "Alta volatilidade em horários de notícias reduz assertividade da estratégia de reversão em 18%.",
  "Padrões de pin bar em H1 no BTC/USDT mantêm taxa de acerto de 71% nas últimas 50 operações.",
  "Reduzir alavancagem para 2x em sessões asiáticas melhora o Sharpe Ratio em 0.42 pontos.",
  "Correlação ETH/BTC > 0.85 indica reduzir exposição simultânea para evitar drawdown agrupado.",
];

export const thoughts = [
  "Analisando par BTC/USDT no timeframe H1...",
  "Detectado padrão de divergência bullish no RSI.",
  "Cruzando contexto macro: índice DXY em queda (-0.4%).",
  "Aguardando confirmação de volume acima da média 20.",
  "Risco calculado via Kelly: 1.8% do capital disponível.",
];

export type TerminalLine = {
  icon: string;
  time: string;
  text: string;
  tone?: "info" | "warn" | "ok" | "act";
};

export const terminalFeed: TerminalLine[] = [
  { icon: "🕒", time: "10:45:01", text: "Analisando par BTC/USDT no timeframe de 5min...", tone: "info" },
  { icon: "📊", time: "10:45:03", text: "Carregando 240 candles + livro de ofertas (depth 50).", tone: "info" },
  { icon: "🧠", time: "10:45:05", text: "RSI em 72 (Sobrecompra). Aguardando confirmação de Price Action.", tone: "warn" },
  { icon: "🔍", time: "10:45:07", text: "Cruzando memória Obsidian: 14 casos similares — 71% reversão.", tone: "info" },
  { icon: "✨", time: "10:45:09", text: "Padrão Estrela da Noite identificado em H1.", tone: "ok" },
  { icon: "🧮", time: "10:45:10", text: "Calculando risco via Kelly Criterion (p=0.62, b=0.85)...", tone: "info" },
  { icon: "✅", time: "10:45:12", text: "Sugestão: SHORT 0.024 BTC · SL $69.420 · TP $68.150.", tone: "ok" },
  { icon: "📝", time: "10:45:13", text: "Salvando nota #453 no Obsidian: 'reversao-btc-h1-2025'.", tone: "act" },
];

export type MemoryNote = {
  id: number;
  title: string;
  tag: string;
  outcome: "Sucesso" | "Falha" | "Pendente";
  body: string;
  updatedAt: string;
};

export const memoryNotes: MemoryNote[] = [
  {
    id: 453,
    title: "Reversão BTC em sobrecompra H1",
    tag: "price-action",
    outcome: "Sucesso",
    body: "Estrela da Noite + RSI > 70 + volume decrescente. Ajuste sugerido: ampliar SL em +0.4%.",
    updatedAt: "agora",
  },
  {
    id: 452,
    title: "Padrão de reversão em alta volatilidade",
    tag: "risco",
    outcome: "Sucesso",
    body: "Reduzir tamanho da ordem em -25% durante ATR > 2× média de 14 períodos.",
    updatedAt: "há 12 min",
  },
  {
    id: 451,
    title: "Falha de suporte ETH em sessão asiática",
    tag: "macro",
    outcome: "Falha",
    body: "Stop atingido por wick de 0.7%. Reescrever regra: aguardar fechamento de candle.",
    updatedAt: "há 38 min",
  },
  {
    id: 450,
    title: "Momentum SOL em rompimento",
    tag: "tendencia",
    outcome: "Sucesso",
    body: "Confluência de EMA 9>21 + volume 1.8× média. Manter como setup A+.",
    updatedAt: "há 1h",
  },
];

export type Indicator = {
  name: string;
  value: string;
  signal: "Bullish" | "Bearish" | "Neutral";
  detail: string;
};

export const indicators: Indicator[] = [
  { name: "RSI (14)", value: "72.4", signal: "Bearish", detail: "Sobrecompra" },
  { name: "EMA 9 / 21", value: "9 > 21", signal: "Bullish", detail: "Cruz. de alta" },
  { name: "MACD", value: "+0.18", signal: "Bullish", detail: "Histograma crescente" },
  { name: "Volume", value: "1.42×", signal: "Neutral", detail: "Acima da média" },
  { name: "ATR (14)", value: "1.8%", signal: "Bearish", detail: "Volatilidade alta" },
  { name: "Bollinger", value: "Upper", signal: "Bearish", detail: "Toque na banda" },
];
