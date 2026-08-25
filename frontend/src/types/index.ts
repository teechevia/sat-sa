export type Priority = 'HIGH' | 'MEDIUM' | 'LOW';

export type FindingType =
  | 'EXECUTION_GAP'
  | 'SUSPICIOUS_FAST_CLOSURE'
  | 'REPEATED_INCIDENTS'
  | 'PEER_DEVIATION';

export interface Organization {
  organization_id: string;
  name: string;
  size: string;
  peer_group: string;
  active_asset_count: number;
}

export interface FindingsSummary {
  total_findings: number;
  high_priority_count: number;
  medium_priority_count: number;
  low_priority_count: number;
  finding_ids: string[];
}

export interface OrganizationDetail extends Organization {
  metrics: Record<string, any>;
  peer_baseline: Record<string, any>;
  peer_deviations: Record<string, any>;
  findings_summary: FindingsSummary;
}

export interface Finding {
  finding_id: string;
  organization_id: string;
  finding_type: FindingType;
  priority: Priority;
  title: string;
  description: string;
  evidence: Record<string, any>;
  affected_record_ids: string[];
  assessor_guidance: string;
  rule_id: string;
  priority_score: number;
  generated_at: string;
}

export interface FindingList {
  total: number;
  findings: Finding[];
}

export interface EvidenceRecord {
  record_type: 'alert' | 'case' | string;
  record_id: string;
  organization_id: string;
  details: Record<string, any>;
}

export interface EvidenceResponse {
  finding_id: string;
  organization_id: string;
  finding_type: FindingType;
  total_affected_records: number;
  evidence_records: EvidenceRecord[];
}

export interface Metrics {
  meta: Record<string, any>;
  data_quality: Record<string, any>;
  total_organizations: number;
  total_alerts: number;
  total_investigations: number;
  total_escalations: number;
  total_cases: number;
  total_findings: number;
  summary_by_priority: Record<string, number>;
  summary_by_rule: Record<string, number>;
  organizations: Record<string, any>[];
}
