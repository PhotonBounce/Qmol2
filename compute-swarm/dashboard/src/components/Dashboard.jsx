import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { format, subDays, startOfDay } from 'date-fns'
import api from '../api/client'
import { useToast } from '../components/Toast'
import Skeleton from '../components/Skeleton'
import { Briefcase, CheckCircle, CreditCard, Users, PlusCircle, AlertCircle } from 'lucide-react'

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

export default function Dashboard() {
  const navigate = useNavigate()
  const { addToast } = useToast()
  const [stats, setStats] = useState({
    activeJobs: 0,
    completedJobs: 0,
    totalCreditsSpent: 0,
    totalWorkersOnline: 0,
  })
  const [recentJobs, setRecentJobs] = useState([])
  const [chartData, setChartData] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let isMounted = true
    const fetchDashboard = async () => {
      setLoading(true)
      try {
        const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString()
        const jobsRes = await api.get('/jobs', { params: { limit: 50, created_after: sevenDaysAgo } })
        const jobs = jobsRes.data.items || []

        const active = jobs.filter((j) => ['pending', 'assigned', 'running'].includes(j.status)).length
        const completed = jobs.filter((j) => j.status === 'completed' || j.status === 'validating').length
        const creditsSpent = jobs.reduce((sum, j) => {
          const units = j.work_units?.length || j.work_unit_count || 0
          return sum + units * (j.reward_per_unit || 0)
        }, 0)

        if (isMounted) {
          setStats({
            activeJobs: active,
            completedJobs: completed,
            totalCreditsSpent: creditsSpent.toFixed(2),
            totalWorkersOnline: 0,
          })
          setRecentJobs(jobs.slice(0, 5))
        }

        const last7 = Array.from({ length: 7 }, (_, i) => {
          const day = startOfDay(subDays(new Date(), 6 - i))
          const dayStr = format(day, 'yyyy-MM-dd')
          const count = jobs.filter((j) => {
            if (!j.created_at) return false
            const d = format(new Date(j.created_at), 'yyyy-MM-dd')
            return d === dayStr && (j.status === 'completed' || j.status === 'validated')
          }).length
          return { date: format(day, 'MMM dd'), count }
        })
        if (isMounted) setChartData(last7)

        try {
          const workersRes = await api.get('/workers')
          const workers = workersRes.data.items || []
          if (isMounted) {
            setStats((s) => ({ ...s, totalWorkersOnline: workers.filter((w) => w.status === 'online').length }))
          }
        } catch {
          // Workers endpoint may not be exposed to researchers; ignore error
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

    fetchDashboard()
    return () => { isMounted = false }
  }, [addToast])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
          <p className="text-sm text-slate-500">Overview of your ComputeSwarm activity.</p>
        </div>
        <button onClick={() => navigate('/jobs/new')} className="btn-primary">
          <PlusCircle className="mr-2 h-4 w-4" /> Submit New Job
        </button>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Skeleton variant="card" />
          <Skeleton variant="card" />
          <Skeleton variant="card" />
          <Skeleton variant="card" />
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard title="Active Jobs" value={stats.activeJobs} icon={Briefcase} colorClass="bg-blue-600" />
          <StatCard title="Completed Jobs" value={stats.completedJobs} icon={CheckCircle} colorClass="bg-green-600" />
          <StatCard title="Credits Spent" value={stats.totalCreditsSpent} icon={CreditCard} colorClass="bg-amber-600" />
          <StatCard title="Workers Online" value={stats.totalWorkersOnline} icon={Users} colorClass="bg-swarm-indigo-600" />
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="card lg:col-span-2">
          <h2 className="mb-4 text-lg font-semibold text-slate-900">Jobs Completed (Last 7 Days)</h2>
          <div className="h-72">
            {loading ? (
              <Skeleton variant="chart" />
            ) : chartData.length === 0 ? (
              <div className="flex h-full items-center justify-center text-sm text-slate-400">
                No data available
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#94a3b8" />
                  <YAxis allowDecimals={false} tick={{ fontSize: 12 }} stroke="#94a3b8" />
                  <Tooltip />
                  <Line type="monotone" dataKey="count" stroke="#4f46e5" strokeWidth={2} dot={{ r: 4, fill: '#4f46e5' }} activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="card">
          <h2 className="mb-4 text-lg font-semibold text-slate-900">Recent Jobs</h2>
          <div className="space-y-3">
            {loading && recentJobs.length === 0 ? (
              <div className="space-y-3">
                <Skeleton variant="card" />
                <Skeleton variant="card" />
                <Skeleton variant="card" />
              </div>
            ) : recentJobs.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-400">No jobs yet.</p>
            ) : (
              recentJobs.map((job) => (
                <button
                  key={job.id}
                  onClick={() => navigate(`/jobs/${job.id}`)}
                  className="w-full rounded-lg border border-slate-200 p-3 text-left hover:border-swarm-indigo-300 hover:bg-swarm-indigo-50 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium text-slate-900 truncate">{job.name}</p>
                    <span className={`inline-flex rounded-md px-2 py-0.5 text-xs font-medium ${
                      job.status === 'completed' || job.status === 'validated' ? 'bg-green-50 text-green-700' :
                      job.status === 'failed' ? 'bg-red-50 text-red-700' :
                      job.status === 'running' || job.status === 'assigned' ? 'bg-amber-50 text-amber-700' :
                      'bg-blue-50 text-blue-700'
                    }`}>
                      {job.status}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">{job.docker_image}</p>
                </button>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
