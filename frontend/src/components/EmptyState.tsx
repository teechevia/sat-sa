import React from 'react';
import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  title?: string;
  message?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No Findings Detected',
  message = 'No supervisory findings match the selected filters.',
}) => {
  return (
    <div className="state-box">
      <Inbox className="state-icon" size={32} />
      <h4 style={{ color: 'var(--text-main)', marginBottom: '0.35rem' }}>{title}</h4>
      <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{message}</p>
    </div>
  );
};
