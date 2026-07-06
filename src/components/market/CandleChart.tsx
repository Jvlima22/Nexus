import { useEffect, useRef, useState } from "react";
import {
  createChart,
  ColorType,
  CrosshairMode,
  LineStyle,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type LineData,
  type HistogramData,
  type UTCTimestamp,
} from "lightweight-charts";
import { fetchCandles, openCandleStream, type Candle } from "@/lib/connector";
import { ema, sma, bollinger, rsi, macd } from "@/lib/indicators";
import type { IndicatorState } from "@/hooks/useChartIndicators";
import { Loader2, WifiOff } from "lucide-react";

const toBar = (c: Candle): CandlestickData => ({
  time: c.time as UTCTimestamp,
  open: c.open,
  high: c.high,
  low: c.low,
  close: c.close,
});

// ── Registro declarativo das séries por indicador ──────────────────────────────
type Scale = "rsi" | "macd";
interface SeriesSpec {
  id: string;
  type: "line" | "hist";
  color?: string;
  width?: 1 | 2;
  style?: LineStyle;
  scale?: Scale; // ausente = escala de preço (sobre os candles)
}
const REGISTRY: Record<keyof IndicatorState, SeriesSpec[]> = {
  bollinger: [
    { id: "bb_upper", type: "line", color: "#52525b", width: 1 },
    { id: "bb_mid", type: "line", color: "#71717a", width: 1, style: LineStyle.Dotted },
    { id: "bb_lower", type: "line", color: "#52525b", width: 1 },
  ],
  ema9: [{ id: "ema9", type: "line", color: "#38bdf8", width: 2 }],
  ema21: [{ id: "ema21", type: "line", color: "#f59e0b", width: 2 }],
  sma: [{ id: "sma", type: "line", color: "#a78bfa", width: 2 }],
  rsi: [{ id: "rsi", type: "line", color: "#e879f9", width: 1, scale: "rsi" }],
  macd: [
    { id: "macd_hist", type: "hist", scale: "macd" },
    { id: "macd_line", type: "line", color: "#38bdf8", width: 1, scale: "macd" },
    { id: "macd_signal", type: "line", color: "#f43f5e", width: 1, scale: "macd" },
  ],
};
const SPEC_BY_ID: Record<string, SeriesSpec> = Object.fromEntries(
  Object.values(REGISTRY).flat().map((s) => [s.id, s]),
);

type Overlay = ISeriesApi<"Line"> | ISeriesApi<"Histogram">;
type Status = ["loading"] | ["live"] | ["error", string?];

const line = (times: UTCTimestamp[], vals: (number | null)[]): LineData[] =>
  times.map((t, i) => ({ time: t, value: vals[i] })).filter((d) => d.value != null) as LineData[];

const hist = (times: UTCTimestamp[], vals: (number | null)[]): HistogramData[] =>
  times
    .map((t, i) => ({ time: t, value: vals[i], color: (vals[i] ?? 0) >= 0 ? "#10b981" : "#f43f5e" }))
    .filter((d) => d.value != null) as HistogramData[];

/** Dados de uma série a partir dos candles (recomputa do zero — barato p/ ≤200 pts). */
function seriesData(id: string, candles: Candle[]): LineData[] | HistogramData[] {
  const times = candles.map((c) => c.time as UTCTimestamp);
  const closes = candles.map((c) => c.close);
  switch (id) {
    case "bb_upper": return line(times, bollinger(closes).map((b) => b?.upper ?? null));
    case "bb_mid": return line(times, bollinger(closes).map((b) => b?.mid ?? null));
    case "bb_lower": return line(times, bollinger(closes).map((b) => b?.lower ?? null));
    case "ema9": return line(times, ema(closes, 9));
    case "ema21": return line(times, ema(closes, 21));
    case "sma": return line(times, sma(closes, 50));
    case "rsi": return line(times, rsi(closes, 14));
    case "macd_line": return line(times, macd(closes).map((m) => m?.macd ?? null));
    case "macd_signal": return line(times, macd(closes).map((m) => m?.signal ?? null));
    case "macd_hist": return hist(times, macd(closes).map((m) => m?.hist ?? null));
    default: return [];
  }
}

function setOverlayData(s: Overlay, id: string, candles: Candle[]): void {
  if (SPEC_BY_ID[id].type === "hist") (s as ISeriesApi<"Histogram">).setData(seriesData(id, candles) as HistogramData[]);
  else (s as ISeriesApi<"Line">).setData(seriesData(id, candles) as LineData[]);
}

/** Ajusta as margens das escalas: osciladores ocupam faixas no rodapé, candles sobem. */
function applyMargins(chart: IChartApi, candleSeries: ISeriesApi<"Candlestick">, state: IndicatorState): void {
  const nOsc = (state.rsi ? 1 : 0) + (state.macd ? 1 : 0);
  const candleBottom = nOsc === 0 ? 0.06 : nOsc === 1 ? 0.32 : 0.46;
  candleSeries.priceScale().applyOptions({ scaleMargins: { top: 0.06, bottom: candleBottom } });
  if (state.rsi)
    chart.priceScale("rsi").applyOptions({ scaleMargins: nOsc === 2 ? { top: 0.56, bottom: 0.24 } : { top: 0.72, bottom: 0.06 } });
  if (state.macd)
    chart.priceScale("macd").applyOptions({ scaleMargins: nOsc === 2 ? { top: 0.78, bottom: 0.04 } : { top: 0.72, bottom: 0.06 } });
}

