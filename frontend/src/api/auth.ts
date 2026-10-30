import type { LoginResponse, RegisterInput, User } from "../types";
import { api } from "./client";

export const login = async (username: string, password: string) =>
  (await api.post<LoginResponse>("/auth/login/", { username, password })).data;

export const register = async (input: RegisterInput) => (await api.post<User>("/auth/register/", input)).data;

export const logout = async () => {
  await api.post("/auth/logout/");
};

export const getMe = async () => (await api.get<User>("/auth/me/")).data;

export const updateMe = async (changes: Partial<Pick<User, "first_name" | "last_name" | "email">>) =>
  (await api.patch<User>("/auth/me/", changes)).data;

export const changePassword = async (old_password: string, new_password: string) => {
  await api.post("/auth/change-password/", { old_password, new_password });
};
