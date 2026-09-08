import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Loader2, Save, Settings2 } from "lucide-react";
import { toast } from "sonner";
import { api, apiError } from "@/lib/api";
import type { UserSettings } from "@/lib/types";
import { useTheme } from "@/context/ThemeContext";
import { AsciiLoader, ErrorState } from "@/components/common/States";
import { Badge } from "@/components/common/Metrics";

const MODELS = ["gemini-3.6-flash", "gemini-3.1-pro-preview"];

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const [form, setForm] = useState<UserSettings | null>(null);

  const { data, isLoading, error, refetch } = useQuery<UserSettings>({
    queryKey: ["settings"],
    queryFn: async () => (await api.get("/settings")).data,
  });

  const health = useQuery<{ ai_enabled: boolean; ai_model: string; cache_backend: string; database: string }>({
    queryKey: ["health"],
    queryFn: async () => (await api.get("/health")).data,
  });

  useEffect(() => {
    if (data) setForm(data);
  }, [data]);

  const save = useMutation({
    mutationFn: async () => (await api.patch("/settings", form)).data,
    onSuccess: (updated: UserSettings) => {
      toast.success("Settings saved");
      setForm(updated);
      if (updated.theme === "dark" || updated.theme === "light") setTheme(updated.theme);
    },
    onError: (mutationError) => toast.error(apiError(mutationError, "Could not save settings")),
  });

  if (isLoading || !form) return <AsciiLoader label="Loading settings" />;
  if (error) return <ErrorState message="Could not load settings." onRetry={() => void refetch()} />;

  const toggle = (key: keyof UserSettings) => setForm({ ...form, [key]: !form[key] } as UserSettings);

  return (
    <div className="space-y-6" data-testid="settings-page">
      <header className="border-b border-border pb-6">
        <p className="label-mono">Preferences</p>
        <h1 className="mt-2 flex items-center gap-3 font-mono text-3xl font-extrabold uppercase tracking-tighter">
          <Settings2 className="h-6 w-6 text-primary" /> Settings
        </h1>
      </header>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="panel p-6" data-testid="appearance-section">
          <p className="label-mono mb-5">Appearance</p>
          <div className="space-y-4">
            <div>
              <label htmlFor="theme" className="label-mono">
                Theme
              </label>
              <select
                id="theme"
                value={form.theme}
                onChange={(event) => {
                  setForm({ ...form, theme: event.target.value });
                  if (event.target.value === "dark" || event.target.value === "light") setTheme(event.target.value);
                }}
                className="mt-2 h-11 w-full border border-border bg-background px-3 font-mono text-xs outline-none focus:border-primary"
                data-testid="settings-theme-select"
              >
                <option value="dark">Dark (default)</option>
                <option value="light">Light</option>
                <option value="system">Follow system</option>
              </select>
              <p className="mt-2 text-xs text-muted-foreground">Currently rendering the {theme} palette.</p>
            </div>
          </div>
        </section>

        <section className="panel p-6" data-testid="ai-section">
          <p className="label-mono mb-5">AI engine</p>
          <div className="space-y-4">
            <div>
              <label htmlFor="ai_model" className="label-mono">
                Preferred model
              </label>
              <select
                id="ai_model"
                value={form.ai_model}
                onChange={(event) => setForm({ ...form, ai_model: event.target.value })}
                className="mt-2 h-11 w-full border border-border bg-background px-3 font-mono text-xs outline-none focus:border-primary"
                data-testid="settings-model-select"
              >
                {[...new Set([form.ai_model, ...MODELS])].map((model) => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                ))}
              </select>
              <p className="mt-2 text-xs text-muted-foreground">
                The active server model is configured with <code className="font-mono">GEMINI_TEXT_MODEL</code> in
                backend/.env.
              </p>
            </div>
            <div>
              <label htmlFor="review_depth" className="label-mono">
                Default review depth
              </label>
              <select
                id="review_depth"
                value={form.review_depth}
                onChange={(event) => setForm({ ...form, review_depth: event.target.value })}
                className="mt-2 h-11 w-full border border-border bg-background px-3 font-mono text-xs outline-none focus:border-primary"
                data-testid="settings-depth-select"
              >
                <option value="quick">Quick</option>
                <option value="standard">Standard</option>
                <option value="deep">Deep</option>
              </select>
            </div>
          </div>
        </section>

        <section className="panel p-6" data-testid="automation-section">
          <p className="label-mono mb-5">Automation</p>
          <div className="divide-y divide-border">
            {[
              ["auto_generate_docs", "Auto-generate documentation after analysis"],
              ["auto_generate_diagrams", "Auto-generate diagrams after analysis"],
              ["email_notifications", "Email me when a review completes"],
            ].map(([key, label]) => (
              <label key={key} className="flex cursor-pointer items-center justify-between gap-4 py-4">
                <span className="text-sm">{label}</span>
                <input
                  type="checkbox"
                  checked={Boolean(form[key as keyof UserSettings])}
                  onChange={() => toggle(key as keyof UserSettings)}
                  className="h-4 w-4 accent-[hsl(var(--primary))]"
                  data-testid={`settings-toggle-${key}`}
                />
              </label>
            ))}
          </div>
        </section>

        <section className="panel p-6" data-testid="system-section">
          <p className="label-mono mb-5">System status</p>
          {health.data ? (
            <dl className="divide-y divide-border font-mono text-[11px]">
              {[
                ["AI provider", health.data.ai_enabled ? `online · ${health.data.ai_model}` : "offline (static mode)"],
                ["Database", health.data.database],
                ["Cache backend", health.data.cache_backend],
              ].map(([key, value]) => (
                <div key={key} className="flex items-center justify-between py-3">
                  <dt className="text-muted-foreground">{key}</dt>
                  <dd>
                    <Badge className={String(value).includes("offline") ? "border-signal-medium/60 text-signal-medium" : "border-signal-ok/60 text-signal-ok"}>
                      {value}
                    </Badge>
                  </dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="font-mono text-xs text-muted-foreground">Checking system…</p>
          )}
        </section>
      </div>

      <button
        type="button"
        onClick={() => save.mutate()}
        disabled={save.isPending}
        className="flex items-center gap-2 border border-primary bg-primary px-6 py-3 font-mono text-[11px] uppercase tracking-[0.2em] text-primary-foreground transition-colors hover:bg-primary/85 disabled:opacity-60"
        data-testid="save-settings-button"
      >
        {save.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
        Save settings
      </button>
    </div>
  );
}
