import { createFileRoute, useNavigate, useRouterState } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Activity, AlertCircle, Loader2 } from "lucide-react";
import { toast } from "sonner";

export const Route = createFileRoute("/login")({
  head: () => ({ meta: [{ title: "Nexus Trader — Entrar" }] }),
  component: LoginPage,
});

function LoginPage() {
  const { session, loading, signInWithPassword, signUpWithPassword, signInWithGoogle } = useAuth();
  const navigate = useNavigate();
  const search = useRouterState({ select: (s) => s.location.search }) as { redirect?: string };

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    if (!loading && session) {
      navigate({ to: search?.redirect ?? "/" });
    }
  }, [loading, session, navigate, search]);

  async function submit(mode: "in" | "up") {
    setSubmitting(true);
    setError(undefined);
    const res = mode === "in"
      ? await signInWithPassword(email, password)
      : await signUpWithPassword(email, password);
    setSubmitting(false);
    if (res.error) {
      setError(res.error);
    } else if (mode === "up") {
      toast.success("Conta criada — verifique seu email para confirmar.");
    }
  }

  async function google() {
    setSubmitting(true);
    const res = await signInWithGoogle();
    setSubmitting(false);
    if (res.error) setError(res.error);
  }

  return (
    <div className="min-h-screen grid place-items-center bg-background px-4">
      <Card className="w-full max-w-md p-8">
        <div className="flex items-center gap-2 mb-6">
          <div className="grid place-items-center h-9 w-9 rounded-md bg-primary/15 text-primary">
            <Activity className="h-4 w-4" />
          </div>
          <div>
            <div className="text-sm font-semibold">Nexus Trader</div>
            <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Autonomous AI</div>
          </div>
        </div>

        <Tabs defaultValue="in">
          <TabsList className="grid grid-cols-2 w-full">
            <TabsTrigger value="in">Entrar</TabsTrigger>
            <TabsTrigger value="up">Criar conta</TabsTrigger>
          </TabsList>
          {(["in", "up"] as const).map((mode) => (
            <TabsContent key={mode} value={mode} className="space-y-3 mt-4">
              <div className="space-y-1.5">
                <Label htmlFor={`email-${mode}`}>Email</Label>
                <Input id={`email-${mode}`} type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor={`pwd-${mode}`}>Senha</Label>
                <Input id={`pwd-${mode}`} type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
              </div>
              {error && (
                <div className="flex items-start gap-2 text-xs text-destructive bg-destructive/10 rounded p-2">
                  <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
                  {error}
                </div>
              )}
              <Button disabled={submitting} onClick={() => submit(mode)} className="w-full">
                {submitting && <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" />}
                {mode === "in" ? "Entrar" : "Criar conta"}
              </Button>
            </TabsContent>
          ))}
        </Tabs>

        <div className="my-5 flex items-center gap-3">
          <div className="h-px flex-1 bg-border" />
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">ou</div>
          <div className="h-px flex-1 bg-border" />
        </div>

        <Button variant="outline" disabled={submitting} onClick={google} className="w-full">
          Continuar com Google
        </Button>
      </Card>
    </div>
  );
}
