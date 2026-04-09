import { API_BASE } from "./config";
import { buildQuery, requestJson } from "./client";

export type LogEntry = {
  id: string;
  timestamp?: string;
  level?: string;
  severity?: string;
  service?: string;
  message?: string;
  error?: string;
  trace_id?: string;
  user_id?: string;
  status_code?: number;
  duration_ms?: number;
  request_path?: string;
  http_method?: string;
  environment?: string;
  raw?: Record<string, unknown>;
};

export type LogSearchResponse = {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  results: LogEntry[];
};

export type Aggregations = {
  volume_over_time: Array<{ timestamp: string; total: number; by_level: Record<string, number> }>;
  level_distribution: Record<string, number>;
  top_errors: Array<{ message: string; count: number }>;
  latency_by_service: Array<{ service: string; p50?: number; p95?: number; p99?: number }>;
};

export type LogSearchParams = {
  start_time?: string;
  end_time?: string;
  service?: string;
  level?: string;
  levels?: string;
  search?: string;
  trace_id?: string;
  user_id?: string;
  status_code?: number;
  min_duration_ms?: number;
  page?: number;
  page_size?: number;
  sort?: string;
  order?: string;
};

export const searchLogs = (params: LogSearchParams) => {
  const query = buildQuery(params);
  return requestJson<LogSearchResponse>(`${API_BASE}/logs/search/${query}`);
};

export const getAggregations = (params: LogSearchParams) => {
  const query = buildQuery(params);
  return requestJson<Aggregations>(`${API_BASE}/logs/aggregations/${query}`);
};

export const getTrace = (traceId: string) => {
  return requestJson<{ trace_id: string; count: number; logs: LogEntry[] }>(
    `${API_BASE}/logs/trace/${traceId}/`
  );
};
