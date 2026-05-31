import { Card } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { useMemo, useState } from "react";
import { ShieldAlert, Calculator } from "lucide-react";

export function RiskPanel() {
  const [bank, setBank] = useState(1000);
  const [prob, setProb] = useState([60]);
  const [payback, setPayback] = useState([80]);
  const [leverage, setLeverage] = useState([3]);

  const kelly = useMemo(() => {
    const p = prob[0] / 100;
    const b = payback[0] / 100;
    const f = Math.max(0, (b * p - (1 - p)) / b); // fraction
    return {
      fraction: f,
      amount: bank * f,
    };
  }, [bank, prob, payback]);

  const ruinRisk = useMemo(() => {
    // Heuristic illustrative curve
    const r = Math.min(100, leverage[0] ** 1.6 * 1.4);
    return r;
  }, [leverage]);

  const allocPct = Math.min(100, (kelly.amount / bank) * 100);

  return (
    <Card className="p-5 bg-card border-border">
      <div className="flex items-center gap-2 mb-4">
        <ShieldAlert className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-medium">Gerenciamento de Risco · Pro</h3>
      </div>

      {/* Allocation ring */}
      <div className="flex items-center gap-5">
        <AllocationRing pct={allocPct} />
        <div className="flex-1 space-y-1.5">
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">Em risco agora</span>
            <span className="tabular-nums font-medium">
              ${kelly.amount.toFixed(2)}{" "}
              <span className="text-muted-foreground">/ ${bank.toFixed(0)}</span>
            </span>
          </div>
          <div className="h-1.5 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full bg-primary transition-all"
              style={{ width: `${allocPct}%` }}
            />
          </div>
          <div className="text-[10px] text-muted-foreground">
            Fração Kelly: {(kelly.fraction * 100).toFixed(2)}% do capital
          </div>
        </div>
      </div>

      <div className="h-px bg-border my-5" />

      {/* Kelly calculator */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Calculator className="h-3.5 w-3.5 text-muted-foreground" />
          <span className="text-xs font-medium">Calculadora Kelly</span>
        </div>

        <div className="grid grid-cols-2 gap-4 text-xs">
          <Field label="Banca ($)">
            <input
              type="number"
              value={bank}
              onChange={(e) => setBank(Number(e.target.value) || 0)}
              className="w-full bg-input border border-border rounded-md px-2 py-1.5 text-sm tabular-nums"
            />
          </Field>
          <Field label="Sugestão Kelly">
            <div className="px-2 py-1.5 rounded-md bg-primary/10 border border-primary/25 text-primary font-semibold tabular-nums">
              ${kelly.amount.toFixed(2)}
            </div>
          </Field>
        </div>

        <Slide label="Probabilidade de acerto" suffix="%" value={prob} onChange={setProb} min={1} max={99} />
        <Slide label="Payback (b)" suffix="%" value={payback} onChange={setPayback} min={10} max={300} />

        <p className="font-mono text-[11px] text-muted-foreground bg-background/40 border border-border rounded-md px-3 py-2 leading-relaxed">
          Banca: ${bank} | Prob: {prob[0]}% | Payback: {payback[0]}% →{" "}
          <span className="text-primary">Sugestão Kelly: ${kelly.amount.toFixed(2)}</span>
        </p>
      </div>

      <div className="h-px bg-border my-5" />

      {/* Leverage / ruin */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="font-medium">Alavancagem</span>
          <span className="tabular-nums text-primary">{leverage[0]}x</span>
        </div>
        <Slider value={leverage} onValueChange={setLeverage} min={1} max={20} step={1} />
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-muted-foreground">Risco de Ruína</span>
          <span
            className={`tabular-nums font-medium ${
              ruinRisk < 20 ? "text-success" : ruinRisk < 50 ? "text-warning" : "text-danger"
            }`}
          >
            {ruinRisk.toFixed(1)}%
          </span>
        </div>
        <div className="h-1.5 rounded-full bg-muted overflow-hidden">
          <div
            className={`h-full transition-all ${
              ruinRisk < 20 ? "bg-success" : ruinRisk < 50 ? "bg-warning" : "bg-danger"
            }`}
            style={{ width: `${ruinRisk}%` }}
          />
        </div>
      </div>
    </Card>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <div className="text-[11px] text-muted-foreground">{label}</div>
      {children}
    </div>
  );
}

function Slide({
  label, suffix, value, onChange, min, max,
}: { label: string; suffix: string; value: number[]; onChange: (v: number[]) => void; min: number; max: number }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-muted-foreground">{label}</span>
        <span className="tabular-nums">{value[0]}{suffix}</span>
      </div>
      <Slider value={value} onValueChange={onChange} min={min} max={max} step={1} />
    </div>
  );
}

function AllocationRing({ pct }: { pct: number }) {
  const r = 32;
  const c = 2 * Math.PI * r;
  const offset = c - (Math.min(100, pct) / 100) * c;
  return (
    <div className="relative h-[90px] w-[90px] shrink-0">
      <svg viewBox="0 0 80 80" className="h-full w-full -rotate-90">
        <circle cx="40" cy="40" r={r} stroke="oklch(0.28 0.012 260)" strokeWidth="7" fill="none" />
        <circle
          cx="40"
          cy="40"
          r={r}
          stroke="oklch(0.72 0.17 160)"
          strokeWidth="7"
          fill="none"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          className="transition-all duration-500"
        />
      </svg>
      <div className="absolute inset-0 grid place-items-center">
        <div className="text-center">
          <div className="text-base font-semibold tabular-nums leading-none">{pct.toFixed(1)}%</div>
          <div className="text-[9px] uppercase tracking-wider text-muted-foreground mt-0.5">alocado</div>
        </div>
      </div>
    </div>
  );
}
