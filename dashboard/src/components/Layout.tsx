import { useState } from 'react';
import { Link, useLocation, useNavigate, Outlet } from 'react-router-dom';
import {
  LayoutDashboard,
  Calculator,
  List,
  BarChart3,
  Users,
  Shield,
  Settings,
  Menu,
  X,
  Moon,
  Sun,
  Monitor,
  FlaskConical,
  LogOut,
  ChevronRight,
} from 'lucide-react';
import { useAuthStore } from '@/store/auth';
import { useTheme } from '@/hooks/useTheme';
import type { Theme } from '@/types/api';

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
  adminOnly?: boolean;
}

const navItems: NavItem[] = [
  { label: 'Dashboard', href: '/', icon: LayoutDashboard },
  { label: 'Compute', href: '/compute', icon: Calculator },
  { label: 'Jobs', href: '/jobs', icon: List },
  { label: 'Usage', href: '/usage', icon: BarChart3 },
  { label: 'Teams', href: '/teams', icon: Users },
  { label: 'Admin', href: '/admin', icon: Shield, adminOnly: true },
  { label: 'Settings', href: '/settings', icon: Settings },
];

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { apiKey, tier, quota, clearAuth } = useAuthStore();
  const { theme, setTheme } = useTheme();

  const isAdmin = tier === 'enterprise' || tier === 'admin';
  const quotaPct = quota && quota.total > 0 ? (quota.used / quota.total) * 100 : 0;

  const filteredNav = navItems.filter((n) => !n.adminOnly || isAdmin);

  const handleLogout = () => {
    clearAuth();
    navigate('/');
  };

  const themeIcon = {
    light: Sun,
    dark: Moon,
    system: Monitor,
  }[theme];

  const ThemeIcon = themeIcon;

  return (
    <div className="flex min-h-screen bg-[var(--bg-primary)]">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 transform border-r border-[var(--border)] bg-[var(--bg-secondary)] transition-transform duration-300 lg:static lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        aria-label="Main navigation"
      >
        <div className="flex h-full flex-col">
          {/* Logo */}
          <div className="flex items-center gap-3 border-b border-[var(--border)] px-4 py-4">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--accent)] text-white">
              <FlaskConical size={20} />
            </div>
            <div>
              <h1 className="text-lg font-bold text-[var(--fg-primary)]">Q-Mol</h1>
              <p className="text-xs text-[var(--fg-muted)]">v2.0.0</p>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="ml-auto rounded-md p-1 text-[var(--fg-muted)] hover:bg-[var(--bg-tertiary)] lg:hidden"
              aria-label="Close sidebar"
            >
              <X size={20} />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 overflow-y-auto px-3 py-4">
            <ul className="space-y-1">
              {filteredNav.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.href;
                return (
                  <li key={item.href}>
                    <Link
                      to={item.href}
                      onClick={() => setSidebarOpen(false)}
                      className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-[var(--accent-50)] text-[var(--accent)]'
                          : 'text-[var(--fg-secondary)] hover:bg-[var(--bg-tertiary)] hover:text-[var(--fg-primary)]'
                      }`}
                      aria-current={isActive ? 'page' : undefined}
                    >
                      <Icon size={18} />
                      {item.label}
                      {isActive && (
                        <ChevronRight size={14} className="ml-auto opacity-50" />
                      )}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>

          {/* Sidebar footer */}
          <div className="border-t border-[var(--border)] px-3 py-4">
            {apiKey && (
              <div className="mb-3 rounded-lg bg-[var(--bg-tertiary)] p-3">
                <div className="mb-2 flex items-center justify-between text-xs">
                  <span className="text-[var(--fg-muted)]">Quota</span>
                  <span className="font-medium text-[var(--fg-primary)]">
                    {quota?.used.toLocaleString()} / {quota?.total.toLocaleString()}
                  </span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-[var(--border)]">
                  <div
                    className={`h-full rounded-full transition-all ${
                      quotaPct > 90
                        ? 'bg-red-500'
                        : quotaPct > 70
                        ? 'bg-amber-500'
                        : 'bg-[var(--accent)]'
                    }`}
                    style={{ width: `${Math.min(100, quotaPct)}%` }}
                    aria-valuenow={quotaPct}
                    aria-valuemin={0}
                    aria-valuemax={100}
                    role="progressbar"
                  />
                </div>
                <p className="mt-1 text-[10px] text-[var(--fg-muted)]">{tier || 'free'} tier</p>
              </div>
            )}
            <div className="flex items-center gap-2">
              <div className="relative">
                <button
                  onClick={() => {
                    const themes: Theme[] = ['light', 'dark', 'system'];
                    const next = themes[(themes.indexOf(theme) + 1) % themes.length];
                    setTheme(next);
                  }}
                  className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-[var(--fg-secondary)] hover:bg-[var(--bg-tertiary)]"
                  aria-label={`Theme: ${theme}`}
                >
                  <ThemeIcon size={14} />
                  <span className="capitalize">{theme}</span>
                </button>
              </div>
              {apiKey && (
                <button
                  onClick={handleLogout}
                  className="ml-auto flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
                >
                  <LogOut size={14} />
                  Sign out
                </button>
              )}
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* Top bar */}
        <header className="sticky top-0 z-30 flex items-center gap-4 border-b border-[var(--border)] bg-[var(--bg-secondary)]/80 px-4 py-3 backdrop-blur-sm lg:px-6">
          <button
            onClick={() => setSidebarOpen(true)}
            className="rounded-lg p-2 text-[var(--fg-secondary)] hover:bg-[var(--bg-tertiary)] lg:hidden"
            aria-label="Open sidebar"
          >
            <Menu size={20} />
          </button>

          <div className="flex flex-1 items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              {apiKey ? (
                <span className="badge badge-green">
                  <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  API key active
                </span>
              ) : (
                <span className="badge badge-yellow">No API key</span>
              )}
            </div>

            <div className="flex items-center gap-3">
              {apiKey && quota && (
                <div className="hidden items-center gap-2 sm:flex">
                  <span className="text-xs text-[var(--fg-muted)]">
                    {Math.round(quotaPct)}% used
                  </span>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-4 lg:p-6">
          <Outlet />
        </main>

        {/* Footer */}
        <footer className="border-t border-[var(--border)] px-4 py-3 text-center text-xs text-[var(--fg-muted)] lg:px-6">
          Q-Mol Dashboard v1.0.0 · API v2.0.0 ·{' '}
          <a
            href="https://api.qmol.app/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="text-[var(--accent)] hover:underline"
          >
            API Docs
          </a>
        </footer>
      </div>
    </div>
  );
}
