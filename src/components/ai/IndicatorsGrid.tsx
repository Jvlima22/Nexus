import { Card } from "@/components/ui/card";
import { indicators } from "@/lib/mock-data";
import { Gauge, TrendingUp, TrendingDown, Minus } from "lucide-react";

const signalMeta = {
  Bullish: { cls: "text-success bg-success/10 border-success/25", Icon: TrendingUp },
  Bearish: { cls: "text-danger bg-danger/10 border-danger/25", Icon: TrendingDown },
  Neutral: { cls: "text-muted-foreground bg-muted/40 border-border", Icon: Minus },
} as const;

export function IndicatorsGrid() {
  return (
    <Card className="p-5 bg-card border-border">
      <div className="flex items-center gap-2 mb-4">
        <Gauge className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-medium">Sinais & Indicadores</h3>
        <span className="ml-auto text-[10px] text-muted-foreground">BTC/USDT · H1</span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
        {indicators.map((ind) => {
          const meta = signalMeta[ind.signal];
          const Icon = meta.Icon;
          return (
            <div
              key={ind.name}
              className="rounded-md border border-border bg-background/40 p-3"
            >
              <div className="flex items-center justify-between">
                <span className="text-[11px] text-muted-foreground">{ind.name}</span>
                <span className={`inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded border ${meta.cls}`}>
                  <Icon className="h-2.5 w-2.5" /> {ind.signal}
                </span>
              </div>
              <div className="mt-1.5 text-base font-semibold tabular-nums">{ind.value}</div>
              <div className="text-[10px] text-muted-foreground">{ind.detail}</div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
