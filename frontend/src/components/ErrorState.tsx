import React from 'react';
import { AlertTriangle } from 'lucide-react';

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  message = 'Unable to load data. Please verify the backend API is running.',
  onRetry,
}) => {
  return (
    <div className="state-box" style={{ borderColor: 'var(--priority-high-border)' }}>
      <AlertTriangle className="state-icon" size={32} style={{ color: 'var(--priority-high-text)' }} />
      <h4 style={{ color: 'var(--text-main)', marginBottom: '0.35rem' }}>API Connection Error</h4>
      <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1rem', maxWidth: '500px' }}>
        {message}
      </p>
      {onRetry && (
        <button onClick={onRetry} className="btn">
          Retry Request
        </button>
      )}
    </div>
  );
};
