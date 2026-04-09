import { API_BASE } from "./config";
import { requestJson } from "./client";

export type Rule = {
  id?: string;
  name?: string;
  description?: string;
  service?: string;
  condition?: string;
  operator?: string;
  threshold?: number;
  window_sec?: number;
  severity?: string;
  is_active?: boolean;
  created_at?: string;
  created_by_email?: string;
  metric?: string;
};

export const listRules = () => {
  return requestJson<Rule[]>(`${API_BASE}/rules/`);
};
