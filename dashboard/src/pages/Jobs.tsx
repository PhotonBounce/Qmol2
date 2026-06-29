import { useState, useEffect, useCallback } from 'react';
import {
  List,
  Loader,
  CheckCircle,
  XCircle,
  Clock,
  Download,
  X,
  AlertCircle,
} from 'lucide-react';
import { useAuthStore } from '@/store/auth';
import { apiClient } from '@/api/client';
import type { Job, JobEvent } from '@/types/api';

export default function Jobs() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { apiKey } = useAuthStore();

  const fetchJobs = useCallback(async () => {
    if (!apiKey) return;
    try {
      const { data } = await apiClient.get<Job[]>('/jobs');
      setJobs(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch jobs');
    } finally {
      setLoading(false);
    }
  }, [apiKey]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  // SSE for real-time progress
  useEffect(() => {
    if (!apiKey) return;
    const eventSource = new EventSource(`${import.meta.env.VITE_API_URL || 'http://localhost:8000/v1'}/jobs/stream?api_key=${apiKey}`);
    eventSource.onmessage = (e) => {
      try {
        const event: JobEvent = JSON.parse(e.data);
        setJobs((prev) =>
          prev.map((j) =>
            j.job_id === event.job_id
              ? {
                  ...j,
                  status: event.status as Job['status'],
                  progress: event.progress,
                  processed: event.processed,
                  total: event.total,
                }
              : j
          )
        );
      } catch {
        /* ignore parse errors */
      }
    };
    eventSource.onerror = () => {
      eventSource.close();
    };
    return () => eventSource.close();
  }, [apiKey]);

  const handleCancel = async (jobId: string) => {
    try {
      await apiClient.post(`/jobs/${jobId}/cancel`);
      setJobs((prev) =>
        prev.map((j) => (j.job_id === jobId ? { ...j, status: 'cancelled' } : j))
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Cancel failed');
    }
  };

  const handleDownload = async (jobId: string) => {
    try {
      const { data, headers } = await apiClient.get<Blob>(`/jobs/${jobId}/result`, {
        responseType: 'blob',
      });
      const blob = new Blob([data], { type: headers['content-type'] || 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `job-${jobId}.jsonl`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Download failed');
    }
  };

  const statusIcon = (status: Job['status']) => {
    switch (status) {
      case 'pending':
        return <Clock size={16} className="text-amber-500" />;
      case 'running':
        return <Loader size={16} className="animate-spin text-[var(--accent)]" />;
      case 'completed':
        return <CheckCircle size={16} className="text-emerald-500" />;
      case 'failed':
        return <XCircle size={16} className="text-red-500" />;
      case 'cancelled':
        return <X size={16} className="text-[var(--fg-muted)]" />;
      default:
        return null;
    }
  };

  const statusBadge = (status: Job['status']) => {
    const classes: Record<string, string> = {
      pending: 'badge-yellow',
      running: 'badge-blue',
      completed: 'badge-green',
      failed: 'badge-red',
      cancelled: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
    };
    return <span className={`badge ${classes[status] || ''}`}>{status}</span>;
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--fg-primary)]">Jobs</h1>
          <p className="mt-1 text-sm text-[var(--fg-secondary)]">
            Monitor and manage compute jobs
          </p>
        </div>
        <button onClick={fetchJobs} className="btn btn-secondary">
          Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950/30 dark:text-red-400">
          <AlertCircle size={16} className="inline mr-1" />
          {error}
        </div>
      )}

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border)] bg-[var(--bg-tertiary)]">
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--fg-muted)]">Job ID</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--fg-muted)]">Status</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--fg-muted)]">Progress</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--fg-muted)]">Endpoint</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-[var(--fg-muted)]">Created</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-[var(--fg-muted)]">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-[var(--fg-muted)]">
                    <Loader size={20} className="mx-auto animate-spin mb-2" />
                    Loading jobs...
                  </td>
                </tr>
              ) : jobs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-[var(--fg-muted)]">
                    No jobs found. Submit a batch compute to create one.
                  </td>
                </tr>
              ) : (
                jobs.map((job) => (
                  <tr
                    key={job.job_id}
                    className="border-b border-[var(--border-light)] hover:bg-[var(--bg-tertiary)] transition-colors"
                  >
                    <td className="px-4 py-3 font-mono text-xs text-[var(--fg-secondary)]">
                      {job.job_id.slice(0, 12)}...
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {statusIcon(job.status)}
                        {statusBadge(job.status)}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="w-32">
                        <div className="h-1.5 overflow-hidden rounded-full bg-[var(--border)]">
                          <div
                            className={`h-full rounded-full transition-all ${
                              job.status === 'failed'
                                ? 'bg-red-500'
                                : job.status === 'completed'
                                ? 'bg-emerald-500'
                                : 'bg-[var(--accent)]'
                            }`}
                            style={{ width: `${job.progress}%` }}
                          />
                        </div>
                        <p className="mt-1 text-[10px] text-[var(--fg-muted)]">
                          {job.processed} / {job.total}
                        </p>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-[var(--fg-secondary)]">{job.endpoint}</td>
                    <td className="px-4 py-3 text-xs text-[var(--fg-muted)]">
                      {new Date(job.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        {job.status === 'running' && (
                          <button
                            onClick={() => handleCancel(job.job_id)}
                            className="rounded-md p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-950/30"
                            title="Cancel"
                          >
                            <X size={16} />
                          </button>
                        )}
                        {job.status === 'completed' && (
                          <button
                            onClick={() => handleDownload(job.job_id)}
                            className="rounded-md p-1.5 text-[var(--accent)] hover:bg-[var(--accent-50)]"
                            title="Download result"
                          >
                            <Download size={16} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
