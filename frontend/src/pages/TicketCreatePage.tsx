import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { describeError } from "../api/errors";
import { createTicket } from "../api/tickets";
import { ErrorBanner, Field, priorityLabel } from "../components/ui";
import { PRIORITIES, type TicketPriority } from "../types";

export default function TicketCreatePage() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<TicketPriority>("medium");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    // Step 2 of the request lifecycle: cheap client-side checks for fast feedback.
    // The backend validates again (never trust the browser), so these rules are a convenience, not security.
    const local: Record<string, string> = {};
    if (title.trim().length < 5) local.title = "Title must be at least 5 characters.";
    if (description.trim().length < 10) local.description = "Please describe the problem in at least 10 characters.";
    setFieldErrors(local);
    if (Object.keys(local).length > 0) return;

    setSubmitting(true);
    try {
      const ticket = await createTicket({ title, description, priority });
      navigate(`/tickets/${ticket.id}`);
    } catch (err) {
      const described = describeError(err);
      setFieldErrors(described.fields);
      setError(described.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="panel narrow" onSubmit={onSubmit} noValidate>
      <h1>New ticket</h1>
      <ErrorBanner message={error} />
      <Field label="Title" error={fieldErrors.title}>
        <input value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} />
      </Field>
      <Field label="Description" error={fieldErrors.description}>
        <textarea rows={6} value={description} onChange={(e) => setDescription(e.target.value)} />
      </Field>
      <Field label="Priority" error={fieldErrors.priority}>
        <select value={priority} onChange={(e) => setPriority(e.target.value as TicketPriority)}>
          {PRIORITIES.map((p) => (
            <option key={p} value={p}>
              {priorityLabel[p]}
            </option>
          ))}
        </select>
      </Field>
      <button className="btn primary" disabled={submitting}>
        {submitting ? "Submitting…" : "Submit ticket"}
      </button>
    </form>
  );
}
