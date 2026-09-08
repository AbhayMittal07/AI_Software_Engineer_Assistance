import { Loader2, AlertTriangle, Inbox } from "lucide-react";
import { cn } from "@/lib/utils";

export function AsciiLoader({ label = "Loading", className = "" }: { label?: string; className?: string }) {
  return (
    <div
      className={cn("flex flex-col items-center justify-center gap-3 py-16", className)}
      data-testid="ascii-loader"
    >
      <pre className="font-mono text-[10px] leading-tight text-primary sm:text-xs">
        {`  ╔══════════════════════════════╗
  ║   A N A L Y S I N G   ...    ║
  ║   ▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░   ║
  ╚══════════════════════════════╝`}
      </pre>
      <p className="label-mono flex items-center gap-2">
        <Loader2 className="h-3 w-3 animate-spin" />
        {label}
        <span className="animate-blink">_</span>
      </p>
    </div>
  );
}

export function InlineSpinner({ label }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 font-mono text-xs text-muted-foreground">
      <Loader2 className="h-3.5 w-3.5 animate-spin" />
      {label}
    </span>
  );
}

export function SkeletonBlock({ className = "" }: { className?: string }) {
  return <div className={cn("animate-pulse border border-border bg-muted/60", className)} />;
}

export function SkeletonGrid({ count = 4, height = "h-28" }: { count?: number; height?: string }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4" data-testid="skeleton-grid">
      {Array.from({ length: count }).map((_, index) => (
        <SkeletonBlock key={index} className={height} />
      ))}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
  testId = "empty-state",
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
  testId?: string;
}) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 border border-dashed border-border bg-card/40 px-6 py-16 text-center"
      data-testid={testId}
    >
      <Inbox className="h-7 w-7 text-muted-foreground" />
      <h3 className="font-mono text-base tracking-tight">{title}</h3>
      {description && <p className="max-w-md text-sm text-muted-foreground">{description}</p>}
      {action}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
  testId = "error-state",
}: {
  message: string;
  onRetry?: () => void;
  testId?: string;
}) {
  return (
    <div
      className="flex flex-col items-start gap-3 border border-signal-critical/50 bg-signal-critical/5 p-6"
      data-testid={testId}
    >
      <div className="flex items-center gap-2 text-signal-critical">
        <AlertTriangle className="h-4 w-4" />
        <span className="label-mono text-signal-critical">Error</span>
      </div>
      <p className="text-sm text-foreground/90">{message}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="border border-signal-critical/60 px-3 py-1.5 font-mono text-xs uppercase tracking-wider text-signal-critical transition-colors hover:bg-signal-critical hover:text-white"
          data-testid="error-retry-button"
        >
          Retry
        </button>
      )}
    </div>
  );
}
