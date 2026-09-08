import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, Loader2, Network, RefreshCw, Save } from "lucide-react";
import { toast } from "sonner";
import { api, apiError } from "@/lib/api";
import type { DiagramItem } from "@/lib/types";
import { Badge } from "@/components/common/Metrics";
import { AsciiLoader, EmptyState, ErrorState } from "@/components/common/States";
import { MermaidView } from "@/components/common/MermaidView";
import { DIAGRAM_LABELS, formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";

type Format = "mermaid" | "plantuml" | "drawio";

export default function ArchitecturePage() {
  const { repoId } = useParams();
  const queryClient = useQueryClient();
  const [activeId, setActiveId] = useState<number | null>(null);
  const [format, setFormat] = useState<Format>("mermaid");
  const [draft, setDraft] = useState("");

  const { data, isLoading, error, refetch } = useQuery<DiagramItem[]>({
    queryKey: ["diagrams", repoId],
    queryFn: async () => (await api.get(`/repositories/${repoId}/diagrams`)).data,
  });

  const active = data?.find((item) => item.id === activeId) || null;

  useEffect(() => {
    if (data?.length && activeId === null) setActiveId(data[0].id);
  }, [data, activeId]);

  useEffect(() => {
    if (!active) return;
    setDraft(format === "mermaid" ? active.mermaid : format === "plantuml" ? active.plantuml : active.drawio_xml);
  }, [active, format]);

  const generate = useMutation({
    mutationFn: async () =>
      (await api.post(`/repositories/${repoId}/diagrams`, { diagram_types: [], regenerate: true })).data,
    onSuccess: (diagrams: DiagramItem[]) => {
      toast.success(`Generated ${diagrams.length} diagrams`);
      void queryClient.invalidateQueries({ queryKey: ["diagrams", repoId] });
      void queryClient.invalidateQueries({ queryKey: ["repository", repoId] });
      if (diagrams.length) setActiveId(diagrams[0].id);
    },
    onError: (mutationError) => toast.error(apiError(mutationError, "Diagram generation failed")),
  });

  const save = useMutation({
    mutationFn: async () => {
      const payload =
        format === "mermaid" ? { mermaid: draft } : format === "plantuml" ? { plantuml: draft } : { drawio_xml: draft };
      return (await api.patch(`/diagrams/${activeId}`, payload)).data;
    },
    onSuccess: () => {
      toast.success("Diagram saved");
      void queryClient.invalidateQueries({ queryKey: ["diagrams", repoId] });
    },
    onError: (mutationError) => toast.error(apiError(mutationError, "Save failed")),
  });

  const download = async () => {
    if (!activeId) return;
    const response = await api.get(`/diagrams/${activeId}/export`, { params: { format }, responseType: "blob" });
    const url = window.URL.createObjectURL(response.data as Blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${active?.diagram_type || "diagram"}.${format === "drawio" ? "drawio" : format === "mermaid" ? "mmd" : "puml"}`;
    link.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6" data-testid="architecture-page">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-6">
        <div>
          <p className="label-mono">
            <Link to={`/repositories/${repoId}`} className="text-primary underline underline-offset-4" data-testid="diagrams-repo-link">
              ← back to repository
            </Link>
          </p>
          <h1 className="mt-2 flex items-center gap-3 font-mono text-3xl font-extrabold uppercase tracking-tighter">
            <Network className="h-6 w-6 text-primary" /> Architecture
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Editable Mermaid, PlantUML and Draw.io sources for architecture, component, flow, sequence, class,
            ER, data-flow, dependency and structure diagrams.
          </p>
        </div>
        <button
          type="button"
          disabled={generate.isPending}
          onClick={() => generate.mutate()}
          className="flex items-center gap-2 border border-primary bg-primary px-4 py-2 font-mono text-[11px] uppercase tracking-wider text-primary-foreground transition-colors hover:bg-primary/85 disabled:opacity-60"
          data-testid="generate-diagrams-button"
        >
          {generate.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
          {generate.isPending ? "Generating" : "Generate all diagrams"}
        </button>
      </header>

      {generate.isPending && (
        <div className="panel p-4">
          <AsciiLoader label="Rendering architecture intelligence" />
        </div>
      )}

      {isLoading && <AsciiLoader label="Loading diagrams" />}
      {error && <ErrorState message="Could not load diagrams." onRetry={() => void refetch()} />}

      {data && data.length === 0 && !generate.isPending && (
        <EmptyState
          title="No diagrams yet"
          description="Generate the diagram set to visualise this repository."
          action={
            <button
              type="button"
              onClick={() => generate.mutate()}
              className="border border-primary px-4 py-2 font-mono text-[11px] uppercase tracking-wider text-primary"
              data-testid="diagrams-empty-generate"
            >
              Generate diagrams
            </button>
          }
          testId="diagrams-empty"
        />
      )}

      {data && data.length > 0 && (
        <>
          <nav className="flex flex-wrap gap-2" data-testid="diagram-type-tabs">
            {data.map((diagram) => (
              <button
                key={diagram.id}
                type="button"
                onClick={() => setActiveId(diagram.id)}
                className={cn(
                  "border px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider transition-colors",
                  activeId === diagram.id
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-border text-muted-foreground hover:border-primary hover:text-primary"
                )}
                data-testid={`diagram-tab-${diagram.diagram_type}`}
              >
                {DIAGRAM_LABELS[diagram.diagram_type] || diagram.diagram_type}
              </button>
            ))}
          </nav>

          {active && (
            <div className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
              <div className="panel" data-testid="diagram-preview-panel">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-5 py-3">
                  <div>
                    <h2 className="font-mono text-base tracking-tight">{active.title}</h2>
                    <p className="label-mono mt-1">Updated {formatDateTime(active.created_at)}</p>
                  </div>
                  <Badge className={active.ai_powered ? "border-primary/60 text-primary" : "border-border text-muted-foreground"}>
                    {active.ai_powered ? "AI generated" : "derived"}
                  </Badge>
                </div>
                {format === "mermaid" ? (
                  <MermaidView code={draft} testId="diagram-mermaid-preview" />
                ) : (
                  <div className="p-5">
                    <p className="label-mono mb-3">
                      {format === "plantuml" ? "PlantUML source" : "Draw.io mxGraph XML"} — paste into{" "}
                      {format === "plantuml" ? "plantuml.com" : "app.diagrams.net"} to render
                    </p>
                    <pre className="max-h-[520px] overflow-auto border border-border bg-muted/40 p-4 font-mono text-[11px] leading-relaxed" data-testid="diagram-alt-preview">
                      {draft}
                    </pre>
                  </div>
                )}
              </div>

              <div className="panel" data-testid="diagram-editor-panel">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-5 py-3">
                  <div className="flex gap-2">
                    {(["mermaid", "plantuml", "drawio"] as Format[]).map((item) => (
                      <button
                        key={item}
                        type="button"
                        onClick={() => setFormat(item)}
                        className={cn(
                          "border px-3 py-1 font-mono text-[10px] uppercase tracking-wider transition-colors",
                          format === item ? "border-primary text-primary" : "border-border text-muted-foreground hover:text-foreground"
                        )}
                        data-testid={`format-tab-${item}`}
                      >
                        {item}
                      </button>
                    ))}
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => save.mutate()}
                      disabled={save.isPending}
                      className="flex items-center gap-2 border border-primary px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider text-primary transition-colors hover:bg-primary hover:text-primary-foreground disabled:opacity-60"
                      data-testid="save-diagram-button"
                    >
                      {save.isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Save className="h-3 w-3" />}
                      Save
                    </button>
                    <button
                      type="button"
                      onClick={() => void download()}
                      className="border border-border p-2 transition-colors hover:border-primary hover:text-primary"
                      data-testid="download-diagram-button"
                      aria-label="Download diagram source"
                    >
                      <Download className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
                <textarea
                  value={draft}
                  onChange={(event) => setDraft(event.target.value)}
                  spellCheck={false}
                  className="h-[520px] w-full resize-none bg-background p-5 font-mono text-[11px] leading-relaxed outline-none focus:ring-2 focus:ring-primary/40"
                  data-testid="diagram-source-editor"
                />
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
