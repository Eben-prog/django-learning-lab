import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import type { Role } from "../types";
import { Loading } from "./ui";

/**
 * UX guard only. It hides screens from people who can't use them, but the REAL enforcement is on the
 * backend (permissions.py). Anyone can bypass this component with curl or DevTools.
 */
export default function ProtectedRoute({ roles }: { roles?: Role[] }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <Loading label="Checking your session…" />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (roles && !roles.includes(user.role)) {
    return <div className="banner error">You do not have permission to view this page.</div>;
  }
  return <Outlet />;
}
