import { useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { describeError } from "../api/errors";
import { addComment, assignTicket, deleteTicket, getTicket, listComments, setTicketStatus } from "../api/tickets";
import { listUsers } from "../api/users";
import { ErrorBanner, Loading, PriorityBadge, StatusBadge, formatDate, fullName, statusLabel } from "../components/ui";
import { useAuth } from "../hooks/useAuth";
import { useFetch } from "../hooks/useFetch";
import { STATUSES, type Ticket, type TicketStatus } from "../types";

export default function TicketDetailPage() {
  const { id } = useParams();
  const ticketId = Number(id);
  const navigate = useNavigate();
  const { user } = useAuth();
  const isStaff = user?.role === "agent" || user?.role === "admin";

  const ticketQuery = useFetch(() => getTicket(ticketId), [ticketId]);
  const commentsQuery = useFetch(() => listComments(ticketId), [ticketId]);
  const agentsQuery = useFetch(
    async () => (isStaff ? (await listUsers({ role: "agent", page_size: 100 })).results : []),
    [isStaff],
  );

  const [actionError, setActionError] = useState<string | null>(null);
  const [body, setBody] = useState("");
  const [internal, setInternal] = useState(false);
  const [busy, setBusy] = useState(false);

  // Runs a mutation, shows any API error, and refreshes what changed.
  async function run(action: () => Promise<unknown>, after?: () => void) {
    setActionError(null);
    setBusy(true);
    try {
      await action();
      after?.();
    } catch (err) {
      setActionError(describeError(err).message);
    } finally {
      setBusy(false);
    }
  }

  const applyTicket = (updated: Ticket) => {
    ticketQuery.setData(updated);
    commentsQuery.reload(); // status/assignment changes add a system comment
  };

  function onComment(e: FormEvent) {
    e.preventDefault();
    run(
      () => addComment(ticketId, body, internal),
      () => {
        setBody("");
        setInternal(false);
        commentsQuery.reload();
      },
    );
  }

  if (!Number.isInteger(ticketId)) return <ErrorBanner message="Invalid ticket id in the URL." />;
  if (ticketQuery.loading) return <Loading />;
  if (ticketQuery.error || !ticketQuery.data) return <ErrorBanner message={ticketQuery.error ?? "Ticket not found."} />;
  const ticket = ticketQuery.data;

  return (
    <section className="detail">
      <div className="row between">
        <h1>
          #{ticket.id} {ticket.title}
        </h1>
        <div className="row">
          <StatusBadge status={ticket.status} />
          <PriorityBadge priority={ticket.priority} />
        </div>
      </div>
      <ErrorBanner message={actionError} />

      <p className="description">{ticket.description}</p>
      <dl className="meta">
        <dt>Requester</dt>
        <dd>{fullName(ticket.created_by)}</dd>
        <dt>Assignee</dt>
        <dd>{ticket.assigned_to ? fullName(ticket.assigned_to) : "Unassigned"}</dd>
        <dt>Created</dt>
        <dd>{formatDate(ticket.created_at)}</dd>
        <dt>Last updated</dt>
        <dd>
          {formatDate(ticket.updated_at)}
          {ticket.updated_by && ` by ${fullName(ticket.updated_by)}`}
        </dd>
        {ticket.closed_at && (
          <>
            <dt>Closed</dt>
            <dd>{formatDate(ticket.closed_at)}</dd>
          </>
        )}
      </dl>

      {isStaff && (
        <div className="panel row wrap">
          <label className="field inline">
            <span>Assign to</span>
            <select
              disabled={busy}
              value={ticket.assigned_to?.id ?? ""}
              onChange={(e) => run(() => assignTicket(ticketId, e.target.value ? Number(e.target.value) : null).then(applyTicket))}
            >
              <option value="">Unassigned</option>
              {(agentsQuery.data ?? []).map((a) => (
                <option key={a.id} value={a.id}>
                  {fullName(a)}
                </option>
              ))}
            </select>
          </label>
          <label className="field inline">
            <span>Move to</span>
            <select
              disabled={busy}
              value=""
              onChange={(e) => e.target.value && run(() => setTicketStatus(ticketId, e.target.value as TicketStatus).then(applyTicket))}
            >
              <option value="">Choose status…</option>
              {STATUSES.filter((s) => s !== ticket.status).map((s) => (
                <option key={s} value={s}>
                  {statusLabel[s]}
                </option>
              ))}
            </select>
          </label>
          {user?.role === "admin" && (
            <button
              className="btn danger"
              disabled={busy}
              onClick={() => window.confirm("Delete this ticket and all its comments?") && run(() => deleteTicket(ticketId), () => navigate("/tickets"))}
            >
              Delete
            </button>
          )}
        </div>
      )}

      <h2>Conversation</h2>
      <ErrorBanner message={commentsQuery.error} />
      {commentsQuery.loading && !commentsQuery.data && <Loading />}
      <ul className="comments">
        {(commentsQuery.data ?? []).map((c) => (
          <li key={c.id} className={`comment${c.is_system ? " system" : ""}${c.is_internal ? " internal" : ""}`}>
            <div className="comment-head">
              <strong>{fullName(c.author)}</strong>
              <span className="muted">{formatDate(c.created_at)}</span>
              {c.is_internal && <span className="badge priority-high">Internal note</span>}
            </div>
            <p>{c.body}</p>
          </li>
        ))}
      </ul>

      {ticket.status === "closed" ? (
        <p className="muted">This ticket is closed. {isStaff ? "Reopen it to continue the conversation." : ""}</p>
      ) : (
        <form className="panel" onSubmit={onComment}>
          <textarea rows={3} placeholder="Write a reply…" value={body} onChange={(e) => setBody(e.target.value)} required />
          <div className="row between">
            {isStaff ? (
              <label className="check">
                <input type="checkbox" checked={internal} onChange={(e) => setInternal(e.target.checked)} />
                Internal note (hidden from customer)
              </label>
            ) : (
              <span />
            )}
            <button className="btn primary" disabled={busy || !body.trim()}>
              Post reply
            </button>
          </div>
        </form>
      )}
    </section>
  );
}
