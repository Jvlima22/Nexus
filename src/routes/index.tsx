import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { ArrowUpRight, ArrowDownRight, Wallet, TrendingUp, Activity } from "lucide-react";
import { ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid, Area, AreaChart } from "recharts";
import { equityCurve } from "@/lib/mock-data";
import { AITerminal } from "@/components/ai/AITerminal";
import { IndicatorsGrid } from "@/components/ai/IndicatorsGrid";
import { useBankroll } from "@/hooks/useBankroll";
import { useTrades } from "@/hooks/useTrades";
import { useRiskEvents } from "@/hooks/useRiskEvents";
import { cn } from "@/lib/utils";

type Account = "mt5" | "iq";
/** Conta selecionada → `source` usado em bankroll_history/trades/risk_events. */
const ACCOUNT_SOURCE: Record<Account, string> = { mt5: "nexus_mt5", iq: "nexus" };
const ACCOUNT_LABEL: Record<Account, string> = { mt5: "MT5 (real)", iq: "IQ Option (practice)" };

export const Route = createFileRoute("/")({
  validateSearch: (s: Record<string, unknown>): { account: Account } => ({
    account: s.account === "iq" ? "iq" : "mt5",
  }),
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

function todayStartIso(): string {
  const d = new Date();
  d.setUTCHours(0, 0, 0, 0);
  return d.toISOString();
}

function DashboardPage() {
  const { account } = Route.useSearch();
  const navigate = useNavigate({ from: Route.fullPath });
  const source = ACCOUNT_SOURCE[account];

  const { points, latest } = useBankroll(source);
  const allTrades = useTrades(100);
  const riskEvents = useRiskEvents(source, 10);

  const trades = allTrades.filter((t) => t.source === source);

  const balanceFmt =
    latest != null ? latest.balance.toLocaleString("pt-BR", { style: "currency", currency: "USD" }) : "—";
  // Série real do saldo; cai no mock se ainda não há snapshots pra essa conta.
  const equity = points.length ? points.map((p, i) => ({ day: String(i + 1), value: p.balance })) : equityCurve;
  const equityDelta = points.length >= 2 ? points[points.length - 1].balance - points[0].balance : null;

  const todayIso = todayStartIso();
  const closedToday = trades.filter((t) => t.closed_at && t.closed_at >= todayIso);
  const openedToday = trades.filter((t) => t.time && t.time >= todayIso);
  const pnlToday = closedToday.reduce((sum, t) => sum + (t.pnl ?? t.result ?? 0), 0);
  const wins = closedToday.filter((t) => (t.pnl ?? t.result ?? 0) > 0).length;
  const winRate = closedToday.length ? Math.round((wins / closedToday.length) * 100) : null;

  const lastActivity = [...trades.map((t) => t.time ?? t.closed_at), ...riskEvents.map((e) => e.created_at)]
    .filter((v): v is string => !!v)
    .sort()
    .at(-1);
  const isActive = lastActivity ? Date.now() - new Date(lastActivity).getTime() < 15 * 60 * 1000 : false;

  return (
    <AppLayout title="Visão Geral" subtitle="Estado do agente e performance da banca">
      <div className="flex items-center justify-between mb-4">
        <span className="text-xs text-muted-foreground uppercase tracking-wider">Conta</span>
        <ToggleGroup
          type="single"
          value={account}
          onValueChange={(v) => v && navigate({ search: { account: v as Account } })}
        >
          <ToggleGroupItem value="mt5" className="text-xs">{ACCOUNT_LABEL.mt5}</ToggleGroupItem>
          <ToggleGroupItem value="iq" className="text-xs">{ACCOUNT_LABEL.iq}</ToggleGroupItem>
        </ToggleGroup>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Stat label="Saldo atual" value={balanceFmt} delta={`${ACCOUNT_LABEL[account]} (tempo real)`} positive icon={Wallet} />
        <Stat
          label="P/L diário"
          value={pnlToday.toLocaleString("pt-BR", { style: "currency", currency: "USD", signDisplay: "always" })}
          delta={winRate != null ? `${winRate}% acerto` : "sem operações fechadas hoje"}
          positive={pnlToday >= 0}
          icon={TrendingUp}
        />
        <Stat label="Operações hoje" value={String(openedToday.length)} delta={`${closedToday.length} fechadas`} positive icon={Activity} />
        <StatusCard active={isActive} lastActivity={lastActivity} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
        <Card className="lg:col-span-1 p-5 bg-card border-border">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-medium">Evolução da banca</h3>
              <p className="text-xs text-muted-foreground">{ACCOUNT_LABEL[account]}</p>
            </div>
            {equityDelta != null && (
              <div className="text-right">
                <div className={cn("text-lg font-semibold tabular-nums", equityDelta >= 0 ? "text-success" : "text-danger")}>
                  {equityDelta >= 0 ? "+" : ""}
                  {equityDelta.toLocaleString("pt-BR", { style: "currency", currency: "USD" })}
                </div>
              </div>
            )}
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
          <AITerminal source={source} />
        </div>
      </div>

      <div className="mt-4">
        <IndicatorsGrid />
      </div>
    </AppLayout>
  );
}

function StatusCard({ active, lastActivity }: { active: boolean; lastActivity?: string }) {
  const label = active ? "Operando" : "Inativo";
  const detail = lastActivity
    ? `Última atividade ${new Date(lastActivity).toLocaleTimeString("pt-BR")}`
    : "Sem atividade registrada";
  return (
    <Card className="p-5 bg-card border-border">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs text-muted-foreground uppercase tracking-wider">Status do agente</div>
          <div className="mt-2 flex items-center gap-2">
            <span className={cn("h-2 w-2 rounded-full pulse-ring", active ? "bg-success" : "bg-muted-foreground")} />
            <span className="text-lg font-semibold">{label}</span>
          </div>
          <div className="mt-1 text-xs text-muted-foreground">{detail}</div>
        </div>
        <div className={cn("h-9 w-9 grid place-items-center rounded-md", active ? "bg-success/15 text-success" : "bg-muted text-muted-foreground")}>
          <Activity className="h-4 w-4" />
        </div>
      </div>
    </Card>
  );
}
