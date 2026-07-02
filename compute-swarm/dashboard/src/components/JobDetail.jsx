import React, { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { format } from 'date-fns'
import api from '../api/client'
import { useToast } from '../components/Toast'
import Skeleton from '../components/Skeleton'
import { AlertCircle, Download, XCircle, Loader2 } from 'lucide-react'

const STATUS_COLORS = {
  pending: '#3b82f6',
  assigned: '#f59e0b',
  running: '#f59e0b',
  completed: '#22c55e',
  failed: '#ef4444',
  validated: '#22c55e',
}

const STATUS_BADGE = {
  pending: 'bg-blue-50 text-blue-700 ring-blue-600/20',
  assigned: 'bg-amber-50 text-amber-700 ring-amber-600/20',
  running: 'bg-amber-50 text-amber-700 ring-amber-600/20',
  completed: 'bg-green-50 text-green-700 ring-green-600/20',
  failed: 'bg-red-50 text-red-700 ring-red-600/20',
  validated: 'bg-green-50 text-green-700 ring-green-600/20',
}

function StatusBadge({ status }) {
  const cls = STATUS_BADGE[status] || STATUS_BADGE.pending
  return <span className={`badge ${cls}`}>{status}</span>
}

export default function JobDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { addToast } = useToast()
  const [job, setJob] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [cancelLoading, setCancelLoading] = useState(false)
  const [downloadLoading, setDownloadLoading] = useState(false)
  const [pollFailures, setPollFailures] = useState(0)

  const fetchJob = useCallback(async (silent = false) => {
    try {
      const res = await api.get(`/jobs/${id}`)
      setJob(res.data)
      if (!silent) setError('')
      setPollFailures(0)
    } catch (err) {
      if (!silent) setError(err.message)
      if (silent) setPollFailures((prev) => prev + 1)
    }
  }, [id])

  useEffect(() => {
    let isMounted = true
    setLoading(true)
    fetchJob(false).finally(() => {
      if (isMounted) setLoading(false)
    })
    return () => { isMounted = false }
  }, [fetchJob])

  useEffect(() => {
    if (job && ['completed', 'failed', 'validated'].includes(job.status)) {
      return
    }
    const interval = setInterval(() => {
      fetchJob(true)
    }, 5000)
    return () => clearInterval(interval)
  }, [fetchJob, job])

  const handleCancel = async () => {
    if (!window.confirm('Are you sure you want to cancel this job?')) return
    setCancelLoading(true)
    try {
      await api.post(`/jobs/${id}/cancel`)
      addToast('Job cancelled successfully', 'success')
      fetchJob()
    } catch (err) {
      setError(err.message)
      addToast(err.message, 'error')
    } finally {
      setCancelLoading(false)
    }
  }

  const handleDownload = async () => {
    setDownloadLoading(true)
    try {
      const res = await api.get(`/jobs/${id}/results`)
      const { download_url } = res.data
      if (download_url) {
        window.open(download_url, '_blank')
      } else {
        throw new Error('No download URL available')
      }
    } catch (err) {
      setError(err.message || 'Download failed')
      addToast(err.message || 'Download failed', 'error')
    } finally {
      setDownloadLoading(false)
    }
  }

  if (loading && !job) {
    return (
      <div className="mx-auto max-w-5xl space-y-6">
        <Skeleton variant="card" />
        <div className="grid gap-6 md:grid-cols-3">
          <div className="md:col-span-2"><Skeleton variant="card" /></div>
          <div><Skeleton variant="card" /></div>
        </div>
        <Skeleton variant="table" rows={4} cols={5} />
      </div>
    )
  }

  if (!job) {
    return (
      <div className="card text-center py-12">
        <p className="text-slate-500">Job not found.</p>
        <button onClick={() => navigate('/jobs')} className="btn-primary mt-4">Back to Jobs</button>
      </div>
    )
  }

  const units = job.work_units || []
  const total = units.length || job.work_unit_count || 0
  const completed = units.filter((u) => u.status === 'completed' || u.status === 'validated').length
  const failed = units.filter((u) => u.status === 'failed').length
  const running = units.filter((u) => u.status === 'running' || u.status === 'assigned').length
  const pending = units.filter((u) => u.status === 'pending').length

  const chartData = [
    { name: 'Completed', value: completed, color: '#22c55e' },
    { name: 'Running', value: running, color: '#f59e0b' },
    { name: 'Pending', value: pending, color: '#3b82f6' },
    { name: 'Failed', value: failed, color: '#ef4444' },
  ].filter((d) => d.value > 0)

  const progressPct = total ? Math.round((completed / total) * 100) : 0

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{job.name}</h1>
          <p className="text-sm text-slate-500">ID: {job.id}</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={handleDownload} disabled={downloadLoading} className="btn-secondary">
            <Download className="mr-2 h-4 w-4" />
            {downloadLoading ? 'Getting link…' : 'Download Results'}
          </button>
          {['pending', 'assigned', 'running'].includes(job.status) && (
            <button onClick={handleCancel} disabled={cancelLoading} className="btn-danger">
              <XCircle className="mr-2 h-4 w-4" />
              {cancelLoading ? 'Cancelling…' : 'Cancel Job'}
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {pollFailures >= 3 && (
        <div className="flex items-center gap-2 rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
          <AlertCircle className="h-4 w-4 shrink-0" />
          Connection lost. Updates may be delayed. Retrying…
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-3">
        <div className="card md:col-span-2">
          <h2 className="mb-4 text-lg font-semibold text-slate-900">Job Details</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase">Status</p>
              <div className="mt-1"><StatusBadge status={job.status} /></div>
            </div>
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase">Docker Image</p>
              <p className="mt-1 text-sm font-medium text-slate-900">{job.docker_image}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase">Command</p>
              <p className="mt-1 text-sm font-medium text-slate-900 font-mono">{job.command || '—'}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase">Reward per Unit</p>
              <p className="mt-1 text-sm font-medium text-slate-900">{job.reward_per_unit} credits</p>
            </div>
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase">Created</p>
              <p className="mt-1 text-sm text-slate-700">{job.created_at ? format(new Date(job.created_at), 'PPP p') : '—'}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-slate-500 uppercase">Updated</p>
              <p className="mt-1 text-sm text-slate-700">{job.updated_at ? format(new Date(job.updated_at), 'PPP p') : '—'}</p>
            </div>
          </div>

          <div className="mt-6">
            <p className="text-xs font-medium text-slate-500 uppercase mb-2">Overall Progress</p>
            <div className="h-3 w-full overflow-hidden rounded-full bg-slate-200">
              <div className="h-full rounded-full bg-swarm-indigo-600 transition-all" style={{ width: `${progressPct}%` }} />
            </div>
            <p className="mt-1 text-sm text-slate-500">{completed}/{total} units completed ({progressPct}%)</p>
          </div>
        </div>

        <div className="card flex flex-col">
          <h2 className="mb-4 text-lg font-semibold text-slate-900">Unit Status</h2>
          <div className="flex-1 min-h-[200px]">
            {chartData.length === 0 ? (
              <div className="flex h-full items-center justify-center text-sm text-slate-400">
                No data available
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={chartData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius="80%">
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
          <div className="mt-4 space-y-1">
            {chartData.map((d) => (
              <div key={d.name} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-full" style={{ backgroundColor: d.color }} />
                  <span className="text-slate-600">{d.name}</span>
                </div>
                <span className="font-medium text-slate-900">{d.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card">
        <h2 className="mb-4 text-lg font-semibold text-slate-900">Work Units</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="px-4 py-3 font-semibold">Unit #</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3 font-semibold">Assigned Worker</th>
                <th className="px-4 py-3 font-semibold">Result URL</th>
                <th className="px-4 py-3 font-semibold">Checksum</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {units.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-slate-400">No work units available.</td>
                </tr>
              ) : (
                units.map((unit, idx) => (
                  <tr key={unit.id || idx} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-900">{unit.unit_index ?? idx}</td>
                    <td className="px-4 py-3"><StatusBadge status={unit.status} /></td>
                    <td className="px-4 py-3 text-slate-700">{unit.assigned_worker_id ? unit.assigned_worker_id.slice(0, 8) + '…' : '—'}</td>
                    <td className="px-4 py-3">
                      {unit.result_artifact_url ? (
                        <a href={unit.result_artifact_url} target="_blank" rel="noreferrer" className="text-swarm-indigo-600 hover:underline">View</a>
                      ) : '—'}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-600">
                      {unit.result_checksum ? unit.result_checksum.slice(0, 16) + '…' : '—'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
