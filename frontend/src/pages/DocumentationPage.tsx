import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Copy, Download, Loader2, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { api, apiError } from "@/lib/api";
import type { DocumentItem } from "@/lib/types";
import { Badge } from "@/components/common/Metrics";
import { AsciiLoader, EmptyState, ErrorState } from "@/components/common/States";
import { MarkdownView } from "@/components/common/MarkdownView";
import { DOC_LABELS, formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";

export default function DocumentationPage() {
  const { repoId } = useParams();
  const queryClient = useQueryClient();
  const [activeId, setActiveId] = useState<number | null>(null);
  const [showSource, setShowSource] = useState(false);

  const { data, isLoading, error, refetch } = useQuery<DocumentItem[]>({
    queryKey: ["documentation", repoId],
    queryFn: async () => (await api.get(`/repositories/${repoId}/documentation`)).data,
  });

  useEffect(() => {
    if (data?.length && activeId === null) setActiveId(data[0].id);
  }, [data, activeId]);

  const generate = useMutation({
    mutationFn: async () =>
      (await api.post(`/repositories/${repoId}/documentation`, { doc_types: [], regenerate: true })).data,
    onSuccess: (docs: DocumentItem[]) => {
      toast.success(`Generated ${docs.length} documents`);
      void queryClient.invalidateQueries({ queryKey: ["documentation", repoId] });
      void queryClient.invalidateQueries({ queryKey: ["repository", repoId] });
      if (docs.length) setActiveId(docs[0].id);
    },
    onError: (mutationError) => toast.error(apiError(mutationError, "Documentation generation failed")),
  });

  const active = data?.find((item) => item.id === activeId) || null;

  const download = () => {
    if (!active) return;
    const blob = new Blob([active.content], { type: "text/markdown" });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${active.doc_type}.md`;
    link.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6" data-testid="documentation-page">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-6">
        <div>
          <p className="label-mono">
            <Link to={`/repositories/${repoId}`} className="text-primary underline underline-offset-4" data-testid="docs-repo-link">
              ← back to repository
            </Link>
          </p>
          <h1 className="mt-2 flex items-center gap-3 font-mono text-3xl font-extrabold uppercase tracking-tighter">
            <BookOpen className="h-6 w-6 text-primary" /> Documentation
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            README, API reference, developer guide, install & deployment guides, architecture and more.
          </p>
        </div>
        <button
          type="button"
          disabled={generate.isPending}
          onClick={() => generate.mutate()}
          className="flex items-center gap-2 border border-primary bg-primary px-4 py-2 font-mono text-[11px] uppercase tracking-wider text-primary-foreground transition-colors hover:bg-primary/85 disabled:opacity-60"
          data-testid="generate-docs-button"
        >
          {generate.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
          {generate.isPending ? "Generating" : "Generate all docs"}
        </button>
      </header>

      {generate.isPending && (
        <div className="panel p-4">
          <AsciiLoader label="Gemini is writing 9 documents" />
        </div>
      )}

      {isLoading && <AsciiLoader label="Loading documentation" />}
      {error && <ErrorState message="Could not load documentation." onRetry={() => void refetch()} />}

      {data && data.length === 0 && !generate.isPending && (
        <EmptyState
          title="No documentation generated yet"
          description="Generate the full documentation set for this repository."
          action={
            <button
              type="button"
              onClick={() => generate.mutate()}
              className="border border-primary px-4 py-2 font-mono text-[11px] uppercase tracking-wider text-primary"
              data-testid="docs-empty-generate"
            >
              Generate documentation
            </button>
          }
          testId="documentation-empty"
        />
      )}

      {data && data.length > 0 && (
        <div className="grid gap-4 lg:grid-cols-[260px_1fr]">
          <nav className="panel h-fit" data-testid="documentation-nav">
            <p className="label-mono border-b border-border px-4 py-3">Documents</p>
            <ul>
              {data.map((doc) => (
                <li key={doc.id}>
                  <button
                    type="button"
                    onClick={() => setActiveId(doc.id)}
                    className={cn(
                      "flex w-full items-center justify-between gap-2 border-l-2 px-4 py-2.5 text-left font-mono text-[11px] uppercase tracking-wider transition-colors",
                      activeId === doc.id
                        ? "border-l-primary bg-primary/10 text-primary"
                        : "border-l-transparent text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                    )}
                    data-testid={`doc-tab-${doc.doc_type}`}
                  >
                    {DOC_LABELS[doc.doc_type] || doc.doc_type}
                    {!doc.ai_powered && <span className="text-[9px] opacity-70">static</span>}
                  </button>
                </li>
              ))}
            </ul>
          </nav>

          <article className="panel" data-testid="documentation-viewer">
            {active ? (
              <>
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-6 py-4">
                  <div>
                    <h2 className="font-mono text-lg tracking-tight">{active.title}</h2>
                    <p className="label-mono mt-1">Updated {formatDateTime(active.created_at)}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge className={active.ai_powered ? "border-primary/60 text-primary" : "border-border text-muted-foreground"}>
                      {active.ai_powered ? "AI generated" : "static template"}
                    </Badge>
                    <button
                      type="button"
                      onClick={() => setShowSource((prev) => !prev)}
                      className="border border-border px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider transition-colors hover:border-primary hover:text-primary"
                      data-testid="toggle-doc-source"
                    >
                      {showSource ? "Rendered" : "Markdown"}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        void navigator.clipboard.writeText(active.content);
                        toast.success("Markdown copied");
                      }}
                      className="border border-border p-2 transition-colors hover:border-primary hover:text-primary"
                      data-testid="copy-doc-button"
                      aria-label="Copy markdown"
                    >
                      <Copy className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={download}
                      className="border border-border p-2 transition-colors hover:border-primary hover:text-primary"
                      data-testid="download-doc-button"
                      aria-label="Download markdown"
                    >
                      <Download className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
                <div className="p-6">
                  {showSource ? (
                    <pre className="overflow-x-auto whitespace-pre-wrap border border-border bg-muted/40 p-4 font-mono text-[11px] leading-relaxed" data-testid="doc-source">
                      {active.content}
                    </pre>
                  ) : (
                    <MarkdownView content={active.content} testId="doc-rendered" />
                  )}
                </div>
              </>
            ) : (
              <EmptyState title="Select a document" testId="doc-select-empty" />
            )}
          </article>
        </div>
      )}
    </div>
  );
}
