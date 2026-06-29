import { useState, useEffect } from 'react';
import {
  Shield,
  Users,
  FlaskConical,
  DollarSign,
  Activity,
  AlertCircle,
  Loader,
} from 'lucide-react';
import { useAuthStore } from '@/store/auth';
import type { AdminStats, AuditLogEntry } from '@/types/api';

// Mock data for demonstration
const MOCK_STATS: AdminStats = {
  total_users: 1248,
  total_molecules: 4_500_000,
  revenue: 34_290,
  api_uptime: 99.97,
  top_users: [
    { user_id: 'u-1', email: 'bigpharma@example.com', calls: 12500, smiles: 45000 },
    { user_id: 'u-2', email: 'uni-research@lab.edu', calls: 8200, smiles: 28000 },
    { user_id: 'u-3', email: 'startup@biotech.io', calls: 6100, smiles: 19000 },
    { user_id: 'u-4', email: 'consultant@chem.io', calls: 3400, smiles: 12000 },
    { user_id: 'u-5', email: 'student@uni.edu', calls: 2100, smiles: 7500 },
  ],
  recent_audit: [
    { id: '1', action: 'compute', user_id: 'u-1', endpoint: '/compute', timestamp: new Date().toISOString(), details: {} },
    { id: '2', action: 'signup', user_id: 'u-99', endpoint: '/signup', timestamp: new Date(Date.now() - 60000).toISOString(), details: {} },
    { id: '3', action: 'key_rotate', user_id: 'u-2', endpoint: '/key/rotate', timestamp: new Date(Date.now() - 120000).toISOString(), details: {} },
    { id: '4', action: 'compute', user_id: 'u-3', endpoint: '/predict', timestamp: new Date(Date.now() - 180000).toISOString(), details: {} },
  ],
  cache: { hit_ratio: 0.87, size: 256 },
  job_queue_depth: 3,
};

export default function Admin() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);
  const { tier } = useAuthStore();

  const isAdmin = tier === 'enterprise' || tier === 'admin';

  useEffect(() => {
    // Simulate fetching admin stats
    const timer = setTimeout(() => {
      setStats(MOCK_STATS);
      setLoading(false);
    }, 800);
    return () => clearTimeout(timer);
  }, []);

  if (!isAdmin) {
    return (
      <div className="mx-auto max-w-2xl py-12 text-center">
        <AlertCircle size={48} className="mx-auto mb-4 text-red-500" />
        <h1 className="text-xl font-bold text-[var(--fg-primary)]">Access Denied</h1>
        <p className="mt-2 text-[var(--fg-secondary)]">
          Admin panel requires enterprise or admin tier.
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex h-[60vh] items-center justify-center">
        <Loader size={32} className="animate-spin text-[var(--accent)]" />
      </div>
    );
  }

  const statCards = [
    { label: 'Total Users', value: stats?.total_users.toLocaleString() ?? '—', icon: Users, color: 'text-blue-500' },
    { label: 'Molecules', value: stats?.total_molecules.toLocaleString() ?? '—', icon: FlaskConical, color: 'text-[var(--accent)]' },
    { label: 'Revenue', value: `$${stats?.revenue.toLocaleString() ?? '—'}`, icon: DollarSign, color: 'text-emerald-500' },
    { label: 'API Uptime', value: `${stats?.api_uptime ?? '—'}%`, icon: Activity, color: 'text-amber-500' },
  ];

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--fg-primary)]">Admin</h1>
          <p className="mt-1 text-sm text-[var(--fg-secondary)]">System overview and management</p>
        </div>
        <span className="badge badge-green">
          <Shield size={12} className="mr-1" />
          Admin
        </span>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {statCards.map((card) => {
          const Icon = card.icon;
          return (
            <div key={card.label} className="card p-5 card-hover">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-[var(--fg-muted)]">{card.label}</p>
                  <p className="mt-1 text-2xl font-bold text-[var(--fg-primary)]">{card.value}</p>
                </div>
                <div className={`rounded-lg p-2 bg-opacity-10 ${card.color.replace('text-', 'bg-')}`}>
                  <Icon size={24} className={card.color} />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Cache & Queue */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-[var(--fg-primary)] mb-3">Cache Stats</h2>
          <div className="space-y-3">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-[var(--fg-muted)]">Hit Ratio</span>
                <span className="font-medium text-[var(--fg-primary)]">
                  {Math.round((stats?.cache.hit_ratio ?? 0) * 100)}%
                </span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-[var(--bg-tertiary)]">
                <div
                  className="h-full rounded-full bg-[var(--accent)]"
                  style={{ width: `${(stats?.cache.hit_ratio ?? 0) * 100}%` }}
                />
              </div>
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-[var(--fg-muted)]">Cache Size</span>
              <span className="font-medium text-[var(--fg-primary)]">{stats?.cache.size} MB</span>
            </div>
          </div>
        </div>
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-[var(--fg-primary)] mb-3">Job Queue</h2>
          <div className="flex items-center gap-4">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[var(--accent-50)] text-[var(--accent)] text-2xl font-bold">
              {stats?.job_queue_depth}
            </div>
            <div>
              <p className="text-sm text-[var(--fg-primary)]">Jobs pending</p>
              <p className="text-xs text-[var(--fg-muted)]">
                {stats?.job_queue_depth === 0
                  ? 'Queue is clear'
                  : 'Workers are processing'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Top users */}
      <div className="card overflow-hidden">
        <h2 className="p-5 text-sm font-semibold text-[var(--fg-primary)] border-b border-[var(--border)]">
          Top Users (30d)
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] bg-[var(--bg-tertiary)]">
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--fg-muted)]">User</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--fg-muted)]">Calls</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--fg-muted)]">SMILES</th>
              </tr>
            </thead>
            <tbody>
              {stats?.top_users.map((user) => (
                <tr
                  key={user.user_id}
                  className="border-b border-[var(--border-light)] hover:bg-[var(--bg-tertiary)] transition-colors"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="flex h-7 w-7 items-center justify-center rounded-full bg-[var(--accent-50)] text-[var(--accent)] text-xs font-medium">
                        {user.email[0].toUpperCase()}
                      </div>
                      <span className="text-[var(--fg-primary)]">{user.email}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-[var(--fg-secondary)]">{user.calls.toLocaleString()}</td>
                  <td className="px-4 py-3 text-[var(--fg-secondary)]">{user.smiles.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Audit log */}
      <div className="card overflow-hidden">
        <h2 className="p-5 text-sm font-semibold text-[var(--fg-primary)] border-b border-[var(--border)]">
          Recent Audit Log
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] bg-[var(--bg-tertiary)]">
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--fg-muted)]">Action</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--fg-muted)]">Endpoint</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--fg-muted)]">Time</th>
              </tr>
            </thead>
            <tbody>
              {stats?.recent_audit.map((log) => (
                <tr
                  key={log.id}
                  className="border-b border-[var(--border-light)] hover:bg-[var(--bg-tertiary)] transition-colors"
                >
                  <td className="px-4 py-3">
                    <span className="badge badge-blue">{log.action}</span>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-[var(--fg-secondary)]">{log.endpoint}</td>
                  <td className="px-4 py-3 text-xs text-[var(--fg-muted)]">
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
