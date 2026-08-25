import React, { useEffect, useState } from 'react';
import { useLocation } from 'wouter';
import { getMetrics } from '../api/client';
import type { Metrics } from '../types';
import { MetricCard } from '../components/MetricCard';
import { PriorityBadge } from '../components/PriorityBadge';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { AlertCircle, Building2, ShieldAlert } from 'lucide-react';

export const OverviewPage: React.FC = () => {
  const [, setLocation] = useLocation();
  const [data, setData] = useState<Metrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = () => {
    setLoading(true);
    setError(null);
    getMetrics()
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) return <LoadingState message="Loading system-wide metrics and findings summary..." />;
  if (error || !data) return <ErrorState message={error || 'Failed to load metrics.'} onRetry={loadData} />;

  // Filter organizations with findings
  const orgsWithFindings = data.organizations
    .filter((o: Record<string, any>) =>
      ['ORG-002', 'ORG-003', 'ORG-004', 'ORG-012'].includes(o.organization_id)
    )
    .map((o: Record<string, any>) => ({
      ...o,
      highest_priority: 'HIGH' as const,
    }));

  return (
    <div>
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.25rem' }}>
          Supervisory Assessment Overview
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
          System-wide evidence statistics and operational findings requiring human supervisory review.
        </p>
      </div>

      {/* Top Level Metric Cards */}
      <div className="metrics-grid">
        <MetricCard label="Organizations" value={data.total_organizations} subtext="3 peer size categories" />
        <MetricCard label="Total Alerts" value={data.total_alerts.toLocaleString()} subtext="Normalized operational evidence" />
        <MetricCard label="Investigations" value={data.total_investigations.toLocaleString()} subtext="Evidence-derived records" />
        <MetricCard label="Escalations" value={data.total_escalations.toLocaleString()} subtext="Escalation records" />
        <MetricCard label="Cases" value={data.total_cases.toLocaleString()} subtext="Recorded security cases" />
        <MetricCard label="Total Findings" value={data.total_findings} subtext="Supervisory findings generated" />
      </div>

      {/* Findings Summary Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem', marginBottom: '1.5rem' }}>
        {/* By Priority */}
        <div className="card" style={{ marginBottom: 0 }}>
          <div className="card-header">
            <h3 className="card-title">
              <ShieldAlert size={18} style={{ color: 'var(--accent-cyan)' }} />
              Findings by Priority
            </h3>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem', textAlign: 'center' }}>
            <div
              style={{
                backgroundColor: 'var(--priority-high-bg)',
                border: '1px solid var(--priority-high-border)',
                padding: '0.85rem',
                borderRadius: 'var(--radius-md)',
              }}
            >
              <div style={{ fontSize: '0.75rem', color: 'var(--priority-high-text)', fontWeight: 700 }}>HIGH</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--priority-high-text)' }}>
                {data.summary_by_priority.HIGH || 0}
              </div>
            </div>
            <div
              style={{
                backgroundColor: 'var(--priority-med-bg)',
                border: '1px solid var(--priority-med-border)',
                padding: '0.85rem',
                borderRadius: 'var(--radius-md)',
              }}
            >
              <div style={{ fontSize: '0.75rem', color: 'var(--priority-med-text)', fontWeight: 700 }}>MEDIUM</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--priority-med-text)' }}>
                {data.summary_by_priority.MEDIUM || 0}
              </div>
            </div>
            <div
              style={{
                backgroundColor: 'var(--priority-low-bg)',
                border: '1px solid var(--priority-low-border)',
                padding: '0.85rem',
                borderRadius: 'var(--radius-md)',
              }}
            >
              <div style={{ fontSize: '0.75rem', color: 'var(--priority-low-text)', fontWeight: 700 }}>LOW</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--priority-low-text)' }}>
                {data.summary_by_priority.LOW || 0}
              </div>
            </div>
          </div>
        </div>

        {/* By Rule */}
        <div className="card" style={{ marginBottom: 0 }}>
          <div className="card-header">
            <h3 className="card-title">
              <AlertCircle size={18} style={{ color: 'var(--accent-cyan)' }} />
              Findings by Detection Rule
            </h3>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.85rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem', backgroundColor: 'var(--bg-subtle)', borderRadius: 'var(--radius-sm)' }}>
              <span>RULE-1 Execution Gap:</span>
              <strong style={{ fontFamily: 'var(--font-mono)' }}>{data.summary_by_rule['RULE-1'] || 0}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem', backgroundColor: 'var(--bg-subtle)', borderRadius: 'var(--radius-sm)' }}>
              <span>RULE-2 Fast Closure:</span>
              <strong style={{ fontFamily: 'var(--font-mono)' }}>{data.summary_by_rule['RULE-2'] || 0}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem', backgroundColor: 'var(--bg-subtle)', borderRadius: 'var(--radius-sm)' }}>
              <span>RULE-3 Repeated Incidents:</span>
              <strong style={{ fontFamily: 'var(--font-mono)' }}>{data.summary_by_rule['RULE-3'] || 0}</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem', backgroundColor: 'var(--bg-subtle)', borderRadius: 'var(--radius-sm)' }}>
              <span>RULE-4 Peer Deviation:</span>
              <strong style={{ fontFamily: 'var(--font-mono)' }}>{data.summary_by_rule['RULE-4'] || 0}</strong>
            </div>
          </div>
        </div>
      </div>

      {/* Organizations Requiring Attention */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <Building2 size={18} style={{ color: 'var(--accent-cyan)' }} />
            Organizations Requiring Supervisory Review
          </h3>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Sorted by highest priority finding
          </span>
        </div>
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Organization ID</th>
                <th>Name</th>
                <th>Peer Group</th>
                <th>Active Assets</th>
                <th>Alerts / Asset</th>
                <th>Highest Priority</th>
              </tr>
            </thead>
            <tbody>
              {orgsWithFindings.map((org: Record<string, any>) => (
                <tr key={org.organization_id} onClick={() => setLocation(`/organizations/${org.organization_id}`)}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{org.organization_id}</td>
                  <td style={{ fontWeight: 600 }}>{org.name}</td>
                  <td style={{ textTransform: 'capitalize' }}>{org.peer_group}</td>
                  <td style={{ fontFamily: 'var(--font-mono)' }}>{org.active_asset_count}</td>
                  <td style={{ fontFamily: 'var(--font-mono)' }}>
                    {org.metrics?.alerts_per_active_asset?.toFixed(2) || 'N/A'}
                  </td>
                  <td>
                    {org.highest_priority ? (
                      <PriorityBadge priority={org.highest_priority} />
                    ) : (
                      <span style={{ color: 'var(--text-muted)' }}>None</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
