import React, { useEffect, useState } from 'react';
import { useLocation, useRoute } from 'wouter';
import { getFinding, getFindingEvidence } from '../api/client';
import type { EvidenceResponse, Finding } from '../types';
import { PriorityBadge } from '../components/PriorityBadge';
import { FindingTypeBadge } from '../components/FindingTypeBadge';
import { EvidenceTable } from '../components/EvidenceTable';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { ArrowLeft, HelpCircle, Layers, Sliders } from 'lucide-react';

export const FindingDetailPage: React.FC = () => {
  const [, params] = useRoute('/findings/:findingId');
  const [, setLocation] = useLocation();
  const findingId = params?.findingId || '';

  const [finding, setFinding] = useState<Finding | null>(null);
  const [evidenceData, setEvidenceData] = useState<EvidenceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = () => {
    if (!findingId) return;
    setLoading(true);
    setError(null);

    Promise.all([getFinding(findingId), getFindingEvidence(findingId)])
      .then(([findingRes, evidenceRes]) => {
        setFinding(findingRes);
        setEvidenceData(evidenceRes);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadData();
  }, [findingId]);

  if (loading) return <LoadingState message={`Loading finding ${findingId} details and evidence records...`} />;
  if (error || !finding) return <ErrorState message={error || `Finding '${findingId}' not found.`} onRetry={loadData} />;

  const ev = finding.evidence || {};
  const breakdown = ev.priority_scoring_breakdown || [];

  return (
    <div>
      <button
        onClick={() => setLocation('/findings')}
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
        <ArrowLeft size={14} /> Back to Findings
      </button>

      {/* Main Header Banner */}
      <div
        className="card"
        style={{
          borderLeft: `4px solid ${
            finding.priority === 'HIGH'
              ? 'var(--priority-high-border)'
              : finding.priority === 'MEDIUM'
              ? 'var(--priority-med-border)'
              : 'var(--priority-low-border)'
          }`,
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.5rem' }}>
              <PriorityBadge priority={finding.priority} />
              <FindingTypeBadge type={finding.finding_type} ruleId={finding.rule_id} />
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                {finding.finding_id}
              </span>
            </div>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>{finding.title}</h1>
            <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              Organization: <strong style={{ color: 'var(--text-main)', fontFamily: 'var(--font-mono)' }}>{finding.organization_id}</strong>
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Priority Score</div>
            <div style={{ fontSize: '1.8rem', fontWeight: 700, fontFamily: 'var(--font-mono)' }}>{finding.priority_score}</div>
          </div>
        </div>

        {/* Description Box */}
        <div className="evidence-box" style={{ marginTop: '1.25rem', marginBottom: 0 }}>
          <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600, marginBottom: '0.3rem' }}>
            Supervisory Description
          </div>
          <p style={{ fontSize: '0.92rem', color: 'var(--text-main)', lineHeight: 1.6 }}>
            {finding.description}
          </p>
        </div>
      </div>

      {/* WHY THIS WAS FLAGGED (Rules & Thresholds) */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <Sliders size={18} style={{ color: 'var(--accent-cyan)' }} />
            Why This Was Flagged (Detection Logic & Thresholds)
          </h3>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
          {/* Metrics & Observed Values */}
          <div>
            <h4 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
              Observed Metrics & Thresholds
            </h4>
            <div className="data-table-container">
              <table className="data-table">
                <tbody>
                  <tr>
                    <td style={{ fontWeight: 600 }}>Rule Triggered</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{finding.rule_id} ({finding.finding_type})</td>
                  </tr>

                  {ev.observed_missing_rate !== undefined && (
                    <>
                      <tr>
                        <td style={{ fontWeight: 600 }}>Observed Missing Investigation Rate</td>
                        <td style={{ fontFamily: 'var(--font-mono)', color: '#f59e0b', fontWeight: 700 }}>
                          {(ev.observed_missing_rate * 100).toFixed(1)}%
                        </td>
                      </tr>
                      <tr>
                        <td style={{ fontWeight: 600 }}>Rule Threshold</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{(ev.threshold_missing_rate * 100).toFixed(0)}%</td>
                      </tr>
                      <tr>
                        <td style={{ fontWeight: 600 }}>Critical Alerts Missing / Total</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>
                          {ev.missing_investigation_count} / {ev.total_critical_alerts}
                        </td>
                      </tr>
                    </>
                  )}

                  {ev.observed_flagged_rate !== undefined && (
                    <>
                      <tr>
                        <td style={{ fontWeight: 600 }}>Observed Fast Closed Uninvestigated Rate</td>
                        <td style={{ fontFamily: 'var(--font-mono)', color: '#f59e0b', fontWeight: 700 }}>
                          {(ev.observed_flagged_rate * 100).toFixed(1)}%
                        </td>
                      </tr>
                      <tr>
                        <td style={{ fontWeight: 600 }}>Rule Threshold</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{(ev.threshold_flagged_rate * 100).toFixed(0)}%</td>
                      </tr>
                      <tr>
                        <td style={{ fontWeight: 600 }}>Fast Closure Limit</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>&lt; {ev.threshold_fast_minutes} minutes</td>
                      </tr>
                      <tr>
                        <td style={{ fontWeight: 600 }}>Flagged Median Closure Time</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{ev.median_closure_duration_minutes} min</td>
                      </tr>
                    </>
                  )}

                  {ev.flagged_group_count !== undefined && (
                    <>
                      <tr>
                        <td style={{ fontWeight: 600 }}>Flagged Recurring Incident Groups</td>
                        <td style={{ fontFamily: 'var(--font-mono)', color: '#f59e0b', fontWeight: 700 }}>
                          {ev.flagged_group_count} groups ({ev.total_affected_cases} cases)
                        </td>
                      </tr>
                      <tr>
                        <td style={{ fontWeight: 600 }}>Worst Pattern</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>
                          {ev.worst_repeated_group?.asset_id} + {ev.worst_repeated_group?.incident_type} ({ev.worst_repeated_group?.case_count} cases)
                        </td>
                      </tr>
                    </>
                  )}

                  {ev.deviation_pct !== undefined && (
                    <>
                      <tr>
                        <td style={{ fontWeight: 600 }}>Observed Value</td>
                        <td style={{ fontFamily: 'var(--font-mono)', color: '#f59e0b', fontWeight: 700 }}>
                          {ev.observed_org_value} alerts/asset
                        </td>
                      </tr>
                      <tr>
                        <td style={{ fontWeight: 600 }}>Peer Group Median ({ev.peer_group})</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>{ev.peer_median} alerts/asset</td>
                      </tr>
                      <tr>
                        <td style={{ fontWeight: 600 }}>Peer Deviation</td>
                        <td style={{ fontFamily: 'var(--font-mono)', color: '#f59e0b', fontWeight: 700 }}>
                          {ev.deviation_pct}% ({ev.direction})
                        </td>
                      </tr>
                    </>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Transparent Additive Priority Breakdown */}
          <div>
            <h4 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem', textTransform: 'uppercase' }}>
              Transparent Priority Scoring Breakdown (Score: {finding.priority_score})
            </h4>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
              {breakdown.map((b: string, idx: number) => (
                <div
                  key={idx}
                  style={{
                    backgroundColor: 'var(--bg-subtle)',
                    padding: '0.5rem 0.75rem',
                    borderRadius: 'var(--radius-sm)',
                    fontSize: '0.82rem',
                    borderLeft: '3px solid var(--accent-cyan)',
                    fontFamily: 'var(--font-mono)',
                  }}
                >
                  {b}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ASSESSOR GUIDANCE */}
      <div className="guidance-box">
        <div className="guidance-title">
          <HelpCircle size={18} /> Human Assessor Guidance
        </div>
        <p style={{ fontSize: '0.9rem', color: 'var(--text-main)', lineHeight: 1.6 }}>
          {finding.assessor_guidance}
        </p>
      </div>

      {/* EVIDENCE TABLE (Record Traceability) */}
      <EvidenceTable records={evidenceData?.evidence_records || []} />

      {/* SOURCE RECORD IDs TRACEABILITY LIST */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <Layers size={18} style={{ color: 'var(--accent-cyan)' }} />
            Source Record Traceability ({finding.affected_record_ids.length} Record IDs)
          </h3>
        </div>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
          This finding is 100% traceable back to original evidence records in the source dataset.
        </p>
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '0.35rem',
            maxHeight: '150px',
            overflowY: 'auto',
            padding: '0.5rem',
            backgroundColor: '#090d16',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-color)',
          }}
        >
          {finding.affected_record_ids.map((id) => (
            <span
              key={id}
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.72rem',
                backgroundColor: 'var(--bg-subtle)',
                padding: '0.15rem 0.4rem',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--border-color)',
              }}
            >
              {id}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};
