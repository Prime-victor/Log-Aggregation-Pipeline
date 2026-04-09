const ACCESS_TOKEN_KEY = "lip_access_token";
const REFRESH_TOKEN_KEY = "lip_refresh_token";

export type AuthTokens = {
  access: string;
  refresh: string;
};

export const getAccessToken = () => localStorage.getItem(ACCESS_TOKEN_KEY) || "";
export const getRefreshToken = () => localStorage.getItem(REFRESH_TOKEN_KEY) || "";

export const setTokens = (tokens: Partial<AuthTokens>) => {
  if (tokens.access) {
    localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access);
  }
  if (tokens.refresh) {
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh);
  }
};

export const clearTokens = () => {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
};
