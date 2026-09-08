import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Loader2, ShieldCheck, Terminal } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("demo@example.com");
  const [password, setPassword] = useState("Demo@12345");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email.trim(), password);
      toast.success("Signed in");
      navigate("/", { replace: true });
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : "Unable to sign in");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      <div className="noise relative hidden flex-col justify-between overflow-hidden border-r border-border bg-card p-12 lg:flex">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center border border-primary text-primary">
            <Terminal className="h-4 w-4" />
          </span>
          <span className="font-mono text-sm font-bold uppercase tracking-tight">AI SWE Assistant</span>
        </div>
        <div className="relative z-10 max-w-xl">
          <p className="label-mono mb-5">Static analysis · Gemini review · RAG chat</p>
          <h1 className="font-mono text-4xl font-extrabold uppercase leading-[1.05] tracking-tighter sm:text-5xl">
            Ship code
            <br />
            <span className="text-primary">reviewed by AI</span>
            <br />
            not by luck.
          </h1>
          <p className="mt-6 max-w-md text-base leading-relaxed text-muted-foreground">
            Upload a ZIP or import a Git URL. Get OWASP security scans, complexity analysis, SOLID
            violations, editable architecture diagrams, generated tests, documentation and PDF reports.
          </p>
          <div className="mt-10 grid grid-cols-3 border border-border">
            {[
              ["9", "Doc types"],
              ["9", "Diagram types"],
              ["6", "Score metrics"],
            ].map(([value, label]) => (
              <div key={label} className="border-r border-border p-4 last:border-r-0">
                <p className="font-mono text-2xl font-bold tracking-tighter text-primary">{value}</p>
                <p className="label-mono mt-1">{label}</p>
              </div>
            ))}
          </div>
        </div>
        <p className="label-mono flex items-center gap-2">
          <ShieldCheck className="h-3 w-3" /> JWT auth · bcrypt · rate limited · local-first
        </p>
      </div>

      <div className="flex items-center justify-center p-6 sm:p-12">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="w-full max-w-sm"
        >
          <p className="label-mono">Authentication</p>
          <h2 className="mt-2 font-mono text-2xl font-bold tracking-tighter">Sign in</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Use the seeded demo account or your own credentials.
          </p>

          <form onSubmit={submit} className="mt-8 space-y-5" data-testid="login-form">
            <div className="space-y-2">
              <label htmlFor="email" className="label-mono">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="h-11 w-full border border-border bg-card px-3 font-mono text-sm outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/40"
                data-testid="login-email-input"
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="password" className="label-mono">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="h-11 w-full border border-border bg-card px-3 font-mono text-sm outline-none transition-colors focus:border-primary focus:ring-2 focus:ring-primary/40"
                data-testid="login-password-input"
              />
            </div>

            {error && (
              <p
                className="border border-signal-critical/60 bg-signal-critical/10 px-3 py-2 text-xs text-signal-critical"
                data-testid="login-error"
              >
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="flex h-11 w-full items-center justify-center gap-2 border border-primary bg-primary font-mono text-xs uppercase tracking-[0.2em] text-primary-foreground transition-colors hover:bg-primary/85 disabled:opacity-60"
              data-testid="login-submit-button"
            >
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
              {loading ? "Signing in" : "Sign in"}
            </button>
          </form>

          <p className="mt-6 text-xs text-muted-foreground">
            No account?{" "}
            <Link to="/register" className="text-primary underline underline-offset-4" data-testid="go-to-register-link">
              Create one
            </Link>
          </p>
          <div className="mt-8 border border-border p-4">
            <p className="label-mono mb-2">Seeded accounts</p>
            <p className="font-mono text-[11px] text-muted-foreground">admin@example.com / Admin@12345</p>
            <p className="font-mono text-[11px] text-muted-foreground">demo@example.com / Demo@12345</p>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
