import { TrendingUp, TrendingDown, Minus, Activity } from "lucide-react";
import { Card } from "@/components/ui/card";
import { useSentiment } from "@/hooks/useSentiment";
import type { MacroBias } from "@/lib/connector";
import { cn } from "@/lib/utils";

const BIAS_META: Record<MacroBias, { label: string; cls: string; Icon: typeof TrendingUp }> = {
  bullish: { label: "Bullish", cls: "text-success", Icon: TrendingUp },
  bearish: { label: "Bearish", cls: "text-danger", Icon: TrendingDown },
  neutral: { label: "Neutro", cls: "text-warning", Icon: Minus },
};

/**
 * Camada de Inteligência Preditiva (Polymarket) — bias macro em tempo real.
 * O bias agregado aqui é o MESMO que o Risk Judge usa como regra 0: numa direção
 * contrária, a ordem é vetada (MACRO_CONFLICT) no servidor.
 */
export function PolymarketFeed() {
  const { markets, macroBias } = useSentiment();
  const macro = BIAS_META[macroBias];

  return (
    <Card className="p-0 bg-card border-border overflow-hidden">
      <div className="px-5 py-4 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-medium">Sentimento Macro · Polymarket</h3>
        </div>
        <span className={cn("inline-flex items-center gap-1.5 text-xs font-medium", macro.cls)}>
          <macro.Icon className="h-3.5 w-3.5" />
          {macro.label}
        </span>
      </div>

      <div className="max-h-72 overflow-y-auto">
        {markets.length === 0 ? (
          <p className="px-5 py-6 text-sm text-muted-foreground text-center">
            Sem mercados monitorados. Defina <code className="text-xs">POLYMARKET_SLUGS</code> no
            Connector para puxar o bias macro.
          </p>
        ) : (
          markets.map((m) => {
            const meta = BIAS_META[m.bias];
            const pct = Math.round(m.probability * 100);
            return (
              <div key={m.slug} className="px-5 py-3 border-b border-border/50 last:border-0">
                <div className="flex items-start justify-between gap-3">
                  <span className="text-sm leading-snug flex-1">{m.question ?? m.slug}</span>
                  <span className={cn("inline-flex items-center gap-1 text-xs font-medium shrink-0", meta.cls)}>
                    <meta.Icon className="h-3.5 w-3.5" />
                    {pct}%
                  </span>
                </div>
                <div className="mt-2 h-1.5 rounded-full bg-muted overflow-hidden">
                  <div
                    className={cn(
                      "h-full transition-all",
                      m.bias === "bullish" ? "bg-success" : m.bias === "bearish" ? "bg-danger" : "bg-warning",
                    )}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                {m.volume != null && (
                  <div className="mt-1 text-[10px] text-muted-foreground tabular-nums">
                    vol ${Intl.NumberFormat("en", { notation: "compact" }).format(m.volume)}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </Card>
  );
}
