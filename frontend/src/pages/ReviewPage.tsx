import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Download, FileDown, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { api, apiError } from "@/lib/api";
import type { Finding, ReviewDetail } from "@/lib/types";
import { Badge, ScoreBar, ScoreRing } from "@/components/common/Metrics";
import { AsciiLoader, EmptyState, ErrorState } from "@/components/common/States";
import { MarkdownView } from "@/components/common/MarkdownView";
import { formatDateTime, severityClass } from "@/lib/format";
import { cn } from "@/lib/utils";

const TABS = [
  { key: "findings", label: "Findings" },
  { key: "security", label: "Security / OWASP" },
  { key: "performance", label: "Performance" },
  { key: "quality", label: "Smells & dead code" },
  { key: "complexity", label: "Complexity" },
  { key: "architecture", label: "Architecture & SOLID" },
  { key: "dependencies", label: "Dependencies" },
  { key: "fixes", label: "Refactors & fixes" },
  { key: "tests", label: "Generated tests" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

function FindingCard({ finding, index }: { finding: Finding; index: number }) {
  return (
    <article className="border border-border bg-card p-5" data-testid={`finding-card-${index}`}>
      <div className="flex flex-wrap items-center gap-2">
        <Badge className={severityClass(finding.severity)}>{finding.severity || "info"}</Badge>
        {finding.category && <Badge className="border-border text-muted-foreground">{finding.category}</Badge>}
        {finding.owasp && <Badge className="border-primary/50 text-primary">{finding.owasp}</Badge>}
        {finding.cwe && <Badge className="border-border text-muted-foreground">{finding.cwe}</Badge>}
        {finding.source === "static" && <Badge className="border-border text-muted-foreground">static</Badge>}
        {finding.file && (
          <span className="ml-auto font-mono text-[11px] text-muted-foreground">
            {finding.file}
            {finding.line ? `:${finding.line}` : ""}
          </span>
        )}
      </div>
      <h3 className="mt-3 font-mono text-sm font-bold tracking-tight">{finding.title || finding.name || "Finding"}</h3>
      {finding.description && <p className="mt-2 text-sm text-muted-foreground">{finding.description}</p>}
      {finding.impact && (
        <p className="mt-2 text-xs text-muted-foreground">
          <span className="label-mono mr-2">Impact</span>
          {finding.impact}
        </p>
      )}
      {(finding.recommendation || finding.remediation || finding.optimization || finding.refactoring) && (
        <p className="mt-3 border-l-2 border-primary pl-3 text-sm">
          {finding.recommendation || finding.remediation || finding.optimization || finding.refactoring}
        </p>
      )}
      {finding.code_snippet && (
        <pre className="mt-3 overflow-x-auto border border-border bg-muted/50 p-3 font-mono text-[11px]">
          {finding.code_snippet}
        </pre>
      )}
      {finding.suggested_fix && (
        <pre className="mt-2 overflow-x-auto border border-signal-ok/40 bg-signal-ok/5 p-3 font-mono text-[11px]">
          {finding.suggested_fix}
        </pre>
      )}
    </article>
  );
}

function Section({ items, empty, prefix }: { items: Finding[]; empty: string; prefix: string }) {
  if (!items?.length) return <EmptyState title={empty} testId={`${prefix}-empty`} />;
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      {items.map((item, index) => (
        <FindingCard key={`${prefix}-${index}`} finding={item} index={index} />
      ))}
    </div>
  );
}

export default function ReviewPage() {
  const { reviewId } = useParams();
  const [tab, setTab] = useState<TabKey>("findings");
  const [severityFilter, setSeverityFilter] = useState("all");

  const { data, isLoading, error, refetch } = useQuery<ReviewDetail>({
    queryKey: ["review", reviewId],
    queryFn: async () => (await api.get(`/reviews/${reviewId}`)).data,
  });

  const createReport = useMutation({
    mutationFn: async () =>
      (await api.post(`/repositories/${data?.repository_id}/reports`, { review_id: data?.id })).data,
    onSuccess: async (report: { id: number; file_name: string }) => {
      toast.success("PDF report generated");
      const response = await api.get(`/reports/${report.id}/download`, { responseType: "blob" });
      const url = window.URL.createObjectURL(response.data as Blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = report.file_name;
      link.click();
      window.URL.revokeObjectURL(url);
    },
    onError: (mutationError) => toast.error(apiError(mutationError, "Report generation failed")),
  });

  const filteredFindings = useMemo(() => {
    if (!data) return [];
    if (severityFilter === "all") return data.findings;
    return data.findings.filter((item) => String(item.severity).toLowerCase() === severityFilter);
  }, [data, severityFilter]);

  if (isLoading) return <AsciiLoader label="Loading review" />;
  if (error || !data) return <ErrorState message="Review not found." onRetry={() => void refetch()} />;

  const stats = data.stats || {};

  return (
    <div className="space-y-6" data-testid="review-page">
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-border pb-6">
        <div>
          <p className="label-mono">
            Review #{data.id} ·{" "}
            <Link to={`/repositories/${data.repository_id}`} className="text-primary underline underline-offset-4" data-testid="review-repo-link">
              {data.repository_name || `repository ${data.repository_id}`}
            </Link>
          </p>
          <h1 className="mt-2 font-mono text-3xl font-extrabold uppercase tracking-tighter">AI code review</h1>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Badge className={data.ai_powered ? "border-primary/60 text-primary" : "border-signal-medium/60 text-signal-medium"}>
              <Sparkles className="mr-1.5 h-3 w-3" />
              {data.ai_powered ? `${data.provider} · ${data.model}` : "static analysis only"}
            </Badge>
            <Badge className="border-border text-muted-foreground">{data.depth} depth</Badge>
            <Badge className="border-border text-muted-foreground">{formatDateTime(data.completed_at || data.created_at)}</Badge>
          </div>
        </div>
        <button
          type="button"
          disabled={createReport.isPending}
          onClick={() => createReport.mutate()}
          className="flex items-center gap-2 border border-primary bg-primary px-4 py-2 font-mono text-[11px] uppercase tracking-wider text-primary-foreground transition-colors hover:bg-primary/85 disabled:opacity-60"
          data-testid="generate-report-button"
        >
          {createReport.isPending ? <Download className="h-3.5 w-3.5 animate-pulse" /> : <FileDown className="h-3.5 w-3.5" />}
          {createReport.isPending ? "Building PDF" : "Download PDF report"}
        </button>
      </header>

      <section className="panel p-6" data-testid="review-scores">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <ScoreRing score={data.quality_score} label="Code quality" testId="review-ring-quality" />
          <ScoreRing score={data.security_score} label="Security" testId="review-ring-security" />
          <ScoreRing score={data.maintainability_score} label="Maintainability" testId="review-ring-maintainability" />
          <ScoreRing score={data.performance_score} label="Performance" testId="review-ring-performance" />
        </div>
        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          <ScoreBar label="Complexity" score={data.complexity_score} testId="review-bar-complexity" />
          <ScoreBar label="Technical debt (higher = less debt)" score={data.technical_debt_score} testId="review-bar-debt" />
          <ScoreBar label="Scalability" score={data.scalability_score} testId="review-bar-scalability" />
        </div>
      </section>

      <section className="panel p-6" data-testid="review-summary">
        <p className="label-mono mb-3">Executive summary</p>
        <MarkdownView content={data.summary || "_No summary produced._"} testId="review-summary-markdown" />
        <div className="mt-6 grid grid-cols-2 gap-3 border-t border-border pt-6 sm:grid-cols-4 lg:grid-cols-6">
          {[
            ["Findings", stats.total_findings ?? data.findings.length],
            ["Critical", stats.critical ?? 0],
            ["High", stats.high ?? 0],
            ["Security", data.security_findings.length],
            ["Smells", data.code_smells.length],
            ["Tests", data.generated_tests.length],
          ].map(([label, value]) => (
            <div key={String(label)} className="border border-border p-3">
              <p className="label-mono">{label}</p>
              <p className="mt-1 font-mono text-xl font-bold tracking-tighter">{String(value)}</p>
            </div>
          ))}
        </div>
      </section>

      <nav className="flex flex-wrap gap-2 border-b border-border pb-3" data-testid="review-tabs">
        {TABS.map((item) => (
          <button
            key={item.key}
            type="button"
            onClick={() => setTab(item.key)}
            className={cn(
              "border px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider transition-colors",
              tab === item.key
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border text-muted-foreground hover:border-primary hover:text-primary"
            )}
            data-testid={`review-tab-${item.key}`}
          >
            {item.label}
          </button>
        ))}
      </nav>

      {tab === "findings" && (
        <div className="space-y-4" data-testid="tab-findings">
          <div className="flex flex-wrap gap-2">
            {["all", "critical", "high", "medium", "low", "info"].map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setSeverityFilter(item)}
                className={cn(
                  "border px-3 py-1 font-mono text-[10px] uppercase tracking-wider transition-colors",
                  severityFilter === item ? "border-primary text-primary" : "border-border text-muted-foreground hover:text-foreground"
                )}
                data-testid={`severity-filter-${item}`}
              >
                {item}
              </button>
            ))}
          </div>
          <Section items={filteredFindings} empty="No findings for this filter" prefix="finding" />
        </div>
      )}

      {tab === "security" && (
        <div data-testid="tab-security">
          <Section items={data.security_findings} empty="No security findings reported" prefix="security" />
        </div>
      )}

      {tab === "performance" && (
        <div data-testid="tab-performance">
          <Section items={[...data.performance_findings, ...data.optimization_suggestions]} empty="No performance issues reported" prefix="performance" />
        </div>
      )}

      {tab === "quality" && (
        <div className="space-y-6" data-testid="tab-quality">
          <div>
            <p className="label-mono mb-3">Code smells</p>
            <Section items={data.code_smells} empty="No code smells reported" prefix="smell" />
          </div>
          <div>
            <p className="label-mono mb-3">Dead code & unused symbols</p>
            <Section items={[...data.dead_code, ...data.unused_symbols]} empty="No dead code detected" prefix="dead" />
          </div>
          <div>
            <p className="label-mono mb-3">Duplicate code</p>
            {data.duplicate_code.length ? (
              <div className="grid gap-3">
                {data.duplicate_code.map((item, index) => (
                  <div key={index} className="border border-border p-4" data-testid={`duplicate-${index}`}>
                    <p className="font-mono text-xs text-primary">{(item.files || []).join("  ↔  ")}</p>
                    <p className="mt-2 text-sm text-muted-foreground">{item.description}</p>
                    {item.recommendation && <p className="mt-2 border-l-2 border-primary pl-3 text-sm">{item.recommendation}</p>}
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="No duplicate blocks detected" testId="duplicate-empty" />
            )}
          </div>
        </div>
      )}

      {tab === "complexity" && (
        <div className="panel overflow-x-auto" data-testid="tab-complexity">
          {data.complexity_analysis.length ? (
            <table className="w-full font-mono text-[11px]">
              <thead>
                <tr className="border-b border-border text-left uppercase tracking-wider text-muted-foreground">
                  <th className="px-5 py-3">File</th>
                  <th className="px-5 py-3">Function</th>
                  <th className="px-5 py-3">Cyclomatic</th>
                  <th className="px-5 py-3">Time</th>
                  <th className="px-5 py-3">Space</th>
                  <th className="px-5 py-3">Recommendation</th>
                </tr>
              </thead>
              <tbody>
                {data.complexity_analysis.map((item, index) => (
                  <tr key={index} className="border-b border-border/60 last:border-b-0" data-testid={`complexity-row-${index}`}>
                    <td className="px-5 py-3">{item.file}</td>
                    <td className="px-5 py-3">{item.function}</td>
                    <td className="px-5 py-3 text-primary">{item.cyclomatic ?? "—"}</td>
                    <td className="px-5 py-3">{item.time_complexity || "—"}</td>
                    <td className="px-5 py-3">{item.space_complexity || "—"}</td>
                    <td className="px-5 py-3 text-muted-foreground">{item.recommendation || item.explanation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <EmptyState title="No complexity hotspots detected" testId="complexity-empty" />
          )}
        </div>
      )}

      {tab === "architecture" && (
        <div className="space-y-6" data-testid="tab-architecture">
          <div className="panel p-6">
            <p className="label-mono mb-3">Clean architecture assessment</p>
            <p className="text-sm">{data.clean_architecture?.assessment || "Not assessed."}</p>
            {Array.isArray(data.clean_architecture?.recommendations) && (
              <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-muted-foreground">
                {data.clean_architecture.recommendations.map((item: string, index: number) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            )}
          </div>
          <div>
            <p className="label-mono mb-3">SOLID violations</p>
            <Section items={data.solid_violations.map((item) => ({ ...item, title: `${item.principle}: ${item.class_or_function}`, recommendation: item.fix }))} empty="No SOLID violations reported" prefix="solid" />
          </div>
          <div>
            <p className="label-mono mb-3">Design patterns detected</p>
            <Section items={data.design_patterns.map((item) => ({ ...item, title: item.pattern, description: item.usage, recommendation: item.assessment }))} empty="No design patterns identified" prefix="pattern" />
          </div>
          <div>
            <p className="label-mono mb-3">Best practices</p>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {data.best_practices.map((item, index) => (
                <div key={index} className="border border-border p-4" data-testid={`practice-${index}`}>
                  <div className="flex items-center justify-between gap-2">
                    <p className="font-mono text-xs">{item.area}</p>
                    <Badge className={item.status === "good" ? "border-signal-ok/60 text-signal-ok" : "border-signal-medium/60 text-signal-medium"}>
                      {item.status}
                    </Badge>
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">{item.detail}</p>
                  <p className="mt-2 text-xs">{item.action}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === "dependencies" && (
        <div className="panel overflow-x-auto" data-testid="tab-dependencies">
          {data.dependency_analysis.length ? (
            <table className="w-full font-mono text-[11px]">
              <thead>
                <tr className="border-b border-border text-left uppercase tracking-wider text-muted-foreground">
                  <th className="px-5 py-3">Package</th>
                  <th className="px-5 py-3">Version</th>
                  <th className="px-5 py-3">Risk</th>
                  <th className="px-5 py-3">Note</th>
                  <th className="px-5 py-3">Recommendation</th>
                </tr>
              </thead>
              <tbody>
                {data.dependency_analysis.map((item, index) => (
                  <tr key={index} className="border-b border-border/60 last:border-b-0" data-testid={`dependency-row-${index}`}>
                    <td className="px-5 py-3">{item.name}</td>
                    <td className="px-5 py-3 text-muted-foreground">{item.version || "unpinned"}</td>
                    <td className="px-5 py-3">
                      <Badge className={severityClass(item.risk === "high" ? "high" : item.risk === "medium" ? "medium" : "low")}>
                        {item.risk}
                      </Badge>
                    </td>
                    <td className="px-5 py-3 text-muted-foreground">{item.note}</td>
                    <td className="px-5 py-3">{item.recommendation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <EmptyState title="No dependency analysis available" testId="dependency-analysis-empty" />
          )}
        </div>
      )}

      {tab === "fixes" && (
        <div className="space-y-6" data-testid="tab-fixes">
          <div>
            <p className="label-mono mb-3">Refactoring suggestions</p>
            <Section items={data.refactoring_suggestions.map((item) => ({ ...item, description: item.benefit, code_snippet: item.before, suggested_fix: item.after }))} empty="No refactoring suggestions" prefix="refactor" />
          </div>
          <div>
            <p className="label-mono mb-3">Auto-fix suggestions</p>
            <Section items={data.auto_fixes.map((item) => ({ ...item, description: item.explanation, code_snippet: item.original, suggested_fix: item.fixed }))} empty="No auto-fixes proposed" prefix="autofix" />
          </div>
          {Array.isArray(stats.inline_comments) && stats.inline_comments.length > 0 && (
            <div className="panel p-5">
              <p className="label-mono mb-3">Inline code comments</p>
              <ul className="space-y-2 font-mono text-[11px]">
                {stats.inline_comments.map((item: any, index: number) => (
                  <li key={index} className="border-l-2 border-primary pl-3" data-testid={`inline-comment-${index}`}>
                    <span className="text-primary">
                      {item.file}:{item.line}
                    </span>{" "}
                    <span className="text-muted-foreground">{item.comment}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {tab === "tests" && (
        <div className="space-y-4" data-testid="tab-tests">
          {data.generated_tests.length ? (
            data.generated_tests.map((test, index) => (
              <div key={index} className="panel p-5" data-testid={`generated-test-${index}`}>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge className="border-primary/60 text-primary">{test.kind}</Badge>
                  <Badge className="border-border text-muted-foreground">{test.framework}</Badge>
                  <span className="font-mono text-[11px] text-muted-foreground">{test.file_name}</span>
                  {test.target_file && <span className="ml-auto font-mono text-[11px] text-muted-foreground">targets {test.target_file}</span>}
                </div>
                {test.description && <p className="mt-2 text-sm text-muted-foreground">{test.description}</p>}
                <pre className="mt-3 overflow-x-auto border border-border bg-muted/50 p-4 font-mono text-[11px] leading-relaxed">
                  {test.code}
                </pre>
              </div>
            ))
          ) : (
            <EmptyState title="No tests generated" description="Run a deeper review to generate unit and integration tests." testId="tests-empty" />
          )}
        </div>
      )}
    </div>
  );
}
