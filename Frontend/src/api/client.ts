import { API_BASE } from "./config";
import { getAccessToken, getRefreshToken, setTokens, clearTokens } from "./token";

export type ApiError = {
  status: number;
  message: string;
  details?: unknown;
};

const DEFAULT_TIMEOUT_MS = 12000;

const buildHeaders = (headers?: HeadersInit) => {
  const token = getAccessToken();
  const base: HeadersInit = {
    "Content-Type": "application/json"
  };
  if (token) {
    base.Authorization = `Bearer ${token}`;
  }
  return { ...base, ...headers };
};

const parseJson = (text: string) => {
  if (!text) {
    return null;
  }
  return JSON.parse(text);
};

const refreshAccessToken = async () => {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    throw new Error("No refresh token available");
  }

  const response = await fetch(`${API_BASE}/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh: refreshToken })
  });

  const text = await response.text();
  const data = text ? parseJson(text) : null;

  if (!response.ok) {
    clearTokens();
    throw {
      status: response.status,
      message: data?.detail || response.statusText || "Refresh failed",
      details: data
    } as ApiError;
  }

  setTokens({ access: data.access, refresh: data.refresh });
};

export const buildQuery = (params: Record<string, string | number | boolean | undefined>) => {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === "") {
      return;
    }
    query.set(key, String(value));
  });
  const str = query.toString();
  return str ? `?${str}` : "";
};

export async function requestJson<T>(
  url: string,
  options: RequestInit = {},
  timeoutMs = DEFAULT_TIMEOUT_MS
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      headers: buildHeaders(options.headers),
      signal: controller.signal
    });

    if (response.status === 401 && getRefreshToken()) {
      await refreshAccessToken();
      const retry = await fetch(url, {
        ...options,
        headers: buildHeaders(options.headers),
        signal: controller.signal
      });
      const retryText = await retry.text();
      const retryData = retryText ? parseJson(retryText) : null;

      if (!retry.ok) {
        throw {
          status: retry.status,
          message: retryData?.error?.message || retry.statusText || "Request failed",
          details: retryData
        } as ApiError;
      }
      return retryData as T;
    }

    const text = await response.text();
    const data = text ? parseJson(text) : null;

    if (!response.ok) {
      const error: ApiError = {
        status: response.status,
        message: data?.error?.message || response.statusText || "Request failed",
        details: data
      };
      throw error;
    }

    return data as T;
  } catch (error) {
    if (error instanceof SyntaxError) {
      throw {
        status: 500,
        message: "Invalid JSON response",
        details: error
      } as ApiError;
    }
    throw error as ApiError;
  } finally {
    clearTimeout(timeout);
  }
}

export async function requestText(
  url: string,
  options: RequestInit = {},
  timeoutMs = DEFAULT_TIMEOUT_MS
): Promise<{ ok: boolean; status: number; body: string }>
{
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    const body = await response.text();
    return { ok: response.ok, status: response.status, body };
  } finally {
    clearTimeout(timeout);
  }
}
