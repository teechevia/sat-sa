import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { PriorityBadge } from '../components/PriorityBadge';
import { FindingTypeBadge } from '../components/FindingTypeBadge';
import { MetricCard } from '../components/MetricCard';
import { PeerComparison } from '../components/PeerComparison';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { EmptyState } from '../components/EmptyState';
import { EvidenceTable } from '../components/EvidenceTable';

describe('Frontend UI Components & States', () => {
  it('renders loading state with custom message', () => {
    render(<LoadingState message="Loading system metrics..." />);
    expect(screen.getByText('Loading system metrics...')).toBeInTheDocument();
  });

  it('renders error state with retry button', () => {
    const onRetry = vi.fn();
    render(<ErrorState message="API connection failed" onRetry={onRetry} />);
    expect(screen.getByText('API connection failed')).toBeInTheDocument();
    expect(screen.getByText('Retry Request')).toBeInTheDocument();
  });

  it('renders empty state message', () => {
    render(<EmptyState title="No Findings Match Filters" message="Try adjusting filter options." />);
    expect(screen.getByText('No Findings Match Filters')).toBeInTheDocument();
    expect(screen.getByText('Try adjusting filter options.')).toBeInTheDocument();
  });

  it('renders priority badges with correct text', () => {
    render(
      <div>
        <PriorityBadge priority="HIGH" />
        <PriorityBadge priority="MEDIUM" />
        <PriorityBadge priority="LOW" />
      </div>
    );
    expect(screen.getByText('HIGH')).toBeInTheDocument();
    expect(screen.getByText('MEDIUM')).toBeInTheDocument();
    expect(screen.getByText('LOW')).toBeInTheDocument();
  });

  it('renders finding type badge with rule ID', () => {
    render(<FindingTypeBadge type="EXECUTION_GAP" ruleId="RULE-1" />);
    expect(screen.getByText('RULE-1: Execution Gap')).toBeInTheDocument();
  });

  it('renders metric card label and value', () => {
    render(<MetricCard label="Total Alerts" value={9830} subtext="Normalized evidence" />);
    expect(screen.getByText('Total Alerts')).toBeInTheDocument();
    expect(screen.getByText('9830')).toBeInTheDocument();
    expect(screen.getByText('Normalized evidence')).toBeInTheDocument();
  });

  it('renders peer comparison table with metrics and deviation', () => {
    const metrics = { alerts_per_active_asset: 0.44 };
    const peerBaseline = { alerts_per_active_asset_median: 3.21 };
    const peerDeviations = {
      alerts_per_active_asset: {
        org_value: 0.44,
        peer_median: 3.21,
        deviation_pct: -86.2,
        direction: 'below',
      },
    };

    render(
      <PeerComparison
        metrics={metrics}
        peerBaseline={peerBaseline}
        peerDeviations={peerDeviations}
      />
    );

    expect(screen.getByText('Peer Group Comparison (Leave-One-Out Median)')).toBeInTheDocument();
    expect(screen.getByText('Alerts / Active Asset')).toBeInTheDocument();
    expect(screen.getByText('0.44')).toBeInTheDocument();
    expect(screen.getByText('3.21')).toBeInTheDocument();
    expect(screen.getByText('-86.2%')).toBeInTheDocument();
  });

  it('renders evidence table with alert records', () => {
    const records = [
      {
        record_type: 'alert',
        record_id: 'A-00754',
        organization_id: 'ORG-002',
        details: {
          alert_id: 'A-00754',
          severity: 'critical',
          incident_type: 'malware',
          asset_id: 'ASSET-01',
          created_at: '2025-01-01T10:00:00',
          closed_at: '2025-01-01T14:00:00',
          investigated: false,
          escalated: false,
          closure_duration_min: 240,
        },
      },
    ];

    render(<EvidenceTable records={records} />);
    expect(screen.getByText('A-00754')).toBeInTheDocument();
    expect(screen.getByText('critical')).toBeInTheDocument();
    expect(screen.getByText('ASSET-01')).toBeInTheDocument();
  });
});
