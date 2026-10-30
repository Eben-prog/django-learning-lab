import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import ProfilePage from "./pages/ProfilePage";
import RegisterPage from "./pages/RegisterPage";
import TicketCreatePage from "./pages/TicketCreatePage";
import TicketDetailPage from "./pages/TicketDetailPage";
import TicketListPage from "./pages/TicketListPage";
import UsersPage from "./pages/UsersPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="tickets" element={<TicketListPage />} />
          <Route path="tickets/new" element={<TicketCreatePage />} />
          <Route path="tickets/:id" element={<TicketDetailPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route element={<ProtectedRoute roles={["admin"]} />}>
            <Route path="users" element={<UsersPage />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<div className="auth-card">Page not found.</div>} />
    </Routes>
  );
}
