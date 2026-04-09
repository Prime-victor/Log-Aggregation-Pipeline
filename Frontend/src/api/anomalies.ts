import { API_BASE, AI_BASE } from "./config";
import { requestJson } from "./client";

export type Anomaly = {
  id?: string;
  service?: string;
  anomaly_type?: string;
  status?: string;
  anomaly_score?: number;
  confidence?: number;
  description?: string;
  detected_at?: string;
  summary?: string;
  score?: number;
};

export const listAnomalies = () => {
  return requestJson<Anomaly[]>(`${API_BASE}/anomalies/`);
};

export const triggerAnomalyDetection = () => {
  return requestJson<{ status: string }>(`${AI_BASE}/detect`, { method: "POST" });
};
