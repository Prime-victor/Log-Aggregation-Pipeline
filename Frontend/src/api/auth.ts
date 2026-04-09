import { API_BASE } from "./config";
import { requestJson } from "./client";
import { getRefreshToken } from "./token";

export type AuthUser = {
  id: string;
  email: string;
  role: string;
  full_name: string;
};

export const login = async (email: string, password: string) => {
  return requestJson<{ access: string; refresh: string; user: AuthUser }>(
    `${API_BASE}/auth/login/`,
    {
      method: "POST",
      body: JSON.stringify({ email, password })
    }
  );
};

export const refresh = async () => {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    throw new Error("No refresh token available");
  }
  return requestJson<{ access: string; refresh?: string }>(
    `${API_BASE}/auth/refresh/`,
    {
      method: "POST",
      body: JSON.stringify({ refresh: refreshToken })
    }
  );
};

export const getMe = async () => {
  return requestJson<AuthUser>(`${API_BASE}/auth/me/`);
};
