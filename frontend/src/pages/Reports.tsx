import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, FileText, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { api, apiError } from "@/lib/api";
import type { ReportItem } from "@/lib/types";
import { Badge } from "@/components/common/Metrics";
import { AsciiLoader, EmptyState, ErrorState } from "@/components/common/States";
import { formatBytes, formatDateTime } from "@/lib/format";

export default function Reports() {
  const [params] = useSearchParams();
  const repositoryId = params.get("repository_id");
  const queryClient = useQueryClient();

  const { data, isLoading, error, refetch } = useQuery<ReportItem[]>({
    queryKey: ["reports", repositoryId],
    queryFn: async () =>
      (await api.get("/reports", { params: repositoryId ? { repository_id: repositoryId } : {} })).data,
  });

  const remove = useMutation({
    mutationFn: async (id: number) => api.delete(`/reports/${id}`),
    onSuccess: () => {
      toast.success("Report deleted");
      void queryClient.invalidateQueries({ queryKey: ["reports"] });
    },
    onError: (mutationError) => toast.error(apiError(mutationError)),
  });

  const download = async (report: ReportItem) => {
    try {
      const response = await api.get(`/reports/${report.id}/download`, { responseType: "blob" });
      const url = window.URL.createObjectURL(response.data as Blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = report.file_name;
      link.click();
      window.URL.revokeObjectURL(url);
    } catch (downloadError) {
      toast.error(apiError(downloadError, "Download failed"));
    }
  };

  return (
    <div className="space-y-6" data-testid="reports-page">
      <header className="border-b border-border pb-6">
        <p className="label-mono">Deliverables</p>
        <h1 className="mt-2 font-mono text-3xl font-extrabold uppercase tracking-tighter">Reports</h1>
        <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
          Downloadable PDF engineering reports: repository summary, metrics, security findings, performance,
          code quality, diagram sources, documentation extracts and recommendations.
        </p>
      </header>

      {isLoading && <AsciiLoader label="Loading reports" />}
      {error && <ErrorState message="Could not load reports." onRetry={() => void refetch()} />}

      {data && data.length === 0 && (
        <EmptyState
          title="No reports generated"
          description="Open a completed review and use “Download PDF report”."
          testId="reports-empty"
        />
      )}

      {data && data.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" data-testid="reports-grid">
          {data.map((report) => (
            <article key={report.id} className="panel hover-lift flex h-full flex-col p-5" data-testid={`report-card-${report.id}`}>
              <div className="flex items-start gap-3">
                <FileText className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
                <div className="min-w-0">
                  <h2 className="truncate font-mono text-sm font-bold tracking-tight">{report.title}</h2>
                  <p className="label-mono mt-1">
                    {report.repository_name || `repo ${report.repository_id}`} ·{" "}
                    {report.review_id ? `review #${report.review_id}` : "no review"}
                  </p>
                </div>
              </div>
              <p className="mt-4 font-mono text-[11px] text-muted-foreground">{report.file_name}</p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {(report.sections || []).map((section) => (
                  <Badge key={section} className="border-border text-muted-foreground">
                    {section}
                  </Badge>
                ))}
              </div>
              <p className="label-mono mt-4">
                {formatBytes(report.size_bytes)} · {formatDateTime(report.created_at)}
              </p>
              <div className="mt-auto flex items-center gap-2 pt-4">
                <button
                  type="button"
                  onClick={() => void download(report)}
                  className="flex flex-1 items-center justify-center gap-2 border border-primary py-2 font-mono text-[11px] uppercase tracking-wider text-primary transition-colors hover:bg-primary hover:text-primary-foreground"
                  data-testid={`download-report-${report.id}`}
                >
                  <Download className="h-3.5 w-3.5" /> Download
                </button>
                <button
                  type="button"
                  onClick={() => remove.mutate(report.id)}
                  className="border border-border p-2 transition-colors hover:border-signal-critical hover:text-signal-critical"
                  data-testid={`delete-report-${report.id}`}
                  aria-label="Delete report"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
