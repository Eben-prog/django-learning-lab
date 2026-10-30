import { useState, type ChangeEvent, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { describeError } from "../api/errors";
import { ErrorBanner, Field } from "../components/ui";
import { useAuth } from "../hooks/useAuth";

export default function RegisterPage() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: "", email: "", password: "", first_name: "", last_name: "" });
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const set = (name: keyof typeof form) => (e: ChangeEvent<HTMLInputElement>) => setForm({ ...form, [name]: e.target.value });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setFieldErrors({});
    setSubmitting(true);
    try {
      await register(form);
      navigate("/", { replace: true });
    } catch (err) {
      const described = describeError(err);
      setFieldErrors(described.fields);
      setError(described.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="auth-card" onSubmit={onSubmit}>
      <h1>Create account</h1>
      <ErrorBanner message={error} />
      <Field label="Username" error={fieldErrors.username}>
        <input value={form.username} onChange={set("username")} autoComplete="username" required />
      </Field>
      <Field label="Email" error={fieldErrors.email}>
        <input type="email" value={form.email} onChange={set("email")} autoComplete="email" required />
      </Field>
      <Field label="First name" error={fieldErrors.first_name}>
        <input value={form.first_name} onChange={set("first_name")} autoComplete="given-name" />
      </Field>
      <Field label="Last name" error={fieldErrors.last_name}>
        <input value={form.last_name} onChange={set("last_name")} autoComplete="family-name" />
      </Field>
      <Field label="Password" error={fieldErrors.password}>
        <input type="password" value={form.password} onChange={set("password")} autoComplete="new-password" required />
      </Field>
      <button className="btn primary" disabled={submitting}>
        {submitting ? "Creating…" : "Create account"}
      </button>
      <p className="muted">
        Already registered? <Link to="/login">Sign in</Link>
      </p>
    </form>
  );
}
