import { useCallback, useEffect, useRef, useState } from "react";
import { useServerFn } from "@tanstack/react-start";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/hooks/useAuth";
import { ingestKnowledge, askNexus } from "@/lib/rpc/knowledge";
import {
  Link2,
  Upload,
  FileText,
  Globe,
  ClipboardType,
  Trash2,
  Loader2,
  Send,
  Sparkles,
  Database,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface SourceRow {
  id: string;
  kind: "file" | "url" | "text";
  title: string;
  char_count: number;
  token_estimate: number;
  status: "processing" | "ready" | "error";
  active: boolean;
  created_at: string;
}

const KIND_META = {
  file: { icon: FileText, label: "Arquivo" },
  url: { icon: Globe, label: "URL" },
  text: { icon: ClipboardType, label: "Texto" },
} as const;

async function fileToBase64(file: File): Promise<string> {
  const buf = new Uint8Array(await file.arrayBuffer());
  let bin = "";
  const chunk = 0x8000;
  for (let i = 0; i < buf.length; i += chunk) {
    bin += String.fromCharCode(...buf.subarray(i, i + chunk));
  }
  return btoa(bin);
}

interface Answer {
  text: string;
  elapsedMs: number;
  cached: boolean;
  sources: number;
  cacheRead: number;
  cacheWrite: number;
}

export function KnowledgeContext() {
  const { session } = useAuth();
  const ingest = useServerFn(ingestKnowledge);
  const ask = useServerFn(askNexus);

  const [sources, setSources] = useState<SourceRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [url, setUrl] = useState("");
  const [paste, setPaste] = useState("");
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [answer, setAnswer] = useState<Answer | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    if (!session) return;
    setLoading(true);
    const { data, error } = await supabase
      .from("knowledge_sources")
      .select(
        "id,kind,title,char_count,token_estimate,status,active,created_at",
      )
      .eq("user_id", session.user.id)
      .order("created_at", { ascending: false });
    if (error) toast.error(`Erro ao carregar fontes: ${error.message}`);
    else setSources((data ?? []) as SourceRow[]);
    setLoading(false);
  }, [session]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const token = session?.access_token;

  async function addUrl() {
    if (!token || !url.trim()) return;
    setBusy(true);
    try {
      await ingest({
        data: { accessToken: token, kind: "url", url: url.trim() },
      });
      setUrl("");
      toast.success("URL adicionada ao contexto.");
      await refresh();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function addPaste() {
    if (!token || !paste.trim()) return;
    setBusy(true);
    try {
      await ingest({
        data: { accessToken: token, kind: "text", text: paste.trim() },
      });
      setPaste("");
      toast.success("Texto adicionado ao contexto.");
      await refresh();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function addFiles(files: FileList) {
    if (!token) return;
    setBusy(true);
    try {
      for (const file of Array.from(files)) {
        const isPdf =
          file.type.includes("pdf") || file.name.toLowerCase().endsWith(".pdf");
        if (isPdf) {
          const dataBase64 = await fileToBase64(file);
          await ingest({
            data: {
              accessToken: token,
              kind: "file",
              title: file.name,
              mime: file.type,
              dataBase64,
            },
          });
        } else {
          const text = await file.text();
          await ingest({
            data: { accessToken: token, kind: "file", title: file.name, text },
          });
        }
      }
      toast.success("Arquivo(s) adicionado(s) ao contexto.");
      await refresh();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  async function toggleActive(row: SourceRow) {
    const { error } = await supabase
      .from("knowledge_sources")
      .update({ active: !row.active })
      .eq("id", row.id);
    if (error) toast.error(error.message);
    else
      setSources((s) =>
        s.map((r) => (r.id === row.id ? { ...r, active: !r.active } : r)),
      );
  }

  async function remove(row: SourceRow) {
    const { error } = await supabase
      .from("knowledge_sources")
      .delete()
      .eq("id", row.id);
    if (error) toast.error(error.message);
    else setSources((s) => s.filter((r) => r.id !== row.id));
  }

  async function submitQuestion() {
    if (!token || !question.trim()) return;
    setAsking(true);
    setAnswer(null);
    try {
      const r = await ask({
        data: { accessToken: token, question: question.trim() },
      });
      setAnswer({
        text: r.answer,
        elapsedMs: r.elapsedMs,
        cached: r.cached,
        sources: r.sources,
        cacheRead: r.usage.cache_read_input_tokens,
        cacheWrite: r.usage.cache_creation_input_tokens,
      });
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e));
    } finally {
      setAsking(false);
    }
  }

  const activeTokens = sources
    .filter((s) => s.active && s.status === "ready")
    .reduce((n, s) => n + s.token_estimate, 0);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
      {/* Adicionar + lista */}
      <Card className="lg:col-span-5 p-4 bg-card border-border space-y-4">
        <div className="flex items-center gap-2">
          <Database className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-medium">Contexto da IA</h3>
          <span className="ml-auto text-[10px] text-muted-foreground tabular-nums">
            {sources.length} fontes · ~{activeTokens.toLocaleString("pt-BR")}{" "}
            tokens ativos
          </span>
        </div>

        {/* URL */}
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Link2 className="h-3.5 w-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addUrl()}
              placeholder="https://… (link para o contexto)"
              className="h-8 pl-7 text-xs bg-background/40"
              disabled={busy}
            />
          </div>
          <Button
            size="sm"
            className="h-8"
            onClick={addUrl}
            disabled={busy || !url.trim()}
          >
            Add
          </Button>
        </div>

        {/* Upload */}
        <button
          onClick={() => fileRef.current?.click()}
          disabled={busy}
          className="w-full rounded-md border border-dashed border-border hover:border-primary/50 bg-background/30 py-4 grid place-items-center gap-1 text-xs text-muted-foreground transition-colors disabled:opacity-50"
        >
          <Upload className="h-4 w-4" />
          Clique para enviar arquivos (.md, .txt, .csv, .json, .pdf)
        </button>
        <input
          ref={fileRef}
          type="file"
          multiple
          accept=".md,.txt,.csv,.json,.pdf,text/*,application/pdf"
          className="hidden"
          onChange={(e) => e.target.files && addFiles(e.target.files)}
        />

        {/* Colar texto */}
        <div className="space-y-2">
          <Textarea
            value={paste}
            onChange={(e) => setPaste(e.target.value)}
            placeholder="…ou cole texto direto aqui"
            className="text-xs bg-background/40 min-h-[64px]"
            disabled={busy}
          />
          <Button
            size="sm"
            variant="secondary"
            className="h-7 w-full"
            onClick={addPaste}
            disabled={busy || !paste.trim()}
          >
            {busy ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              "Adicionar texto"
            )}
          </Button>
        </div>

        {/* Lista */}
        <div className="space-y-1.5 max-h-[280px] overflow-y-auto pt-1">
          {loading ? (
            <div className="grid place-items-center py-6 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
            </div>
          ) : sources.length === 0 ? (
            <p className="text-xs text-muted-foreground text-center py-4">
              Nenhuma fonte. Adicione URLs, arquivos ou texto acima.
            </p>
          ) : (
            sources.map((s) => {
              const Icon = KIND_META[s.kind].icon;
              return (
                <div
                  key={s.id}
                  className={cn(
                    "flex items-center gap-2 rounded-md border border-border bg-background/40 px-2.5 py-1.5",
                    !s.active && "opacity-50",
                  )}
                >
                  <Icon className="h-3.5 w-3.5 text-primary/70 shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="text-xs truncate">{s.title}</div>
                    <div className="text-[10px] text-muted-foreground tabular-nums">
                      {KIND_META[s.kind].label} · ~
                      {s.token_estimate.toLocaleString("pt-BR")} tokens
                    </div>
                  </div>
                  <button
                    onClick={() => toggleActive(s)}
                    title={
                      s.active ? "Desativar do contexto" : "Ativar no contexto"
                    }
                    className={cn(
                      "h-4 w-7 rounded-full transition-colors shrink-0 relative",
                      s.active ? "bg-primary" : "bg-muted",
                    )}
                  >
                    <span
                      className={cn(
                        "absolute top-0.5 h-3 w-3 rounded-full bg-background transition-all",
                        s.active ? "left-3.5" : "left-0.5",
                      )}
                    />
                  </button>
                  <button
                    onClick={() => remove(s)}
                    className="text-muted-foreground hover:text-danger shrink-0"
                    title="Remover"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              );
            })
          )}
        </div>
      </Card>

      {/* Perguntar */}
      <Card className="lg:col-span-7 p-4 bg-card border-border flex flex-col">
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-medium">Perguntar à NEXUS</h3>
          <span className="ml-auto text-[10px] text-muted-foreground">
            usa o contexto ativo (prompt caching)
          </span>
        </div>

        <div className="flex gap-2">
          <Textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey))
                submitQuestion();
            }}
            placeholder="Pergunte algo com base no contexto carregado…  (Ctrl/⌘+Enter)"
            className="text-sm bg-background/40 min-h-[72px]"
            disabled={asking}
          />
          <Button
            onClick={submitQuestion}
            disabled={asking || !question.trim()}
            className="self-end h-9"
          >
            {asking ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>

        <div className="flex-1 mt-3 rounded-md border border-border bg-background/30 p-3 overflow-y-auto min-h-[200px]">
          {asking ? (
            <div className="grid place-items-center h-full text-muted-foreground gap-2">
              <Loader2 className="h-5 w-5 animate-spin" />
              <span className="text-xs">Consultando o contexto…</span>
            </div>
          ) : answer ? (
            <div className="space-y-2">
              <p className="text-sm leading-relaxed whitespace-pre-wrap text-foreground/90">
                {answer.text}
              </p>
              <div className="flex flex-wrap gap-2 pt-2 border-t border-border text-[10px] text-muted-foreground tabular-nums">
                <span>{answer.elapsedMs} ms</span>
                <span>· {answer.sources} fontes</span>
                <span
                  className={answer.cached ? "text-success" : "text-warning"}
                >
                  ·{" "}
                  {answer.cached
                    ? `cache HIT (${answer.cacheRead.toLocaleString("pt-BR")} tk lidos)`
                    : `cache escrito (${answer.cacheWrite.toLocaleString("pt-BR")} tk) — próxima é instantânea`}
                </span>
              </div>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground text-center pt-8">
              A resposta aparece aqui. A 1ª pergunta grava o cache do contexto;
              as seguintes leem em milissegundos.
            </p>
          )}
        </div>
      </Card>
    </div>
  );
}
