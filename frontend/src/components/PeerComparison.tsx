import React from 'react';

interface PeerComparisonProps {
  metrics: Record<string, any>;
  peerBaseline: Record<string, any>;
  peerDeviations: Record<string, any>;
}

const COMPARISON_METRICS = [
  { key: 'alerts_per_active_asset', label: 'Alerts / Active Asset' },
  { key: 'critical_alerts_per_active_asset', label: 'Critical Alerts / Active Asset' },
  { key: 'investigation_rate', label: 'Overall Investigation Rate', format: 'pct' },
  { key: 'critical_investigation_rate', label: 'Critical Investigation Rate', format: 'pct' },
];

export const PeerComparison: React.FC<PeerComparisonProps> = ({
  metrics,
  peerBaseline,
  peerDeviations,
}) => {
  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">Peer Group Comparison (Leave-One-Out Median)</h3>
      </div>
      <div className="data-table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th>Metric</th>
              <th>Organization Value</th>
              <th>Peer Group Median</th>
              <th>Difference / Deviation</th>
              <th>Direction</th>
            </tr>
          </thead>
          <tbody>
            {COMPARISON_METRICS.map(({ key, label, format }) => {
              const orgVal = metrics[key];
              const pMedian = peerBaseline[`${key}_median`];
              const devInfo = peerDeviations[key] || {};

              const fmtVal = (v: any) => {
                if (v === undefined || v === null) return 'N/A';
                if (format === 'pct') return `${(v * 100).toFixed(1)}%`;
                return typeof v === 'number' ? v.toFixed(2) : String(v);
              };

              const devPct = devInfo.deviation_pct;
              const direction = devInfo.direction;

              return (
                <tr key={key}>
                  <td style={{ fontWeight: 600 }}>{label}</td>
                  <td style={{ fontFamily: 'var(--font-mono)' }}>{fmtVal(orgVal)}</td>
                  <td style={{ fontFamily: 'var(--font-mono)' }}>{fmtVal(pMedian)}</td>
                  <td style={{ fontFamily: 'var(--font-mono)' }}>
                    {devPct !== undefined && devPct !== null ? (
                      <span
                        style={{
                          color:
                            Math.abs(devPct) >= 40
                              ? '#f59e0b'
                              : '#9ca3af',
                          fontWeight: Math.abs(devPct) >= 40 ? 700 : 400,
                        }}
                      >
                        {devPct > 0 ? `+${devPct.toFixed(1)}%` : `${devPct.toFixed(1)}%`}
                      </span>
                    ) : (
                      'N/A'
                    )}
                  </td>
                  <td>
                    {direction ? (
                      <span className="rule-tag" style={{ textTransform: 'capitalize' }}>
                        {direction}
                      </span>
                    ) : (
                      'Normal'
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
