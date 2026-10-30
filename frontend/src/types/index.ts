// These interfaces are the FRONTEND's copy of the API contract (see docs/API.md and backend serializers.py).
// If the backend renames a field, TypeScript will not notice at runtime - keep them in sync by hand.

export type Role = "customer" | "agent" | "admin";
export type TicketStatus = "open" | "in_progress" | "resolved" | "closed";
export type TicketPriority = "low" | "medium" | "high" | "urgent";

export const STATUSES: TicketStatus[] = ["open", "in_progress", "resolved", "closed"];
export const PRIORITIES: TicketPriority[] = ["low", "medium", "high", "urgent"];

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  role: Role;
  is_active: boolean;
  date_joined: string;
}

export interface UserSummary {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  role: Role;
}

export interface Ticket {
  id: number;
  title: string;
  description: string;
  status: TicketStatus;
  priority: TicketPriority;
  created_by: UserSummary;
  assigned_to: UserSummary | null;
  updated_by: UserSummary | null;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
}

export interface TicketComment {
  id: number;
  author: UserSummary;
  body: string;
  is_internal: boolean;
  is_system: boolean;
  created_at: string;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface TicketListParams {
  page?: number;
  status?: TicketStatus | "";
  priority?: TicketPriority | "";
  search?: string;
  unassigned?: boolean;
}

export interface NewTicket {
  title: string;
  description: string;
  priority: TicketPriority;
}

export interface RegisterInput {
  username: string;
  email: string;
  password: string;
  first_name: string;
  last_name: string;
}

export interface DashboardStats {
  scope: "all" | "own";
  total: number;
  by_status: Record<TicketStatus, number>;
  by_priority: Record<TicketPriority, number>;
  created_last_7_days: number;
  unassigned: number | null;
  assigned_to_me: number | null;
}

export interface LoginResponse {
  access: string;
  user: User;
}
