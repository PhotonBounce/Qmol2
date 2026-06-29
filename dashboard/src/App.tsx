import { Routes, Route } from 'react-router-dom';
import { Suspense, lazy } from 'react';
import { useAuthStore } from '@/store/auth';
import Layout from '@/components/Layout';
import ErrorBoundary from '@/components/ErrorBoundary';

const Dashboard = lazy(() => import('@/pages/Dashboard'));
const Compute = lazy(() => import('@/pages/Compute'));
const Jobs = lazy(() => import('@/pages/Jobs'));
const Usage = lazy(() => import('@/pages/Usage'));
const Teams = lazy(() => import('@/pages/Teams'));
const Admin = lazy(() => import('@/pages/Admin'));
const Settings = lazy(() => import('@/pages/Settings'));

function LoadingFallback() {
  return (
    <div className="flex h-[60vh] items-center justify-center">
      <div className="flex items-center gap-2 text-[var(--fg-muted)]">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-[var(--accent)] border-t-transparent" />
        <span>Loading...</span>
      </div>
    </div>
  );
}

function App() {
  const apiKey = useAuthStore((s) => s.apiKey);

  return (
    <ErrorBoundary>
      <Routes>
        <Route element={<Layout />}>
          <Route
            path="/"
            element={
              <Suspense fallback={<LoadingFallback />}>
                <Dashboard />
              </Suspense>
            }
          />
          <Route
            path="/compute"
            element={
              <Suspense fallback={<LoadingFallback />}>
                <Compute />
              </Suspense>
            }
          />
          <Route
            path="/jobs"
            element={
              <Suspense fallback={<LoadingFallback />}>
                <Jobs />
              </Suspense>
            }
          />
          <Route
            path="/usage"
            element={
              <Suspense fallback={<LoadingFallback />}>
                <Usage />
              </Suspense>
            }
          />
          <Route
            path="/teams"
            element={
              <Suspense fallback={<LoadingFallback />}>
                <Teams />
              </Suspense>
            }
          />
          <Route
            path="/admin"
            element={
              <Suspense fallback={<LoadingFallback />}>
                <Admin />
              </Suspense>
            }
          />
          <Route
            path="/settings"
            element={
              <Suspense fallback={<LoadingFallback />}>
                <Settings />
              </Suspense>
            }
          />
        </Route>
      </Routes>
    </ErrorBoundary>
  );
}

export default App;
