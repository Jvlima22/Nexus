import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { useServerFn } from "@tanstack/react-start";
import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { CheckCircle2, XCircle, Plug, Loader2, Shield, AlertCircle, ExternalLink } from "lucide-react";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/hooks/useAuth";
import { connectBroker, testBroker, revokeBroker } from "@/lib/rpc/connections";
import type { BrokerId } from "@/lib/brokers";
import { toast } from "sonner";

export const Route = createFileRoute("/conexoes")({
  head: () => ({
    meta: [
      { title: "Nexus Trader — Conexões" },
      { name: "description", content: "Status de conexão com corretoras." },
    ],
  }),
  component: ConnectionsPage,
});

interface BrokerDef {
  id: BrokerId;
  name: string;
  desc: string;
  authMethod: "oauth" | "api_key" | "ssid";
  keyDocsUrl?: string;
}

const BROKERS: BrokerDef[] = [
  {
    id: "binance",
    name: "Binance",
    desc: "Spot & Futures · API Key",
    authMethod: "api_key",
    keyDocsUrl: "https://www.binance.com/en/my/settings/api-management",
  },
  {
    id: "iqoption",
    name: "IQ Option",
    desc: "Opções binárias · SSID (não-oficial)",
    authMethod: "ssid",
  },
  {
    id: "deriv",
    name: "Deriv",
    desc: "Synthetics & Forex · OAuth 2.0",
    authMethod: "oauth",
  },
  {
    id: "bybit",
    name: "Bybit",
    desc: "Derivatives V5 · API Key",
    authMethod: "api_key",
    keyDocsUrl: "https://www.bybit.com/app/user/api-management",
  },
];

interface ConnectionRow {
  id: string;
  broker: BrokerId;
  status: "pending" | "connected" | "error" | "revoked";
  account_label?: string | null;
  last_latency_ms?: number | null;
  last_tested_at?: string | null;
  last_error?: string | null;
  permissions?: Record<string, boolean> | null;
}

function ConnectionsPage() {
  const { session } = useAuth();
  const [rows, setRows] = useState<Record<string, ConnectionRow>>({});
  const [loading, setLoading] = useState(true);
  const [openBroker, setOpenBroker] = useState<BrokerDef | null>(null);

  async function refresh() {
    if (!session) return;
    setLoading(true);
    const { data, error } = await supabase
      .from("broker_connections_safe")
      .select("*")
      .eq("user_id", session.user.id);
    if (error) {
      toast.error(`Erro ao carregar conexões: ${error.message}`);
    } else {
      const map: Record<string, ConnectionRow> = {};
      for (const r of data ?? []) map[r.broker] = r as ConnectionRow;
      setRows(map);
    }
    setLoading(false);
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.user.id]);

  return (
    <AppLayout title="Conexões" subtitle="Corretoras integradas ao agente">
      {loading ? (
        <div className="grid place-items-center h-40">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {BROKERS.map((b) => {
            const row = rows[b.id];
            return (
              <BrokerCard
                key={b.id}
                broker={b}
                row={row}
                onConnect={() => setOpenBroker(b)}
                onChanged={refresh}
              />
            );
          })}
        </div>
      )}

      <ConnectModal broker={openBroker} onClose={() => setOpenBroker(null)} onDone={refresh} />
    </AppLayout>
  );
}

function BrokerCard({
  broker,
  row,
  onConnect,
  onChanged,
}: {
  broker: BrokerDef;
  row?: ConnectionRow;
  onConnect: () => void;
  onChanged: () => void;
}) {
  const { session } = useAuth();
  const test = useServerFn(testBroker);
  const revoke = useServerFn(revokeBroker);
  const [busy, setBusy] = useState<"test" | "revoke" | undefined>();
  const connected = row?.status === "connected";

  async function handleTest() {
    if (!session) return;
    setBusy("test");
    const r = await test({ data: { accessToken: session.access_token, broker: broker.id } });
    setBusy(undefined);
    if (r.ok) toast.success(`${broker.name} OK · ${r.latencyMs}ms`);
    else toast.error(r.error ?? "Falhou");
    onChanged();
  }

  async function handleRevoke() {
    if (!session) return;
    if (!confirm(`Remover conexão com ${broker.name}?`)) return;
    setBusy("revoke");
    const r = await revoke({ data: { accessToken: session.access_token, broker: broker.id } });
    setBusy(undefined);
    if (r.ok) toast.success(`${broker.name} desconectado`);
    else toast.error(r.error ?? "Falhou");
    onChanged();
  }

  return (
    <Card className="p-5 bg-card border-border">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-md bg-accent grid place-items-center">
            <Plug className="h-4 w-4 text-muted-foreground" />
          </div>
          <div>
            <div className="text-sm font-medium">{broker.name}</div>
            <div className="text-xs text-muted-foreground">{broker.desc}</div>
          </div>
        </div>
        {connected ? (
          <span className="inline-flex items-center gap-1 text-xs text-success bg-success/10 px-2 py-1 rounded">
            <CheckCircle2 className="h-3 w-3" /> Conectado
          </span>
        ) : row?.status === "error" ? (
          <span className="inline-flex items-center gap-1 text-xs text-destructive bg-destructive/10 px-2 py-1 rounded">
            <AlertCircle className="h-3 w-3" /> Erro
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-xs text-muted-foreground bg-muted/50 px-2 py-1 rounded">
            <XCircle className="h-3 w-3" /> Offline
          </span>
        )}
      </div>

      <div className="mt-5 grid grid-cols-2 gap-3 text-xs">
        <div className="rounded border border-border bg-background/40 p-3">
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Conta</div>
          <div className="mt-1 tabular-nums">{row?.account_label ?? "Não conectada"}</div>
        </div>
        <div className="rounded border border-border bg-background/40 p-3">
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Latência</div>
          <div className="mt-1 tabular-nums">{row?.last_latency_ms ? `${row.last_latency_ms}ms` : "—"}</div>
        </div>
      </div>

      {row?.permissions && Object.values(row.permissions).some(Boolean) && (
        <div className="mt-3 flex flex-wrap gap-1">
          {Object.entries(row.permissions)
            .filter(([, v]) => v === true)
            .map(([k]) => (
              <span key={k} className="text-[10px] uppercase tracking-wider bg-accent text-muted-foreground rounded px-1.5 py-0.5">
                {k}
              </span>
            ))}
        </div>
      )}

      {row?.last_error && (
        <div className="mt-3 text-[11px] text-destructive bg-destructive/10 rounded p-2">{row.last_error}</div>
      )}

      <div className="mt-4 flex gap-2">
        {connected ? (
          <>
            <Button variant="outline" className="flex-1 h-9 text-xs" disabled={!!busy} onClick={handleTest}>
              {busy === "test" && <Loader2 className="h-3 w-3 mr-1 animate-spin" />} Testar
            </Button>
            <Button variant="outline" className="flex-1 h-9 text-xs" disabled={!!busy} onClick={handleRevoke}>
              {busy === "revoke" && <Loader2 className="h-3 w-3 mr-1 animate-spin" />} Desconectar
            </Button>
          </>
        ) : (
          <Button className="w-full h-9 text-xs" onClick={onConnect}>
            Conectar corretora
          </Button>
        )}
      </div>
    </Card>
  );
}

