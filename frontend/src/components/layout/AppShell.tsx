import { useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  BarChart3,
  BookOpen,
  FileText,
  FolderGit2,
  History,
  LayoutDashboard,
  LogOut,
  Menu,
  Moon,
  Search,
  Settings,
  Sun,
  Terminal,
  Upload,
  User as UserIcon,
  X,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, testId: "nav-dashboard" },
  { to: "/repositories", label: "Repositories", icon: FolderGit2, testId: "nav-repositories" },
  { to: "/upload", label: "Add Repository", icon: Upload, testId: "nav-upload" },
  { to: "/reviews", label: "Review History", icon: History, testId: "nav-reviews" },
  { to: "/reports", label: "Reports", icon: FileText, testId: "nav-reports" },
  { to: "/settings", label: "Settings", icon: Settings, testId: "nav-settings" },
  { to: "/profile", label: "Profile", icon: UserIcon, testId: "nav-profile" },
];

export default function AppShell() {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  const handleSearch = (event: React.FormEvent) => {
    event.preventDefault();
    navigate(`/repositories?q=${encodeURIComponent(query.trim())}`);
    setOpen(false);
  };

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="relative min-h-screen">
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-[248px] flex-col border-r border-border bg-card/95 backdrop-blur-xl transition-transform duration-200 lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full"
        )}
        data-testid="app-sidebar"
      >
        <Link
          to="/"
          className="flex items-center gap-3 border-b border-border px-6 py-5"
          data-testid="sidebar-logo"
        >
          <span className="flex h-8 w-8 items-center justify-center border border-primary text-primary">
            <Terminal className="h-4 w-4" />
          </span>
          <span className="font-mono text-sm font-bold uppercase leading-tight tracking-tight">
            AI SWE
            <span className="block text-[10px] font-normal tracking-[0.25em] text-muted-foreground">
              ASSISTANT
            </span>
          </span>
        </Link>

        <nav className="flex-1 overflow-y-auto py-4">
          {NAV.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                onClick={() => setOpen(false)}
                data-testid={item.testId}
                className={({ isActive }) =>
                  cn(
                    "group flex items-center gap-3 border-l-2 px-6 py-3 font-mono text-xs uppercase tracking-wider transition-colors",
                    isActive
                      ? "border-l-primary bg-primary/10 text-primary"
                      : "border-l-transparent text-muted-foreground hover:border-l-border hover:bg-muted/50 hover:text-foreground"
                  )
                }
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </NavLink>
            );
          })}
        </nav>

        <div className="border-t border-border p-4">
          <div className="mb-3 flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center border border-border bg-muted font-mono text-xs uppercase">
              {(user?.full_name || user?.email || "?").slice(0, 2)}
            </span>
            <div className="min-w-0">
              <p className="truncate font-mono text-xs">{user?.full_name || user?.email}</p>
              <p className="label-mono">{user?.role}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="flex w-full items-center justify-center gap-2 border border-border py-2 font-mono text-[11px] uppercase tracking-wider transition-colors hover:border-signal-critical hover:text-signal-critical"
            data-testid="logout-button"
          >
            <LogOut className="h-3.5 w-3.5" />
            Sign out
          </button>
        </div>
      </aside>

      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setOpen(false)}
          data-testid="sidebar-overlay"
        />
      )}

      <div className="lg:pl-[248px]">
        <header
          className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-border bg-background/90 px-4 backdrop-blur-xl sm:px-6"
          data-testid="app-header"
        >
          <button
            type="button"
            className="border border-border p-2 lg:hidden"
            onClick={() => setOpen((prev) => !prev)}
            data-testid="sidebar-toggle"
            aria-label="Toggle navigation"
          >
            {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>

          <form onSubmit={handleSearch} className="relative flex-1 max-w-md" data-testid="global-search-form">
            <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search repositories…"
              aria-label="Search repositories"
              className="h-9 w-full border border-border bg-card pl-9 pr-3 font-mono text-xs outline-none transition-colors placeholder:text-muted-foreground focus:border-primary focus:ring-2 focus:ring-primary/40"
              data-testid="global-search-input"
            />
          </form>

          <div className="ml-auto flex items-center gap-2">
            <Link
              to="/upload"
              className="hidden items-center gap-2 border border-primary bg-primary px-4 py-2 font-mono text-[11px] uppercase tracking-wider text-primary-foreground transition-colors hover:bg-primary/85 sm:flex"
              data-testid="header-add-repo-button"
            >
              <Upload className="h-3.5 w-3.5" />
              New analysis
            </Link>
            <button
              type="button"
              onClick={toggle}
              className="border border-border p-2 transition-colors hover:border-primary hover:text-primary"
              data-testid="theme-toggle-button"
              aria-label="Toggle colour theme"
            >
              {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
          </div>
        </header>

        <motion.main
          key={location.pathname}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className="mx-auto w-full max-w-[1600px] px-4 py-8 sm:px-6 lg:px-10"
          data-testid="app-main"
        >
          <Outlet />
        </motion.main>

        <footer className="border-t border-border px-6 py-6">
          <p className="label-mono flex flex-wrap items-center gap-2">
            <BarChart3 className="h-3 w-3" /> AI Software Engineering Assistant
            <span className="text-border">/</span>
            <BookOpen className="h-3 w-3" /> FastAPI · MySQL · Redis · ChromaDB · Gemini
          </p>
        </footer>
      </div>
    </div>
  );
}
