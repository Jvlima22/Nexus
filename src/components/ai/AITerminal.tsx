import { useEffect, useMemo, useRef } from "react";
import { Card } from "@/components/ui/card";
import { Terminal } from "lucide-react";
import { cn } from "@/lib/utils";
import { useRiskEvents, type RiskEvent } from "@/hooks/useRiskEvents";
import { useTrades, tradePair, tradeDirection, type TradeRow } from "@/hooks/useTrades";

type Tone = "info" | "warn" | "ok" | "act";
interface Line {
  ts: number;
  icon: string;
  time: string;
  text: string;
  tone: Tone;
}

const toneClass: Record<Tone, string> = {
  info: "text-foreground/70",
  warn: "text-warning",
  ok: "text-success",
  act: "text-primary",
};

function fmtTime(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString("pt-BR");
}

function riskEventToLine(e: RiskEvent): Line {
  const approved = e.decision === "approved";
  return {
    ts: new Date(e.created_at).getTime(),
    icon: approved ? "✅" : "🚫",
    time: fmtTime(e.created_at),
    text: approved
      ? `Risk Judge aprovou ${e.asset} ${e.direction}`
      : `Risk Judge vetou ${e.asset} ${e.direction}: ${e.code} — ${e.reason}`,
    tone: approved ? "ok" : "warn",
  };
}

function tradeToLine(t: TradeRow): Line {
  const pair = tradePair(t);
  const dir = tradeDirection(t) ?? "";
  if (t.status === "open") {
    return {
      ts: t.time ? new Date(t.time).getTime() : 0,
      icon: "📈",
      time: fmtTime(t.time),
      text: `Abriu ${dir} ${pair}`,
      tone: "act",
    };
  }
  const pnl = t.pnl ?? t.result ?? 0;
  return {
    ts: t.closed_at ? new Date(t.closed_at).getTime() : t.time ? new Date(t.time).getTime() : 0,
    icon: pnl >= 0 ? "💰" : "🔻",
    time: fmtTime(t.closed_at ?? t.time),
    text: `Fechou ${pair}: ${pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}`,
    tone: pnl >= 0 ? "ok" : "warn",
  };
}

/** Feed real do Risk Judge + trades da conta selecionada (sem mock). */
export function AITerminal({ source, className }: { source: string; className?: string }) {
  const riskEvents = useRiskEvents(source, 20);
  const trades = useTrades(100);
  const scrollRef = useRef<HTMLDivElement>(null);

  const lines = useMemo(() => {
    const fromRisk = riskEvents.map(riskEventToLine);
    const fromTrades = trades.filter((t) => t.source === source).map(tradeToLine);
    return [...fromRisk, ...fromTrades].sort((a, b) => a.ts - b.ts).slice(-15);
  }, [riskEvents, trades, source]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [lines.length]);

  return (
    <Card className={cn("p-0 bg-card border-border overflow-hidden", className)}>
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border bg-background/40">
        <div className="flex items-center gap-2">
          <span className="flex gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-danger/70" />
            <span className="h-2.5 w-2.5 rounded-full bg-warning/70" />
            <span className="h-2.5 w-2.5 rounded-full bg-success/70" />
          </span>
          <Terminal className="h-3.5 w-3.5 text-muted-foreground ml-2" />
          <span className="text-[11px] uppercase tracking-wider text-muted-foreground">
            claude — nexus://thoughts
          </span>
        </div>
        <span className="text-[10px] text-success flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-success animate-thinking" /> tempo real
        </span>
      </div>

      <div
        ref={scrollRef}
        className="font-mono text-[12.5px] leading-relaxed p-4 h-[340px] overflow-y-auto bg-background/30"
      >
        {lines.length === 0 && (
          <div className="text-muted-foreground/60">Sem atividade registrada ainda para esta conta.</div>
        )}
        {lines.map((line, i) => (
          <div key={`${line.ts}-${i}`} className="flex gap-2 items-baseline animate-fade-in">
            <span className="text-muted-foreground/60 tabular-nums select-none">
              {line.icon} [{line.time}]
            </span>
            <span className={toneClass[line.tone]}>{line.text}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}
