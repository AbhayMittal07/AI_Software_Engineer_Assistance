import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BookOpen,
  BrainCircuit,
  FileCode2,
  FileText,
  GitBranch,
  Loader2,
  MessageSquareCode,
  Network,
  RefreshCw,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { api, apiError } from "@/lib/api";
import type { RepositoryDetail as RepoDetail, Review } from "@/lib/types";
import { Badge, MetricCard, ScoreBar } from "@/components/common/Metrics";
import { AsciiLoader, EmptyState, ErrorState } from "@/components/common/States";
import { FileTree } from "@/components/common/FileTree";
import { formatBytes, formatDateTime, formatNumber, relativeTime, statusTone } from "@/lib/format";

interface FileContent {
  path: string;
  language: string;
  lines: number;
  size_bytes: number;
  content: string;
  truncated: boolean;
}

export default function RepositoryDetail() {
  const { repoId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [selectedFile, setSelectedFile] = useState<string | undefined>();
  const [fileContent, setFileContent] = useState<FileContent | null>(null);
  const [depth, setDepth] = useState("standard");

  const repoQuery = useQuery<RepoDetail>({
    queryKey: ["repository", repoId],
    queryFn: async () => (await api.get(`/repositories/${repoId}`)).data,
  });

  const reviewsQuery = useQuery<Review[]>({
    queryKey: ["repository-reviews", repoId],
    queryFn: async () => (await api.get(`/repositories/${repoId}/reviews`)).data,
  });

  const runReview = useMutation({
    mutationFn: async () => (await api.post(`/repositories/${repoId}/reviews`, { depth })).data,
    onSuccess: (review: Review) => {
      toast.success("AI review completed");
      void queryClient.invalidateQueries({ queryKey: ["repository-reviews", repoId] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      navigate(`/reviews/${review.id}`);
    },
    onError: (error) => toast.error(apiError(error, "Review failed")),
  });

  const reanalyze = useMutation({
    mutationFn: async () => (await api.post(`/repositories/${repoId}/reanalyze`)).data,
    onSuccess: () => {
      toast.success("Repository re-analysed");
      void queryClient.invalidateQueries({ queryKey: ["repository", repoId] });
    },
    onError: (error) => toast.error(apiError(error)),
  });

  const removeRepo = useMutation({
    mutationFn: async () => api.delete(`/repositories/${repoId}`),
    onSuccess: () => {
      toast.success("Repository deleted");
      void queryClient.invalidateQueries({ queryKey: ["repositories"] });
      navigate("/repositories");
    },
    onError: (error) => toast.error(apiError(error)),
  });

  const loadFile = async (path: string) => {
    setSelectedFile(path);
    try {
      const { data } = await api.get<FileContent>(`/repositories/${repoId}/file`, { params: { path } });
      setFileContent(data);
    } catch (error) {
      toast.error(apiError(error, "Could not open file"));
    }
  };

  if (repoQuery.isLoading) return <AsciiLoader label="Loading repository" />;
  if (repoQuery.error || !repoQuery.data)
    return <ErrorState message="Repository not found." onRetry={() => void repoQuery.refetch()} />;

  const repo = repoQuery.data;
  const metrics = repo.metrics || {};

  return (
    <div className="space-y-6" data-testid="repository-detail-page">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-6">
        <div className="min-w-0">
          <p className="label-mono flex items-center gap-2">
            <GitBranch className="h-3 w-3" /> {repo.source_type}
            {repo.source_url && (
              <a href={repo.source_url} target="_blank" rel="noreferrer" className="text-primary underline underline-offset-4" data-testid="repo-source-link">
                {repo.source_url}
              </a>
            )}
          </p>
          <h1 className="mt-2 break-words font-mono text-3xl font-extrabold uppercase tracking-tighter" data-testid="repository-name">
            {repo.name}
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            {repo.description || "No description provided."}
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Badge className={statusTone(repo.status)} testId="repository-detail-status">{repo.status}</Badge>
            <Badge className="border-border text-muted-foreground">{repo.primary_language}</Badge>
            <Badge className="border-border text-muted-foreground">{repo.framework}</Badge>
            <Badge className="border-border text-muted-foreground">{repo.architecture}</Badge>
            <Badge className="border-border text-muted-foreground">{repo.indexed_chunks} RAG chunks</Badge>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <select
            value={depth}
            onChange={(event) => setDepth(event.target.value)}
            className="h-10 border border-border bg-background px-3 font-mono text-[11px] uppercase tracking-wider outline-none focus:border-primary"
            data-testid="review-depth-select"
            aria-label="Review depth"
          >
            <option value="quick">Quick scan</option>
            <option value="standard">Standard review</option>
            <option value="deep">Deep review</option>
          </select>
          <button
            type="button"
            disabled={runReview.isPending}
            onClick={() => runReview.mutate()}
            className="flex items-center gap-2 border border-primary bg-primary px-4 py-2 font-mono text-[11px] uppercase tracking-wider text-primary-foreground transition-colors hover:bg-primary/85 disabled:opacity-60"
            data-testid="run-review-button"
          >
            {runReview.isPending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <BrainCircuit className="h-3.5 w-3.5" />}
            {runReview.isPending ? "Reviewing" : "Run AI review"}
          </button>
          <button
            type="button"
            disabled={reanalyze.isPending}
            onClick={() => reanalyze.mutate()}
            className="border border-border p-2 transition-colors hover:border-primary hover:text-primary"
            data-testid="reanalyze-button"
            aria-label="Re-analyse repository"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${reanalyze.isPending ? "animate-spin" : ""}`} />
          </button>
          <button
            type="button"
            onClick={() => {
              if (window.confirm(`Delete ${repo.name}?`)) removeRepo.mutate();
            }}
            className="border border-border p-2 transition-colors hover:border-signal-critical hover:text-signal-critical"
            data-testid="delete-repository-button"
            aria-label="Delete repository"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </header>

      {runReview.isPending && (
        <div className="panel p-4" data-testid="review-running-banner">
          <AsciiLoader label={`Gemini is performing a ${depth} review`} />
        </div>
      )}

      <nav className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" data-testid="repository-quick-links">
        {[
          { to: `/repositories/${repo.id}/documentation`, label: "Documentation", icon: BookOpen, count: repo.document_count, testId: "link-documentation" },
          { to: `/repositories/${repo.id}/architecture`, label: "Architecture", icon: Network, count: repo.diagram_count, testId: "link-architecture" },
          { to: `/repositories/${repo.id}/chat`, label: "Ask the codebase", icon: MessageSquareCode, count: repo.indexed_chunks, testId: "link-chat" },
          { to: `/reports?repository_id=${repo.id}`, label: "Reports", icon: FileText, count: repo.report_count, testId: "link-reports" },
        ].map((item) => {
          const Icon = item.icon;
          return (
            <Link key={item.to} to={item.to} className="panel hover-lift flex items-center gap-3 p-4" data-testid={item.testId}>
              <Icon className="h-4 w-4 text-primary" />
              <span className="font-mono text-xs uppercase tracking-wider">{item.label}</span>
              <span className="ml-auto font-mono text-sm font-bold text-primary">{formatNumber(item.count)}</span>
            </Link>
          );
        })}
      </nav>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Files" value={formatNumber(repo.file_count)} hint={`${metrics.code_files || 0} source files`} testId="detail-metric-files" />
        <MetricCard label="Lines of code" value={formatNumber(repo.total_lines)} hint={`avg ${metrics.avg_file_lines || 0} per file`} testId="detail-metric-lines" />
        <MetricCard label="Size" value={formatBytes(repo.size_bytes)} hint={`${repo.dependencies.length} dependencies`} testId="detail-metric-size" />
        <MetricCard label="Test ratio" value={`${metrics.test_ratio_pct || 0}%`} hint={`${metrics.test_files || 0} test files`} testId="detail-metric-tests" />
      </section>

      <section className="grid gap-4 lg:grid-cols-[320px_1fr]">
        <div className="panel" data-testid="detected-stack-panel">
          <p className="label-mono border-b border-border px-5 py-3">Detected stack</p>
          <dl className="divide-y divide-border font-mono text-[11px]">
            {[
              ["Language", repo.primary_language],
              ["Framework", repo.framework],
              ["Architecture", repo.architecture],
              ["Project type", repo.project_type],
              ["Package manager", repo.package_manager],
              ["Build tool", repo.build_tool],
              ["Entrypoints", (repo.entrypoints || []).join(", ") || "—"],
              ["Created", formatDateTime(repo.created_at)],
            ].map(([key, value]) => (
              <div key={key} className="flex items-start justify-between gap-3 px-5 py-2.5">
                <dt className="text-muted-foreground">{key}</dt>
                <dd className="max-w-[60%] break-words text-right">{value}</dd>
              </div>
            ))}
          </dl>
          <div className="border-t border-border p-5">
            <p className="label-mono mb-4">Static signals</p>
            <div className="space-y-3">
              <ScoreBar label="Comment density" score={Math.min((metrics.comment_density_pct || 0) * 3, 100)} testId="signal-comments" />
              <ScoreBar label="Test coverage signal" score={Math.min((metrics.test_ratio_pct || 0) * 2, 100)} testId="signal-tests" />
              <ScoreBar label="Complexity headroom" score={Math.max(100 - (metrics.high_complexity_functions || 0) * 8, 0)} testId="signal-complexity" />
            </div>
          </div>
        </div>

        <div className="grid gap-4">
          <div className="panel" data-testid="file-explorer-panel">
            <p className="label-mono border-b border-border px-5 py-3">File explorer</p>
            <div className="grid lg:grid-cols-[280px_1fr]">
              <div className="border-b border-border lg:border-b-0 lg:border-r">
                <FileTree tree={repo.file_tree} onSelect={loadFile} selected={selectedFile} />
              </div>
              <div className="min-h-[200px]">
                {fileContent ? (
                  <div>
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-4 py-2">
                      <p className="font-mono text-[11px] text-primary">{fileContent.path}</p>
                      <p className="label-mono">
                        {fileContent.language} · {fileContent.lines} lines · {formatBytes(fileContent.size_bytes)}
                      </p>
                    </div>
                    <pre className="max-h-[460px] overflow-auto bg-muted/40 p-4 font-mono text-[11px] leading-relaxed" data-testid="file-content">
                      {fileContent.content}
                    </pre>
                  </div>
                ) : (
                  <div className="flex h-full items-center justify-center p-8 text-center">
                    <p className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
                      <FileCode2 className="h-4 w-4" /> Select a file to preview its contents
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="panel" data-testid="dependencies-panel">
            <p className="label-mono border-b border-border px-5 py-3">Dependencies ({repo.dependencies.length})</p>
            {repo.dependencies.length ? (
              <div className="max-h-[300px] overflow-y-auto">
                <table className="w-full font-mono text-[11px]">
                  <thead className="sticky top-0 bg-card">
                    <tr className="border-b border-border text-left uppercase tracking-wider text-muted-foreground">
                      <th className="px-5 py-2">Package</th>
                      <th className="px-5 py-2">Version</th>
                      <th className="px-5 py-2">Ecosystem</th>
                      <th className="px-5 py-2">Type</th>
                    </tr>
                  </thead>
                  <tbody>
                    {repo.dependencies.map((dep) => (
                      <tr key={`${dep.ecosystem}-${dep.name}`} className="border-b border-border/60 last:border-b-0">
                        <td className="px-5 py-2">{dep.name}</td>
                        <td className="px-5 py-2 text-muted-foreground">{dep.version || "unpinned"}</td>
                        <td className="px-5 py-2 text-muted-foreground">{dep.ecosystem}</td>
                        <td className="px-5 py-2 text-muted-foreground">{dep.kind}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState title="No dependencies detected" testId="dependencies-empty" />
            )}
          </div>
        </div>
      </section>

      <section className="panel" data-testid="repository-reviews-panel">
        <p className="label-mono border-b border-border px-5 py-3">Review history</p>
        {reviewsQuery.data && reviewsQuery.data.length > 0 ? (
          <ul>
            {reviewsQuery.data.map((review) => (
              <li key={review.id} className="border-b border-border last:border-b-0">
                <Link
                  to={`/reviews/${review.id}`}
                  className="flex flex-wrap items-center gap-4 px-5 py-4 transition-colors hover:bg-muted/40"
                  data-testid={`review-row-${review.id}`}
                >
                  <span className="font-mono text-sm">#{review.id}</span>
                  <Badge className={statusTone(review.status)}>{review.status}</Badge>
                  <Badge className="border-border text-muted-foreground">{review.depth}</Badge>
                  <Badge className={review.ai_powered ? "border-primary/60 text-primary" : "border-border text-muted-foreground"}>
                    {review.ai_powered ? review.model : "static"}
                  </Badge>
                  <span className="label-mono ml-auto">{relativeTime(review.created_at)}</span>
                  <span className="font-mono text-sm font-bold text-primary">{Math.round(review.quality_score)}</span>
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState title="No reviews yet" description="Run an AI review to generate findings, tests and scores." testId="repo-reviews-empty" />
        )}
      </section>
    </div>
  );
}
