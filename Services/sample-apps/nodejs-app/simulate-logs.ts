import { logger } from "./logger";

// ─── Log simulator: generates realistic traffic patterns ──────────────────────
const SERVICES = ["auth-service", "payment-service", "user-service", "api-gateway"];
const PATHS    = ["/api/users", "/api/orders", "/api/auth/login", "/api/products"];
const METHODS  = ["GET", "POST", "PUT", "DELETE"];
const ERRORS   = [
  "Database connection timeout",
  "Redis ECONNREFUSED",
  "Invalid JWT token",
  "Rate limit exceeded",
  "Null reference exception",
];

function randomInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function randomElement<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

async function simulateLogs() {
  console.log("Starting log simulation...");

  while (true) {
    const service = randomElement(SERVICES);
    const path    = randomElement(PATHS);
    const method  = randomElement(METHODS);
    const roll    = Math.random();

    if (roll < 0.70) {
      // 70% of traffic: normal successful requests
      logger.info("Request processed", {
        service,
        trace_id: crypto.randomUUID(),
        path,
        method,
        status_code: 200,
        duration_ms: randomInt(10, 200),
        user_id: `user_${randomInt(1, 1000)}`,
      });
    } else if (roll < 0.90) {
      // 20%: warnings (slow requests, retries)
      logger.warn("Slow request detected", {
        service,
        trace_id: crypto.randomUUID(),
        path,
        method,
        status_code: 200,
        duration_ms: randomInt(500, 3000),
        user_id: `user_${randomInt(1, 1000)}`,
      });
    } else {
      // 10%: errors — this is what alerts will trigger on
      logger.error("Request failed", {
        service,
        trace_id: crypto.randomUUID(),
        path,
        method,
        status_code: randomElement([500, 502, 503, 404, 401]),
        duration_ms: randomInt(100, 5000),
        error_message: randomElement(ERRORS),
        user_id: `user_${randomInt(1, 1000)}`,
      });
    }

    // Random delay: 100ms–2s between log entries
    await new Promise(r => setTimeout(r, randomInt(100, 2000)));
  }
}

simulateLogs().catch(console.error);