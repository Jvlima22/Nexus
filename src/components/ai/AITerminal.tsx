import { useEffect, useRef, useState } from "react";
import { Card } from "@/components/ui/card";
import { terminalFeed } from "@/lib/mock-data";
import { Terminal } from "lucide-react";
import { cn } from "@/lib/utils";

const toneClass: Record<string, string> = {
  info: "text-foreground/70",
  warn: "text-warning",
  ok: "text-success",
  act: "text-primary",
};

export function AITerminal({ className }: { className?: string }) {
  const [count, setCount] = useState(1);
  const [typed, setTyped] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  // Typewriter for the active line
  useEffect(() => {
    const current = terminalFeed[count - 1];
    if (!current) return;
    setTyped("");
    let i = 0;
    const id = setInterval(() => {
      i++;
      setTyped(current.text.slice(0, i));
      if (i >= current.text.length) clearInterval(id);
    }, 18);
    return () => clearInterval(id);
  }, [count]);

  // Advance line
  useEffect(() => {
    const id = setInterval(() => {
      setCount((c) => (c >= terminalFeed.length ? 1 : c + 1));
    }, 2600);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [count, typed]);

  const visible = terminalFeed.slice(0, count);

  return (
    <Card className={cn("p-0 bg-card border-border overflow-hidden", className)}>
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border bg-background/40">
        <div className="flex items-center gap-2">
          <span className="flex gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-danger/70" />
            <span className="h-2.5 w-2.5 rounded-full bg-warning/70" />
            <span className="h-2.5 w-2.5 rounded-full bg-success/70" />
          </span>
          <Terminal className="h-3.5 w-3.5 text-muted-foreground ml-2" />
          <span className="text-[11px] uppercase tracking-wider text-muted-foreground">
            claude — nexus://thoughts
          </span>
        </div>
        <span className="text-[10px] text-success flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-success animate-thinking" /> streaming
        </span>
      </div>

      <div
        ref={scrollRef}
        className="font-mono text-[12.5px] leading-relaxed p-4 h-[340px] overflow-y-auto bg-background/30"
      >
        {visible.map((line, i) => {
          const last = i === visible.length - 1;
          return (
            <div key={`${count}-${i}`} className="flex gap-2 items-baseline animate-fade-in">
              <span className="text-muted-foreground/60 tabular-nums select-none">
                {line.icon} [{line.time}]
              </span>
              <span className={toneClass[line.tone ?? "info"]}>
                {last ? typed : line.text}
                {last && <span className="inline-block w-1.5 h-3.5 ml-0.5 align-middle bg-primary animate-thinking" />}
              </span>
            </div>
          );
        })}
      </div>
    </Card>
  );
}
