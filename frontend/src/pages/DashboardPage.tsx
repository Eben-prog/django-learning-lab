import { Link } from "react-router-dom";
import { getDashboard } from "../api/dashboard";
import { ErrorBanner, Loading, priorityLabel, statusLabel } from "../components/ui";
import { useFetch } from "../hooks/useFetch";
import { PRIORITIES, STATUSES } from "../types";

export default function DashboardPage() {
  const { data, loading, error, reload } = useFetch(getDashboard, []);

  if (loading) return <Loading />;
  if (error || !data) return <ErrorBanner message={error ?? "No data returned."} />;

  const max = Math.max(1, ...PRIORITIES.map((p) => data.by_priority[p]));
  return (
    <section>
      <div className="row between">
        <h1>{data.scope === "all" ? "All tickets" : "Your tickets"}</h1>
        <button className="btn" onClick={reload}>
          Refresh
        </button>
      </div>

      <div className="stat-grid">
        <div className="stat">
          <span className="stat-value">{data.total}</span>
          <span className="muted">Total</span>
        </div>
        {STATUSES.map((s) => (
          <Link key={s} className="stat" to={`/tickets?status=${s}`}>
            <span className="stat-value">{data.by_status[s]}</span>
            <span className="muted">{statusLabel[s]}</span>
          </Link>
        ))}
        <div className="stat">
          <span className="stat-value">{data.created_last_7_days}</span>
          <span className="muted">New in 7 days</span>
        </div>
        {data.unassigned !== null && (
          <Link className="stat" to="/tickets?unassigned=true">
            <span className="stat-value">{data.unassigned}</span>
            <span className="muted">Unassigned (not closed)</span>
          </Link>
        )}
        {data.assigned_to_me !== null && (
          <div className="stat">
            <span className="stat-value">{data.assigned_to_me}</span>
            <span className="muted">Assigned to me</span>
          </div>
        )}
      </div>

      <h2>By priority</h2>
      <ul className="bars">
        {PRIORITIES.map((p) => (
          <li key={p}>
            <span className="bar-label">{priorityLabel[p]}</span>
            <span className={`bar priority-${p}`} style={{ width: `${(data.by_priority[p] / max) * 100}%` }} />
            <span>{data.by_priority[p]}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
