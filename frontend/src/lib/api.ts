import axios, { AxiosError, AxiosRequestConfig } from "axios";

const configuredBase =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ||
  (import.meta.env.VITE_API_URL as string | undefined) ||
  (import.meta.env.REACT_APP_BACKEND_URL as string | undefined) ||
  "/api";

function normalizeApiBase(baseUrl: string): string {
  const base = baseUrl.trim().replace(/\/+$/, "");
  if (!base) return "/api/";
  return base.endsWith("/api") ? `${base}/` : `${base}/api/`;
}

export const API_BASE = normalizeApiBase(configuredBase);

const ACCESS_KEY = "ai_swe_access_token";
const REFRESH_KEY = "ai_swe_refresh_token";

export const tokenStore = {
  access: () => localStorage.getItem(ACCESS_KEY),
  refresh: () => localStorage.getItem(REFRESH_KEY),
  set(access: string, refresh?: string) {
    localStorage.setItem(ACCESS_KEY, access);
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 600000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  if (typeof config.url === "string" && config.url.startsWith("/")) {
    config.url = config.url.replace(/^\/+/, "");
  }

  const token = tokenStore.access();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshing: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh = tokenStore.refresh();
  if (!refresh) return null;
  try {
    const { data } = await axios.post(`${API_BASE}auth/refresh`, { refresh_token: refresh });
    tokenStore.set(data.access_token, data.refresh_token);
    return data.access_token as string;
  } catch {
    tokenStore.clear();
    return null;
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as AxiosRequestConfig & { _retried?: boolean };
    const status = error.response?.status;
    const requestUrl = typeof config?.url === "string" ? config.url.replace(/^\/+/, "") : "";
    const isAuthCall = requestUrl.startsWith("auth/");
    if (status === 401 && config && !config._retried && !isAuthCall) {
      config._retried = true;
      refreshing = refreshing || refreshAccessToken();
      const token = await refreshing;
      refreshing = null;
      if (token) {
        config.headers = { ...(config.headers || {}), Authorization: `Bearer ${token}` };
        return api.request(config);
      }
      tokenStore.clear();
      if (!window.location.pathname.startsWith("/login")) {
        window.location.assign("/login");
      }
    }
    return Promise.reject(error);
  }
);

export function apiError(error: unknown, fallback = "Something went wrong. Please try again."): string {
  const axiosError = error as AxiosError<any>;
  const detail = axiosError?.response?.data;
  const value = detail?.error?.message ?? detail?.detail ?? detail?.message;
  if (typeof value === "string" && value.trim()) return value;
  if (Array.isArray(value)) {
    return value
      .map((item) => (item && typeof item.msg === "string" ? item.msg : JSON.stringify(item)))
      .join(" ");
  }
  if (typeof detail === "string" && /ECONNREFUSED|proxy error|failed to fetch|network/i.test(detail)) {
    return "Cannot reach the backend API. Start the FastAPI server on http://127.0.0.1:8000 and try again.";
  }
  if (axiosError?.code === "ERR_NETWORK") {
    return "Cannot reach the backend API. Start the FastAPI server on http://127.0.0.1:8000 and try again.";
  }
  if (axiosError?.message) return axiosError.message;
  return fallback;
}
