import { Card } from "@/components/ui/card";
import { memoryNotes } from "@/lib/mock-data";
import { FileText, BookOpen, CheckCircle2, XCircle, Clock } from "lucide-react";

const outcomeMeta = {
  Sucesso: { icon: CheckCircle2, cls: "text-success bg-success/10 border-success/20" },
  Falha: { icon: XCircle, cls: "text-danger bg-danger/10 border-danger/20" },
  Pendente: { icon: Clock, cls: "text-warning bg-warning/10 border-warning/20" },
} as const;

export function KnowledgeBase() {
  return (
    <Card className="p-5 bg-card border-border">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-primary" />
          <h3 className="text-sm font-medium">Base de Conhecimento</h3>
        </div>
        <span className="text-[10px] text-muted-foreground flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-primary animate-thinking" />
          Obsidian Bridge
        </span>
      </div>

      <div className="space-y-3">
        {memoryNotes.map((n) => {
          const meta = outcomeMeta[n.outcome];
          const Icon = meta.icon;
          return (
            <div
              key={n.id}
              className="group relative rounded-md border border-border bg-background/40 p-3 hover:border-primary/40 transition-colors"
            >
              <div className="flex items-start gap-3">
                <div className="h-8 w-8 shrink-0 grid place-items-center rounded-md bg-primary/10 text-primary border border-primary/15">
                  <FileText className="h-3.5 w-3.5" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[10px] text-muted-foreground tabular-nums">Nota #{n.id}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted/50 text-muted-foreground">
                      #{n.tag}
                    </span>
                    <span className={`text-[10px] inline-flex items-center gap-1 px-1.5 py-0.5 rounded border ${meta.cls}`}>
                      <Icon className="h-2.5 w-2.5" /> {n.outcome}
                    </span>
                    <span className="text-[10px] text-muted-foreground/70 ml-auto">{n.updatedAt}</span>
                  </div>
                  <div className="mt-1 text-sm font-medium leading-snug">{n.title}</div>
                  <p className="mt-1 text-xs text-muted-foreground leading-relaxed">{n.body}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
