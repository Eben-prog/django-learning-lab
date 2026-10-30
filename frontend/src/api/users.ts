import type { Paginated, Role, User } from "../types";
import { api } from "./client";

export const listUsers = async (params: { role?: Role; search?: string; page?: number; page_size?: number } = {}) =>
  (await api.get<Paginated<User>>("/users/", { params })).data;

export const updateUser = async (id: number, changes: { role?: Role; is_active?: boolean }) =>
  (await api.patch<User>(`/users/${id}/`, changes)).data;
