import React, { createContext, useContext, useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import { useToast } from '../components/Toast'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
  const { addToast } = useToast()

  useEffect(() => {
    let isMounted = true
    const token = localStorage.getItem('jwt')
    if (token) {
      api.get('/auth/me')
        .then((res) => { if (isMounted) setUser(res.data) })
        .catch(() => { localStorage.removeItem('jwt') })
        .finally(() => { if (isMounted) setLoading(false) })
    } else {
      setLoading(false)
    }
    return () => { isMounted = false }
  }, [])

  const login = async (email, password) => {
    try {
      const res = await api.post('/auth/login', { email, password })
      const token = res.data.access_token
      localStorage.setItem('jwt', token)
      api.defaults.headers.Authorization = `Bearer ${token}`
      const me = await api.get('/auth/me')
      setUser(me.data)
      addToast('Logged in successfully', 'success')
      navigate('/')
    } catch (err) {
      localStorage.removeItem('jwt')
      delete api.defaults.headers.Authorization
      addToast(err.message || 'Login failed', 'error')
      throw err
    }
  }

  const register = async (email, password) => {
    try {
      const res = await api.post('/auth/register', { email, password })
      const token = res.data.access_token
      localStorage.setItem('jwt', token)
      api.defaults.headers.Authorization = `Bearer ${token}`
      const me = await api.get('/auth/me')
      setUser(me.data)
      addToast('Account created successfully', 'success')
      navigate('/')
    } catch (err) {
      localStorage.removeItem('jwt')
      delete api.defaults.headers.Authorization
      addToast(err.message || 'Registration failed', 'error')
      throw err
    }
  }

  const logout = () => {
    localStorage.removeItem('jwt')
    delete api.defaults.headers.Authorization
    setUser(null)
    addToast('Logged out', 'info')
    navigate('/login')
  }

  const value = useMemo(() => ({ user, login, register, logout, loading }), [user, loading])

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
