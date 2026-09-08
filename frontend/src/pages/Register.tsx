import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Loader2, Terminal, UserPlus } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/context/AuthContext";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    if (password.length < 8 || !/[a-zA-Z]/.test(password) || !/\d/.test(password)) {
      setError("Password must be at least 8 characters and contain letters and numbers");
      return;
    }
    setLoading(true);
    try {
      await register(email.trim(), password, fullName.trim());
      toast.success("Account created");
      navigate("/", { replace: true });
    } catch (registerError) {
      setError(registerError instanceof Error ? registerError.message : "Unable to register");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="w-full max-w-md border border-border bg-card p-8"
      >
        <div className="mb-8 flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center border border-primary text-primary">
            <Terminal className="h-4 w-4" />
          </span>
          <div>
            <p className="label-mono">AI SWE Assistant</p>
            <h1 className="font-mono text-xl font-bold tracking-tighter">Create account</h1>
          </div>
        </div>

        <form onSubmit={submit} className="space-y-5" data-testid="register-form">
          <div className="space-y-2">
            <label htmlFor="full_name" className="label-mono">
              Full name
            </label>
            <input
              id="full_name"
              required
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              className="h-11 w-full border border-border bg-background px-3 font-mono text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/40"
              data-testid="register-name-input"
            />
          </div>
          <div className="space-y-2">
            <label htmlFor="reg_email" className="label-mono">
              Email
            </label>
            <input
              id="reg_email"
              type="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="h-11 w-full border border-border bg-background px-3 font-mono text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/40"
              data-testid="register-email-input"
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <label htmlFor="reg_password" className="label-mono">
                Password
              </label>
              <input
                id="reg_password"
                type="password"
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="h-11 w-full border border-border bg-background px-3 font-mono text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/40"
                data-testid="register-password-input"
              />
            </div>
            <div className="space-y-2">
              <label htmlFor="reg_confirm" className="label-mono">
                Confirm
              </label>
              <input
                id="reg_confirm"
                type="password"
                required
                value={confirm}
                onChange={(event) => setConfirm(event.target.value)}
                className="h-11 w-full border border-border bg-background px-3 font-mono text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/40"
                data-testid="register-confirm-input"
              />
            </div>
          </div>

          {error && (
            <p
              className="border border-signal-critical/60 bg-signal-critical/10 px-3 py-2 text-xs text-signal-critical"
              data-testid="register-error"
            >
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="flex h-11 w-full items-center justify-center gap-2 border border-primary bg-primary font-mono text-xs uppercase tracking-[0.2em] text-primary-foreground transition-colors hover:bg-primary/85 disabled:opacity-60"
            data-testid="register-submit-button"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
            {loading ? "Creating" : "Create account"}
          </button>
        </form>

        <p className="mt-6 text-xs text-muted-foreground">
          Already registered?{" "}
          <Link to="/login" className="text-primary underline underline-offset-4" data-testid="go-to-login-link">
            Sign in
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
