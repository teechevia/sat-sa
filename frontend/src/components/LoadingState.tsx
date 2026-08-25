import React from 'react';
import { RefreshCw } from 'lucide-react';

interface LoadingStateProps {
  message?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading operational evidence...',
}) => {
  return (
    <div className="state-box">
      <RefreshCw className="state-icon spin" size={32} style={{ animation: 'spin 1s linear infinite' }} />
      <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>{message}</p>
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};
