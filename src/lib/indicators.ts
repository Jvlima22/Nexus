/**
 * Indicadores técnicos no cliente — séries por ponto alinhadas aos candles (null no
 * warm-up). Espelham as fórmulas do connector (`connector/indicators.py`) p/ o gráfico
 * ao vivo e o snapshot mostrarem os mesmos números. Puro, sem dependências.
 */

/** EMA; seed no 1º ponto, null até juntar `period` pontos (antes é instável). */
export function ema(values: number[], period: number): (number | null)[] {
  if (!values.length) return [];
  const k = 2 / (period + 1);
  const out: number[] = [values[0]];
  for (let i = 1; i < values.length; i++) out.push(values[i] * k + out[i - 1] * (1 - k));
  return out.map((v, i) => (i >= period - 1 ? v : null));
}

/** SMA simples por janela; null antes de juntar `period` pontos. */
export function sma(values: number[], period: number): (number | null)[] {
  return values.map((_, i) => {
    if (i < period - 1) return null;
    let s = 0;
    for (let j = i - period + 1; j <= i; j++) s += values[j];
    return s / period;
  });
}

export interface BollingerPoint {
  mid: number;
  upper: number;
  lower: number;
}

/** Bandas de Bollinger (SMA ± mult·σ). null antes de juntar a janela. */
export function bollinger(values: number[], period = 20, mult = 2): (BollingerPoint | null)[] {
  return values.map((_, i) => {
    if (i < period - 1) return null;
    const win = values.slice(i - period + 1, i + 1);
    const mid = win.reduce((a, b) => a + b, 0) / period;
    const sd = Math.sqrt(win.reduce((a, b) => a + (b - mid) ** 2, 0) / period);
    return { mid, upper: mid + mult * sd, lower: mid - mult * sd };
  });
}

/** RSI clássico (médias simples de ganhos/perdas). null nos primeiros `period` pontos. */
export function rsi(values: number[], period = 14): (number | null)[] {
  const out: (number | null)[] = values.map(() => null);
  for (let i = period; i < values.length; i++) {
    let gains = 0;
    let losses = 0;
    for (let j = i - period + 1; j <= i; j++) {
      const diff = values[j] - values[j - 1];
      if (diff >= 0) gains += diff;
      else losses -= diff;
    }
    const avgGain = gains / period;
    const avgLoss = losses / period;
    out[i] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  }
  return out;
}

export interface MacdPoint {
  macd: number;
  signal: number;
  hist: number;
}

/** MACD (EMA fast − EMA slow) + linha de sinal + histograma. null no warm-up. */
export function macd(values: number[], fast = 12, slow = 26, signal = 9): (MacdPoint | null)[] {
  if (values.length < slow + signal) return values.map(() => null);
  const ef = emaRaw(values, fast);
  const es = emaRaw(values, slow);
  const macdLine = values.map((_, i) => ef[i] - es[i]);
  const signalLine = emaRaw(macdLine, signal);
  return values.map((_, i) => {
    if (i < slow + signal - 2) return null;
    return { macd: macdLine[i], signal: signalLine[i], hist: macdLine[i] - signalLine[i] };
  });
}

/** EMA "crua" (sem nulls) — uso interno do MACD. */
function emaRaw(values: number[], period: number): number[] {
  if (!values.length) return [];
  const k = 2 / (period + 1);
  const out: number[] = [values[0]];
  for (let i = 1; i < values.length; i++) out.push(values[i] * k + out[i - 1] * (1 - k));
  return out;
}
