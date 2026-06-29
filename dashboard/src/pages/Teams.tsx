import { useState } from 'react';
import { Users, Plus, Trash2, Shield, User, AlertCircle } from 'lucide-react';
import type { TeamMember } from '@/types/api';

// Mock team data for demonstration
const MOCK_MEMBERS: TeamMember[] = [
  { id: '1', email: 'admin@lab.edu', role: 'owner', used_this_month: 4500, joined_at: '2023-06-01' },
  { id: '2', email: 'researcher1@lab.edu', role: 'member', used_this_month: 1200, joined_at: '2023-09-15' },
  { id: '3', email: 'researcher2@lab.edu', role: 'member', used_this_month: 800, joined_at: '2024-01-10' },
  { id: '4', email: 'postdoc@lab.edu', role: 'admin', used_this_month: 2100, joined_at: '2023-11-20' },
];

export default function Teams() {
  const [members, setMembers] = useState<TeamMember[]>(MOCK_MEMBERS);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<'member' | 'admin'>('member');
  const [teamQuota, setTeamQuota] = useState(50000);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleInvite = () => {
    if (!inviteEmail.trim() || !inviteEmail.includes('@')) {
      setError('Enter a valid email address');
      return;
    }
    const newMember: TeamMember = {
      id: crypto.randomUUID(),
      email: inviteEmail.trim(),
      role: inviteRole,
      used_this_month: 0,
      joined_at: new Date().toISOString(),
    };
    setMembers([...members, newMember]);
    setInviteEmail('');
    setError(null);
    setSuccess(`Invited ${newMember.email}`);
    setTimeout(() => setSuccess(null), 3000);
  };

  const handleRemove = (id: string) => {
    if (!confirm('Remove this member from the team?')) return;
    setMembers(members.filter((m) => m.id !== id));
  };

  const totalUsed = members.reduce((sum, m) => sum + m.used_this_month, 0);
  const quotaPct = (totalUsed / teamQuota) * 100;

  const roleIcon = (role: TeamMember['role']) => {
    switch (role) {
      case 'owner':
        return <Shield size={14} className="text-amber-500" />;
      case 'admin':
        return <Shield size={14} className="text-[var(--accent)]" />;
      case 'member':
        return <User size={14} className="text-[var(--fg-muted)]" />;
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--fg-primary)]">Teams</h1>
        <p className="mt-1 text-sm text-[var(--fg-secondary)]">
          Manage team members and shared quota
        </p>
      </div>

      {/* Team quota */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Users size={18} className="text-[var(--accent)]" />
            <h2 className="text-sm font-semibold text-[var(--fg-primary)]">Team Quota</h2>
          </div>
          <span className="text-sm text-[var(--fg-muted)]">{members.length} members</span>
        </div>
        <div className="flex items-end justify-between mb-2">
          <div>
            <p className="text-3xl font-bold text-[var(--fg-primary)]">{totalUsed.toLocaleString()}</p>
            <p className="text-sm text-[var(--fg-muted)]">of {teamQuota.toLocaleString()} SMILES used</p>
          </div>
          <p className="text-2xl font-bold text-[var(--fg-primary)]">{Math.round(quotaPct)}%</p>
        </div>
        <div className="h-2.5 overflow-hidden rounded-full bg-[var(--bg-tertiary)]">
          <div
            className={`h-full rounded-full transition-all ${
              quotaPct > 90 ? 'bg-red-500' : quotaPct > 70 ? 'bg-amber-500' : 'bg-[var(--accent)]'
            }`}
            style={{ width: `${Math.min(100, quotaPct)}%` }}
          />
        </div>
        <div className="mt-4 flex items-center gap-3">
          <label className="text-sm text-[var(--fg-secondary)]">Quota limit:</label>
          <input
            type="number"
            value={teamQuota}
            onChange={(e) => setTeamQuota(Number(e.target.value))}
            className="input w-32 text-sm"
            min={1000}
            step={1000}
          />
          <span className="text-xs text-[var(--fg-muted)]">SMILES / month</span>
        </div>
      </div>

      {/* Invite form */}
      <div className="card p-5">
        <h2 className="text-sm font-semibold text-[var(--fg-primary)] mb-4">Invite Member</h2>
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            type="email"
            value={inviteEmail}
            onChange={(e) => setInviteEmail(e.target.value)}
            placeholder="colleague@lab.edu"
            className="input flex-1"
            onKeyDown={(e) => e.key === 'Enter' && handleInvite()}
          />
          <select
            value={inviteRole}
            onChange={(e) => setInviteRole(e.target.value as 'member' | 'admin')}
            className="input w-32"
          >
            <option value="member">Member</option>
            <option value="admin">Admin</option>
          </select>
          <button onClick={handleInvite} className="btn btn-primary">
            <Plus size={16} />
            Invite
          </button>
        </div>
        {error && (
          <div className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950/30 dark:text-red-400">
            <AlertCircle size={16} className="inline mr-1" />
            {error}
          </div>
        )}
        {success && (
          <div className="mt-3 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-600 dark:bg-emerald-950/30 dark:text-emerald-400">
            {success}
          </div>
        )}
      </div>

      {/* Members table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] bg-[var(--bg-tertiary)]">
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--fg-muted)]">Member</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--fg-muted)]">Role</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--fg-muted)]">Used This Month</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--fg-muted)]">Joined</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[var(--fg-muted)]">Actions</th>
              </tr>
            </thead>
            <tbody>
              {members.map((member) => (
                <tr
                  key={member.id}
                  className="border-b border-[var(--border-light)] hover:bg-[var(--bg-tertiary)] transition-colors"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--accent-50)] text-[var(--accent)] font-medium text-xs">
                        {member.email[0].toUpperCase()}
                      </div>
                      <span className="text-[var(--fg-primary)]">{member.email}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1.5">
                      {roleIcon(member.role)}
                      <span className="capitalize text-[var(--fg-secondary)]">{member.role}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="w-32">
                      <div className="h-1.5 overflow-hidden rounded-full bg-[var(--border)]">
                        <div
                          className="h-full rounded-full bg-[var(--accent)]"
                          style={{
                            width: `${Math.min(100, (member.used_this_month / teamQuota) * 100)}%`,
                          }}
                        />
                      </div>
                      <p className="mt-1 text-[10px] text-[var(--fg-muted)]">
                        {member.used_this_month.toLocaleString()}
                      </p>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-[var(--fg-muted)]">
                    {new Date(member.joined_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    {member.role !== 'owner' && (
                      <button
                        onClick={() => handleRemove(member.id)}
                        className="rounded-md p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30"
                        title="Remove member"
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
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
