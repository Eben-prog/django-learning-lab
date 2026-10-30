import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { describeError } from "../api/errors";
import { ErrorBanner, Field } from "../components/ui";
import { useAuth } from "../hooks/useAuth";

export default function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/";
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to={from} replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault(); // without this the browser reloads the page and the request never visibly happens
    setError(null);
    setSubmitting(true);
    try {
      await login(username, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(describeError(err).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="auth-card" onSubmit={onSubmit}>
      <h1>Sign in</h1>
      <ErrorBanner message={error} />
      <Field label="Username">
        <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
      </Field>
      <Field label="Password">
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
      </Field>
      <button className="btn primary" disabled={submitting}>
        {submitting ? "Signing in…" : "Sign in"}
      </button>
      <p className="muted">
        New here? <Link to="/register">Create a customer account</Link>
      </p>
    </form>
  );
}
