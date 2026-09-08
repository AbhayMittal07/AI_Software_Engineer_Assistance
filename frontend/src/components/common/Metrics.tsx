import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { scoreStroke, scoreTone } from "@/lib/format";

export function ScoreRing({
  score,
  label,
  size = 104,
  testId,
}: {
  score: number;
  label: string;
  size?: number;
  testId?: string;
}) {
  const radius = size / 2 - 8;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.max(0, Math.min(100, score)) / 100) * circumference;
  return (
    <div className="flex flex-col items-center gap-2" data-testid={testId}>
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="hsl(var(--border))"
            strokeWidth={6}
          />
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={scoreStroke(score)}
            strokeWidth={6}
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={cn("font-mono text-xl font-bold tracking-tighter", scoreTone(score))}>
            {Math.round(score)}
          </span>
        </div>
      </div>
      <span className="label-mono text-center">{label}</span>
    </div>
  );
}

export function MetricCard({
  label,
  value,
  hint,
  icon,
  tone,
  testId,
  delay = 0,
}: {
  label: string;
  value: string | number;
  hint?: string;
  icon?: React.ReactNode;
  tone?: string;
  testId?: string;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: [0.16, 1, 0.3, 1] }}
      className="panel hover-lift relative overflow-hidden p-5"
      data-testid={testId}
    >
      <div className="flex items-start justify-between gap-3">
        <span className="label-mono">{label}</span>
        {icon && <span className="text-muted-foreground">{icon}</span>}
      </div>
      <p className={cn("stat-value mt-3", tone)}>{value}</p>
      {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
    </motion.div>
  );
}

export function ScoreBar({ label, score, testId }: { label: string; score: number; testId?: string }) {
  return (
    <div className="space-y-1.5" data-testid={testId}>
      <div className="flex items-baseline justify-between">
        <span className="label-mono">{label}</span>
        <span className={cn("font-mono text-sm font-bold", scoreTone(score))}>{Math.round(score)}</span>
      </div>
      <div className="h-1.5 w-full bg-muted">
        <motion.div
          className="h-full"
          style={{ backgroundColor: scoreStroke(score) }}
          initial={{ width: 0 }}
          animate={{ width: `${Math.max(0, Math.min(100, score))}%` }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        />
      </div>
    </div>
  );
}

export function Badge({
  children,
  className,
  testId,
}: {
  children: React.ReactNode;
  className?: string;
  testId?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center border px-2 py-0.5 font-mono text-[10px] uppercase tracking-[0.15em]",
        className
      )}
      data-testid={testId}
    >
      {children}
    </span>
  );
}
