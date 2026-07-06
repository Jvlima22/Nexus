import { useEffect, useState, useCallback, useRef } from "react";
import { toast } from "sonner";
import { Bot, RefreshCw, TrendingUp, TrendingDown, Ban, SkipForward, AlertTriangle, Loader2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import {
  fetchAutotraderStatus,
  toggleAutotrader,
  type AutotraderStatus,
  type AutotraderDecision,
} from "@/lib/connector";
import { cn } from "@/lib/utils";

const ACTION_META: Record<
  AutotraderDecision["action"],
  { cls: string; Icon: typeof TrendingUp; label: string }
> = {
  executed: { cls: "text-success", Icon: TrendingUp, label: "executou" },
  vetoed: { cls: "text-danger", Icon: Ban, label: "vetado" },
  skip: { cls: "text-muted-foreground", Icon: SkipForward, label: "pulou" },
  error: { cls: "text-warning", Icon: AlertTriangle, label: "erro" },
};

function hhmm(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "--:--" : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

/**
 * Painel de controle do Autotrader (Fase 7): liga/desliga o robô determinístico
 * (kill switch via POST /autotrader/toggle) e mostra as últimas decisões do laço.
 * O robô passa toda ordem pelo mesmo Risk Judge — não há caminho que o pule.
 */
export function AutotraderPanel() {
  const [status, setStatus] = useState<AutotraderStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toggling, setToggling] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      setStatus(await fetchAutotraderStatus());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    load();
    timer.current = setInterval(load, 10_000); // segue o laço (poll 60s) sem martelar
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [load]);

  async function onToggle() {
    if (!status) return;
    const next = !status.enabled;
    setToggling(true);
    try {
      await toggleAutotrader(next);
      setStatus({ ...status, enabled: next });
      toast[next ? "success" : "info"](next ? "Autotrader LIGADO" : "Autotrader desligado", {
        description: next
          ? `${status.scan_open ? `${status.watchlist_count} ${status.universe}` : status.assets.join(", ")} · ${status.timeframe}/${status.confirm_timeframe} · ${status.balance_mode}`
          : "Laço pausado — nenhuma nova ordem será aberta.",
      });
    } catch (e) {
      toast.error("Falha ao alternar o autotrader", {
        description: e instanceof Error ? e.message : String(e),
      });
    } finally {
      setToggling(false);
    }
  }

  const on = status?.enabled ?? false;

  return (
    <Card className="p-5 bg-card border-border">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Bot className={cn("h-4 w-4", on ? "text-success" : "text-muted-foreground")} />
          <h3 className="text-sm font-medium">Autotrader</h3>
          {status && (
            <span
              className={cn(
                "text-[10px] px-1.5 py-0.5 rounded uppercase tracking-wider",
                status.balance_mode === "REAL" ? "bg-danger/15 text-danger" : "bg-muted text-muted-foreground",
              )}
            >
              {status.balance_mode}
            </span>
          )}
        </div>
        <button
          onClick={load}
          className="text-muted-foreground hover:text-foreground transition-colors"
          title="Recarregar"
        >
          <RefreshCw className="h-3.5 w-3.5" />
        </button>
      </div>

      {error ? (
        <p className="text-sm text-danger">{error}</p>
      ) : !status ? (
        <p className="text-sm text-muted-foreground">Carregando estado…</p>
      ) : (
        <>
          {/* Kill switch */}
          <div className="flex items-center justify-between rounded-md border border-border bg-background/40 px-3 py-2.5">
            <div>
              <div className={cn("text-sm font-medium", on ? "text-success" : "text-muted-foreground")}>
                {on ? "Operando" : "Parado"}
              </div>
              <div className="text-[11px] text-muted-foreground">
                {status.scan_open
                  ? `${status.watchlist_count} ${status.universe} (payout ≥${status.min_payout}%)`
                  : status.assets.join(", ") || "sem ativos"}{" "}
                · {status.timeframe}
                {status.confluence ? `+${status.confirm_timeframe}` : ""} · {(status.stake_pct * 100).toFixed(0)}%/ordem
              </div>
            </div>
            <button
              onClick={onToggle}
              disabled={toggling}
              role="switch"
              aria-checked={on}
              className={cn(
                "relative inline-flex h-6 w-11 items-center rounded-full transition-colors disabled:opacity-50",
                on ? "bg-success" : "bg-muted",
              )}
            >
              {toggling ? (
                <Loader2 className="h-3 w-3 animate-spin mx-auto text-foreground" />
              ) : (
                <span
                  className={cn(
                    "inline-block h-4 w-4 transform rounded-full bg-background transition-transform",
                    on ? "translate-x-6" : "translate-x-1",
                  )}
                />
              )}
            </button>
          </div>

          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-muted-foreground">
            <span>ticks {status.ticks}</span>
            <span>poll {status.poll_s}s</span>
            <span>máx {status.max_open} abertas</span>
            {status.edge_gate && (
              <span>
                gate {status.edge_enabled_count}/{status.edge_measured_count} com edge
                {" "}(&gt;{(status.edge_min_hit * 100).toFixed(0)}%, n≥{status.edge_min_sample})
              </span>
            )}
            {Object.keys(status.holding).length > 0 && (
              <span>segurando {Object.keys(status.holding).join(", ")}</span>
            )}
          </div>

          {/* Gate de evidência: edge medido por par (só opera quem supera o breakeven) */}
          {status.edge_gate && (
            <div className="mt-3">
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5">
                Edge medido (backtest)
              </div>
              {Object.keys(status.edge).length === 0 ? (
                <p className="text-[11px] text-muted-foreground">
                  Sem medição ainda — o robô backtesta a watchlist no próximo ciclo de edge.
                </p>
              ) : (
                <div className="flex flex-wrap gap-1.5">
                  {Object.entries(status.edge)
                    .sort((a, b) => (b[1].hit_rate ?? 0) - (a[1].hit_rate ?? 0))
                    .slice(0, 24)
                    .map(([sym, e]) => (
                      <span
                        key={sym}
                        title={`${e.sample} sinais${e.passes_gate ? " · habilitado" : " · sem edge"}`}
                        className={cn(
                          "text-[10px] px-1.5 py-0.5 rounded tabular-nums",
                          e.passes_gate ? "bg-success/15 text-success" : "bg-muted text-muted-foreground",
                        )}
                      >
                        {sym.replace("-OTC", "")} {e.hit_rate != null ? `${(e.hit_rate * 100).toFixed(0)}%` : "—"}
                      </span>
                    ))}
                </div>
              )}
            </div>
          )}

          {/* Decisões recentes */}
          <div className="mt-4">
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1.5">
              Decisões recentes
            </div>
            {status.recent.length === 0 ? (
              <p className="text-[11px] text-muted-foreground">
                {on ? "Aguardando o próximo tick…" : "Ligue o robô para começar a avaliar."}
              </p>
            ) : (
              <div className="space-y-1 max-h-56 overflow-y-auto scrollbar-modern">
                {[...status.recent].reverse().map((d, i) => {
                  const m = ACTION_META[d.action];
                  return (
                    <div key={i} className="flex items-start gap-2 text-[11px] border-b border-border/40 pb-1">
                      <m.Icon className={cn("h-3 w-3 mt-0.5 shrink-0", m.cls)} />
                      <span className="text-muted-foreground tabular-nums shrink-0">{hhmm(d.time)}</span>
                      <span className="font-medium shrink-0">{d.asset ?? "—"}</span>
                      {d.direction && (
                        <span className={cn("shrink-0", d.direction === "call" ? "text-success" : "text-danger")}>
                          {d.direction === "call" ? <TrendingUp className="inline h-3 w-3" /> : <TrendingDown className="inline h-3 w-3" />}
                        </span>
                      )}
                      <span className="text-muted-foreground truncate" title={d.detail}>
                        {d.detail}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <p className="mt-3 text-[10px] text-muted-foreground text-center">
            Toda ordem passa pelo Risk Judge (macro · sessão · notícia · 2% · breaker · teto diário).
          </p>
        </>
      )}
    </Card>
  );
}
