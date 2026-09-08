import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { History } from "lucide-react";
import { api } from "@/lib/api";
import type { Paged, Review } from "@/lib/types";
import { Badge } from "@/components/common/Metrics";
import { AsciiLoader, EmptyState, ErrorState } from "@/components/common/States";
import { formatDateTime, scoreTone, statusTone } from "@/lib/format";

export default function ReviewHistory() {
  const [status, setStatus] = useState("all");
  const [page, setPage] = useState(1);

  const { data, isLoading, error, refetch } = useQuery<Paged<Review>>({
    queryKey: ["reviews", status, page],
    queryFn: async () => (await api.get("/reviews", { params: { status, page, page_size: 20 } })).data,
  });

  return (
    <div className="space-y-6" data-testid="review-history-page">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-6">
        <div>
          <p className="label-mono">Audit trail</p>
          <h1 className="mt-2 font-mono text-3xl font-extrabold uppercase tracking-tighter">Review history</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Every AI review executed on your repositories, with score snapshots.
          </p>
        </div>
        <select
          value={status}
          onChange={(event) => {
            setStatus(event.target.value);
            setPage(1);
          }}
          className="h-10 border border-border bg-background px-3 font-mono text-xs outline-none focus:border-primary"
          data-testid="review-status-filter"
          aria-label="Filter reviews by status"
        >
          {["all", "completed", "running", "failed", "pending"].map((item) => (
            <option key={item} value={item}>
              {item === "all" ? "Any status" : item}
            </option>
          ))}
        </select>
      </header>

      {isLoading && <AsciiLoader label="Loading review history" />}
      {error && <ErrorState message="Could not load review history." onRetry={() => void refetch()} />}

      {data && data.items.length === 0 && (
        <EmptyState
          title="No reviews recorded"
          description="Open a repository and run an AI review to populate this history."
          action={
            <Link to="/repositories" className="border border-primary px-4 py-2 font-mono text-[11px] uppercase tracking-wider text-primary" data-testid="history-empty-link">
              Go to repositories
            </Link>
          }
          testId="review-history-empty"
        />
      )}

      {data && data.items.length > 0 && (
        <div className="panel overflow-x-auto" data-testid="review-history-table">
          <table className="w-full font-mono text-[11px]">
            <thead>
              <tr className="border-b border-border text-left uppercase tracking-wider text-muted-foreground">
                <th className="px-5 py-3">ID</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Depth</th>
                <th className="px-5 py-3">Engine</th>
                <th className="px-5 py-3">Quality</th>
                <th className="px-5 py-3">Security</th>
                <th className="px-5 py-3">Findings</th>
                <th className="px-5 py-3">Completed</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody>
              {data.items.map((review) => (
                <tr key={review.id} className="border-b border-border/60 last:border-b-0" data-testid={`history-row-${review.id}`}>
                  <td className="px-5 py-3">#{review.id}</td>
                  <td className="px-5 py-3">
                    <Badge className={statusTone(review.status)}>{review.status}</Badge>
                  </td>
                  <td className="px-5 py-3 text-muted-foreground">{review.depth}</td>
                  <td className="px-5 py-3 text-muted-foreground">{review.ai_powered ? review.model : "static"}</td>
                  <td className={`px-5 py-3 font-bold ${scoreTone(review.quality_score)}`}>{Math.round(review.quality_score)}</td>
                  <td className={`px-5 py-3 font-bold ${scoreTone(review.security_score)}`}>{Math.round(review.security_score)}</td>
                  <td className="px-5 py-3">{review.stats?.total_findings ?? 0}</td>
                  <td className="px-5 py-3 text-muted-foreground">{formatDateTime(review.completed_at || review.created_at)}</td>
                  <td className="px-5 py-3">
                    <Link to={`/reviews/${review.id}`} className="text-primary underline underline-offset-4" data-testid={`history-open-${review.id}`}>
                      Open
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {data && data.pages > 1 && (
        <nav className="flex items-center justify-between border-t border-border pt-4">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setPage((prev) => Math.max(1, prev - 1))}
            className="border border-border px-4 py-2 font-mono text-[11px] uppercase tracking-wider disabled:opacity-40"
            data-testid="history-prev"
          >
            Previous
          </button>
          <span className="label-mono flex items-center gap-2">
            <History className="h-3 w-3" /> Page {data.page} / {data.pages}
          </span>
          <button
            type="button"
            disabled={page >= data.pages}
            onClick={() => setPage((prev) => prev + 1)}
            className="border border-border px-4 py-2 font-mono text-[11px] uppercase tracking-wider disabled:opacity-40"
            data-testid="history-next"
          >
            Next
          </button>
        </nav>
      )}
    </div>
  );
}
