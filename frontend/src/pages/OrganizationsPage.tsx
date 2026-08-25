import React, { useEffect, useState } from 'react';
import { useLocation } from 'wouter';
import { getOrganizations } from '../api/client';
import type { Organization } from '../types';
import { LoadingState } from '../components/LoadingState';
import { ErrorState } from '../components/ErrorState';
import { PriorityBadge } from '../components/PriorityBadge';
import { Building2 } from 'lucide-react';

export const OrganizationsPage: React.FC = () => {
  const [, setLocation] = useLocation();
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = () => {
    setLoading(true);
    setError(null);
    getOrganizations()
      .then((res) => {
        setOrgs(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  };

  useEffect(() => {
    loadData();
  }, []);

  if (loading) return <LoadingState message="Loading organizations directory..." />;
  if (error) return <ErrorState message={error} onRetry={loadData} />;

  // Map known org findings for list view
  const orgPriorityMap: Record<string, 'HIGH' | null> = {
    'ORG-002': 'HIGH',
    'ORG-003': 'HIGH',
    'ORG-004': 'HIGH',
    'ORG-012': 'HIGH',
  };

  return (
    <div>
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.25rem' }}>
          Monitored Organizations Directory
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
          Overview of all 12 organizations participating in the supervisory assessment peer groups.
        </p>
      </div>

      <div className="card">
        <div className="card-header">
          <h3 className="card-title">
            <Building2 size={18} style={{ color: 'var(--accent-cyan)' }} />
            All Monitored Organizations ({orgs.length})
          </h3>
        </div>
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Organization ID</th>
                <th>Name</th>
                <th>Size Category</th>
                <th>Peer Group</th>
                <th>Active Assets</th>
                <th>Assessment Status</th>
              </tr>
            </thead>
            <tbody>
              {orgs.map((org) => {
                const priority = orgPriorityMap[org.organization_id];
                return (
                  <tr
                    key={org.organization_id}
                    onClick={() => setLocation(`/organizations/${org.organization_id}`)}
                  >
                    <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
                      {org.organization_id}
                    </td>
                    <td style={{ fontWeight: 600 }}>{org.name}</td>
                    <td style={{ textTransform: 'capitalize' }}>{org.size}</td>
                    <td style={{ textTransform: 'capitalize' }}>{org.peer_group}</td>
                    <td style={{ fontFamily: 'var(--font-mono)' }}>{org.active_asset_count}</td>
                    <td>
                      {priority ? (
                        <PriorityBadge priority={priority} />
                      ) : (
                        <span style={{ color: '#10b981', fontSize: '0.75rem', fontWeight: 600 }}>
                          Normal / Healthy
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
