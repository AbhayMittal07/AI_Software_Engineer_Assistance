import { Link } from "react-router-dom";
import { AlertOctagon } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-24 text-center" data-testid="not-found-page">
      <AlertOctagon className="h-10 w-10 text-signal-medium" />
      <h1 className="font-mono text-4xl font-extrabold uppercase tracking-tighter">404</h1>
      <p className="max-w-md text-sm text-muted-foreground">
        The route you requested does not exist in this workspace.
      </p>
      <Link
        to="/"
        className="border border-primary px-5 py-2 font-mono text-[11px] uppercase tracking-wider text-primary transition-colors hover:bg-primary hover:text-primary-foreground"
        data-testid="not-found-home-link"
      >
        Back to dashboard
      </Link>
    </div>
  );
}
