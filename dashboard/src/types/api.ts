export interface HealthResponse {
  status: string;
  version: string;
  db: string;
  redis: string;
  timestamp: string;
}

export interface ReadyResponse {
  ready: boolean;
  checks: {
    postgres: boolean;
    redis: boolean;
  };
}

export interface QuotaOut {
  used_this_month: number;
  monthly_quota: number;
  tier: string;
  active?: boolean;
}

export interface UsageHistory {
  daily: Array<{
    day: string;
    calls: number;
    smiles: number;
  }>;
  by_endpoint: Array<{
    endpoint: string;
    calls: number;
    smiles: number;
  }>;
}

export interface ComputeRequest {
  smiles: string[];
}

export interface ComputeResult {
  smiles: string;
  descriptors?: Record<string, number | string | null>;
  error?: string;
}

export interface Job {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  created_at: string;
  updated_at: string;
  endpoint: string;
  total: number;
  processed: number;
  errors: number;
  result_url?: string;
}

export interface JobEvent {
  job_id: string;
  status: string;
  progress: number;
  processed: number;
  total: number;
}

export interface TeamMember {
  id: string;
  email: string;
  role: 'owner' | 'admin' | 'member';
  used_this_month: number;
  joined_at: string;
}

export interface Team {
  id: string;
  name: string;
  quota: number;
  members: TeamMember[];
}

export interface Invoice {
  id: string;
  period: string;
  amount: number;
  status: 'paid' | 'pending' | 'failed';
  created_at: string;
}

export interface AuditLogEntry {
  id: string;
  action: string;
  user_id: string;
  endpoint: string;
  timestamp: string;
  details: Record<string, unknown>;
}

export interface AdminStats {
  total_users: number;
  total_molecules: number;
  revenue: number;
  api_uptime: number;
  top_users: Array<{
    user_id: string;
    email: string;
    calls: number;
    smiles: number;
  }>;
  recent_audit: AuditLogEntry[];
  cache: {
    hit_ratio: number;
    size: number;
  };
  job_queue_depth: number;
}

export interface ReferralInfo {
  share_url: string;
  total_referrals: number;
  paid_purchases: number;
  earned_usd: number;
  bonus_smiles: number;
}

export type Theme = 'light' | 'dark' | 'system';

export interface PropertyDisplay {
  name: string;
  value: number | string;
  unit: string;
  confidence: number; // 0-1
  inDomain: boolean;
  status: 'good' | 'warning' | 'alert';
  description?: string;
}
