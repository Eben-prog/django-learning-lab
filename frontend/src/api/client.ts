import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import type { LoginResponse } from "../types";

// Vite inlines import.meta.env.VITE_* at build time. A wrong value here is a classic "request goes to the wrong place" bug.
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

// The access token lives only in this module's memory: not in localStorage (readable by any injected script).
// It is lost on page reload; AuthProvider then asks /auth/refresh/ (using the HttpOnly cookie) for a new one.
let accessToken: string | null = null;
export function setAccessToken(token: string | null): void {
  accessToken = token;
}

let onSessionExpired: (() => void) | null = null;
export function registerSessionExpiredHandler(handler: (() => void) | null): void {
  onSessionExpired = handler;
}

export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // lets the browser send/receive the refresh cookie across origins (needs CORS_ALLOW_CREDENTIALS)
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  if (accessToken) config.headers.set("Authorization", `Bearer ${accessToken}`);
  return config;
});

// One in-flight refresh shared by all requests that fail at the same moment.
let refreshing: Promise<string> | null = null;

export async function refreshAccessToken(): Promise<LoginResponse> {
  // Use plain axios (not `api`) so this call can't trigger the interceptor below.
  const { data } = await axios.post<LoginResponse>(`${API_BASE_URL}/auth/refresh/`, null, { withCredentials: true });
  setAccessToken(data.access);
  return data;
}

const NO_RETRY_URLS = ["/auth/login/", "/auth/register/", "/auth/refresh/", "/auth/logout/"];

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;
    const expired = error.response?.status === 401 && original && !original._retried;
    if (!expired || NO_RETRY_URLS.some((url) => original.url?.startsWith(url))) throw error;

    original._retried = true;
    try {
      refreshing ??= refreshAccessToken().then((r) => r.access);
      await refreshing;
      return api(original); // replay the original request with the new token
    } catch {
      setAccessToken(null);
      onSessionExpired?.();
      throw error;
    } finally {
      refreshing = null;
    }
  },
);
