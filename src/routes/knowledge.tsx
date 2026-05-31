import { createFileRoute } from "@tanstack/react-router";
import { useCallback, useEffect, useMemo, useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { AppLayout } from "@/components/AppLayout";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { KnowledgeContext } from "@/components/ai/KnowledgeContext";
import {
  fetchVaultTree,
  fetchVaultFile,
  type VaultFile,
} from "@/lib/connector";
import {
  FileText,
  Search,
  Loader2,
  RefreshCw,
  Folder,
  WifiOff,
  Database,
  BookOpen,
} from "lucide-react";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/knowledge")({
  head: () => ({
    meta: [
      { title: "Nexus Trader — Knowledge Center" },
      { name: "description", content: "Notas do vault Obsidian do NEXUS." },
    ],
  }),
  component: KnowledgePage,
});

// Remove o frontmatter YAML (--- ... ---) do topo antes de renderizar.
function stripFrontmatter(md: string): string {
  if (!md.startsWith("---")) return md;
  const end = md.indexOf("\n---", 3);
  if (end === -1) return md;
  const nl = md.indexOf("\n", end + 1);
  return nl === -1 ? "" : md.slice(nl + 1);
}

// [[Alvo|alias]] / [[Alvo]] -> link interno [alias](#wiki:Alvo)
function wikilinks(md: string): string {
  return md.replace(
    /\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g,
    (_m, target: string, alias?: string) => {
      const label = (alias ?? target).trim();
      return `[${label}](#wiki:${encodeURIComponent(target.trim())})`;
    },
  );
}

