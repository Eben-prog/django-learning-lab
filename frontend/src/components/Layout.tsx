import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  return (
    <div className="shell">
      <header className="topbar">
        <strong className="brand">Helpdesk</strong>
        <nav>
          <NavLink to="/">Dashboard</NavLink>
          <NavLink to="/tickets">Tickets</NavLink>
          <NavLink to="/tickets/new">New ticket</NavLink>
          {user?.role === "admin" && <NavLink to="/users">Users</NavLink>}
          <NavLink to="/profile">Profile</NavLink>
        </nav>
        <div className="who">
          <span className="muted">
            {user?.username} · {user?.role}
          </span>
          <button className="btn" onClick={handleLogout}>
            Log out
          </button>
        </div>
      </header>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
