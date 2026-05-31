import { useEffect, useRef, useState } from "react";
import {
  createChart,
  ColorType,
  CrosshairMode,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type UTCTimestamp,
} from "lightweight-charts";
import { fetchCandles, openCandleStream, type Candle } from "@/lib/connector";
import { Loader2, WifiOff } from "lucide-react";

const toBar = (c: Candle): CandlestickData => ({
  time: c.time as UTCTimestamp,
  open: c.open,
  high: c.high,
  low: c.low,
  close: c.close,
});

export function CandleChart({ active, size }: { active: string; size: number }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<"loading" | "live" | "error">("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const chart: IChartApi = createChart(el, {
      width: el.clientWidth,
      height: el.clientHeight,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#a1a1aa", // zinc-400
      },
      grid: {
        vertLines: { color: "#27272a" }, // zinc-800
        horzLines: { color: "#27272a" },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: "#27272a" },
      timeScale: { borderColor: "#27272a", timeVisible: true, secondsVisible: false },
    });

    const series: ISeriesApi<"Candlestick"> = chart.addCandlestickSeries({
      upColor: "#10b981", // emerald-500
      downColor: "#f43f5e", // rose-500
      borderUpColor: "#10b981",
      borderDownColor: "#f43f5e",
      wickUpColor: "#10b981",
      wickDownColor: "#f43f5e",
    });

    let closeStream: (() => void) | null = null;
    let disposed = false;

    setStatus("loading");
    setError(null);

    fetchCandles(active, size)
      .then((candles) => {
        if (disposed) return;
        series.setData(candles.map(toBar));
        chart.timeScale().fitContent();
        setStatus("live");
        closeStream = openCandleStream(
          active,
          size,
          (c) => series.update(toBar(c)),
          (msg) => {
            setStatus("error");
            setError(msg);
          },
        );
      })
      .catch((e: unknown) => {
        if (disposed) return;
        setStatus("error");
        setError(e instanceof Error ? e.message : String(e));
      });

    const ro = new ResizeObserver(() => {
      chart.applyOptions({ width: el.clientWidth, height: el.clientHeight });
    });
    ro.observe(el);

    return () => {
      disposed = true;
      closeStream?.();
      ro.disconnect();
      chart.remove();
    };
  }, [active, size]);

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" />
      {status === "loading" && (
        <div className="absolute inset-0 grid place-items-center text-muted-foreground">
          <Loader2 className="h-5 w-5 animate-spin" />
        </div>
      )}
      {status === "error" && (
        <div className="absolute inset-0 grid place-items-center">
          <div className="flex flex-col items-center gap-2 text-danger text-sm">
            <WifiOff className="h-5 w-5" />
            <span>Não foi possível carregar</span>
            {error && <span className="text-xs text-muted-foreground max-w-xs text-center">{error}</span>}
          </div>
        </div>
      )}
    </div>
  );
}
