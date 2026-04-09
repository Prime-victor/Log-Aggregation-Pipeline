import { API_BASE } from "./config";
import { requestJson } from "./client";

export type User = {
  id?: string;
  email?: string;
  role?: string;
  is_active?: boolean;
};

export const listUsers = () => {
  return requestJson<User[]>(`${API_BASE}/users/`);
};
