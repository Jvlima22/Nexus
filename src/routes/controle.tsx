import { createFileRoute } from "@tanstack/react-router";
import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Pause, Play, Shield, Target, Zap } from "lucide-react";
import { useState } from "react";
import { AutonomyMode } from "@/components/ai/AutonomyMode";
import { RiskPanel } from "@/components/ai/RiskPanel";

export const Route = createFileRoute("/controle")({
  head: () => ({
    meta: [
      { title: "Nexus Trader — Painel de Controle" },
      { name: "description", content: "Configure banca, estratégia e automação do agente." },
    ],
  }),
  component: ControlPage,
});

function ControlPage() {
  const [running, setRunning] = useState(true);
  const [leverage, setLeverage] = useState([3]);

  return (
    <AppLayout title="Painel de Controle" subtitle="Defina os parâmetros de risco e estratégia">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2 p-6 bg-card border-border">
          <div className="flex items-center gap-2 mb-5">
            <Shield className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-medium">Gerenciamento de banca</h3>
          </div>
          <div className="grid sm:grid-cols-2 gap-5">
            <div className="space-y-2">
              <Label className="text-xs">Stop Loss diário (%)</Label>
              <Input defaultValue="3.0" className="bg-input border-border" />
              <p className="text-[11px] text-muted-foreground">Pausa automática ao atingir.</p>
            </div>
            <div className="space-y-2">
              <Label className="text-xs">Take Profit diário (%)</Label>
              <Input defaultValue="6.0" className="bg-input border-border" />
              <p className="text-[11px] text-muted-foreground">Encerra sessão protegendo o ganho.</p>
            </div>
            <div className="space-y-2 sm:col-span-2">
              <div className="flex items-center justify-between">
                <Label className="text-xs">Alavancagem</Label>
                <span className="text-xs tabular-nums text-primary">{leverage[0]}x</span>
              </div>
              <Slider value={leverage} onValueChange={setLeverage} min={1} max={10} step={1} />
              <div className="flex justify-between text-[10px] text-muted-foreground"><span>Seguro</span><span>Agressivo</span></div>
            </div>
          </div>

          <div className="h-px bg-border my-6" />

          <div className="flex items-center gap-2 mb-4">
            <Target className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-medium">Estratégia</h3>
          </div>
          <div className="grid sm:grid-cols-2 gap-5">
            <div className="space-y-2">
              <Label className="text-xs">Perfil ativo</Label>
              <Select defaultValue="moderada">
                <SelectTrigger className="bg-input border-border"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="conservadora">Conservadora (Kelly 0.5)</SelectItem>
                  <SelectItem value="moderada">Moderada (Kelly 0.75)</SelectItem>
                  <SelectItem value="agressiva">Agressiva (Kelly 1.0)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-xs">Timeframe alvo</Label>
              <Select defaultValue="h1">
                <SelectTrigger className="bg-input border-border"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="m5">M5 — Scalp</SelectItem>
                  <SelectItem value="m15">M15 — Curto prazo</SelectItem>
                  <SelectItem value="h1">H1 — Swing intradiário</SelectItem>
                  <SelectItem value="h4">H4 — Swing</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </Card>

        <Card className="p-6 bg-card border-border flex flex-col">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-medium">Automação</h3>
          </div>
          <p className="text-xs text-muted-foreground">
            O agente executa operações com base nos parâmetros acima. Você pode pausar a qualquer momento.
          </p>

          <div className="mt-6 rounded-lg border border-border bg-background/40 p-5">
            <div className="flex items-center gap-3">
              <span className={`h-2.5 w-2.5 rounded-full ${running ? "bg-success pulse-ring" : "bg-muted-foreground"}`} />
              <div>
                <div className="text-sm font-medium">{running ? "Operando" : "Pausado"}</div>
                <div className="text-[11px] text-muted-foreground">{running ? "Última ordem há 4 min" : "Aguardando comando"}</div>
              </div>
            </div>
          </div>

          <Button
            onClick={() => setRunning((r) => !r)}
            size="lg"
            className={`mt-4 w-full h-12 text-sm font-medium ${
              running
                ? "bg-danger text-danger-foreground hover:bg-danger/90"
                : "bg-primary text-primary-foreground hover:bg-primary/90"
            }`}
          >
            {running ? <><Pause className="h-4 w-4 mr-2" /> Pausar automação</> : <><Play className="h-4 w-4 mr-2" /> Iniciar automação</>}
          </Button>

          <div className="mt-6 space-y-2 text-xs">
            <Row label="Capital alocado" value="$12.847" />
            <Row label="Risco por operação" value="1.8%" />
            <Row label="Drawdown máximo" value="3.0%" />
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
        <AutonomyMode />
        <RiskPanel />
      </div>
    </AppLayout>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between border-b border-border pb-1.5">
      <span className="text-muted-foreground">{label}</span>
      <span className="tabular-nums">{value}</span>
    </div>
  );
}
