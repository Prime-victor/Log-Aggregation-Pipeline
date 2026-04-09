import React from "react";
import { LogEntry } from "../api/logs";

const LogTable = ({ logs }: { logs: LogEntry[] }) => {
  if (!logs.length) {
    return <div className="empty">No logs returned for this query.</div>;
  }

  return (
    <div className="table-wrap">
      <table className="log-table">
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Level</th>
            <th>Service</th>
            <th>Message</th>
            <th>Latency</th>
            <th>Trace</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => (
            <tr key={log.id}>
              <td>{log.timestamp || "-"}</td>
              <td><span className={`level level-${(log.level || "").toLowerCase()}`}>{log.level || "-"}</span></td>
              <td>{log.service || "-"}</td>
              <td className="message">{log.message || log.error || "-"}</td>
              <td>{log.duration_ms ? `${Math.round(log.duration_ms)} ms` : "-"}</td>
              <td>{log.trace_id ? log.trace_id.slice(0, 8) : "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default LogTable;
