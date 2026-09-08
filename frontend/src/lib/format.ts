export function formatBytes(bytes = 0): string {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / 1024 ** index).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

export function formatNumber(value = 0): string {
  return new Intl.NumberFormat("en-US").format(value);
}

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  return date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}

export function formatDateTime(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  return `${formatDate(value)} ${date.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}`;
}

export function relativeTime(value?: string | null): string {
  if (!value) return "—";
  const diff = Date.now() - new Date(value).getTime();
  const minutes = Math.round(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 30) return `${days}d ago`;
  return formatDate(value);
}

export const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"] as const;

export function severityClass(severity = "info"): string {
  const key = severity.toLowerCase();
  if (key === "critical") return "border-signal-critical/60 text-signal-critical bg-signal-critical/10";
  if (key === "high") return "border-signal-high/60 text-signal-high bg-signal-high/10";
  if (key === "medium") return "border-signal-medium/60 text-signal-medium bg-signal-medium/10";
  if (key === "low") return "border-signal-low/60 text-signal-low bg-signal-low/10";
  return "border-border text-muted-foreground bg-muted";
}

export function scoreTone(score = 0): string {
  if (score >= 80) return "text-signal-ok";
  if (score >= 60) return "text-signal-medium";
  if (score >= 40) return "text-signal-high";
  return "text-signal-critical";
}

export function scoreStroke(score = 0): string {
  if (score >= 80) return "hsl(var(--signal-ok))";
  if (score >= 60) return "hsl(var(--signal-medium))";
  if (score >= 40) return "hsl(var(--signal-high))";
  return "hsl(var(--signal-critical))";
}

export function statusTone(status = ""): string {
  switch (status) {
    case "ready":
    case "completed":
      return "border-signal-ok/60 text-signal-ok bg-signal-ok/10";
    case "analyzing":
    case "running":
    case "pending":
      return "border-signal-low/60 text-signal-low bg-signal-low/10";
    case "failed":
      return "border-signal-critical/60 text-signal-critical bg-signal-critical/10";
    default:
      return "border-border text-muted-foreground bg-muted";
  }
}

export const DOC_LABELS: Record<string, string> = {
  readme: "README",
  api: "API Reference",
  developer: "Developer Guide",
  installation: "Installation",
  deployment: "Deployment",
  structure: "Folder Structure",
  dependencies: "Dependencies",
  environment: "Environment Vars",
  architecture: "Architecture",
};

export const DIAGRAM_LABELS: Record<string, string> = {
  architecture: "Architecture",
  component: "Component",
  flow: "Flow",
  sequence: "Sequence",
  class: "Class",
  er: "ER",
  dataflow: "Data Flow",
  dependency: "Dependency Graph",
  structure: "Repository Structure",
};
