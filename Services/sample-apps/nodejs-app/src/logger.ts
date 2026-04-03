import winston from "winston";

// ─── Custom JSON format for structured logging ────────────────────────────────
// This format ensures logs are parseable by Logstash.
const structuredFormat = winston.format.combine(
  winston.format.timestamp({ format: "ISO" }),
  winston.format.errors({ stack: true }),  // Include stack traces
  winston.format.printf(({ timestamp, level, message, service, ...meta }: { timestamp: string; level: string; message: string; service?: string; [key: string]: any }) => {
    return JSON.stringify({
      timestamp,
      level,
      message,
      service: service || process.env.SERVICE_NAME || "nodejs-app",
      environment: process.env.NODE_ENV || "development",
      ...meta,
    });
  })
);

export const logger = winston.createLogger({
  level: process.env.LOG_LEVEL || "info",
  format: structuredFormat,
  transports: [
    // Console (picked up by Docker / Filebeat)
    new winston.transports.Console(),
    // File (Filebeat reads this)
    new winston.transports.File({
      filename: "/var/log/apps/nodejs/app.log",
      maxsize: 10 * 1024 * 1024,  // 10MB rotation
      maxFiles: 5,
    }),
  ],
});

// ─── Request logging middleware ───────────────────────────────────────────────
export function requestLogger(req: any, res: any, next: any) {
  const start = Date.now();
  const traceId = req.headers["x-trace-id"] || crypto.randomUUID();

  res.on("finish", () => {
    logger.info("HTTP request completed", {
      trace_id: traceId,
      method: req.method,
      path: req.path,
      status_code: res.statusCode,
      duration_ms: Date.now() - start,
      user_agent: req.headers["user-agent"],
      client_ip: req.ip,
    });
  });

  next();
}