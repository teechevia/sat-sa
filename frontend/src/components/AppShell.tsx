import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'wouter';
import { Shield, LayoutDashboard, Building2, AlertCircle } from 'lucide-react';
import { getHealth } from '../api/client';

interface AppShellProps {
  children: React.ReactNode;
}

export const AppShell: React.FC<AppShellProps> = ({ children }) => {
  const [location] = useLocation();
  const [health, setHealth] = useState<'ok' | 'error' | 'loading'>('loading');

  useEffect(() => {
    getHealth()
      .then(() => setHealth('ok'))
      .catch(() => setHealth('error'));
  }, []);

  return (
    <div className="app-container">
      <header className="header">
        <div className="brand">
          <Shield className="brand-icon" size={24} />
          <div>
            <div className="brand-title">SAT-SA</div>
            <div className="brand-subtitle">Supervisory Assessment & Signal Analysis</div>
          </div>
        </div>

        <nav className="nav-links">
          <Link href="/">
            <a className={`nav-item ${location === '/' ? 'active' : ''}`}>
              <LayoutDashboard size={16} /> Overview
            </a>
          </Link>
          <Link href="/organizations">
            <a className={`nav-item ${location.startsWith('/organizations') ? 'active' : ''}`}>
              <Building2 size={16} /> Organizations
            </a>
          </Link>
          <Link href="/findings">
            <a className={`nav-item ${location.startsWith('/findings') ? 'active' : ''}`}>
              <AlertCircle size={16} /> Findings
            </a>
          </Link>
        </nav>

        <div className="system-status">
          <div
            className="status-dot"
            style={{
              backgroundColor:
                health === 'ok' ? '#10b981' : health === 'error' ? '#ef4444' : '#f59e0b',
            }}
          />
          <span>
            {health === 'ok'
              ? 'API Active'
              : health === 'error'
              ? 'API Offline'
              : 'Checking API...'}
          </span>
        </div>
      </header>

      <main className="main-content">{children}</main>
    </div>
  );
};
