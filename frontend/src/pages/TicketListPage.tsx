import { useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { listTickets } from "../api/tickets";
import Pagination from "../components/Pagination";
import { ErrorBanner, Loading, PriorityBadge, StatusBadge, formatDate, fullName, priorityLabel, statusLabel } from "../components/ui";
import { useFetch } from "../hooks/useFetch";
import { PRIORITIES, STATUSES, type TicketPriority, type TicketStatus } from "../types";

const PAGE_SIZE = 10; // must match StandardPagination.page_size in backend/config/pagination.py

export default function TicketListPage() {
  // Filters live in the URL (?status=open&page=2) so the page can be bookmarked, shared and survives refresh.
  const [params, setParams] = useSearchParams();
  const page = Number(params.get("page") ?? "1") || 1;
  const status = (params.get("status") ?? "") as TicketStatus | "";
  const priority = (params.get("priority") ?? "") as TicketPriority | "";
  const search = params.get("search") ?? "";
  const unassigned = params.get("unassigned") === "true";
  const [searchText, setSearchText] = useState(search);

  const { data, loading, error } = useFetch(
    () => listTickets({ page, status, priority, search, unassigned }),
    [page, status, priority, search, unassigned],
  );

  function update(changes: Record<string, string | null>) {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    if (!("page" in changes)) next.delete("page"); // any filter change returns to page 1
    setParams(next);
  }

  function onSearch(e: FormEvent) {
    e.preventDefault();
    update({ search: searchText.trim() || null });
  }

  return (
    <section>
      <div className="row between">
        <h1>Tickets</h1>
        <Link className="btn primary" to="/tickets/new">
          New ticket
        </Link>
      </div>

      <form className="filters" onSubmit={onSearch}>
        <input placeholder="Search title or description" value={searchText} onChange={(e) => setSearchText(e.target.value)} />
        <select value={status} onChange={(e) => update({ status: e.target.value || null })} aria-label="Status filter">
          <option value="">Any status</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {statusLabel[s]}
            </option>
          ))}
        </select>
        <select value={priority} onChange={(e) => update({ priority: e.target.value || null })} aria-label="Priority filter">
          <option value="">Any priority</option>
          {PRIORITIES.map((p) => (
            <option key={p} value={p}>
              {priorityLabel[p]}
            </option>
          ))}
        </select>
        <label className="check">
          <input type="checkbox" checked={unassigned} onChange={(e) => update({ unassigned: e.target.checked ? "true" : null })} />
          Unassigned
        </label>
        <button className="btn">Search</button>
      </form>

      <ErrorBanner message={error} />
      {loading && <Loading />}
      {!loading && data && data.results.length === 0 && <p className="muted">No tickets match these filters.</p>}
      {data && data.results.length > 0 && (
        <>
          <table className="table">
            <thead>
              <tr>
                <th>#</th>
                <th>Title</th>
                <th>Status</th>
                <th>Priority</th>
                <th>Requester</th>
                <th>Assignee</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {data.results.map((t) => (
                <tr key={t.id}>
                  <td>{t.id}</td>
                  <td>
                    <Link to={`/tickets/${t.id}`}>{t.title}</Link>
                  </td>
                  <td>
                    <StatusBadge status={t.status} />
                  </td>
                  <td>
                    <PriorityBadge priority={t.priority} />
                  </td>
                  <td>{fullName(t.created_by)}</td>
                  <td>{t.assigned_to ? fullName(t.assigned_to) : <span className="muted">Unassigned</span>}</td>
                  <td>{formatDate(t.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination page={page} count={data.count} pageSize={PAGE_SIZE} onChange={(p) => update({ page: String(p) })} />
        </>
      )}
    </section>
  );
}
