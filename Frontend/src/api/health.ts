import { requestText } from "./client";

export type ServiceStatus = {
  name: string;
  url: string;
  status: "healthy" | "unhealthy" | "down";
  latencyMs?: number;
  details?: string;
};

export async function checkService(name: string, url: string): Promise<ServiceStatus> {
  const start = performance.now();
  try {
    const response = await requestText(url, { method: "GET" }, 8000);
    const latencyMs = Math.round(performance.now() - start);
    return {
      name,
      url,
      status: response.ok ? "healthy" : "unhealthy",
      latencyMs,
      details: response.body.slice(0, 120)
    };
  } catch (error) {
    return {
      name,
      url,
      status: "down",
      details: error instanceof Error ? error.message : "Request failed"
    };
  }
}
