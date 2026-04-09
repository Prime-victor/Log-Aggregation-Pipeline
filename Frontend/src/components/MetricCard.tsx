import React from "react";

type MetricCardProps = {
  label: string;
  value: string | number;
  hint?: string;
};

const MetricCard = ({ label, value, hint }: MetricCardProps) => {
  return (
    <div className="card metric-card">
      <p className="muted">{label}</p>
      <h3>{value}</h3>
      {hint ? <p className="muted small">{hint}</p> : null}
    </div>
  );
};

export default MetricCard;