function fmtDate(epoch: number): string {
  return new Date(epoch * 1000).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function KnowledgePage() {
  const [tree, setTree] = useState<VaultFile[]>([]);
  const [activePath, setActivePath] = useState("");
  const [content, setContent] = useState("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const openFile = useCallback((path: string) => {
    setActivePath(path);
    setLoading(true);
    fetchVaultFile(path)
      .then((c) => setContent(c))
      .catch((e) =>
        setContent(
          `> Erro ao abrir: ${e instanceof Error ? e.message : String(e)}`,
        ),
      )
      .finally(() => setLoading(false));
  }, []);

  const loadTree = useCallback(() => {
    fetchVaultTree()
      .then((files) => {
        setTree(files);
        setError(null);
        setActivePath((cur) => {
          if (cur) return cur;
          const first =
            files.find((f) => f.name === "Bem-vindo")?.path ??
            files[0]?.path ??
            "";
          if (first) openFile(first);
          return cur;
        });
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [openFile]);

  useEffect(() => {
    loadTree();
  }, [loadTree]);

  const openWiki = useCallback(
    (raw: string) => {
      const t = decodeURIComponent(raw);
      const f =
        tree.find((x) => x.name === t) ??
        tree.find((x) => x.path.endsWith(`${t}.md`)) ??
        tree.find((x) => x.name.toLowerCase() === t.toLowerCase());
      if (f) openFile(f.path);
    },
    [tree, openFile],
  );

  const filtered = useMemo(
    () =>
      tree.filter((f) =>
        `${f.name} ${f.folder}`.toLowerCase().includes(query.toLowerCase()),
      ),
    [tree, query],
  );

  const groups = useMemo(() => {
    const m = new Map<string, VaultFile[]>();
    for (const f of filtered) {
      const k = f.folder || "(raiz)";
      (m.get(k) ?? m.set(k, []).get(k)!).push(f);
    }
    return [...m.entries()];
  }, [filtered]);

  const active = tree.find((f) => f.path === activePath);
  const rendered = useMemo(
    () => wikilinks(stripFrontmatter(content)),
    [content],
  );

  const mdComponents: Components = {
    h1: (p) => <h1 className="text-xl font-semibold mt-5 mb-2" {...p} />,
    h2: (p) => (
      <h2
        className="text-lg font-semibold mt-5 mb-2 border-b border-border pb-1"
        {...p}
      />
    ),
    h3: (p) => <h3 className="text-base font-semibold mt-4 mb-1.5" {...p} />,
    p: (p) => (
      <p className="text-sm leading-relaxed my-2 text-foreground/90" {...p} />
    ),
    ul: (p) => <ul className="list-disc pl-5 my-2 text-sm space-y-1" {...p} />,
    ol: (p) => (
      <ol className="list-decimal pl-5 my-2 text-sm space-y-1" {...p} />
    ),
    li: (p) => <li className="leading-relaxed" {...p} />,
    blockquote: (p) => (
      <blockquote
        className="border-l-2 border-primary/40 pl-3 my-2 text-muted-foreground"
        {...p}
      />
    ),
    hr: () => <hr className="my-4 border-border" />,
    code: (p) => (
      <code
        className="px-1 py-0.5 rounded bg-muted text-[12px] font-mono"
        {...p}
      />
    ),
    pre: (p) => (
      <pre
        className="my-3 p-3 rounded-md bg-background/60 border border-border overflow-x-auto text-[12px]"
        {...p}
      />
    ),
    table: (p) => (
      <table className="my-3 w-full text-sm border-collapse" {...p} />
    ),
    th: (p) => (
      <th
        className="border border-border px-2 py-1 text-left bg-accent/40"
        {...p}
      />
    ),
    td: (p) => <td className="border border-border px-2 py-1" {...p} />,
    a: ({ href, children }) =>
      href?.startsWith("#wiki:") ? (
        <button
          className="text-primary hover:underline"
          onClick={() => openWiki(href.slice(6))}
        >
          {children}
        </button>
      ) : (
        <a
          href={href}
          target="_blank"
          rel="noreferrer"
          className="text-primary hover:underline"
        >
          {children}
        </a>
      ),
  };

  return (
    <AppLayout
      title="Knowledge Center"
      subtitle="Contexto da IA (RAG) + vault Obsidian do NEXUS"
    >
      <Tabs defaultValue="context">
        <TabsList className="mb-2">
          <TabsTrigger value="context" className="gap-1.5">
            <Database className="h-3.5 w-3.5" /> Contexto da IA
          </TabsTrigger>
          <TabsTrigger value="vault" className="gap-1.5">
            <BookOpen className="h-3.5 w-3.5" /> Vault Obsidian
          </TabsTrigger>
        </TabsList>

        <TabsContent value="context">
          <KnowledgeContext />
        </TabsContent>

        <TabsContent value="vault">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            {/* Árvore */}
            <Card className="lg:col-span-4 p-0 bg-card border-border overflow-hidden flex flex-col">
              <div className="p-3 border-b border-border space-y-2">
                <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground">
                  <FileText className="h-3.5 w-3.5 text-primary" />
                  Obsidian Vault
                  <span className="ml-auto text-[10px] tabular-nums">
                    {tree.length}
                  </span>
                  <button
                    onClick={loadTree}
                    title="Recarregar"
                    className="hover:text-foreground"
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                  </button>
                </div>
                <div className="relative">
                  <Search className="h-3.5 w-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Buscar nota..."
                    className="h-8 pl-7 text-xs bg-background/40"
                  />
                </div>
              </div>
              <div className="flex-1 overflow-y-auto max-h-[600px]">
                {error && (
                  <div className="p-4 text-xs text-danger flex flex-col items-center gap-2 text-center">
                    <WifiOff className="h-4 w-4" />
                    {error}
                  </div>
                )}
                {groups.map(([folder, files]) => (
                  <div key={folder}>
                    <div className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] uppercase tracking-wider text-muted-foreground bg-background/40 sticky top-0">
                      <Folder className="h-3 w-3" />
                      {folder}
                    </div>
                    {files.map((f) => (
                      <button
                        key={f.path}
                        onClick={() => openFile(f.path)}
                        className={cn(
                          "w-full text-left pl-7 pr-3 py-2 border-b border-border/40 hover:bg-accent/40 transition-colors flex items-center gap-2",
                          f.path === activePath && "bg-accent/60",
                        )}
                      >
                        <FileText className="h-3.5 w-3.5 text-primary/70 shrink-0" />
                        <span className="text-xs truncate flex-1">
                          {f.name}
                        </span>
                      </button>
                    ))}
                  </div>
                ))}
              </div>
            </Card>

            {/* Render */}
            <Card className="lg:col-span-8 p-0 bg-card border-border overflow-hidden flex flex-col">
              {active ? (
                <>
                  <div className="px-5 py-3 border-b border-border">
                    <div className="text-sm font-medium">{active.name}</div>
                    <div className="text-[10px] text-muted-foreground tabular-nums">
                      {active.path} · modificado {fmtDate(active.modified)}
                    </div>
                  </div>
                  <div className="flex-1 overflow-y-auto max-h-[640px] px-6 py-4">
                    {loading ? (
                      <div className="grid place-items-center py-10 text-muted-foreground">
                        <Loader2 className="h-5 w-5 animate-spin" />
                      </div>
                    ) : (
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={mdComponents}
                      >
                        {rendered}
                      </ReactMarkdown>
                    )}
                  </div>
                </>
              ) : (
                <div className="p-10 text-center text-sm text-muted-foreground">
                  {error
                    ? "Connector offline ou vault vazio."
                    : "Selecione uma nota."}
                </div>
              )}
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </AppLayout>
  );
}
