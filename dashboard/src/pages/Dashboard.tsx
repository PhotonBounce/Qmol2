import { useState, useEffect, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  Calculator,
  Upload,
  Clock,
  Trash2,
  Sparkles,
  FileText,
  ChevronRight,
} from 'lucide-react';
import { useAuthStore } from '@/store/auth';
import { apiClient } from '@/api/client';
import MoleculeViewer from '@/components/MoleculeViewer';
import PropertyCard from '@/components/PropertyCard';
import type { PropertyDisplay, ComputeResult } from '@/types/api';

interface HistoryItem {
  id: string;
  smiles: string;
  timestamp: number;
  results: PropertyDisplay[];
}

const DEFAULT_PROPERTIES: PropertyDisplay[] = [
  { name: 'Molecular Weight', value: '—', unit: 'g/mol', confidence: 0, inDomain: true, status: 'good', description: 'Monoisotopic mass' },
  { name: 'logP', value: '—', unit: '', confidence: 0, inDomain: true, status: 'good', description: 'Partition coefficient (octanol/water)' },
  { name: 'TPSA', value: '—', unit: 'Å²', confidence: 0, inDomain: true, status: 'good', description: 'Topological polar surface area' },
  { name: 'HBD', value: '—', unit: 'count', confidence: 0, inDomain: true, status: 'good', description: 'Hydrogen bond donors' },
  { name: 'HBA', value: '—', unit: 'count', confidence: 0, inDomain: true, status: 'good', description: 'Hydrogen bond acceptors' },
  { name: 'QED', value: '—', unit: '', confidence: 0, inDomain: true, status: 'good', description: 'Quantitative Estimate of Drug-likeness' },
];

