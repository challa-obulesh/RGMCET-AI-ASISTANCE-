import { useState } from 'react'
import { Bot, Eye, EyeOff, GraduationCap, Sparkles, Users } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext.jsx'

export default function Register({ onNavigate }) {
  const { register } = useAuth()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('student')
  const [showPwd, setShowPwd] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    if (!name.trim() || !email.trim() || !password) return
    if (password.length < 6) { setError('Password must be at least 6 characters.'); return }
    setBusy(true); setError('')
    try {
      const profile = await register(name.trim(), email.trim(), password, role)
      if (profile.role === 'professor') onNavigate('professor')
      else onNavigate('chat')
    } catch (err) {
      setError(err.message || 'Registration failed. Please try again.')
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
        <h1 className="auth-heading">Create your account</h1>
        <p className="auth-sub">Join RGMCET AI Campus Assistant</p>

        <div className="role-selector">
          <button
            id="role-student"
            type="button"
            className={`role-option ${role === 'student' ? 'active' : ''}`}
            onClick={() => setRole('student')}
          >
            <GraduationCap size={18} />
            <span>Student</span>
          </button>
          <button
            id="role-professor"
            type="button"
            className={`role-option ${role === 'professor' ? 'active' : ''}`}
            onClick={() => setRole('professor')}
          >
            <Users size={18} />
            <span>Professor</span>
          </button>
        </div>

        <form className="auth-form" onSubmit={handleSubmit} id="register-form">
          <label>
            Full name
            <input
              id="register-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your full name"
              autoComplete="name"
              required
              disabled={busy}
              minLength={2}
            />
          </label>
          <label>
            Email address
            <input
              id="register-email"
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
                id="register-password"
                type={showPwd ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Minimum 6 characters"
                autoComplete="new-password"
                required
                minLength={6}
                disabled={busy}
              />
              <button type="button" className="pwd-toggle" onClick={() => setShowPwd((s) => !s)} aria-label={showPwd ? 'Hide password' : 'Show password'}>
                {showPwd ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </label>
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button id="register-submit" className="auth-submit" type="submit" disabled={busy || !name || !email || !password}>
            {busy ? 'Creating account…' : `Create ${role} account`}
          </button>
        </form>
        <p className="auth-switch">
          Already have an account?{' '}
          <button className="link-button" onClick={() => onNavigate('login')}>Sign in</button>
        </p>
        <div className="auth-demo-note">
          <Sparkles size={13} />
          <span>Professor accounts link to official RGMCET faculty by email</span>
        </div>
      </div>
    </div>
  )
}
