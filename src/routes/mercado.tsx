import { createFileRoute } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { CandleChart } from "@/components/market/CandleChart";
import { LiveTrades } from "@/components/market/LiveTrades";
import { useAssets, type AssetRow } from "@/hooks/useAssets";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/mercado")({
  head: () => ({
    meta: [
      { title: "Nexus Trader — Mercado" },
      { name: "description", content: "Candles ao vivo e ativos da IQ Option." },
    ],
  }),
  component: MarketPage,
});

const TIMEFRAMES: { label: string; size: number }[] = [
  { label: "1m", size: 60 },
  { label: "5m", size: 300 },
  { label: "15m", size: 900 },
  { label: "1h", size: 3600 },
];

const FALLBACK: AssetRow[] = ["EURUSD", "GBPUSD", "EURJPY", "USDJPY", "AUDCAD"].map((s) => ({
  id: s,
  symbol: s,
  name: s,
  type: "forex",
  is_open: true,
  payout: null,
}));

function MarketPage() {
  const live = useAssets();
  const assets = live.length ? live : FALLBACK;
  const [active, setActive] = useState("EURUSD");
  const [size, setSize] = useState(60);

  const selected = useMemo(() => assets.find((a) => a.symbol === active), [assets, active]);
  // Abertos primeiro, depois alfabético.
  const sorted = useMemo(
    () => [...assets].sort((a, b) => Number(b.is_open) - Number(a.is_open) || a.symbol.localeCompare(b.symbol)),
    [assets],
  );

  return (
    <AppLayout title="Mercado" subtitle="Candles ao vivo direto da IQ Option (via Connector)">
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Ativos */}
        <Card className="lg:col-span-1 p-0 bg-card border-border overflow-hidden flex flex-col">
          <div className="px-4 py-3 border-b border-border flex items-center justify-between">
            <h3 className="text-sm font-medium">Ativos</h3>
            <span className="text-xs text-muted-foreground tabular-nums">{assets.length}</span>
          </div>
          <div className="overflow-y-auto max-h-[520px]">
            {sorted.map((a) => (
              <button
                key={a.id}
                onClick={() => setActive(a.symbol)}
                className={cn(
                  "w-full flex items-center justify-between px-4 py-2.5 text-sm border-b border-border/50 transition-colors text-left",
                  a.symbol === active ? "bg-primary/10" : "hover:bg-accent/40",
                )}
              >
                <span className="flex items-center gap-2">
                  <span className={cn("h-1.5 w-1.5 rounded-full", a.is_open ? "bg-success" : "bg-danger")} />
                  <span className="font-medium">{a.symbol}</span>
                  <span className="text-[10px] uppercase text-muted-foreground">{a.type}</span>
                </span>
                {a.payout != null && (
                  <span className="text-xs tabular-nums text-muted-foreground">{a.payout}%</span>
                )}
              </button>
            ))}
            {live.length === 0 && (
              <p className="px-4 py-3 text-xs text-muted-foreground">
                Lista de fallback — sem dados do Supabase ainda. Verifique o sync do Connector
                (SUPABASE_* + NEXUS_USER_ID).
              </p>
            )}
          </div>
        </Card>

        {/* Gráfico */}
        <Card className="lg:col-span-3 p-0 bg-card border-border overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 border-b border-border">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium">{active}</span>
              {selected?.payout != null && (
                <span className="text-xs px-2 py-0.5 rounded bg-success/15 text-success tabular-nums">
                  payout {selected.payout}%
                </span>
              )}
              {selected && (
                <span className={cn("text-xs", selected.is_open ? "text-success" : "text-danger")}>
                  {selected.is_open ? "aberto" : "fechado"}
                </span>
              )}
            </div>
            <div className="flex items-center gap-1">
              {TIMEFRAMES.map((tf) => (
                <button
                  key={tf.size}
                  onClick={() => setSize(tf.size)}
                  className={cn(
                    "px-3 py-1.5 text-xs rounded-md transition-colors",
                    size === tf.size
                      ? "bg-primary/15 text-primary"
                      : "text-muted-foreground hover:text-foreground hover:bg-accent/60",
                  )}
                >
                  {tf.label}
                </button>
              ))}
            </div>
          </div>
          <div className="h-[480px] p-2">
            <CandleChart active={active} size={size} />
          </div>
        </Card>
      </div>

      <div className="mt-4">
        <LiveTrades active={active} />
      </div>
    </AppLayout>
  );
}
