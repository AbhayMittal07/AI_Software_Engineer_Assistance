import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { KeyRound, Loader2, Save, UserCircle2 } from "lucide-react";
import { toast } from "sonner";
import { api, apiError } from "@/lib/api";
import type { User } from "@/lib/types";
import { useAuth } from "@/context/AuthContext";
import { Badge } from "@/components/common/Metrics";
import { formatDateTime } from "@/lib/format";

export default function Profile() {
  const { user, setUser, refreshUser } = useAuth();
  const [fullName, setFullName] = useState("");
  const [bio, setBio] = useState("");
  const [company, setCompany] = useState("");
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");

  useEffect(() => {
    if (user) {
      setFullName(user.full_name);
      setBio(user.bio || "");
      setCompany(user.company || "");
    }
  }, [user]);

  const saveProfile = useMutation({
    mutationFn: async () =>
      (await api.patch<User>("/users/me", { full_name: fullName, bio, company })).data,
    onSuccess: (updated) => {
      toast.success("Profile updated");
      setUser(updated);
      void refreshUser();
    },
    onError: (error) => toast.error(apiError(error, "Could not update profile")),
  });

  const changePassword = useMutation({
    mutationFn: async () =>
      (await api.post("/auth/change-password", { current_password: current, new_password: next })).data,
    onSuccess: () => {
      toast.success("Password changed — other sessions were revoked");
      setCurrent("");
      setNext("");
    },
    onError: (error) => toast.error(apiError(error, "Could not change password")),
  });

  if (!user) return null;

  return (
    <div className="space-y-6" data-testid="profile-page">
      <header className="border-b border-border pb-6">
        <p className="label-mono">Account</p>
        <h1 className="mt-2 flex items-center gap-3 font-mono text-3xl font-extrabold uppercase tracking-tighter">
          <UserCircle2 className="h-6 w-6 text-primary" /> Profile
        </h1>
      </header>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <section className="panel p-6" data-testid="profile-form-section">
          <p className="label-mono mb-5">Personal details</p>
          <div className="space-y-4">
            <div>
              <label htmlFor="profile_name" className="label-mono">
                Full name
              </label>
              <input
                id="profile_name"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                className="mt-2 h-11 w-full border border-border bg-background px-3 font-mono text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/40"
                data-testid="profile-name-input"
              />
            </div>
            <div>
              <label htmlFor="profile_company" className="label-mono">
                Company / Institution
              </label>
              <input
                id="profile_company"
                value={company}
                onChange={(event) => setCompany(event.target.value)}
                className="mt-2 h-11 w-full border border-border bg-background px-3 font-mono text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/40"
                data-testid="profile-company-input"
              />
            </div>
            <div>
              <label htmlFor="profile_bio" className="label-mono">
                Bio
              </label>
              <textarea
                id="profile_bio"
                value={bio}
                onChange={(event) => setBio(event.target.value)}
                rows={4}
                className="mt-2 w-full border border-border bg-background p-3 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/40"
                data-testid="profile-bio-input"
              />
            </div>
            <button
              type="button"
              onClick={() => saveProfile.mutate()}
              disabled={saveProfile.isPending}
              className="flex items-center gap-2 border border-primary bg-primary px-5 py-2.5 font-mono text-[11px] uppercase tracking-wider text-primary-foreground transition-colors hover:bg-primary/85 disabled:opacity-60"
              data-testid="save-profile-button"
            >
              {saveProfile.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              Save profile
            </button>
          </div>

          <div className="mt-10 border-t border-border pt-6">
            <p className="label-mono mb-5 flex items-center gap-2">
              <KeyRound className="h-3 w-3" /> Change password
            </p>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="current_password" className="label-mono">
                  Current password
                </label>
                <input
                  id="current_password"
                  type="password"
                  value={current}
                  onChange={(event) => setCurrent(event.target.value)}
                  className="mt-2 h-11 w-full border border-border bg-background px-3 font-mono text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/40"
                  data-testid="current-password-input"
                />
              </div>
              <div>
                <label htmlFor="new_password" className="label-mono">
                  New password
                </label>
                <input
                  id="new_password"
                  type="password"
                  value={next}
                  onChange={(event) => setNext(event.target.value)}
                  className="mt-2 h-11 w-full border border-border bg-background px-3 font-mono text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/40"
                  data-testid="new-password-input"
                />
              </div>
            </div>
            <button
              type="button"
              onClick={() => changePassword.mutate()}
              disabled={changePassword.isPending || !current || next.length < 8}
              className="mt-4 flex items-center gap-2 border border-border px-5 py-2.5 font-mono text-[11px] uppercase tracking-wider transition-colors hover:border-primary hover:text-primary disabled:opacity-50"
              data-testid="change-password-button"
            >
              {changePassword.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <KeyRound className="h-4 w-4" />}
              Update password
            </button>
          </div>
        </section>

        <aside className="panel h-fit p-6" data-testid="profile-summary">
          <span className="flex h-14 w-14 items-center justify-center border border-primary font-mono text-lg uppercase text-primary">
            {(user.full_name || user.email).slice(0, 2)}
          </span>
          <p className="mt-4 font-mono text-base tracking-tight">{user.full_name}</p>
          <p className="font-mono text-xs text-muted-foreground">{user.email}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <Badge className="border-primary/60 text-primary" testId="profile-role-badge">
              {user.role}
            </Badge>
            <Badge className={user.is_active ? "border-signal-ok/60 text-signal-ok" : "border-signal-critical/60 text-signal-critical"}>
              {user.is_active ? "active" : "disabled"}
            </Badge>
          </div>
          <dl className="mt-6 space-y-3 font-mono text-[11px]">
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Joined</dt>
              <dd>{formatDateTime(user.created_at)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted-foreground">Last login</dt>
              <dd>{formatDateTime(user.last_login_at)}</dd>
            </div>
          </dl>
        </aside>
      </div>
    </div>
  );
}
