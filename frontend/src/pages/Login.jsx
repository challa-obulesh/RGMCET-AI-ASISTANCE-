import { useState } from 'react'
import { Bot, Eye, EyeOff, Sparkles } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext.jsx'

export default function Login({ onNavigate }) {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPwd, setShowPwd] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    if (!email.trim() || !password) return
    setBusy(true); setError('')
    try {
      const profile = await login(email.trim(), password)
      if (profile.role === 'professor') onNavigate('professor')
      else if (profile.role === 'admin') onNavigate('admin')
      else onNavigate('student')
    } catch (err) {
      setError(err.message || 'Login failed. Check your credentials.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">
          <div className="auth-brand-mark"><Bot size={26} /></div>
          <div>
            <strong>RGMCET AI</strong>
            <small>Campus Assistant</small>
          </div>
        </div>
        <h1 className="auth-heading">Welcome back</h1>
        <p className="auth-sub">Sign in to continue to your campus assistant</p>
        <form className="auth-form" onSubmit={handleSubmit} id="login-form">
          <label>
            Email address
            <input
              id="login-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
              required
              disabled={busy}
            />
          </label>
          <label>
            Password
            <div className="password-wrap">
              <input
                id="login-password"
                type={showPwd ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Your password"
                autoComplete="current-password"
                required
                disabled={busy}
              />
              <button type="button" className="pwd-toggle" onClick={() => setShowPwd((s) => !s)} aria-label={showPwd ? 'Hide password' : 'Show password'}>
                {showPwd ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </label>
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button id="login-submit" className="auth-submit" type="submit" disabled={busy || !email || !password}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
        <p className="auth-switch">
          Don't have an account?{' '}
          <button className="link-button" onClick={() => onNavigate('register')}>Create one</button>
        </p>
        <div className="auth-demo-note">
          <Sparkles size={13} />
          <span>Demo: use any email + 6+ char password to register</span>
        </div>
      </div>
    </div>
  )
}
