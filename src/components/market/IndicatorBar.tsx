import { cn } from "@/lib/utils";
import type { IndicatorState, IndicatorKey } from "@/hooks/useChartIndicators";

const ITEMS: { key: IndicatorKey; label: string }[] = [
  { key: "bollinger", label: "BB" },
  { key: "ema9", label: "EMA9" },
  { key: "ema21", label: "EMA21" },
  { key: "sma", label: "SMA" },
  { key: "rsi", label: "RSI" },
  { key: "macd", label: "MACD" },
];

/** Chips de liga/desliga dos indicadores do gráfico ao vivo. */
export function IndicatorBar({
  state,
  onToggle,
}: {
  state: IndicatorState;
  onToggle: (key: IndicatorKey) => void;
}) {
  return (
    <div className="flex items-center gap-1">
      {ITEMS.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => onToggle(key)}
          aria-pressed={state[key]}
          title={`${state[key] ? "Ocultar" : "Mostrar"} ${label}`}
          className={cn(
            "px-2 py-1 text-[11px] rounded-md transition-colors tabular-nums",
            state[key]
              ? "bg-primary/15 text-primary"
              : "text-muted-foreground hover:text-foreground hover:bg-accent/60",
          )}
        >
          {label}
        </button>
      ))}
    </div>
  );
}