function ConnectModal({
  broker,
  onClose,
  onDone,
}: {
  broker: BrokerDef | null;
  onClose: () => void;
  onDone: () => void;
}) {
  const { session } = useAuth();
  const connect = useServerFn(connectBroker);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | undefined>();
  const [creds, setCreds] = useState<Record<string, string>>({});

  // reset on broker change
  useEffect(() => {
    setCreds({});
    setError(undefined);
  }, [broker?.id]);

  const fields = useMemo(() => {
    if (!broker) return [];
    if (broker.authMethod === "api_key") {
      return [
        { key: "apiKey", label: "API Key", type: "text" as const },
        { key: "apiSecret", label: "API Secret", type: "password" as const },
      ];
    }
    if (broker.authMethod === "ssid") {
      return [
        { key: "email", label: "Email", type: "email" as const },
        { key: "password", label: "Senha", type: "password" as const },
      ];
    }
    return [];
  }, [broker]);

  if (!broker) return null;

  async function handleSubmit() {
    if (!session || !broker) return;
    setBusy(true);
    setError(undefined);
    const r = await connect({
      data: { accessToken: session.access_token, broker: broker.id, credentials: creds },
    });
    setBusy(false);
    if (r.ok) {
      toast.success(`${broker.name} conectado · ${r.latencyMs}ms`);
      onDone();
      onClose();
    } else {
      setError(r.error);
    }
  }

  function handleOAuthRedirect() {
    if (!broker) return;
    if (broker.id === "deriv") {
      const appId = import.meta.env.VITE_DERIV_APP_ID as string | undefined;
      if (!appId) {
        setError("VITE_DERIV_APP_ID não configurado");
        return;
      }
      const url = new URL("https://oauth.deriv.com/oauth2/authorize");
      url.searchParams.set("app_id", appId);
      window.location.href = url.toString();
    }
  }

  return (
    <Dialog open={!!broker} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Conectar {broker.name}</DialogTitle>
          <DialogDescription>
            {broker.authMethod === "oauth" && "Você será redirecionado para autorizar o NEXUS."}
            {broker.authMethod === "api_key" && "Crie uma API Key SEM permissão de saque (withdraw)."}
            {broker.authMethod === "ssid" && "Login não-oficial — use ciente de que pode quebrar se a IQ Option mudar o endpoint."}
          </DialogDescription>
        </DialogHeader>

        {broker.authMethod === "oauth" ? (
          <div className="py-4">
            <Button onClick={handleOAuthRedirect} className="w-full">
              <ExternalLink className="h-3.5 w-3.5 mr-2" />
              Autorizar com {broker.name}
            </Button>
          </div>
        ) : (
          <div className="space-y-3 py-2">
            {broker.keyDocsUrl && (
              <a
                href={broker.keyDocsUrl}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-primary hover:underline inline-flex items-center gap-1"
              >
                <ExternalLink className="h-3 w-3" /> Onde criar a API Key na {broker.name}
              </a>
            )}
            {fields.map((f) => (
              <div key={f.key} className="space-y-1.5">
                <Label htmlFor={f.key}>{f.label}</Label>
                <Input
                  id={f.key}
                  type={f.type}
                  value={creds[f.key] ?? ""}
                  onChange={(e) => setCreds((c) => ({ ...c, [f.key]: e.target.value }))}
                  autoComplete="off"
                />
              </div>
            ))}

            <div className="flex items-start gap-2 text-[11px] text-muted-foreground bg-accent/40 rounded p-2">
              <Shield className="h-3.5 w-3.5 mt-0.5 shrink-0 text-primary" />
              <span>
                Credenciais são cifradas com AES-256-GCM antes de salvar. NEXUS bloqueia automaticamente
                chaves com permissão de saque.
              </span>
            </div>

            {error && (
              <div className="flex items-start gap-2 text-xs text-destructive bg-destructive/10 rounded p-2">
                <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                {error}
              </div>
            )}
          </div>
        )}

        {broker.authMethod !== "oauth" && (
          <DialogFooter>
            <Button variant="outline" onClick={onClose} disabled={busy}>
              Cancelar
            </Button>
            <Button onClick={handleSubmit} disabled={busy}>
              {busy && <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" />}
              Conectar
            </Button>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}
