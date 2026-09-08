import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { AuthProvider } from "@/context/AuthContext";
import { ThemeProvider } from "@/context/ThemeContext";
import AppShell from "@/components/layout/AppShell";
import { ProtectedRoute, PublicOnlyRoute } from "@/components/layout/ProtectedRoute";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import Dashboard from "@/pages/Dashboard";
import Repositories from "@/pages/Repositories";
import RepositoryUpload from "@/pages/RepositoryUpload";
import RepositoryDetail from "@/pages/RepositoryDetail";
import ReviewPage from "@/pages/ReviewPage";
import ReviewHistory from "@/pages/ReviewHistory";
import DocumentationPage from "@/pages/DocumentationPage";
import ArchitecturePage from "@/pages/ArchitecturePage";
import ChatPage from "@/pages/ChatPage";
import Reports from "@/pages/Reports";
import SettingsPage from "@/pages/SettingsPage";
import Profile from "@/pages/Profile";
import NotFound from "@/pages/NotFound";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 20_000 },
  },
});

export default function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider>
            <Routes>
              <Route
                path="/login"
                element={
                  <PublicOnlyRoute>
                    <Login />
                  </PublicOnlyRoute>
                }
              />
              <Route
                path="/register"
                element={
                  <PublicOnlyRoute>
                    <Register />
                  </PublicOnlyRoute>
                }
              />
              <Route
                element={
                  <ProtectedRoute>
                    <AppShell />
                  </ProtectedRoute>
                }
              >
                <Route path="/" element={<Dashboard />} />
                <Route path="/repositories" element={<Repositories />} />
                <Route path="/upload" element={<RepositoryUpload />} />
                <Route path="/repositories/:repoId" element={<RepositoryDetail />} />
                <Route path="/repositories/:repoId/documentation" element={<DocumentationPage />} />
                <Route path="/repositories/:repoId/architecture" element={<ArchitecturePage />} />
                <Route path="/repositories/:repoId/chat" element={<ChatPage />} />
                <Route path="/reviews" element={<ReviewHistory />} />
                <Route path="/reviews/:reviewId" element={<ReviewPage />} />
                <Route path="/reports" element={<Reports />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="/profile" element={<Profile />} />
                <Route path="/dashboard" element={<Navigate to="/" replace />} />
                <Route path="*" element={<NotFound />} />
              </Route>
            </Routes>
            <Toaster
              position="bottom-right"
              toastOptions={{
                style: {
                  background: "hsl(var(--card))",
                  color: "hsl(var(--foreground))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: 0,
                  fontFamily: "IBM Plex Sans, sans-serif",
                },
              }}
            />
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
