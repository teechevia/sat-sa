import type {
  EvidenceResponse,
  Finding,
  FindingList,
  Metrics,
  Organization,
  OrganizationDetail,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'https://sat-sa.onrender.com';

async function fetchJson<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const res = await fetch(url, options);
    if (!res.ok) {
      const errorText = await res.text();
      let errorMsg = `HTTP ${res.status}: ${res.statusText}`;
      try {
        const parsed = JSON.parse(errorText);
        if (parsed.detail) {
          errorMsg = typeof parsed.detail === 'string' ? parsed.detail : JSON.stringify(parsed.detail);
        }
      } catch {
        // use status text
      }
      throw new Error(errorMsg);
    }
    return (await res.json()) as T;
  } catch (err: any) {
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      throw new Error(`Unable to connect to SAT-SA API at ${API_BASE_URL}. Ensure backend is running.`);
    }
    throw err;
  }
}

export async function getHealth(): Promise<{ status: string; service: string; version: string }> {
  return fetchJson<{ status: string; service: string; version: string }>('/api/health');
}

export async function getOrganizations(): Promise<Organization[]> {
  return fetchJson<Organization[]>('/api/organizations');
}

export async function getOrganization(id: string): Promise<OrganizationDetail> {
  return fetchJson<OrganizationDetail>(`/api/organizations/${encodeURIComponent(id)}`);
}

export async function getOrgMetrics(id: string): Promise<Record<string, any>> {
  return fetchJson<Record<string, any>>(`/api/organizations/${encodeURIComponent(id)}/metrics`);
}

export interface FindingFilters {
  organization_id?: string;
  finding_type?: string;
  priority?: string;
}

export async function getFindings(filters?: FindingFilters): Promise<FindingList> {
  const query = new URLSearchParams();
  if (filters?.organization_id) query.set('organization_id', filters.organization_id);
  if (filters?.finding_type) query.set('finding_type', filters.finding_type);
  if (filters?.priority) query.set('priority', filters.priority);

  const queryString = query.toString();
  const endpoint = queryString ? `/api/findings?${queryString}` : '/api/findings';
  return fetchJson<FindingList>(endpoint);
}

export async function getFinding(id: string): Promise<Finding> {
  return fetchJson<Finding>(`/api/findings/${encodeURIComponent(id)}`);
}

export async function getFindingEvidence(id: string): Promise<EvidenceResponse> {
  return fetchJson<EvidenceResponse>(`/api/findings/${encodeURIComponent(id)}/evidence`);
}

export async function getMetrics(): Promise<Metrics> {
  return fetchJson<Metrics>('/api/metrics');
}
