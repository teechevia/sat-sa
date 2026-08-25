import React from 'react';
import type { FindingType } from '../types';

interface FindingTypeBadgeProps {
  type: FindingType;
  ruleId?: string;
}

const TYPE_NAMES: Record<FindingType, string> = {
  EXECUTION_GAP: 'Execution Gap',
  SUSPICIOUS_FAST_CLOSURE: 'Suspicious Fast Closure',
  REPEATED_INCIDENTS: 'Repeated Incidents',
  PEER_DEVIATION: 'Peer Activity Deviation',
};

export const FindingTypeBadge: React.FC<FindingTypeBadgeProps> = ({ type, ruleId }) => {
  return (
    <span className="rule-tag" title={type}>
      {ruleId ? `${ruleId}: ` : ''}{TYPE_NAMES[type] || type}
    </span>
  );
};
