import { useCallback, useEffect, useState } from "react";

/** Quais indicadores estão ligados no gráfico ao vivo. */
export interface IndicatorState {
  bollinger: boolean;
  ema9: boolean;
  ema21: boolean;
  sma: boolean;
  rsi: boolean;
  macd: boolean;
}

export type IndicatorKey = keyof IndicatorState;

const STORAGE_KEY = "nexus.chart.indicators";
const DEFAULT: IndicatorState = {
  bollinger: true, // já mostra valor de cara; resto desligado p/ não poluir
  ema9: false,
  ema21: false,
  sma: false,
  rsi: false,
  macd: false,
};

function load(): IndicatorState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? { ...DEFAULT, ...(JSON.parse(raw) as Partial<IndicatorState>) } : DEFAULT;
  } catch {
    return DEFAULT;
  }
}

/** Estado dos indicadores do gráfico, persistido no localStorage. */
export function useChartIndicators(): [IndicatorState, (key: IndicatorKey) => void] {
  const [state, setState] = useState<IndicatorState>(DEFAULT);

  // Lê do localStorage só no cliente (SSR-safe).
  useEffect(() => {
    setState(load());
  }, []);

  const toggle = useCallback((key: IndicatorKey) => {
    setState((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      } catch {
        /* localStorage indisponível — ignora */
      }
      return next;
    });
  }, []);

  return [state, toggle];
}
