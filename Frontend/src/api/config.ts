const env = import.meta.env as ImportMetaEnv;

export const API_BASE = env.VITE_API_BASE || "http://localhost:8000/api/v1";
export const BACKEND_HEALTH = env.VITE_BACKEND_HEALTH || "http://localhost:8000/health";

export const AI_BASE = env.VITE_AI_BASE || "http://localhost:8001/api/v1";
export const AI_HEALTH = env.VITE_AI_HEALTH || "http://localhost:8001/health";

export const ELASTIC_HEALTH = env.VITE_ELASTIC_HEALTH || "http://localhost:9200";
export const KIBANA_HEALTH = env.VITE_KIBANA_HEALTH || "http://localhost:5601/api/status";
export const LOGSTASH_HEALTH = env.VITE_LOGSTASH_HEALTH || "http://localhost:9600";

export const DEFAULT_TIME_RANGE_HOURS = Number(env.VITE_DEFAULT_RANGE_HOURS || 6);
