import React, { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import api from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../components/Toast'
import AdminLayout from './AdminLayout'
import Skeleton from './Skeleton'
import { Users, Cpu, Briefcase, CreditCard, Shield, Ban, Play, AlertCircle } from 'lucide-react'

const TABS = [
  { key: 'overview', label: 'Overview', icon: Shield },
  { key: 'workers', label: 'Workers', icon: Cpu },
  { key: 'jobs', label: 'Jobs', icon: Briefcase },
  { key: 'users', label: 'Users', icon: Users },
]

const WORKER_STATUS_STYLES = {
  online: 'bg-green-50 text-green-700 ring-green-600/20',
  offline: 'bg-slate-50 text-slate-700 ring-slate-600/20',
  busy: 'bg-amber-50 text-amber-700 ring-amber-600/20',
  banned: 'bg-red-50 text-red-700 ring-red-600/20',
}

const JOB_STATUS_STYLES = {
  pending: 'bg-blue-50 text-blue-700 ring-blue-600/20',
  assigned: 'bg-amber-50 text-amber-700 ring-amber-600/20',
  running: 'bg-amber-50 text-amber-700 ring-amber-600/20',
  completed: 'bg-green-50 text-green-700 ring-green-600/20',
  failed: 'bg-red-50 text-red-700 ring-red-600/20',
  validating: 'bg-purple-50 text-purple-700 ring-purple-600/20',
}

function StatusBadge({ status, styles }) {
  const cls = styles[status] || styles.pending || 'bg-slate-50 text-slate-700'
  return <span className={`badge ${cls}`}>{status}</span>
}

function StatCard({ title, value, icon: Icon, colorClass }) {
  return (
    <div className="card flex items-center gap-4">
      <div className={`flex h-12 w-12 items-center justify-center rounded-lg ${colorClass}`}>
        <Icon className="h-6 w-6 text-white" />
      </div>
      <div>
        <p className="text-sm font-medium text-slate-500">{title}</p>
        <p className="text-2xl font-bold text-slate-900">{value}</p>
      </div>
    </div>
  )
}

export default function AdminPage() {
  const { user } = useAuth()
  const { addToast } = useToast()
  const navigate = useNavigate()
  const location = useLocation()

  // Parse tab from URL path
  const pathTab = location.pathname.split('/')[2] || 'overview'
  const activeTab = TABS.some(t => t.key === pathTab) ? pathTab : 'overview'

  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState({ total_users: 0, total_workers: 0, total_jobs: 0, total_credits_in_circulation: 0 })
  const [workers, setWorkers] = useState([])
  const [jobs, setJobs] = useState([])
  const [users, setUsers] = useState([])
  const [workerPage, setWorkerPage] = useState(1)
  const [jobPage, setJobPage] = useState(1)
  const [userPage, setUserPage] = useState(1)
  const [totalWorkers, setTotalWorkers] = useState(0)
  const [totalJobs, setTotalJobs] = useState(0)
  const [totalUsers, setTotalUsers] = useState(0)

  const pageSize = 10

  // Guard: redirect non-admins
  useEffect(() => {
    if (user && user.role !== 'admin') {
      navigate('/')
      addToast('Admin access required', 'error')
    }
  }, [user, navigate, addToast])

  const fetchStats = async () => {
    try {
      const res = await api.get('/admin/stats')
      setStats(res.data)
    } catch (err) {
      addToast(err.message, 'error')
    }
  }

  const fetchWorkers = async () => {
    try {
      const res = await api.get('/admin/workers', { params: { skip: (workerPage - 1) * pageSize, limit: pageSize } })
      setWorkers(res.data.items || [])
      setTotalWorkers(res.data.total || 0)
    } catch (err) {
      addToast(err.message, 'error')
    }
  }

  const fetchJobs = async () => {
    try {
      const res = await api.get('/admin/jobs', { params: { skip: (jobPage - 1) * pageSize, limit: pageSize } })
      setJobs(res.data.items || [])
      setTotalJobs(res.data.total || 0)
    } catch (err) {
      addToast(err.message, 'error')
    }
  }

  const fetchUsers = async () => {
    try {
      const res = await api.get('/admin/users', { params: { skip: (userPage - 1) * pageSize, limit: pageSize } })
      setUsers(res.data.items || [])
      setTotalUsers(res.data.total || 0)
    } catch (err) {
      addToast(err.message, 'error')
    }
  }

  useEffect(() => {
    if (!user || user.role !== 'admin') return
    let isMounted = true
    const run = async () => {
      setLoading(true)
      if (isMounted) await fetchStats()
      if (isMounted) await fetchWorkers()
      if (isMounted) await fetchJobs()
      if (isMounted) await fetchUsers()
      if (isMounted) setLoading(false)
    }
    run()
    return () => { isMounted = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, workerPage, jobPage, userPage])

  const handleBan = async (workerId, action) => {
    try {
      const res = await api.post(`/admin/workers/${workerId}/${action}`)
      addToast(`Worker ${action}ned. Status: ${res.data.status}`, 'success')
      fetchWorkers()
      fetchStats()
    } catch (err) {
      addToast(err.message, 'error')
    }
  }

  const totalWorkerPages = Math.max(1, Math.ceil(totalWorkers / pageSize))
  const totalJobPages = Math.max(1, Math.ceil(totalJobs / pageSize))
  const totalUserPages = Math.max(1, Math.ceil(totalUsers / pageSize))

  const setTab = (key) => {
    navigate(`/admin${key === 'overview' ? '' : `/${key}`}`)
  }

  if (!user || user.role !== 'admin') {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-swarm-indigo-600 border-t-transparent" />
      </div>
    )
  }

  return (
    <AdminLayout>
      <div className="mx-auto max-w-6xl space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Admin Dashboard</h1>
            <p className="text-sm text-slate-500">Manage the ComputeSwarm platform.</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 border-b border-slate-200 pb-1">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setTab(tab.key)}
              className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition-colors rounded-t-lg ${
                activeTab === tab.key
                  ? 'border-b-2 border-swarm-indigo-600 text-swarm-indigo-700'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {loading && activeTab === 'overview' && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Skeleton variant="card" />
            <Skeleton variant="card" />
            <Skeleton variant="card" />
            <Skeleton variant="card" />
          </div>
        )}

        {/* Overview Tab */}
        {activeTab === 'overview' && !loading && (
          <div className="space-y-6">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard title="Total Users" value={stats.total_users} icon={Users} colorClass="bg-blue-600" />
              <StatCard title="Total Workers" value={stats.total_workers} icon={Cpu} colorClass="bg-swarm-indigo-600" />
              <StatCard title="Total Jobs" value={stats.total_jobs} icon={Briefcase} colorClass="bg-amber-600" />
              <StatCard title="Credits in Circulation" value={stats.total_credits_in_circulation.toFixed(2)} icon={CreditCard} colorClass="bg-green-600" />
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              <div className="card">
                <h2 className="mb-4 text-lg font-semibold text-slate-900">Workers Overview</h2>
                {workers.length === 0 ? (
                  <p className="text-sm text-slate-400">No workers found.</p>
                ) : (
                  <div className="space-y-3">
                    {workers.slice(0, 5).map((w) => (
                      <div key={w.id} className="flex items-center justify-between rounded-lg border border-slate-200 p-3">
                        <div>
                          <p className="text-sm font-medium text-slate-900">{w.name}</p>
                          <p className="text-xs text-slate-500">Reputation: {w.reputation_score.toFixed(2)}</p>
                        </div>
                        <StatusBadge status={w.status} styles={WORKER_STATUS_STYLES} />
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="card">
                <h2 className="mb-4 text-lg font-semibold text-slate-900">Recent Jobs</h2>
                {jobs.length === 0 ? (
                  <p className="text-sm text-slate-400">No jobs found.</p>
                ) : (
                  <div className="space-y-3">
                    {jobs.slice(0, 5).map((j) => (
                      <div key={j.id} className="flex items-center justify-between rounded-lg border border-slate-200 p-3">
                        <div>
                          <p className="text-sm font-medium text-slate-900">{j.name}</p>
                          <p className="text-xs text-slate-500">Owner: {j.user_id?.slice(0, 8)}…</p>
                        </div>
                        <StatusBadge status={j.status} styles={JOB_STATUS_STYLES} />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Workers Tab */}
        {activeTab === 'workers' && (
          <div className="card overflow-hidden">
            <h2 className="mb-4 text-lg font-semibold text-slate-900">All Workers</h2>
            {loading ? (
              <Skeleton variant="table" rows={5} cols={6} />
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="bg-slate-50 text-slate-600">
                    <tr>
                      <th className="px-4 py-3 font-semibold">Name</th>
                      <th className="px-4 py-3 font-semibold">Status</th>
                      <th className="px-4 py-3 font-semibold">Reputation</th>
                      <th className="px-4 py-3 font-semibold">Last Heartbeat</th>
                      <th className="px-4 py-3 font-semibold">Credits Earned</th>
                      <th className="px-4 py-3 font-semibold">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {workers.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-4 py-8 text-center text-slate-400">No workers found.</td>
                      </tr>
                    ) : (
                      workers.map((w) => (
                        <tr key={w.id} className="hover:bg-slate-50">
                          <td className="px-4 py-3 font-medium text-slate-900">{w.name}</td>
                          <td className="px-4 py-3"><StatusBadge status={w.status} styles={WORKER_STATUS_STYLES} /></td>
                          <td className="px-4 py-3 text-slate-700">{w.reputation_score?.toFixed(2)}</td>
                          <td className="px-4 py-3 text-slate-500">
                            {w.last_heartbeat ? new Date(w.last_heartbeat).toLocaleString() : '—'}
                          </td>
                          <td className="px-4 py-3 text-slate-700">{w.total_credits_earned?.toFixed(2)}</td>
                          <td className="px-4 py-3">
                            {w.status === 'banned' ? (
                              <button
                                onClick={() => handleBan(w.id, 'unban')}
                                className="inline-flex items-center gap-1 rounded-md bg-green-50 px-2 py-1 text-xs font-medium text-green-700 hover:bg-green-100"
                              >
                                <Play className="h-3 w-3" /> Unban
                              </button>
                            ) : (
                              <button
                                onClick={() => handleBan(w.id, 'ban')}
                                className="inline-flex items-center gap-1 rounded-md bg-red-50 px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-100"
                              >
                                <Ban className="h-3 w-3" /> Ban
                              </button>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}
            <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3">
              <span className="text-sm text-slate-500">Page {workerPage} of {totalWorkerPages}</span>
              <div className="flex gap-2">
                <button onClick={() => setWorkerPage(p => Math.max(1, p - 1))} disabled={workerPage === 1} className="btn-secondary disabled:opacity-40">Prev</button>
                <button onClick={() => setWorkerPage(p => Math.min(totalWorkerPages, p + 1))} disabled={workerPage === totalWorkerPages} className="btn-secondary disabled:opacity-40">Next</button>
              </div>
            </div>
          </div>
        )}

        {/* Jobs Tab */}
        {activeTab === 'jobs' && (
          <div className="card overflow-hidden">
            <h2 className="mb-4 text-lg font-semibold text-slate-900">All Jobs</h2>
            {loading ? (
              <Skeleton variant="table" rows={5} cols={5} />
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="bg-slate-50 text-slate-600">
                    <tr>
                      <th className="px-4 py-3 font-semibold">Name</th>
                      <th className="px-4 py-3 font-semibold">Status</th>
                      <th className="px-4 py-3 font-semibold">Owner</th>
                      <th className="px-4 py-3 font-semibold">Work Units</th>
                      <th className="px-4 py-3 font-semibold">Created</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {jobs.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-4 py-8 text-center text-slate-400">No jobs found.</td>
                      </tr>
                    ) : (
                      jobs.map((j) => (
                        <tr key={j.id} className="hover:bg-slate-50">
                          <td className="px-4 py-3 font-medium text-slate-900">{j.name}</td>
                          <td className="px-4 py-3"><StatusBadge status={j.status} styles={JOB_STATUS_STYLES} /></td>
                          <td className="px-4 py-3 text-slate-700 font-mono text-xs">{j.user_id?.slice(0, 8)}…</td>
                          <td className="px-4 py-3 text-slate-700">{j.work_unit_count}</td>
                          <td className="px-4 py-3 text-slate-500">{j.created_at ? new Date(j.created_at).toLocaleString() : '—'}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}
            <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3">
              <span className="text-sm text-slate-500">Page {jobPage} of {totalJobPages}</span>
              <div className="flex gap-2">
                <button onClick={() => setJobPage(p => Math.max(1, p - 1))} disabled={jobPage === 1} className="btn-secondary disabled:opacity-40">Prev</button>
                <button onClick={() => setJobPage(p => Math.min(totalJobPages, p + 1))} disabled={jobPage === totalJobPages} className="btn-secondary disabled:opacity-40">Next</button>
              </div>
            </div>
          </div>
        )}

        {/* Users Tab */}
        {activeTab === 'users' && (
          <div className="card overflow-hidden">
            <h2 className="mb-4 text-lg font-semibold text-slate-900">All Users</h2>
            {loading ? (
              <Skeleton variant="table" rows={5} cols={5} />
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="bg-slate-50 text-slate-600">
                    <tr>
                      <th className="px-4 py-3 font-semibold">Email</th>
                      <th className="px-4 py-3 font-semibold">Role</th>
                      <th className="px-4 py-3 font-semibold">Credits</th>
                      <th className="px-4 py-3 font-semibold">Total Spent</th>
                      <th className="px-4 py-3 font-semibold">Created</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {users.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-4 py-8 text-center text-slate-400">No users found.</td>
                      </tr>
                    ) : (
                      users.map((u) => (
                        <tr key={u.id} className="hover:bg-slate-50">
                          <td className="px-4 py-3 font-medium text-slate-900">{u.email}</td>
                          <td className="px-4 py-3">
                            <span className={`badge ${u.role === 'admin' ? 'bg-purple-50 text-purple-700 ring-purple-600/20' : 'bg-blue-50 text-blue-700 ring-blue-600/20'}`}>
                              {u.role}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-slate-700">{u.credits_balance?.toFixed(2)}</td>
                          <td className="px-4 py-3 text-slate-700">{u.total_credits_spent?.toFixed(2)}</td>
                          <td className="px-4 py-3 text-slate-500">{u.created_at ? new Date(u.created_at).toLocaleString() : '—'}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}
            <div className="flex items-center justify-between border-t border-slate-200 px-4 py-3">
              <span className="text-sm text-slate-500">Page {userPage} of {totalUserPages}</span>
              <div className="flex gap-2">
                <button onClick={() => setUserPage(p => Math.max(1, p - 1))} disabled={userPage === 1} className="btn-secondary disabled:opacity-40">Prev</button>
                <button onClick={() => setUserPage(p => Math.min(totalUserPages, p + 1))} disabled={userPage === totalUserPages} className="btn-secondary disabled:opacity-40">Next</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AdminLayout>
  )
}
