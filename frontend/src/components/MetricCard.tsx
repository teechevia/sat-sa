import React from 'react';

interface MetricCardProps {
  label: string;
  value: string | number;
  subtext?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({ label, value, subtext }) => {
  return (
    <div className="metric-card">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      {subtext && <div className="metric-subtext">{subtext}</div>}
    </div>
  );
};
