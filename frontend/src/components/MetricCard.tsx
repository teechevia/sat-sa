import React from 'react';

interface MetricCardProps { label: string; value: string | number; subtext?: string; }

export const MetricCard: React.FC<MetricCardProps> = ({ label, value, subtext }) => (
  <section className="metric-card" aria-label={`${label}: ${value}`}>
    <div className="metric-label">{label}</div>
    <div className="metric-value">{value}</div>
    {subtext && <div className="metric-subtext">{subtext}</div>}
  </section>
);
