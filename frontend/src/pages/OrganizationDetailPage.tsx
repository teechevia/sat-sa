import React, { useEffect, useState } from 'react';
import { useLocation, useRoute } from 'wouter';
import { getOrganization, getFindings } from '../api/client';
import type { Finding, OrganizationDetail } from '../types';
import { MetricCard } from '../components/MetricCard';
import { PeerComparison } from '../components/PeerComparison';
import { PriorityBadge } from '../components/PriorityBadge';
import { FindingTypeBadge } from '../components/FindingTypeBadge';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { ArrowLeft, AlertCircle } from 'lucide-react';

export const OrganizationDetailPage: React.FC = () => {
  const [, params] = useRoute('/organizations/:id');
  const [, setLocation] = useLocation();
  const orgId = params?.id || '';

  const [org, setOrg] = useState<OrganizationDetail | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = () => {
    if (!orgId) return;
    setLoading(true);
    setError(null);

    Promise.all([getOrganization(orgId), getFindings({ organization_id: orgId })])
      .then(([orgRes, findingsRes]) => {
        setOrg(orgRes);
        setFindings(findingsRes.findings);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadData();
  }, [orgId]);

  if (loading) return <LoadingState message={`Loading assessment data for ${orgId}...`} />;
  if (error || !org) return <ErrorState message={error || `Organization '${orgId}' not found.`} onRetry={loadData} />;

  const m = org.metrics || {};

  return (
    <div>
      <button
        onClick={() => setLocation('/organizations')}
        className="btn"
        style={{
          backgroundColor: 'var(--bg-subtle)',
          color: 'var(--text-muted)',
          border: '1px solid var(--border-color)',
          marginBottom: '1rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.4rem',
        }}
      >
        <ArrowLeft size={14} /> Back to Organizations
      </button>

      {/* Identity Banner */}
      <div className="card" style={{ borderLeft: '4px solid var(--accent-cyan)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              {org.organization_id}
            </div>
            <h1 style={{ fontSize: '1.6rem', fontWeight: 700 }}>{org.name}</h1>
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
              <span className="rule-tag" style={{ textTransform: 'capitalize' }}>Size: {org.size}</span>
              <span className="rule-tag" style={{ textTransform: 'capitalize' }}>Peer Group: {org.peer_group}</span>
              <span className="rule-tag">Assets: {org.active_asset_count}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Key Metrics Grid */}
      <div className="metrics-grid">
        <MetricCard label="Total Alerts" value={m.total_alerts?.toLocaleString() || '0'} />
        <MetricCard label="Critical Alerts" value={m.critical_alerts?.toLocaleString() || '0'} />
        <MetricCard
          label="Investigation Rate"
          value={m.investigation_rate !== undefined ? `${(m.investigation_rate * 100).toFixed(1)}%` : '0%'}
          subtext={`Critical: ${m.critical_investigation_rate !== undefined ? (m.critical_investigation_rate * 100).toFixed(1) : '0'}%`}
        />
        <MetricCard
          label="Escalation Rate"
          value={m.escalation_rate !== undefined ? `${(m.escalation_rate * 100).toFixed(1)}%` : '0%'}
        />
        <MetricCard
          label="Alerts / Active Asset"
          value={m.alerts_per_active_asset !== undefined ? m.alerts_per_active_asset.toFixed(2) : '0'}
        />
        <MetricCard
          label="Critical / Active Asset"
          value={m.critical_alerts_per_active_asset !== undefined ? m.critical_alerts_per_active_asset.toFixed(2) : '0'}
        />
        <MetricCard label="Total Cases" value={m.total_cases?.toLocaleString() || '0'} />
      </div>

      {/* Peer Comparison Section */}
      <PeerComparison
        metrics={org.metrics}
        peerBaseline={org.peer_baseline}
        peerDeviations={org.peer_deviations}
      />

      {/* Associated Findings Section */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <AlertCircle size={18} style={{ color: 'var(--accent-cyan)' }} />
            Supervisory Findings for {org.name} ({findings.length})
          </h3>
        </div>
        {findings.length === 0 ? (
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', padding: '1rem 0' }}>
            No supervisory findings detected for this organization. Operational metrics are within baseline parameters.
          </p>
        ) : (
          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Priority</th>
                  <th>Finding ID</th>
                  <th>Rule ID</th>
                  <th>Finding Title</th>
                  <th>Score</th>
                  <th>Affected Records</th>
                </tr>
              </thead>
              <tbody>
                {findings.map((f) => (
                  <tr key={f.finding_id} onClick={() => setLocation(`/findings/${f.finding_id}`)}>
                    <td><PriorityBadge priority={f.priority} /></td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{f.finding_id}</td>
                    <td><FindingTypeBadge type={f.finding_type} ruleId={f.rule_id} /></td>
                    <td style={{ fontWeight: 600 }}>{f.title}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{f.priority_score}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{f.affected_record_ids.length} records</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
