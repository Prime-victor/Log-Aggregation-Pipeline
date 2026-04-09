import React from "react";

const StatusPill = ({ status }: { status: "healthy" | "unhealthy" | "down" }) => {
  return <span className={`status-pill status-${status}`}>{status}</span>;
};

export default StatusPill;
