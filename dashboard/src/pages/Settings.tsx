import { useState } from 'react';
import {
  Settings,
  Eye,
  EyeOff,
  Copy,
  RefreshCw,
  Moon,
  Sun,
  Monitor,
  Download,
  Trash2,
  Check,
  KeyRound,
} from 'lucide-react';
import { useAuthStore } from '@/store/auth';
import { useTheme } from '@/hooks/useTheme';
import { apiClient } from '@/api/client';
import type { Theme } from '@/types/api';

export default function SettingsPage() {
  const { apiKey, setApiKey, clearAuth } = useAuthStore();
  const { theme, setTheme } = useTheme();
  const [showKey, setShowKey] = useState(false);
  const [copied, setCopied] = useState(false);
  const [rotating, setRotating] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleCopy = async () => {
    if (!apiKey) return;
    await navigator.clipboard.writeText(apiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRotate = async () => {
    if (!apiKey) return;
    if (!confirm('Rotate your API key? The current key will be disabled immediately.')) return;
    setRotating(true);
    setError(null);
    try {
      const { data } = await apiClient.post<{ new_key: string }>('/key/rotate');
      setApiKey(data.new_key);
      setSuccess('API key rotated. New key is displayed below.');
      setTimeout(() => setSuccess(null), 5000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Rotation failed');
    } finally {
      setRotating(false);
    }
  };

  const handleExport = async () => {
    if (!apiKey) return;
    setExporting(true);
    try {
      const { data } = await apiClient.get<Record<string, unknown>>('/account/export');
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'qmol-account-export.json';
      a.click();
      URL.revokeObjectURL(url);
      setSuccess('Account data exported.');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setExporting(false);
    }
  };

  const handleDelete = async () => {
    if (!apiKey) return;
    if (!confirm('Permanently delete your account and ALL data? This cannot be undone.')) return;
    try {
      await apiClient.delete('/account');
      clearAuth();
      setSuccess('Account deleted.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed');
    }
  };

  const themeOptions: { value: Theme; label: string; icon: React.ElementType }[] = [
    { value: 'light', label: 'Light', icon: Sun },
    { value: 'dark', label: 'Dark', icon: Moon },
    { value: 'system', label: 'System', icon: Monitor },
  ];

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--fg-primary)]">Settings</h1>
        <p className="mt-1 text-sm text-[var(--fg-secondary)]">Manage your account and preferences</p>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-950/30 dark:text-red-400">
          {error}
        </div>
      )}
      {success && (
        <div className="rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-600 dark:bg-emerald-950/30 dark:text-emerald-400">
          {success}
        </div>
      )}

      {/* API Key */}
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <KeyRound size={18} className="text-[var(--accent)]" />
          <h2 className="text-sm font-semibold text-[var(--fg-primary)]">API Key</h2>
        </div>
        {apiKey ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <div className="relative flex-1">
                <input
                  type={showKey ? 'text' : 'password'}
                  value={apiKey}
                  readOnly
                  className="input pr-10 font-mono text-sm"
                />
                <button
                  onClick={() => setShowKey(!showKey)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-[var(--fg-muted)] hover:text-[var(--fg-primary)]"
                  aria-label={showKey ? 'Hide API key' : 'Show API key'}
                >
                  {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              <button
                onClick={handleCopy}
                className="btn btn-secondary"
                title="Copy to clipboard"
              >
                {copied ? <Check size={16} className="text-emerald-500" /> : <Copy size={16} />}
              </button>
              <button
                onClick={handleRotate}
                disabled={rotating}
                className="btn btn-secondary"
                title="Rotate API key"
              >
                <RefreshCw size={16} className={rotating ? 'animate-spin' : ''} />
              </button>
            </div>
            <p className="text-xs text-[var(--fg-muted)]">
              Keep your API key secure. Do not share it or commit it to version control.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-[var(--fg-muted)]">No API key set. Enter your key below:</p>
            <div className="flex gap-2">
              <input
                type="password"
                placeholder="qmol_..."
                className="input flex-1 font-mono text-sm"
                onChange={(e) => {
                  if (e.target.value.length > 0) setApiKey(e.target.value);
                }}
              />
            </div>
            <p className="text-xs text-[var(--fg-muted)]">
              Get a free API key from the{' '}
              <a href="/" className="text-[var(--accent)] hover:underline">
                main page
              </a>
              .
            </p>
          </div>
        )}
      </div>

      {/* Theme */}
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Settings size={18} className="text-[var(--accent)]" />
          <h2 className="text-sm font-semibold text-[var(--fg-primary)]">Appearance</h2>
        </div>
        <div className="flex gap-2">
          {themeOptions.map((opt) => {
            const Icon = opt.icon;
            const active = theme === opt.value;
            return (
              <button
                key={opt.value}
                onClick={() => setTheme(opt.value)}
                className={`flex flex-1 items-center justify-center gap-2 rounded-lg border px-4 py-2.5 text-sm font-medium transition-colors ${
                  active
                    ? 'border-[var(--accent)] bg-[var(--accent-50)] text-[var(--accent)]'
                    : 'border-[var(--border)] bg-[var(--bg-primary)] text-[var(--fg-secondary)] hover:bg-[var(--bg-tertiary)]'
                }`}
              >
                <Icon size={16} />
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Data & Privacy */}
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <Download size={18} className="text-[var(--accent)]" />
          <h2 className="text-sm font-semibold text-[var(--fg-primary)]">Data & Privacy</h2>
        </div>
        <div className="space-y-3">
          <div className="flex items-center justify-between rounded-lg border border-[var(--border)] p-3">
            <div>
              <p className="text-sm font-medium text-[var(--fg-primary)]">Export Account Data</p>
              <p className="text-xs text-[var(--fg-muted)]">Download all your data (GDPR export)</p>
            </div>
            <button
              onClick={handleExport}
              disabled={exporting || !apiKey}
              className="btn btn-secondary"
            >
              <Download size={16} />
              {exporting ? 'Exporting...' : 'Export'}
            </button>
          </div>
          <div className="flex items-center justify-between rounded-lg border border-red-200 bg-red-50 p-3 dark:border-red-900 dark:bg-red-950/20">
            <div>
              <p className="text-sm font-medium text-red-700 dark:text-red-400">Delete Account</p>
              <p className="text-xs text-red-500 dark:text-red-300">
                Permanently delete your account and all data
              </p>
            </div>
            <button
              onClick={handleDelete}
              disabled={!apiKey}
              className="btn btn-danger"
            >
              <Trash2 size={16} />
              Delete
            </button>
          </div>
        </div>
      </div>

      {/* About */}
      <div className="card p-5">
        <h2 className="text-sm font-semibold text-[var(--fg-primary)] mb-2">About</h2>
        <div className="space-y-1 text-sm text-[var(--fg-secondary)]">
          <p>Dashboard version: 1.0.0</p>
          <p>API version: 2.0.0</p>
          <p>
            Support:{' '}
            <a href="mailto:support@qmol.app" className="text-[var(--accent)] hover:underline">
              support@qmol.app
            </a>
          </p>
          <p>
            <a href="https://api.qmol.app/docs" target="_blank" rel="noopener noreferrer" className="text-[var(--accent)] hover:underline">
              API Documentation
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
