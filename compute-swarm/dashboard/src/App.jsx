import React, { useState } from 'react'
import { Routes, Route, NavLink, useNavigate, Navigate, useLocation, Link, useMatch } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { ToastProvider, useToast } from './components/Toast'
import { Home, Briefcase, PlusCircle, CreditCard, User, LogOut, Menu, X, Activity, HelpCircle, Shield } from 'lucide-react'

import Dashboard from './components/Dashboard'
import JobList from './components/JobList'
import JobSubmit from './components/JobSubmit'
import JobDetail from './components/JobDetail'
import BillingPage from './components/BillingPage'
import LoginPage from './components/LoginPage'
import RegisterPage from './components/RegisterPage'
import AdminPage from './components/AdminPage'
import HelpPage from './components/HelpPage'

const VERSION = '0.1.0-MVP'

function AdminGuard({ children }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  const { addToast } = useToast()
  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-swarm-indigo-600 border-t-transparent"></div>
      </div>
    )
  }
  if (!user || user.role !== 'admin') {
    if (user) addToast('Admin access required', 'error')
    return <Navigate to="/" state={{ from: location }} replace />
  }
  return children
}

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-swarm-indigo-600 border-t-transparent"></div>
      </div>
    )
  }
  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }
  return children
}

function NavBar() {
  const { user, logout } = useAuth()
  const [mobileOpen, setMobileOpen] = useState(false)
  const navigate = useNavigate()

  const linkClass = ({ isActive }) =>
    `flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
      isActive
        ? 'bg-swarm-indigo-50 text-swarm-indigo-700'
        : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
    }`

  return (
    <nav className="sticky top-0 z-50 border-b border-slate-200 bg-white/80 backdrop-blur-md">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-swarm-indigo-600">
              <Activity className="h-5 w-5 text-white" />
            </div>
            <span
              className="cursor-pointer text-lg font-bold tracking-tight text-slate-900"
              onClick={() => navigate('/')}
            >
              ComputeSwarm
            </span>
          </div>

          {user && (
            <>
              <div className="hidden md:flex md:items-center md:gap-1">
                <NavLink to="/" className={linkClass} end>
                  <Home className="h-4 w-4" />
                  Dashboard
                </NavLink>
                <NavLink to="/jobs" className={linkClass}>
                  <Briefcase className="h-4 w-4" />
                  Jobs
                </NavLink>
                <NavLink to="/jobs/new" className={linkClass}>
                  <PlusCircle className="h-4 w-4" />
                  New Job
                </NavLink>
                <NavLink to="/billing" className={linkClass}>
                  <CreditCard className="h-4 w-4" />
                  Billing
                </NavLink>
                <NavLink to="/help" className={linkClass}>
                  <HelpCircle className="h-4 w-4" />
                  Help
                </NavLink>
                {user.role === 'admin' && (
                  <NavLink to="/admin" className={linkClass}>
                    <Shield className="h-4 w-4" />
                    Admin
                  </NavLink>
                )}
                <div className="mx-2 h-6 w-px bg-slate-200" />
                <div className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-slate-600">
                  <User className="h-4 w-4" />
                  {user.email}
                </div>
                <button onClick={logout} className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50 transition-colors">
                  <LogOut className="h-4 w-4" />
                  Logout
                </button>
              </div>

              <div className="md:hidden">
                <button onClick={() => setMobileOpen(!mobileOpen)} className="rounded-lg p-2 text-slate-600 hover:bg-slate-100">
                  {mobileOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
                </button>
              </div>
            </>
          )}

          {!user && (
            <div className="flex items-center gap-2">
              <button onClick={() => navigate('/login')} className="btn-secondary">Log In</button>
              <button onClick={() => navigate('/register')} className="btn-primary">Sign Up</button>
            </div>
          )}
        </div>
      </div>

      {user && mobileOpen && (
        <div className="md:hidden border-t border-slate-200 bg-white px-4 pb-4">
          <NavLink to="/" className={linkClass} onClick={() => setMobileOpen(false)} end>
            <Home className="h-4 w-4" /> Dashboard
          </NavLink>
          <NavLink to="/jobs" className={linkClass} onClick={() => setMobileOpen(false)}>
            <Briefcase className="h-4 w-4" /> Jobs
          </NavLink>
          <NavLink to="/jobs/new" className={linkClass} onClick={() => setMobileOpen(false)}>
            <PlusCircle className="h-4 w-4" /> New Job
          </NavLink>
          <NavLink to="/billing" className={linkClass} onClick={() => setMobileOpen(false)}>
            <CreditCard className="h-4 w-4" /> Billing
          </NavLink>
          <NavLink to="/help" className={linkClass} onClick={() => setMobileOpen(false)}>
            <HelpCircle className="h-4 w-4" /> Help
          </NavLink>
          {user.role === 'admin' && (
            <NavLink to="/admin" className={linkClass} onClick={() => setMobileOpen(false)}>
              <Shield className="h-4 w-4" /> Admin
            </NavLink>
          )}
          <button onClick={() => { setMobileOpen(false); logout(); }} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-50">
            <LogOut className="h-4 w-4" /> Logout
          </button>
        </div>
      )}
    </nav>
  )
}

function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white py-6">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2">
        <p className="text-sm text-slate-500">
          ComputeSwarm <span className="font-mono text-xs text-slate-400">v{VERSION}</span>
        </p>
        <div className="flex items-center gap-4 text-sm text-slate-500">
          <a href="https://github.com/your-org/compute-swarm" className="hover:text-swarm-indigo-600 transition-colors" target="_blank" rel="noreferrer">GitHub</a>
          <span className="text-slate-300">|</span>
          <Link to="/help" className="hover:text-swarm-indigo-600 transition-colors">Help</Link>
        </div>
      </div>
    </footer>
  )
}

function AppRoutes() {
  const adminMatch = useMatch('/admin/*')
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <NavBar />
      {adminMatch ? (
        <AdminGuard><AdminPage /></AdminGuard>
      ) : (
        <main className="mx-auto max-w-7xl w-full px-4 sm:px-6 lg:px-8 py-8 flex-1">
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/jobs" element={<ProtectedRoute><JobList /></ProtectedRoute>} />
            <Route path="/jobs/new" element={<ProtectedRoute><JobSubmit /></ProtectedRoute>} />
            <Route path="/jobs/:id" element={<ProtectedRoute><JobDetail /></ProtectedRoute>} />
            <Route path="/billing" element={<ProtectedRoute><BillingPage /></ProtectedRoute>} />
            <Route path="/help" element={<HelpPage />} />
            <Route path="*" element={
              <div className="card text-center py-12">
                <h1 className="text-2xl font-bold text-slate-900">404</h1>
                <p className="text-slate-500 mt-2">Page not found.</p>
                <Link to="/" className="btn-primary mt-4 inline-block">Back to Dashboard</Link>
              </div>
            } />
          </Routes>
        </main>
      )}
      <Footer />
    </div>
  )
}

function App() {
  return (
    <ToastProvider>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </ToastProvider>
  )
}

export default App
