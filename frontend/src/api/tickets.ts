import type {
  NewTicket, Paginated, Ticket, TicketComment, TicketListParams, TicketStatus,
} from "../types";
import { api } from "./client";

export const listTickets = async (params: TicketListParams) => {
  // Drop empty values so we don't send ?status=&search= (the backend would reject status="").
  const query = Object.fromEntries(Object.entries(params).filter(([, v]) => v !== "" && v !== undefined && v !== false));
  return (await api.get<Paginated<Ticket>>("/tickets/", { params: query })).data;
};

export const getTicket = async (id: number) => (await api.get<Ticket>(`/tickets/${id}/`)).data;

export const createTicket = async (input: NewTicket) => (await api.post<Ticket>("/tickets/", input)).data;

export const updateTicket = async (id: number, changes: Partial<NewTicket>) =>
  (await api.patch<Ticket>(`/tickets/${id}/`, changes)).data;

export const deleteTicket = async (id: number) => {
  await api.delete(`/tickets/${id}/`);
};

export const assignTicket = async (id: number, assignedTo: number | null) =>
  (await api.post<Ticket>(`/tickets/${id}/assign/`, { assigned_to: assignedTo })).data;

export const setTicketStatus = async (id: number, status: TicketStatus) =>
  (await api.post<Ticket>(`/tickets/${id}/status/`, { status })).data;

export const listComments = async (id: number) => (await api.get<TicketComment[]>(`/tickets/${id}/comments/`)).data;

export const addComment = async (id: number, body: string, isInternal: boolean) =>
  (await api.post<TicketComment>(`/tickets/${id}/comments/`, { body, is_internal: isInternal })).data;
