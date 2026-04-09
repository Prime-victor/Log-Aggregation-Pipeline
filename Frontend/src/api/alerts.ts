import { API_BASE } from "./config";
import { requestJson } from "./client";

export type Alert = {
  id?: string;
  rule_name?: string;
  status?: string;
  severity?: string;
  service?: string;
  message?: string;
  created_at?: string;
  title?: string;
};

export const listAlerts = () => {
  return requestJson<Alert[]>(`${API_BASE}/alerts/`);
};
