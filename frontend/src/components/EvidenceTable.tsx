import React, { useState } from 'react';
import type { EvidenceRecord } from '../types';
import { FileCode } from 'lucide-react';

interface EvidenceTableProps {
  records: EvidenceRecord[];
}

export const EvidenceTable: React.FC<EvidenceTableProps> = ({ records }) => {
  const [showRaw, setShowRaw] = useState(false);

  if (!records || records.length === 0) {
    return (
      <div className="evidence-box">
        <p style={{ color: 'var(--text-muted)' }}>No individual record evidence attached.</p>
      </div>
    );
  }

  const isAlert = records[0].record_type === 'alert';

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">Supporting Evidence Records ({records.length} Traceable Records)</h3>
        <button
          onClick={() => setShowRaw(!showRaw)}
          className="btn"
          style={{
            backgroundColor: 'var(--bg-subtle)',
            color: 'var(--text-muted)',
            border: '1px solid var(--border-color)',
            fontSize: '0.75rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.3rem',
          }}
        >
          <FileCode size={14} />
          {showRaw ? 'Hide Raw JSON View' : 'Show Raw JSON View'}
        </button>
      </div>

      {showRaw ? (
        <pre
          style={{
            backgroundColor: '#090d16',
            padding: '1rem',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-color)',
            fontSize: '0.75rem',
            fontFamily: 'var(--font-mono)',
            maxHeight: '400px',
            overflow: 'auto',
          }}
        >
          {JSON.stringify(records, null, 2)}
        </pre>
      ) : (
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              {isAlert ? (
                <tr>
                  <th>Alert ID</th>
                  <th>Severity</th>
                  <th>Incident Type</th>
                  <th>Asset ID</th>
                  <th>Created At</th>
                  <th>Closed At</th>
                  <th>Investigated</th>
                  <th>Escalated</th>
                  <th>Closure Duration</th>
                </tr>
              ) : (
                <tr>
                  <th>Case ID</th>
                  <th>Asset ID</th>
                  <th>Incident Type</th>
                  <th>Opened At</th>
                  <th>Closed At</th>
                  <th>Recurrence Count</th>
                  <th>Remediation Evidence</th>
                </tr>
              )}
            </thead>
            <tbody>
              {records.slice(0, 50).map((rec) => {
                const d = rec.details;
                return isAlert ? (
                  <tr key={rec.record_id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{rec.record_id}</td>
                    <td>
                      <span
                        className="rule-tag"
                        style={{
                          color:
                            d.severity === 'critical'
                              ? '#fca5a5'
                              : d.severity === 'high'
                              ? '#fcd34d'
                              : 'var(--text-muted)',
                        }}
                      >
                        {d.severity}
                      </span>
                    </td>
                    <td>{d.incident_type}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{d.asset_id}</td>
                    <td>{d.created_at ? new Date(d.created_at).toLocaleString() : 'N/A'}</td>
                    <td>{d.closed_at ? new Date(d.closed_at).toLocaleString() : 'Open'}</td>
                    <td>
                      <span style={{ color: d.investigated ? '#10b981' : '#ef4444', fontWeight: 600 }}>
                        {d.investigated ? 'Yes' : 'No'}
                      </span>
                    </td>
                    <td>{d.escalated ? 'Yes' : 'No'}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>
                      {d.closure_duration_min !== null && d.closure_duration_min !== undefined
                        ? `${d.closure_duration_min.toFixed(1)} min`
                        : 'Open'}
                    </td>
                  </tr>
                ) : (
                  <tr key={rec.record_id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{rec.record_id}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{d.asset_id}</td>
                    <td>{d.incident_type}</td>
                    <td>{d.opened_at ? new Date(d.opened_at).toLocaleString() : 'N/A'}</td>
                    <td>{d.closed_at ? new Date(d.closed_at).toLocaleString() : 'Open'}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{d.recurrence_count}</td>
                    <td>
                      <span style={{ color: d.remediation_evidence ? '#10b981' : '#ef4444', fontWeight: 600 }}>
                        {d.remediation_evidence ? 'True' : 'False'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {records.length > 50 && (
            <div style={{ padding: '0.5rem 1rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Showing first 50 of {records.length} records.
            </div>
          )}
        </div>
      )}
    </div>
  );
};
