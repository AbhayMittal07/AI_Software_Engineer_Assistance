import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ArrowDownUp, Filter, Github, Package, Search, Trash2, Upload } from "lucide-react";
import { toast } from "sonner";
import { api, apiError } from "@/lib/api";
import type { Paged, Repository } from "@/lib/types";
import { Badge } from "@/components/common/Metrics";
import { AsciiLoader, EmptyState, ErrorState } from "@/components/common/States";
import { formatBytes, formatNumber, relativeTime, statusTone } from "@/lib/format";

const SORTS = [
  { value: "created_at", label: "Newest" },
  { value: "name", label: "Name" },
  { value: "total_lines", label: "Lines" },
  { value: "file_count", label: "Files" },
];

export default function Repositories() {
  const [params, setParams] = useSearchParams();
  const queryClient = useQueryClient();
  const [query, setQuery] = useState(params.get("q") || "");
  const [language, setLanguage] = useState("all");
  const [status, setStatus] = useState("all");
  const [sortBy, setSortBy] = useState("created_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);

  useEffect(() => {
    setQuery(params.get("q") || "");
  }, [params]);

  const { data, isLoading, error, refetch } = useQuery<Paged<Repository>>({
    queryKey: ["repositories", query, language, status, sortBy, sortDir, page],
    queryFn: async () =>
      (
        await api.get("/repositories", {
          params: { q: query || undefined, language, status, sort_by: sortBy, sort_dir: sortDir, page, page_size: 12 },
        })
      ).data,
  });

  const remove = useMutation({
    mutationFn: async (id: number) => api.delete(`/repositories/${id}`),
    onSuccess: () => {
      toast.success("Repository deleted");
      void queryClient.invalidateQueries({ queryKey: ["repositories"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (mutationError) => toast.error(apiError(mutationError)),
  });

  const languages = useMemo(() => {
    const values = new Set<string>();
    (data?.items || []).forEach((repo) => values.add(repo.primary_language));
    return ["all", ...Array.from(values)];
  }, [data]);

  return (
    <div className="space-y-6" data-testid="repositories-page">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-6">
        <div>
          <p className="label-mono">Inventory</p>
          <h1 className="mt-2 font-mono text-3xl font-extrabold uppercase tracking-tighter">Repositories</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {data ? `${data.total} project${data.total === 1 ? "" : "s"} indexed` : "Loading inventory…"}
          </p>
        </div>
        <Link
          to="/upload"
          className="flex items-center gap-2 border border-primary bg-primary px-4 py-2 font-mono text-[11px] uppercase tracking-wider text-primary-foreground transition-colors hover:bg-primary/85"
          data-testid="repositories-add-button"
        >
          <Upload className="h-3.5 w-3.5" /> Add repository
        </Link>
      </header>

      <div className="panel grid gap-3 p-4 md:grid-cols-[1fr_auto_auto_auto]" data-testid="repositories-filters">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <input
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setPage(1);
              setParams(event.target.value ? { q: event.target.value } : {});
            }}
            placeholder="Filter by name or description…"
            className="h-10 w-full border border-border bg-background pl-9 pr-3 font-mono text-xs outline-none focus:border-primary focus:ring-2 focus:ring-primary/40"
            data-testid="repositories-search-input"
          />
        </div>
        <select
          value={language}
          onChange={(event) => {
            setLanguage(event.target.value);
            setPage(1);
          }}
          className="h-10 border border-border bg-background px-3 font-mono text-xs outline-none focus:border-primary"
          data-testid="repositories-language-filter"
          aria-label="Filter by language"
        >
          {languages.map((item) => (
            <option key={item} value={item}>
              {item === "all" ? "All languages" : item}
            </option>
          ))}
        </select>
        <select
          value={status}
          onChange={(event) => {
            setStatus(event.target.value);
            setPage(1);
          }}
          className="h-10 border border-border bg-background px-3 font-mono text-xs outline-none focus:border-primary"
          data-testid="repositories-status-filter"
          aria-label="Filter by status"
        >
          {["all", "ready", "analyzing", "failed", "pending"].map((item) => (
            <option key={item} value={item}>
              {item === "all" ? "Any status" : item}
            </option>
          ))}
        </select>
        <div className="flex gap-2">
          <select
            value={sortBy}
            onChange={(event) => setSortBy(event.target.value)}
            className="h-10 flex-1 border border-border bg-background px-3 font-mono text-xs outline-none focus:border-primary"
            data-testid="repositories-sort-select"
            aria-label="Sort by"
          >
            {SORTS.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => setSortDir((prev) => (prev === "asc" ? "desc" : "asc"))}
            className="border border-border px-3 transition-colors hover:border-primary hover:text-primary"
            data-testid="repositories-sort-direction"
            aria-label="Toggle sort direction"
          >
            <ArrowDownUp className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {isLoading && <AsciiLoader label="Fetching repositories" />}
      {error && <ErrorState message="Could not load repositories." onRetry={() => void refetch()} />}

      {data && data.items.length === 0 && (
        <EmptyState
          title="Nothing matches those filters"
          description="Clear the filters or add a new repository to analyse."
          action={
            <Link to="/upload" className="border border-primary px-4 py-2 font-mono text-[11px] uppercase tracking-wider text-primary" data-testid="repositories-empty-add">
              Add repository
            </Link>
          }
          testId="repositories-empty"
        />
      )}

      {data && data.items.length > 0 && (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3" data-testid="repositories-grid">
          {data.items.map((repo, index) => (
            <motion.article
              key={repo.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35, delay: index * 0.04, ease: [0.16, 1, 0.3, 1] }}
              className="panel hover-lift flex h-full flex-col p-5"
              data-testid={`repository-card-${repo.id}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <Link to={`/repositories/${repo.id}`} className="block truncate font-mono text-base font-bold tracking-tight hover:text-primary" data-testid={`repository-link-${repo.id}`}>
                    {repo.name}
                  </Link>
                  <p className="label-mono mt-1 flex items-center gap-1.5">
                    {repo.source_type === "github" ? <Github className="h-3 w-3" /> : <Package className="h-3 w-3" />}
                    {repo.source_type} · {relativeTime(repo.created_at)}
                  </p>
                </div>
                <Badge className={statusTone(repo.status)} testId={`repository-status-${repo.id}`}>
                  {repo.status}
                </Badge>
              </div>

              <p className="mt-3 line-clamp-2 min-h-[2.5rem] text-xs text-muted-foreground">
                {repo.description || "No description provided."}
              </p>

              <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-2 border-t border-border pt-4 font-mono text-[11px]">
                <div className="flex justify-between"><dt className="text-muted-foreground">Lang</dt><dd>{repo.primary_language}</dd></div>
                <div className="flex justify-between"><dt className="text-muted-foreground">Stack</dt><dd className="truncate pl-2">{repo.framework}</dd></div>
                <div className="flex justify-between"><dt className="text-muted-foreground">Files</dt><dd>{formatNumber(repo.file_count)}</dd></div>
                <div className="flex justify-between"><dt className="text-muted-foreground">LOC</dt><dd>{formatNumber(repo.total_lines)}</dd></div>
                <div className="flex justify-between"><dt className="text-muted-foreground">Size</dt><dd>{formatBytes(repo.size_bytes)}</dd></div>
                <div className="flex justify-between"><dt className="text-muted-foreground">Chunks</dt><dd>{formatNumber(repo.indexed_chunks)}</dd></div>
              </dl>

              <div className="mt-auto flex items-center gap-2 pt-4">
                <Link
                  to={`/repositories/${repo.id}`}
                  className="flex-1 border border-border py-2 text-center font-mono text-[11px] uppercase tracking-wider transition-colors hover:border-primary hover:text-primary"
                  data-testid={`repository-open-${repo.id}`}
                >
                  Open
                </Link>
                <Link
                  to={`/repositories/${repo.id}/chat`}
                  className="flex-1 border border-border py-2 text-center font-mono text-[11px] uppercase tracking-wider transition-colors hover:border-primary hover:text-primary"
                  data-testid={`repository-chat-${repo.id}`}
                >
                  Ask AI
                </Link>
                <button
                  type="button"
                  onClick={() => {
                    if (window.confirm(`Delete ${repo.name}? This removes all reviews, docs and diagrams.`)) {
                      remove.mutate(repo.id);
                    }
                  }}
                  className="border border-border p-2 transition-colors hover:border-signal-critical hover:text-signal-critical"
                  data-testid={`repository-delete-${repo.id}`}
                  aria-label={`Delete ${repo.name}`}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </motion.article>
          ))}
        </div>
      )}

      {data && data.pages > 1 && (
        <nav className="flex items-center justify-between border-t border-border pt-4" data-testid="repositories-pagination">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setPage((prev) => Math.max(1, prev - 1))}
            className="border border-border px-4 py-2 font-mono text-[11px] uppercase tracking-wider disabled:opacity-40"
            data-testid="pagination-prev"
          >
            Previous
          </button>
          <span className="label-mono flex items-center gap-2">
            <Filter className="h-3 w-3" /> Page {data.page} / {data.pages}
          </span>
          <button
            type="button"
            disabled={page >= data.pages}
            onClick={() => setPage((prev) => prev + 1)}
            className="border border-border px-4 py-2 font-mono text-[11px] uppercase tracking-wider disabled:opacity-40"
            data-testid="pagination-next"
          >
            Next
          </button>
        </nav>
      )}
    </div>
  );
}
