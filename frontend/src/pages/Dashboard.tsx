import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  FileText,
  FolderGit2,
  GitBranch,
  ShieldAlert,
  Sparkles,
  Upload,
} from "lucide-react";
import { api } from "@/lib/api";
import type { DashboardStats } from "@/lib/types";
import { MetricCard, ScoreBar, ScoreRing, Badge } from "@/components/common/Metrics";
import { AsciiLoader, EmptyState, ErrorState } from "@/components/common/States";
import { formatNumber, relativeTime, scoreTone, statusTone } from "@/lib/format";

const CHART_COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
];

export default function Dashboard() {
  const { data, isLoading, error, refetch } = useQuery<DashboardStats>({
    queryKey: ["dashboard"],
    queryFn: async () => (await api.get("/dashboard")).data,
  });

  if (isLoading) return <AsciiLoader label="Aggregating metrics" />;
  if (error || !data)
    return <ErrorState message="Could not load dashboard metrics." onRetry={() => void refetch()} />;

  const languageData = Object.entries(data.language_distribution).map(([name, value]) => ({ name, value }));
  const severityData = ["critical", "high", "medium", "low", "info"]
    .map((key) => ({ name: key, value: data.severity_distribution[key] || 0 }))
    .filter((item) => item.value > 0);

  return (
    <div className="space-y-8" data-testid="dashboard-page">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-border pb-6">
        <div>
          <p className="label-mono">Control centre</p>
          <h1 className="mt-2 font-mono text-3xl font-extrabold uppercase tracking-tighter sm:text-4xl">
            Dashboard
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Aggregated engineering intelligence across every repository you have analysed.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Badge
            className={data.ai_enabled ? "border-signal-ok/60 bg-signal-ok/10 text-signal-ok" : "border-signal-medium/60 bg-signal-medium/10 text-signal-medium"}
            testId="ai-status-badge"
          >
            <Sparkles className="mr-1.5 h-3 w-3" />
            {data.ai_enabled ? `AI online · ${data.ai_model}` : "AI offline · static mode"}
          </Badge>
          <Link
            to="/upload"
            className="flex items-center gap-2 border border-primary bg-primary px-4 py-2 font-mono text-[11px] uppercase tracking-wider text-primary-foreground transition-colors hover:bg-primary/85"
            data-testid="dashboard-new-analysis-button"
          >
            <Upload className="h-3.5 w-3.5" /> New analysis
          </Link>
        </div>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Repositories"
          value={formatNumber(data.total_repositories)}
          hint={`${data.total_documents} docs · ${data.total_diagrams} diagrams`}
          icon={<FolderGit2 className="h-4 w-4" />}
          testId="metric-repositories"
          delay={0}
        />
        <MetricCard
          label="AI Reviews"
          value={formatNumber(data.total_reviews)}
          hint={`${data.total_reports} PDF reports generated`}
          icon={<BrainCircuit className="h-4 w-4" />}
          testId="metric-reviews"
          delay={0.05}
        />
        <MetricCard
          label="Findings"
          value={formatNumber(data.total_findings)}
          hint="across all completed reviews"
          icon={<Activity className="h-4 w-4" />}
          testId="metric-findings"
          delay={0.1}
        />
        <MetricCard
          label="Critical + High"
          value={formatNumber(data.critical_findings)}
          hint="require immediate attention"
          icon={<ShieldAlert className="h-4 w-4" />}
          tone="text-signal-critical"
          testId="metric-critical"
          delay={0.15}
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <div className="panel p-6" data-testid="score-overview-panel">
          <div className="mb-6 flex items-center justify-between">
            <p className="label-mono">Average score profile</p>
            <span className={`font-mono text-sm font-bold ${scoreTone(data.avg_quality_score)}`}>
              {data.avg_quality_score}/100
            </span>
          </div>
          <div className="grid grid-cols-2 gap-6 sm:grid-cols-3">
            <ScoreRing score={data.avg_quality_score} label="Code quality" testId="ring-quality" />
            <ScoreRing score={data.avg_security_score} label="Security" testId="ring-security" />
            <ScoreRing score={data.avg_maintainability_score} label="Maintainability" testId="ring-maintainability" />
          </div>
          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            <ScoreBar label="Performance" score={data.avg_performance_score} testId="bar-performance" />
            <ScoreBar label="Complexity" score={data.avg_complexity_score} testId="bar-complexity" />
            <ScoreBar label="Technical debt" score={data.avg_technical_debt_score} testId="bar-debt" />
          </div>
        </div>

        <div className="panel p-6" data-testid="severity-panel">
          <p className="label-mono mb-6">Finding severity mix</p>
          {severityData.length ? (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie data={severityData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90} paddingAngle={2}>
                  {severityData.map((entry, index) => (
                    <Cell key={entry.name} fill={CHART_COLORS[index % CHART_COLORS.length]} stroke="hsl(var(--card))" />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: 0,
                    fontFamily: "JetBrains Mono, monospace",
                    fontSize: 11,
                  }}
                />
                <Legend wrapperStyle={{ fontFamily: "JetBrains Mono, monospace", fontSize: 10, textTransform: "uppercase" }} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState title="No findings yet" description="Run an AI review to populate severity data." testId="severity-empty" />
          )}
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="panel p-6" data-testid="trend-panel">
          <p className="label-mono mb-6">Score trend</p>
          {data.score_trend.length ? (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={data.score_trend}>
                <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="2 4" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }} stroke="hsl(var(--muted-foreground))" />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }} stroke="hsl(var(--muted-foreground))" />
                <Tooltip
                  contentStyle={{
                    background: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: 0,
                    fontFamily: "JetBrains Mono, monospace",
                    fontSize: 11,
                  }}
                />
                <Line type="monotone" dataKey="quality" stroke={CHART_COLORS[0]} strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="security" stroke={CHART_COLORS[4]} strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="maintainability" stroke={CHART_COLORS[1]} strokeWidth={2} dot={false} />
                <Legend wrapperStyle={{ fontFamily: "JetBrains Mono, monospace", fontSize: 10, textTransform: "uppercase" }} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState title="No trend data" description="Reviews will chart here over time." testId="trend-empty" />
          )}
        </div>

        <div className="panel p-6" data-testid="language-panel">
          <p className="label-mono mb-6">Language distribution</p>
          {languageData.length ? (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={languageData}>
                <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="2 4" vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }} stroke="hsl(var(--muted-foreground))" />
                <YAxis allowDecimals={false} tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }} stroke="hsl(var(--muted-foreground))" />
                <Tooltip
                  contentStyle={{
                    background: "hsl(var(--card))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: 0,
                    fontFamily: "JetBrains Mono, monospace",
                    fontSize: 11,
                  }}
                />
                <Bar dataKey="value" fill={CHART_COLORS[0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyState title="No repositories yet" description="Upload a project to see language stats." testId="language-empty" />
          )}
        </div>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <div className="panel" data-testid="recent-repos-panel">
          <div className="flex items-center justify-between border-b border-border px-6 py-4">
            <p className="label-mono">Recent repositories</p>
            <Link to="/repositories" className="font-mono text-[11px] uppercase tracking-wider text-primary" data-testid="view-all-repos-link">
              View all
            </Link>
          </div>
          {data.recent_repositories.length ? (
            <ul>
              {data.recent_repositories.map((repo) => (
                <li key={repo.id} className="border-b border-border last:border-b-0">
                  <Link
                    to={`/repositories/${repo.id}`}
                    className="flex items-center gap-4 px-6 py-4 transition-colors hover:bg-muted/40"
                    data-testid={`recent-repo-${repo.id}`}
                  >
                    <GitBranch className="h-4 w-4 shrink-0 text-primary" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-mono text-sm">{repo.name}</p>
                      <p className="label-mono mt-0.5">
                        {repo.primary_language} · {repo.framework} · {formatNumber(repo.total_lines)} LOC
                      </p>
                    </div>
                    <Badge className={statusTone(repo.status)}>{repo.status}</Badge>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState
              title="No repositories"
              description="Upload a ZIP or import a Git URL to begin."
              action={
                <Link to="/upload" className="border border-primary px-4 py-2 font-mono text-[11px] uppercase tracking-wider text-primary" data-testid="empty-upload-link">
                  Add repository
                </Link>
              }
              testId="repos-empty"
            />
          )}
        </div>

        <div className="panel" data-testid="recent-reviews-panel">
          <div className="flex items-center justify-between border-b border-border px-6 py-4">
            <p className="label-mono">Recent reviews</p>
            <Link to="/reviews" className="font-mono text-[11px] uppercase tracking-wider text-primary" data-testid="view-all-reviews-link">
              History
            </Link>
          </div>
          {data.recent_reviews.length ? (
            <ul>
              {data.recent_reviews.map((review) => (
                <li key={review.id} className="border-b border-border last:border-b-0">
                  <Link
                    to={`/reviews/${review.id}`}
                    className="flex items-center gap-4 px-6 py-4 transition-colors hover:bg-muted/40"
                    data-testid={`recent-review-${review.id}`}
                  >
                    <AlertTriangle className={`h-4 w-4 shrink-0 ${scoreTone(review.quality_score)}`} />
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-mono text-sm">Review #{review.id}</p>
                      <p className="label-mono mt-0.5">
                        {review.depth} · {relativeTime(review.created_at)} · {review.stats?.total_findings ?? 0} findings
                      </p>
                    </div>
                    <span className={`font-mono text-lg font-bold ${scoreTone(review.quality_score)}`}>
                      {Math.round(review.quality_score)}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="No reviews yet" description="Open a repository and run an AI review." testId="reviews-empty" />
          )}
        </div>
      </section>

      <section className="panel flex flex-wrap items-center justify-between gap-4 p-6" data-testid="reports-cta">
        <div className="flex items-center gap-3">
          <FileText className="h-5 w-5 text-primary" />
          <div>
            <p className="font-mono text-sm">{data.total_reports} PDF reports available</p>
            <p className="text-xs text-muted-foreground">
              Repository summary, architecture, security findings, metrics and recommendations.
            </p>
          </div>
        </div>
        <Link
          to="/reports"
          className="border border-border px-4 py-2 font-mono text-[11px] uppercase tracking-wider transition-colors hover:border-primary hover:text-primary"
          data-testid="dashboard-reports-link"
        >
          Open reports
        </Link>
      </section>
    </div>
  );
}
