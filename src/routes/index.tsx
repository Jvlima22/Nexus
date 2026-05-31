import { createFileRoute } from "@tanstack/react-router";
import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { ArrowUpRight, ArrowDownRight, Wallet, TrendingUp, Activity } from "lucide-react";
import { ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid, Area, AreaChart } from "recharts";
import { equityCurve } from "@/lib/mock-data";
import { AITerminal } from "@/components/ai/AITerminal";
import { IndicatorsGrid } from "@/components/ai/IndicatorsGrid";
import { useBankroll } from "@/hooks/useBankroll";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Nexus Trader — Visão Geral" },
      { name: "description", content: "Dashboard de trading autônomo orquestrado por IA." },
    ],
  }),
  component: DashboardPage,
});

function Stat({
  label, value, delta, icon: Icon, positive, glow,
}: { label: string; value: string; delta?: string; icon: any; positive?: boolean; glow?: boolean }) {
  return (
    <Card className={cn("p-5 bg-card border-border rounded-lg transition-shadow", glow && "profit-glow")}>
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs text-muted-foreground uppercase tracking-wider">{label}</div>
          <div className="mt-2 text-2xl font-semibold tracking-tight tabular-nums">{value}</div>
          {delta && (
            <div className={`mt-1 inline-flex items-center gap-1 text-xs ${positive ? "text-success" : "text-danger"}`}>
              {positive ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
              {delta}
            </div>
          )}
        </div>
        <div className="h-9 w-9 grid place-items-center rounded-md bg-accent text-muted-foreground">
          <Icon className="h-4 w-4" />
        </div>
      </div>
    </Card>
  );
}

function DashboardPage() {
  const { points, latest } = useBankroll();
  const balanceFmt =
    latest != null ? latest.toLocaleString("pt-BR", { style: "currency", currency: "USD" }) : "—";
  // Série real do saldo; cai no mock se ainda não há dados.
  const equity = points.length ? points.map((p, i) => ({ day: String(i + 1), value: p.balance })) : equityCurve;

  return (
    <AppLayout title="Visão Geral" subtitle="Estado do agente e performance da banca">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Stat label="Saldo atual" value={balanceFmt} delta="banca IQ (tempo real)" positive icon={Wallet} />
        <Stat label="P/L diário" value="+$354,20" delta="+2.84%" positive icon={TrendingUp} />
        <Stat label="Operações hoje" value="14" delta="71% acerto" positive icon={Activity} />
        <StatusCard />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
        <Card className="lg:col-span-1 p-5 bg-card border-border">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-medium">Evolução da banca</h3>
              <p className="text-xs text-muted-foreground">Últimos 30 dias</p>
            </div>
            <div className="text-right">
              <div className="text-lg font-semibold tabular-nums">+$2.847,30</div>
              <div className="text-xs text-success">+28,5%</div>
            </div>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={equity}>
                <defs>
                  <linearGradient id="g1" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="oklch(0.72 0.17 160)" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="oklch(0.72 0.17 160)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="oklch(0.28 0.012 260)" vertical={false} />
                <XAxis dataKey="day" stroke="oklch(0.55 0.01 260)" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="oklch(0.55 0.01 260)" fontSize={11} tickLine={false} axisLine={false} width={50} />
                <Tooltip
                  contentStyle={{
                    background: "oklch(0.20 0.013 260)",
                    border: "1px solid oklch(0.28 0.012 260)",
                    borderRadius: 8,
                    fontSize: 12,
                  }}
                />
                <Area type="monotone" dataKey="value" stroke="oklch(0.72 0.17 160)" strokeWidth={2} fill="url(#g1)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <div className="lg:col-span-2">
          <AITerminal />
        </div>
      </div>

      <div className="mt-4">
        <IndicatorsGrid />
      </div>
    </AppLayout>
  );
}

function StatusCard() {
  return (
    <Card className="p-5 bg-card border-border">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs text-muted-foreground uppercase tracking-wider">Status do agente</div>
          <div className="mt-2 flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-success pulse-ring" />
            <span className="text-lg font-semibold">Operando</span>
          </div>
          <div className="mt-1 text-xs text-muted-foreground">Sessão #4821 · 02:14h</div>
        </div>
        <div className="h-9 w-9 grid place-items-center rounded-md bg-success/15 text-success">
          <Activity className="h-4 w-4" />
        </div>
      </div>
    </Card>
  );
}
