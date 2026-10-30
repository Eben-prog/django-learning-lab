import type { ReactNode } from "react";
import type { TicketPriority, TicketStatus } from "../types";

export const statusLabel: Record<TicketStatus, string> = {
  open: "Open",
  in_progress: "In progress",
  resolved: "Resolved",
  closed: "Closed",
};

export const priorityLabel: Record<TicketPriority, string> = { low: "Low", medium: "Medium", high: "High", urgent: "Urgent" };

export const StatusBadge = ({ status }: { status: TicketStatus }) => (
  <span className={`badge status-${status}`}>{statusLabel[status]}</span>
);

export const PriorityBadge = ({ priority }: { priority: TicketPriority }) => (
  <span className={`badge priority-${priority}`}>{priorityLabel[priority]}</span>
);

export const ErrorBanner = ({ message }: { message: string | null }) =>
  message ? (
    <div className="banner error" role="alert">
      {message}
    </div>
  ) : null;

export const Loading = ({ label = "Loading…" }: { label?: string }) => (
  <p className="muted" aria-live="polite">
    {label}
  </p>
);

export const Field = ({ label, error, children }: { label: string; error?: string; children: ReactNode }) => (
  <label className="field">
    <span>{label}</span>
    {children}
    {error && <small className="field-error">{error}</small>}
  </label>
);

export const formatDate = (iso: string) =>
  new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });

export const fullName = (u: { first_name: string; last_name: string; username: string }) =>
  `${u.first_name} ${u.last_name}`.trim() || u.username;
