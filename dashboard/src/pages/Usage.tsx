import { useMemo } from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import { BarChart3, CreditCard, AlertCircle } from 'lucide-react';
import { useAuthStore } from '@/store/auth';
import type { UsageHistory, Invoice } from '@/types/api';

const COLORS = ['#0d9488', '#14b8a6', '#2dd4bf', '#5eead4', '#99f6e4', '#ccfbf1'];

// Mock data for demonstration; in production, fetch from /usage/history
const MOCK_HISTORY: UsageHistory = {
  daily: Array.from({ length: 30 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (29 - i));
    return {
      day: d.toISOString().slice(5, 10),
      calls: Math.floor(Math.random() * 200) + 10,
      smiles: Math.floor(Math.random() * 500) + 50,
    };
  }),
  by_endpoint: [
    { endpoint: '/compute', calls: 1240, smiles: 3500 },
    { endpoint: '/descriptors', calls: 680, smiles: 1200 },
    { endpoint: '/predict', calls: 420, smiles: 890 },
    { endpoint: '/screen', calls: 310, smiles: 620 },
    { endpoint: '/convert', calls: 150, smiles: 300 },
    { endpoint: '/fingerprints', calls: 90, smiles: 180 },
  ],
};

const MOCK_INVOICES: Invoice[] = [
  { id: 'inv-1', period: '2024-01', amount: 29, status: 'paid', created_at: '2024-01-01' },
  { id: 'inv-2', period: '2024-02', amount: 29, status: 'paid', created_at: '2024-02-01' },
  { id: 'inv-3', period: '2024-03', amount: 299, status: 'pending', created_at: '2024-03-01' },
];

export default function Usage() {
  const { quota } = useAuthStore();
  const quotaPct = quota && quota.total > 0 ? (quota.used / quota.total) * 100 : 0;

  const chartData = useMemo(() => MOCK_HISTORY.daily, []);
  const pieData = useMemo(
    () =>
      MOCK_HISTORY.by_endpoint.map((e) => ({
        name: e.endpoint,
        value: e.calls,
      })),
    []
  );

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--fg-primary)]">Usage</h1>
        <p className="mt-1 text-sm text-[var(--fg-secondary)]">
          Quota, analytics, and billing
        </p>
      </div>

      {/* Quota meter */}
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 size={18} className="text-[var(--accent)]" />
          <h2 className="text-sm font-semibold text-[var(--fg-primary)]">Monthly Quota</h2>
        </div>
        <div className="flex items-end justify-between mb-2">
          <div>
            <p className="text-3xl font-bold text-[var(--fg-primary)]">
              {quota?.used.toLocaleString() ?? '—'}
            </p>
            <p className="text-sm text-[var(--fg-muted)]">
              of {quota?.total.toLocaleString() ?? '—'} SMILES used
            </p>
          </div>
          <p className="text-2xl font-bold text-[var(--fg-primary)]">{Math.round(quotaPct)}%</p>
        </div>
        <div className="h-3 overflow-hidden rounded-full bg-[var(--bg-tertiary)]">
          <div
            className={`h-full rounded-full transition-all ${
              quotaPct > 90 ? 'bg-red-500' : quotaPct > 70 ? 'bg-amber-500' : 'bg-[var(--accent)]'
            }`}
            style={{ width: `${Math.min(100, quotaPct)}%` }}
            role="progressbar"
            aria-valuenow={Math.round(quotaPct)}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
        {quotaPct > 90 && (
          <div className="mt-3 flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950/30 dark:text-red-400">
            <AlertCircle size={16} />
            You are approaching your monthly quota limit. Upgrade to avoid service interruption.
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Line chart */}
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-[var(--fg-primary)] mb-4">Calls per Day (30d)</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="day" tick={{ fontSize: 12, fill: 'var(--fg-muted)' }} />
                <YAxis tick={{ fontSize: 12, fill: 'var(--fg-muted)' }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--bg-secondary)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="calls"
                  stroke="var(--accent)"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
                <Line
                  type="monotone"
                  dataKey="smiles"
                  stroke="#2dd4bf"
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Pie chart */}
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-[var(--fg-primary)] mb-4">Endpoint Breakdown</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {pieData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--bg-secondary)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                  }}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Invoices */}
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <CreditCard size={18} className="text-[var(--accent)]" />
          <h2 className="text-sm font-semibold text-[var(--fg-primary)]">Invoices</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)]">
                <th className="px-3 py-2 text-left text-xs font-medium text-[var(--fg-muted)]">Period</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-[var(--fg-muted)]">Amount</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-[var(--fg-muted)]">Status</th>
                <th className="px-3 py-2 text-left text-xs font-medium text-[var(--fg-muted)]">Date</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_INVOICES.map((inv) => (
                <tr key={inv.id} className="border-b border-[var(--border-light)] hover:bg-[var(--bg-tertiary)]">
                  <td className="px-3 py-2 text-[var(--fg-primary)]">{inv.period}</td>
                  <td className="px-3 py-2 text-[var(--fg-secondary)]">${inv.amount}</td>
                  <td className="px-3 py-2">
                    <span
                      className={`badge ${
                        inv.status === 'paid'
                          ? 'badge-green'
                          : inv.status === 'pending'
                          ? 'badge-yellow'
                          : 'badge-red'
                      }`}
                    >
                      {inv.status}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-xs text-[var(--fg-muted)]">
                    {new Date(inv.created_at).toLocaleDateString()}
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