/** Cria/remove séries conforme os toggles e popula a partir dos candles em cache. */
function syncIndicators(
  chart: IChartApi,
  candleSeries: ISeriesApi<"Candlestick">,
  overlays: Map<string, Overlay>,
  candles: Candle[],
  state: IndicatorState,
): void {
  (Object.keys(REGISTRY) as (keyof IndicatorState)[]).forEach((key) => {
    REGISTRY[key].forEach((spec) => {
      const exists = overlays.has(spec.id);
      if (state[key] && !exists) {
        const common = {
          priceLineVisible: false,
          lastValueVisible: false,
          ...(spec.scale ? { priceScaleId: spec.scale } : {}),
        };
        const s: Overlay =
          spec.type === "hist"
            ? chart.addHistogramSeries(common)
            : chart.addLineSeries({
                ...common,
                color: spec.color,
                lineWidth: spec.width ?? 1,
                lineStyle: spec.style ?? LineStyle.Solid,
                crosshairMarkerVisible: false,
              });
        overlays.set(spec.id, s);
      } else if (!state[key] && exists) {
        chart.removeSeries(overlays.get(spec.id)!);
        overlays.delete(spec.id);
      }
    });
  });
  applyMargins(chart, candleSeries, state);
  overlays.forEach((s, id) => setOverlayData(s, id, candles));
}

export function CandleChart({
  active,
  size,
  indicators,
}: {
  active: string;
  size: number;
  indicators: IndicatorState;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const candlesRef = useRef<Candle[]>([]);
  const overlaysRef = useRef<Map<string, Overlay>>(new Map());
  const indicatorsRef = useRef(indicators);
  indicatorsRef.current = indicators; // sempre o estado mais recente p/ o stream

  const [status, setStatus] = useState<Status>(["loading"]);

  // ── chart + candles + stream (recria ao trocar ativo/timeframe) ──
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const chart = createChart(el, {
      width: el.clientWidth,
      height: el.clientHeight,
      layout: { background: { type: ColorType.Solid, color: "transparent" }, textColor: "#a1a1aa" },
      grid: { vertLines: { color: "#27272a" }, horzLines: { color: "#27272a" } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: "#27272a" },
      timeScale: { borderColor: "#27272a", timeVisible: true, secondsVisible: false },
    });
    const series = chart.addCandlestickSeries({
      upColor: "#10b981", downColor: "#f43f5e",
      borderUpColor: "#10b981", borderDownColor: "#f43f5e",
      wickUpColor: "#10b981", wickDownColor: "#f43f5e",
    });
    chartRef.current = chart;
    candleSeriesRef.current = series;
    overlaysRef.current = new Map();

    let closeStream: (() => void) | null = null;
    let disposed = false;
    setStatus(["loading"]);

    fetchCandles(active, size)
      .then((candles) => {
        if (disposed) return;
        candlesRef.current = candles;
        series.setData(candles.map(toBar));
        chart.timeScale().fitContent();
        syncIndicators(chart, series, overlaysRef.current, candles, indicatorsRef.current);
        setStatus(["live"]);
        closeStream = openCandleStream(
          active,
          size,
          (c) => {
            const arr = candlesRef.current;
            const last = arr[arr.length - 1];
            if (last && last.time === c.time) arr[arr.length - 1] = c;
            else arr.push(c);
            series.update(toBar(c));
            overlaysRef.current.forEach((s, id) => setOverlayData(s, id, candlesRef.current));
          },
          (msg) => setStatus(["error", msg]),
        );
      })
      .catch((e: unknown) => {
        if (disposed) return;
        setStatus(["error", e instanceof Error ? e.message : String(e)] as Status);
      });

    const ro = new ResizeObserver(() => chart.applyOptions({ width: el.clientWidth, height: el.clientHeight }));
    ro.observe(el);

    return () => {
      disposed = true;
      closeStream?.();
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      overlaysRef.current = new Map();
      candlesRef.current = [];
    };
  }, [active, size]);

  // ── reconcilia overlays quando os toggles mudam (sem refetch) ──
  useEffect(() => {
    const chart = chartRef.current;
    const series = candleSeriesRef.current;
    if (chart && series && candlesRef.current.length) {
      syncIndicators(chart, series, overlaysRef.current, candlesRef.current, indicators);
    }
  }, [indicators]);

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" />
      {status[0] === "loading" && (
        <div className="absolute inset-0 grid place-items-center text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin" />
        </div>
      )}
      {status[0] === "error" && (
        <div className="absolute inset-0 grid place-items-center">
          <div className="flex flex-col items-center gap-2 text-danger text-sm">
            <WifiOff className="h-5 w-5" />
            <span>Não foi possível carregar</span>
            {status[1] && <span className="text-xs text-muted-foreground max-w-xs text-center">{status[1]}</span>}
          </div>
        </div>
      )}
    </div>
  );
}

