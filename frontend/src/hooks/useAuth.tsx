import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import * as authApi from "../api/auth";
import { refreshAccessToken, registerSessionExpiredHandler, setAccessToken } from "../api/client";
import type { RegisterInput, User } from "../types";

interface AuthState {
  user: User | null;
  loading: boolean; // true while we check whether a refresh cookie gives us a session at startup
  login: (username: string, password: string) => Promise<void>;
  register: (input: RegisterInput) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (user: User) => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // On page load the in-memory token is gone; try to restore the session from the HttpOnly refresh cookie.
  useEffect(() => {
    registerSessionExpiredHandler(() => setUser(null));
    refreshAccessToken()
      .then((data) => setUser(data.user))
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
    return () => registerSessionExpiredHandler(null);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const data = await authApi.login(username, password);
    setAccessToken(data.access);
    setUser(data.user);
  }, []);

  const register = useCallback(
    async (input: RegisterInput) => {
      await authApi.register(input);
      await login(input.username, input.password);
    },
    [login],
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      setAccessToken(null);
      setUser(null);
    }
  }, []);

  const value = useMemo(() => ({ user, loading, login, register, logout, setUser }), [user, loading, login, register, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
