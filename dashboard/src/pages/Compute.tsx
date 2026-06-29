import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  Calculator,
  FileDown,
  Upload,
  Play,
  AlertCircle,
  CheckCircle,
  Loader,
} from 'lucide-react';
import { useAuthStore } from '@/store/auth';
import { apiClient } from '@/api/client';
import type { Job } from '@/types/api';

const ENDPOINTS = [
  { value: 'compute', label: 'Compute descriptors', charge: 'free' },
  { value: 'descriptors', label: 'Full descriptors (217+)', charge: '2/mol' },
  { value: 'predict', label: 'ADMET predict', charge: '3/mol' },
  { value: 'screen', label: 'Drug-likeness screen', charge: '5/mol' },
  { value: 'formula', label: 'Formula & mass', charge: '1/mol' },
  { value: 'convert', label: 'Convert / standardize', charge: '1/mol' },
];

const FORMATS = ['csv', 'json', 'parquet'] as const;
type ExportFormat = typeof FORMATS[number];

export default function Compute() {
  const [input, setInput] = useState('');
  const [endpoint, setEndpoint] = useState('compute');
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<Record<string, unknown>[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exportFormat, setExportFormat] = useState<ExportFormat>('csv');
  const { apiKey } = useAuthStore();

  const parseSmiles = (text: string): string[] => {
    return text
      .split(/\r?\n/)
      .map((s) => s.trim())
      .filter((s) => s.length > 0 && !s.startsWith('#'));
  };

  const handleSubmit = async () => {
    const smiles = parseSmiles(input);
    if (smiles.length === 0) {
      setError('Enter at least one SMILES string');
      return;
    }
    if (!apiKey) {
      setError('API key required. Add it in Settings.');
      return;
    }
    setLoading(true);
    setError(null);
    setResults(null);
    setJob(null);

    try {
      // For small batches, call directly; for large batches, use jobs
      if (smiles.length <= 50) {
        const { data } = await apiClient.post<Record<string, unknown>[]>(`/${endpoint}`, { smiles });
        setResults(data);
      } else {
        const { data } = await apiClient.post<Job>('/jobs', {
          smiles,
          endpoint: `/${endpoint}`,
        });
        setJob(data);
        // Poll for progress
        pollJob(data.job_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed');
    } finally {
      setLoading(false);
    }
  };

  const pollJob = async (jobId: string) => {
    const interval = setInterval(async () => {
      try {
        const { data } = await apiClient.get<Job>(`/jobs/${jobId}`);
        setJob(data);
        if (data.status === 'completed' || data.status === 'failed' || data.status === 'cancelled') {
          clearInterval(interval);
          if (data.status === 'completed') {
            const { data: resultData } = await apiClient.get<Record<string, unknown>[]>(`/jobs/${jobId}/result`);
            setResults(resultData);
          }
        }
      } catch {
        clearInterval(interval);
      }
    }, 2000);
  };

  const handleDrop = useCallback((acceptedFiles: File[]) => {
    acceptedFiles.forEach((file) => {
      const reader = new FileReader();
      reader.onload = () => {
        const text = reader.result as string;
        setInput((prev) => (prev ? prev + '\n' + text : text));
      };
      reader.readAsText(file);
    });
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: handleDrop,
    accept: { 'text/*': ['.csv', '.txt', '.smi'] },
  });

  const handleExport = () => {
    if (!results) return;
    let blob: Blob;
    let filename: string;
    if (exportFormat === 'json') {
      blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' });
      filename = 'qmol-results.json';
    } else if (exportFormat === 'csv') {
      const headers = Object.keys(results[0] || {}).join(',');
      const rows = results.map((r) =>
        Object.values(r)
          .map((v) => (typeof v === 'string' ? `"${v.replace(/"/g, '""')}"` : v))
          .join(',')
      );
      blob = new Blob([headers + '\n' + rows.join('\n')], { type: 'text/csv' });
      filename = 'qmol-results.csv';
    } else {
      // parquet placeholder - export as JSON for now
      blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' });
      filename = 'qmol-results.json';
    }
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const smilesList = parseSmiles(input);
  const selectedEndpoint = ENDPOINTS.find((e) => e.value === endpoint);

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--fg-primary)]">Batch Compute</h1>
        <p className="mt-1 text-sm text-[var(--fg-secondary)]">
          Submit multiple SMILES for batch processing
        </p>
      </div>

      <div className="card p-5">
        <div className="mb-4 flex flex-col gap-4 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label className="mb-1 block text-sm font-medium text-[var(--fg-primary)]">
              Endpoint
            </label>
            <select
              value={endpoint}
              onChange={(e) => setEndpoint(e.target.value)}
              className="input"
            >
              {ENDPOINTS.map((e) => (
                <option key={e.value} value={e.value}>
                  {e.label} ({e.charge})
                </option>
              ))}
            </select>
          </div>
          <div className="text-sm text-[var(--fg-muted)]">
            {smilesList.length} molecules · Charge: {selectedEndpoint?.charge}
          </div>
        </div>

        <div {...getRootProps()} className="mb-3">
          <input {...getInputProps()} />
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={`# Paste SMILES, one per line\nCCO\nc1ccccc1\nCC(=O)Oc1ccccc1C(=O)O`}
            rows={8}
            className="input resize-y font-mono text-sm"
          />
          <p className="mt-1 text-xs text-[var(--fg-muted)]">
            {isDragActive
              ? 'Drop files here...'
              : 'Drag & drop CSV/SMI files, or paste SMILES directly'}
          </p>
        </div>

        {error && (
          <div className="mb-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950/30 dark:text-red-400">
            <AlertCircle size={16} className="inline mr-1" />
            {error}
          </div>
        )}

        <div className="flex items-center gap-3">
          <button
            onClick={handleSubmit}
            disabled={loading || smilesList.length === 0}
            className="btn btn-primary"
          >
            {loading ? (
              <>
                <Loader size={16} className="animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Play size={16} />
                Submit
              </>
            )}
          </button>
          <button
            onClick={() => setInput('')}
            className="btn btn-ghost"
            disabled={input.length === 0}
          >
            Clear
          </button>
        </div>
      </div>

      {/* Job progress */}
      {job && (
        <div className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-[var(--fg-primary)]">Job {job.job_id}</h3>
            <span className="badge">
              {job.status === 'completed' ? (
                <CheckCircle size={12} className="mr-1 text-emerald-500" />
              ) : job.status === 'failed' ? (
                <AlertCircle size={12} className="mr-1 text-red-500" />
              ) : (
                <Loader size={12} className="mr-1 animate-spin text-[var(--accent)]" />
              )}
              {job.status}
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-[var(--bg-tertiary)]">
            <div
              className="h-full rounded-full bg-[var(--accent)] transition-all"
              style={{ width: `${job.progress}%` }}
            />
          </div>
          <p className="mt-2 text-xs text-[var(--fg-muted)]">
            {job.processed} / {job.total} processed · {job.errors} errors
          </p>
        </div>
      )}

      {/* Results table */}
      {results && results.length > 0 && (
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-[var(--fg-primary)]">
              Results ({results.length})
            </h3>
            <div className="flex items-center gap-2">
              <select
                value={exportFormat}
                onChange={(e) => setExportFormat(e.target.value as ExportFormat)}
                className="input text-xs py-1.5"
              >
                {FORMATS.map((f) => (
                  <option key={f} value={f}>
                    {f.toUpperCase()}
                  </option>
                ))}
              </select>
              <button onClick={handleExport} className="btn btn-secondary text-xs">
                <FileDown size={14} />
                Export
              </button>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)]">
                  {Object.keys(results[0]).map((k) => (
                    <th key={k} className="px-2 py-2 text-left text-xs font-medium text-[var(--fg-muted)]">
                      {k}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {results.slice(0, 100).map((row, i) => (
                  <tr key={i} className="border-b border-[var(--border-light)] hover:bg-[var(--bg-tertiary)]">
                    {Object.values(row).map((v, j) => (
                      <td key={j} className="px-2 py-1.5 text-[var(--fg-secondary)]">
                        {typeof v === 'number' ? v.toFixed(4) : String(v)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {results.length > 100 && (
              <p className="mt-2 text-xs text-[var(--fg-muted)]">
                Showing first 100 of {results.length} rows. Export for full data.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
