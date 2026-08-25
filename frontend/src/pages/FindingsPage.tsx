import React, { useEffect, useState } from 'react';
import { useLocation } from 'wouter';
import { getFindings, getOrganizations } from '../api/client';
import type { Finding, Organization } from '../types';
import { PriorityBadge } from '../components/PriorityBadge';
import { FindingTypeBadge } from '../components/FindingTypeBadge';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { AlertCircle, Filter, RotateCcw } from 'lucide-react';

export const FindingsPage: React.FC = () => {
  const [, setLocation] = useLocation();

  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [total, setTotal] = useState(0);

  const [selectedOrg, setSelectedOrg] = useState<string>('');
  const [selectedType, setSelectedType] = useState<string>('');
  const [selectedPriority, setSelectedPriority] = useState<string>('');

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getOrganizations()
      .then(setOrgs)
      .catch(() => {});
  }, []);

  const loadFindings = () => {
    setLoading(true);
    setError(null);

    getFindings({
      organization_id: selectedOrg || undefined,
      finding_type: selectedType || undefined,
      priority: selectedPriority || undefined,
    })
      .then((res) => {
        setFindings(res.findings);
        setTotal(res.total);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadFindings();
  }, [selectedOrg, selectedType, selectedPriority]);

  const resetFilters = () => {
    setSelectedOrg('');
    setSelectedType('');
    setSelectedPriority('');
  };

  return (
    <div>
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.25rem' }}>
          Supervisory Findings List
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
          Browse, filter, and inspect operational weakness signals identified by SAT-SA detection rules.
        </p>
      </div>

      {/* Filter Bar */}
      <div className="filters-bar">
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--text-muted)', marginRight: '0.5rem' }}>
          <Filter size={16} />
          <span style={{ fontWeight: 600, fontSize: '0.75rem', textTransform: 'uppercase' }}>Filters:</span>
        </div>

        {/* Org Filter */}
        <div className="filter-group">
          <label className="filter-label">Organization</label>
          <select
            className="filter-select"
            value={selectedOrg}
            onChange={(e) => setSelectedOrg(e.target.value)}
          >
            <option value="">All Organizations</option>
            {orgs.map((o) => (
              <option key={o.organization_id} value={o.organization_id}>
                {o.organization_id} ({o.name})
              </option>
            ))}
          </select>
        </div>

        {/* Finding Type Filter */}
        <div className="filter-group">
          <label className="filter-label">Finding Type</label>
          <select
            className="filter-select"
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
          >
            <option value="">All Finding Types</option>
            <option value="EXECUTION_GAP">RULE-1 Execution Gap</option>
            <option value="SUSPICIOUS_FAST_CLOSURE">RULE-2 Suspicious Fast Closure</option>
            <option value="REPEATED_INCIDENTS">RULE-3 Repeated Incidents</option>
            <option value="PEER_DEVIATION">RULE-4 Peer Activity Deviation</option>
          </select>
        </div>

        {/* Priority Filter */}
        <div className="filter-group">
          <label className="filter-label">Priority Level</label>
          <select
            className="filter-select"
            value={selectedPriority}
            onChange={(e) => setSelectedPriority(e.target.value)}
          >
            <option value="">All Priorities</option>
            <option value="HIGH">HIGH Priority</option>
            <option value="MEDIUM">MEDIUM Priority</option>
            <option value="LOW">LOW Priority</option>
          </select>
        </div>

        {(selectedOrg || selectedType || selectedPriority) && (
          <button
            onClick={resetFilters}
            className="btn"
            style={{
              backgroundColor: 'transparent',
              border: '1px solid var(--border-color)',
              color: 'var(--text-muted)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.3rem',
              alignSelf: 'flex-end',
            }}
          >
            <RotateCcw size={14} /> Clear Filters
          </button>
        )}
      </div>

      {/* Content Area */}
      {loading ? (
        <LoadingState message="Loading findings matching query filters..." />
      ) : error ? (
        <ErrorState message={error} onRetry={loadFindings} />
      ) : findings.length === 0 ? (
        <EmptyState title="No Findings Match Filters" message="Try relaxing query filters to view supervisory findings." />
      ) : (
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">
              <AlertCircle size={18} style={{ color: 'var(--accent-cyan)' }} />
              Supervisory Findings ({total})
            </h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Ordered deterministically by Priority, Org ID, Finding ID
            </span>
          </div>

          <div className="data-table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Priority</th>
                  <th>Finding ID</th>
                  <th>Org ID</th>
                  <th>Finding Type / Rule</th>
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
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{f.organization_id}</td>
                    <td><FindingTypeBadge type={f.finding_type} ruleId={f.rule_id} /></td>
                    <td style={{ fontWeight: 600 }}>{f.title}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{f.priority_score}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{f.affected_record_ids.length} records</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
