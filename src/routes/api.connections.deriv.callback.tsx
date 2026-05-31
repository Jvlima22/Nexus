import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useServerFn } from "@tanstack/react-start";
import { connectBroker } from "@/lib/rpc/connections";
import { Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

/**
 * Callback do OAuth da Deriv.
 * URL: /api/connections/deriv/callback?token1=...&acct1=...&cur1=...
 *
 * Não é uma "API route" pura — é uma página React que processa os search
 * params e chama o server fn `connectBroker`, depois redireciona para /conexoes.
 */
export const Route = createFileRoute("/api/connections/deriv/callback")({
  validateSearch: (s: Record<string, unknown>) => ({
    token1: typeof s.token1 === "string" ? s.token1 : undefined,
    acct1: typeof s.acct1 === "string" ? s.acct1 : undefined,
    cur1: typeof s.cur1 === "string" ? s.cur1 : undefined,
    state: typeof s.state === "string" ? s.state : undefined,
  }),
  component: DerivCallback,
});

function DerivCallback() {
  const search = Route.useSearch();
  const { session } = useAuth();
  const navigate = useNavigate();
  const connect = useServerFn(connectBroker);
  const [state, setState] = useState<"loading" | "ok" | "error">("loading");
  const [msg, setMsg] = useState<string>();
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    if (!session) return;
    if (!search.token1) {
      setState("error");
      setMsg("Deriv não devolveu token. Tente conectar de novo.");
      return;
    }
    ran.current = true;

    connect({
      data: {
        accessToken: session.access_token,
        broker: "deriv",
        credentials: { token: search.token1, account: search.acct1, currency: search.cur1 },
      },
    })
      .then((r) => {
        if (r.ok) {
          setState("ok");
          setTimeout(() => navigate({ to: "/conexoes" }), 800);
        } else {
          setState("error");
          setMsg(r.error);
        }
      })
      .catch((e) => {
        setState("error");
        setMsg(e instanceof Error ? e.message : String(e));
      });
  }, [session, search, connect, navigate]);

  return (
    <div className="min-h-screen grid place-items-center bg-background px-4">
      <Card className="w-full max-w-md p-8 text-center">
        {state === "loading" && (
          <>
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground mx-auto mb-3" />
            <div className="text-sm">Conectando à Deriv...</div>
          </>
        )}
        {state === "ok" && (
          <>
            <CheckCircle2 className="h-6 w-6 text-success mx-auto mb-3" />
            <div className="text-sm">Conectado! Redirecionando...</div>
          </>
        )}
        {state === "error" && (
          <>
            <AlertCircle className="h-6 w-6 text-destructive mx-auto mb-3" />
            <div className="text-sm font-medium mb-1">Não foi possível conectar</div>
            <div className="text-xs text-muted-foreground mb-4">{msg}</div>
            <Button onClick={() => navigate({ to: "/conexoes" })}>Voltar</Button>
          </>
        )}
      </Card>
    </div>
  );
}
