import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { format } from 'date-fns'
import api from '../api/client'
import { useToast } from '../components/Toast'
import Skeleton from '../components/Skeleton'
import { AlertCircle, ChevronLeft, ChevronRight, Briefcase } from 'lucide-react'

const STATUS_STYLES = {
  pending:   'bg-blue-50 text-blue-700 ring-blue-600/20',
  assigned:  'bg-amber-50 text-amber-700 ring-amber-600/20',
  running:   'bg-amber-50 text-amber-700 ring-amber-600/20',
  completed: 'bg-green-50 text-green-700 ring-green-600/20',
  failed:    'bg-red-50 text-red-700 ring-red-600/20',
  validating:'bg-purple-50 text-purple-700 ring-purple-600/20',
}

function StatusBadge({ status }) {
  const cls = STATUS_STYLES[status] || STATUS_STYLES.pending
  return <span className={`badge ${cls}`}>{status}</span>
}

function ProgressBar({ completed, total }) {
  if (!total) return null
  const pct = Math.round((completed / total) * 100)
  return (
    <div className="w-full">
      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
        <div className="h-full rounded-full bg-swarm-indigo-600 transition-all" style={{ width: `${pct}%` }} />
      </div>
      <p className="mt-1 text-xs text-slate-500">{completed}/{total} units ({pct}%)</p>
    </div>
  )
}

export default function JobList() {
  const [jobs, setJobs] = useState([])
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const { addToast } = useToast()

  useEffect(() => {
    let isMounted = true
    const runFetch = async () => {
      setLoading(true)
      setError('')
      try {
        const res = await api.get('/jobs', { params: { skip: (page - 1) * 10, limit: 10 } })
        if (isMounted) {
          setJobs(res.data.items || [])
          setTotalPages(res.data.total_pages || 1)
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message)
          addToast(err.message, 'error')
        }
      } finally {
        if (isMounted) setLoading(false)
      }
    }
    runFetch()
    return () => { isMounted = false }
  }, [page, addToast])

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Jobs</h1>
          <p className="text-sm text-slate-500">Monitor and manage your compute jobs.</p>
        </div>
        <button onClick={() => navigate('/jobs/new')} className="btn-primary">
          <Briefcase className="mr-2 h-4 w-4" /> New Job
        </button>
      </div>

      <div className="card overflow-hidden">
        {error && (
          <div className="mb-4 flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="px-6 py-3 font-semibold">Name</th>
                <th className="px-6 py-3 font-semibold">Status</th>
                <th className="px-6 py-3 font-semibold">Created</th>
                <th className="px-6 py-3 font-semibold">Progress</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {loading && jobs.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-8">
                    <Skeleton variant="table" rows={5} cols={4} />
                  </td>
                </tr>
              ) : jobs.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-8 text-center text-slate-400">No jobs yet. Submit your first job to get started.</td>
                </tr>
              ) : (
                jobs.map((job) => (
                  <tr
                    key={job.id}
                    onClick={() => navigate(`/jobs/${job.id}`)}
                    className="cursor-pointer hover:bg-slate-50 transition-colors"
                  >
                    <td className="px-6 py-4 font-medium text-slate-900">{job.name}</td>
                    <td className="px-6 py-4"><StatusBadge status={job.status} /></td>
                    <td className="px-6 py-4 text-slate-500">
                      {job.created_at ? format(new Date(job.created_at), 'MMM d, yyyy HH:mm') : '—'}
                    </td>
                    <td className="px-6 py-4">
                      <ProgressBar
                        completed={job.work_units?.filter((u) => u.status === 'completed' || u.status === 'validated').length || 0}
                        total={job.work_units?.length || job.work_unit_count || 0}
                      />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between border-t border-slate-200 px-6 py-4">
          <span className="text-sm text-slate-500">Page {page} of {totalPages}</span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="btn-secondary disabled:opacity-40"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="btn-secondary disabled:opacity-40"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