export default function Dashboard() {
  const [smiles, setSmiles] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<PropertyDisplay[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const { apiKey } = useAuthStore();

  // Load history from localStorage
  useEffect(() => {
    const raw = localStorage.getItem('qmol_history');
    if (raw) {
      try {
        setHistory(JSON.parse(raw));
      } catch {
        /* ignore */
      }
    }
  }, []);

  const saveHistory = useCallback((items: HistoryItem[]) => {
    localStorage.setItem('qmol_history', JSON.stringify(items.slice(0, 10)));
  }, []);

  const handleCompute = async () => {
    if (!smiles.trim()) return;
    if (!apiKey) {
      setError('Please enter your API key in Settings first.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const { data } = await apiClient.post<ComputeResult[]>('/compute', {
        smiles: [smiles.trim()],
      });
      const row = data[0];
      if (row.error) {
        throw new Error(row.error);
      }
      const descriptors = row.descriptors || {};
      const newResults: PropertyDisplay[] = [
        {
          name: 'Molecular Weight',
          value: descriptors.MolWt?.toFixed(2) ?? '—',
          unit: 'g/mol',
          confidence: 1,
          inDomain: true,
          status: 'good',
          description: 'Monoisotopic mass',
        },
        {
          name: 'logP',
          value: descriptors.MolLogP?.toFixed(2) ?? '—',
          unit: '',
          confidence: 0.9,
          inDomain: (descriptors.MolLogP as number) >= -0.5 && (descriptors.MolLogP as number) <= 5,
          status:
            (descriptors.MolLogP as number) > 5
              ? 'warning'
              : (descriptors.MolLogP as number) < -2
              ? 'alert'
              : 'good',
          description: 'Partition coefficient (octanol/water)',
        },
        {
          name: 'TPSA',
          value: descriptors.TPSA?.toFixed(1) ?? '—',
          unit: 'Å²',
          confidence: 1,
          inDomain: true,
          status: 'good',
          description: 'Topological polar surface area',
        },
        {
          name: 'HBD',
          value: descriptors.NumHDonors?.toString() ?? '—',
          unit: 'count',
          confidence: 1,
          inDomain: true,
          status: (descriptors.NumHDonors as number) <= 5 ? 'good' : 'warning',
          description: 'Hydrogen bond donors',
        },
        {
          name: 'HBA',
          value: descriptors.NumHAcceptors?.toString() ?? '—',
          unit: 'count',
          confidence: 1,
          inDomain: true,
          status: (descriptors.NumHAcceptors as number) <= 10 ? 'good' : 'warning',
          description: 'Hydrogen bond acceptors',
        },
        {
          name: 'QED',
          value: descriptors.qed?.toFixed(3) ?? '—',
          unit: '',
          confidence: 0.95,
          inDomain: true,
          status:
            (descriptors.qed as number) > 0.67
              ? 'good'
              : (descriptors.qed as number) > 0.49
              ? 'warning'
              : 'alert',
          description: 'Quantitative Estimate of Drug-likeness',
        },
      ];
      setResults(newResults);
      const item: HistoryItem = {
        id: crypto.randomUUID(),
        smiles: smiles.trim(),
        timestamp: Date.now(),
        results: newResults,
      };
      const next = [item, ...history].slice(0, 10);
      setHistory(next);
      saveHistory(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Compute failed');
    } finally {
      setLoading(false);
    }
  };

  const handleDrop = useCallback(
    (acceptedFiles: File[]) => {
      acceptedFiles.forEach((file) => {
        const reader = new FileReader();
        reader.onload = () => {
          const text = reader.result as string;
          // Simple CSV/SDF parsing: extract SMILES-like strings
          const lines = text
            .split(/\r?\n/)
            .map((l) => l.trim())
            .filter((l) => l.length > 0 && !l.startsWith('#'));
          if (lines.length > 0) {
            setSmiles(lines[0]);
          }
        };
        reader.readAsText(file);
      });
    },
    []
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: handleDrop,
    accept: {
      'text/csv': ['.csv'],
      'chemical/x-mdl-sdfile': ['.sdf', '.sd'],
      'text/plain': ['.txt'],
    },
    multiple: false,
  });

  const clearHistory = () => {
    setHistory([]);
    localStorage.removeItem('qmol_history');
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--fg-primary)]">Dashboard</h1>
          <p className="mt-1 text-sm text-[var(--fg-secondary)]">
            Quick compute, results, and recent history
          </p>
        </div>
      </div>

      {/* Compute Input */}
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Sparkles size={18} className="text-[var(--accent)]" />
          <h2 className="text-sm font-semibold text-[var(--fg-primary)]">Quick Compute</h2>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            type="text"
            value={smiles}
            onChange={(e) => setSmiles(e.target.value)}
            placeholder="Enter SMILES, e.g., CCO, c1ccccc1, CC(=O)Oc1ccccc1C(=O)O"
            className="input flex-1"
            onKeyDown={(e) => e.key === 'Enter' && handleCompute()}
          />
          <button
            onClick={handleCompute}
            disabled={loading || !smiles.trim()}
            className="btn btn-primary min-w-[120px]"
          >
            {loading ? (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                Computing...
              </>
            ) : (
              <>
                <Calculator size={16} />
                Compute
              </>
            )}
          </button>
        </div>
        {error && (
          <div className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600 dark:bg-red-950/30 dark:text-red-400">
            {error}
          </div>
        )}
      </div>

      {/* Results */}
      {results && (
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-4">
            <FileText size={18} className="text-[var(--accent)]" />
            <h2 className="text-sm font-semibold text-[var(--fg-primary)]">Results</h2>
          </div>
          <div className="flex flex-col gap-6 lg:flex-row">
            <div className="flex-shrink-0">
              <MoleculeViewer smiles={smiles} size={220} />
              <p className="mt-2 text-center text-xs font-mono text-[var(--fg-muted)] break-all">
                {smiles}
              </p>
            </div>
            <div className="grid flex-1 grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {results.map((p) => (
                <PropertyCard key={p.name} property={p} compact />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Upload area */}
      <div
        {...getRootProps()}
        className={`card cursor-pointer border-2 border-dashed p-6 text-center transition-colors ${
          isDragActive
            ? 'border-[var(--accent)] bg-[var(--accent-50)]'
            : 'border-[var(--border)] hover:border-[var(--accent-light)] hover:bg-[var(--accent-50)]/50'
        }`}
      >
        <input {...getInputProps()} />
        <Upload size={32} className="mx-auto mb-2 text-[var(--fg-muted)]" />
        <p className="text-sm font-medium text-[var(--fg-primary)]">
          {isDragActive ? 'Drop files here' : 'Drag & drop CSV / SDF files'}
        </p>
        <p className="mt-1 text-xs text-[var(--fg-muted)]">
          or click to browse. Batch processing sends to the Compute page.
        </p>
      </div>

      {/* History */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Clock size={18} className="text-[var(--accent)]" />
            <h2 className="text-sm font-semibold text-[var(--fg-primary)]">Recent History</h2>
          </div>
          {history.length > 0 && (
            <button
              onClick={clearHistory}
              className="btn btn-ghost text-xs text-red-500 hover:text-red-600"
            >
              <Trash2 size={14} />
              Clear
            </button>
          )}
        </div>
        {history.length === 0 ? (
          <p className="py-6 text-center text-sm text-[var(--fg-muted)]">
            No recent computations. Enter a SMILES above to get started.
          </p>
        ) : (
          <ul className="space-y-2">
            {history.map((item) => (
              <li
                key={item.id}
                className="flex items-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--bg-primary)] px-3 py-2.5 hover:bg-[var(--bg-tertiary)] transition-colors cursor-pointer"
                onClick={() => {
                  setSmiles(item.smiles);
                  setResults(item.results);
                }}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    setSmiles(item.smiles);
                    setResults(item.results);
                  }
                }}
              >
                <MoleculeViewer smiles={item.smiles} size={40} />
                <div className="flex-1 min-w-0">
                  <p className="truncate text-xs font-mono text-[var(--fg-secondary)]">
                    {item.smiles}
                  </p>
                  <p className="text-[10px] text-[var(--fg-muted)]">
                    {new Date(item.timestamp).toLocaleString()}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  {item.results.slice(0, 2).map((r) => (
                    <span key={r.name} className="text-xs text-[var(--fg-muted)]">
                      {r.name}: {r.value}
                    </span>
                  ))}
                  <ChevronRight size={14} className="text-[var(--fg-muted)]" />
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
