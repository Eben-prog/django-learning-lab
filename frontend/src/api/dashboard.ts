import type { DashboardStats } from "../types";
import { api } from "./client";

export const getDashboard = async () => (await api.get<DashboardStats>("/dashboard/")).data;
