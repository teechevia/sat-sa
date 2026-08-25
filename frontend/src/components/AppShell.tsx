import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'wouter';
import { Shield, LayoutDashboard, Building2, AlertCircle, Activity } from 'lucide-react';
import { getHealth } from '../api/client';

interface AppShellProps { children: React.ReactNode; }

export const AppShell: React.FC<AppShellProps> = ({ children }) => {
  const [location] = useLocation();
  const [health, setHealth] = useState<'ok' | 'error' | 'loading'>('loading');

  useEffect(() => {
    getHealth().then(() => setHealth('ok')).catch(() => setHealth('error'));
  }, []);

  const statusLabel = health === 'ok' ? 'API ACTIVE' : health === 'error' ? 'API OFFLINE' : 'CHECKING API';
  const statusClass = health === 'ok' ? 'success-text' : health === 'error' ? 'alert-text' : 'warning-text';

  return (
    <div className="app-container">
      <header className="header">
        <Link href="/" className="brand" aria-label="SAT-SA overview">
          <Shield className="brand-icon" size={23} aria-hidden="true" />
          <div><div className="brand-title">SAT-SA</div><div className="brand-subtitle">Supervisory Assessment &amp; Signal Analysis</div></div>
        </Link>
        <nav className="nav-links" aria-label="Primary navigation">
          <Link href="/" className={`nav-item ${location === '/' ? 'active' : ''}`}><LayoutDashboard size={16} aria-hidden="true" /> Overview</Link>
          <Link href="/organizations" className={`nav-item ${location.startsWith('/organizations') ? 'active' : ''}`}><Building2 size={16} aria-hidden="true" /> Organizations</Link>
          <Link href="/findings" className={`nav-item ${location.startsWith('/findings') ? 'active' : ''}`}><AlertCircle size={16} aria-hidden="true" /> Findings</Link>
        </nav>
        <div className="system-status" aria-label={`API status: ${statusLabel}`}><Activity size={13} aria-hidden="true" /><span className={statusClass}>{statusLabel}</span></div>
      </header>
      <main className="main-content">{children}</main>
    </div>
  );
};
