import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  CrosshairMode,
  LineStyle,
  type IChartApi,
  type CandlestickData,
  type LineData,
  type UTCTimestamp,
  type SeriesMarker,
} from "lightweight-charts";
import { ImageDown } from "lucide-react";
import type { TradeSnapshot } from "@/lib/snapshot";
import { ema, bollinger } from "@/lib/indicators";

const lineData = (times: UTCTimestamp[], vals: (number | null)[]): LineData[] =>
  times.map((t, i) => ({ time: t, value: vals[i] })).filter((d) => d.value != null) as LineData[];

/**
 * Redesenha o "print" do mercado no instante da ordem a partir do snapshot salvo:
 * candles + EMA9/EMA21 + bandas de Bollinger + suporte/resistência + marcador da
 * entrada. Botão exporta o gráfico como PNG (chart.takeScreenshot).
 */
export function SnapshotChart({ snapshot }: { snapshot: TradeSnapshot }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

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
    chartRef.current = chart;

    const candles = snapshot.candles;
    const times = candles.map((c) => c.time as UTCTimestamp);
    const closes = candles.map((c) => c.close);

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#10b981", downColor: "#f43f5e",
      borderUpColor: "#10b981", borderDownColor: "#f43f5e",
      wickUpColor: "#10b981", wickDownColor: "#f43f5e",
    });
    candleSeries.setData(
      candles.map((c): CandlestickData => ({
        time: c.time as UTCTimestamp, open: c.open, high: c.high, low: c.low, close: c.close,
      })),
    );

    // EMAs
    const addLine = (vals: (number | null)[], color: string, width: 1 | 2 = 1) => {
      const s = chart.addLineSeries({ color, lineWidth: width, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false });
      s.setData(lineData(times, vals));
    };
    addLine(ema(closes, 9), "#38bdf8"); // sky-400
    addLine(ema(closes, 21), "#f59e0b"); // amber-500

    // Bollinger
    const bb = bollinger(closes);
    addLine(bb.map((b) => b?.upper ?? null), "#52525b"); // zinc-600
    addLine(bb.map((b) => b?.lower ?? null), "#52525b");

    // Suporte / Resistência como linhas horizontais rotuladas
    const { support, resistance } = snapshot.support_resistance;
    if (resistance != null)
      candleSeries.createPriceLine({ price: resistance, color: "#f43f5e", lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: "R" });
    if (support != null)
      candleSeries.createPriceLine({ price: support, color: "#10b981", lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: "S" });

    // Marcador da entrada
    if (snapshot.entry.time != null) {
      const call = snapshot.entry.direction === "call";
      const marker: SeriesMarker<UTCTimestamp> = {
        time: snapshot.entry.time as UTCTimestamp,
        position: call ? "belowBar" : "aboveBar",
        color: call ? "#10b981" : "#f43f5e",
        shape: call ? "arrowUp" : "arrowDown",
        text: snapshot.entry.direction.toUpperCase(),
      };
      candleSeries.setMarkers([marker]);
    }

    chart.timeScale().fitContent();

    const ro = new ResizeObserver(() => chart.applyOptions({ width: el.clientWidth, height: el.clientHeight }));
    ro.observe(el);
    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [snapshot]);

  function exportPng() {
    const canvas = chartRef.current?.takeScreenshot();
    if (!canvas) return;
    const a = document.createElement("a");
    a.href = canvas.toDataURL("image/png");
    a.download = `${snapshot.asset}_${snapshot.timeframe}_${snapshot.entry.time ?? "snap"}.png`;
    a.click();
  }

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" />
      <button
        onClick={exportPng}
        className="absolute right-2 top-2 z-10 inline-flex items-center gap-1 rounded-md bg-background/80 border border-border px-2 py-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors"
        title="Exportar gráfico como PNG"
      >
        <ImageDown className="h-3.5 w-3.5" /> PNG
      </button>
    </div>
  );
}
