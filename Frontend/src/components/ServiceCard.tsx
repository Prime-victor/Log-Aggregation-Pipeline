import React from "react";
import StatusPill from "./StatusPill";
import { ServiceStatus } from "../api/health";

const ServiceCard = ({ service }: { service: ServiceStatus }) => {
  return (
    <div className="card service-card">
      <div className="service-header">
        <div>
          <h3>{service.name}</h3>
          <p className="muted">{service.url}</p>
        </div>
        <StatusPill status={service.status} />
      </div>
      <div className="service-body">
        <div className="metric">
          <span className="metric-label">Latency</span>
          <span className="metric-value">
            {service.latencyMs !== undefined ? `${service.latencyMs} ms` : "-"}
          </span>
        </div>
        <div className="metric">
          <span className="metric-label">Details</span>
          <span className="metric-value small">{service.details || "No response body"}</span>
        </div>
      </div>
    </div>
  );
};

export default ServiceCard;
