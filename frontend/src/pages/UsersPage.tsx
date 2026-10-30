import { useState } from "react";
import { describeError } from "../api/errors";
import { listUsers, updateUser } from "../api/users";
import { ErrorBanner, Loading, fullName } from "../components/ui";
import { useAuth } from "../hooks/useAuth";
import { useFetch } from "../hooks/useFetch";
import type { Role } from "../types";

const ROLES: Role[] = ["customer", "agent", "admin"];

export default function UsersPage() {
  const { user: me } = useAuth();
  const [page, setPage] = useState(1);
  const [actionError, setActionError] = useState<string | null>(null);
  const { data, loading, error, reload } = useFetch(() => listUsers({ page }), [page]);

  async function change(id: number, changes: { role?: Role; is_active?: boolean }) {
    setActionError(null);
    try {
      await updateUser(id, changes);
      reload();
    } catch (err) {
      setActionError(describeError(err).message);
    }
  }

  return (
    <section>
      <h1>Users</h1>
      <p className="muted">Promote customers to support agents, or deactivate accounts. Enforced by the backend.</p>
      <ErrorBanner message={error ?? actionError} />
      {loading && !data && <Loading />}
      {data && (
        <>
          <table className="table">
            <thead>
              <tr>
                <th>User</th>
                <th>Email</th>
                <th>Role</th>
                <th>Active</th>
              </tr>
            </thead>
            <tbody>
              {data.results.map((u) => (
                <tr key={u.id}>
                  <td>
                    {fullName(u)} <span className="muted">@{u.username}</span>
                  </td>
                  <td>{u.email}</td>
                  <td>
                    <select value={u.role} disabled={u.id === me?.id} onChange={(e) => change(u.id, { role: e.target.value as Role })}>
                      {ROLES.map((r) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      checked={u.is_active}
                      disabled={u.id === me?.id}
                      onChange={(e) => change(u.id, { is_active: e.target.checked })}
                      aria-label={`Active: ${u.username}`}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="pagination">
            <button className="btn" disabled={!data.previous} onClick={() => setPage(page - 1)}>
              Previous
            </button>
            <span className="muted">
              Page {page} ({data.count} users)
            </span>
            <button className="btn" disabled={!data.next} onClick={() => setPage(page + 1)}>
              Next
            </button>
          </div>
        </>
      )}
    </section>
  );
}
