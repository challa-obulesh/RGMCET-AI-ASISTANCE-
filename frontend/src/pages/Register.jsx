import { useState, useEffect } from 'react'
import { Bot, Eye, EyeOff, GraduationCap, Sparkles, Users, CheckCircle2 } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext.jsx'
import { api } from '../services/api.js'

export default function Register({ onNavigate }) {
  const { register } = useAuth()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('student')
  const [selectedProfId, setSelectedProfId] = useState('')
  const [facultyList, setFacultyList] = useState([])
  const [showPwd, setShowPwd] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [pendingSuccess, setPendingSuccess] = useState(null)

  useEffect(() => {
    if (role === 'professor' && facultyList.length === 0) {
      api.professors()
        .then((items) => setFacultyList(items || []))
        .catch(() => {})
    }
  }, [role, facultyList.length])

  function handleSelectFaculty(profId) {
    setSelectedProfId(profId)
    const match = facultyList.find(f => f.professor_id === profId)
    if (match) {
      setName(match.name)
      if (match.official_email) {
        setEmail(match.official_email)
      } else if (match.email) {
        setEmail(match.email)
      }
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!name.trim() || !email.trim() || !password) return
    if (password.length < 6) { setError('Password must be at least 6 characters.'); return }
    setBusy(true); setError('')
    try {
      const res = await register(name.trim(), email.trim(), password, role, selectedProfId || null)
      if (res.role === 'professor') {
        if (res.approval_status === 'APPROVED') {
          onNavigate('professor')
        } else {
          setPendingSuccess(res)
        }
      } else {
        onNavigate('student')
      }
    } catch (err) {
      setError(err.message || 'Registration failed. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  if (pendingSuccess) {
    return (
      <div className="auth-page">
        <div className="auth-card" style={{ textAlign: 'center' }}>
          <div style={{ background: '#fef3c7', color: '#92400e', width: 54, height: 54, borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
            <Users size={28} />
          </div>
          <h2 style={{ fontSize: 20, color: '#163d31', margin: '0 0 8px' }}>Registration Received</h2>
          <div style={{ display: 'inline-block', background: '#fef3c7', color: '#92400e', padding: '4px 12px', borderRadius: 16, fontWeight: 700, fontSize: 12, marginBottom: 16 }}>
            Status: PENDING ADMINISTRATOR APPROVAL
          </div>
          <p style={{ fontSize: 14, color: '#4b5563', lineHeight: 1.6, marginBottom: 20 }}>
            Your professor account for <strong>{name}</strong> (<code>{email}</code>) has been successfully created and linked to the official RGMCET faculty registry.
          </p>
          <div style={{ background: '#f9fafb', padding: '12px 16px', borderRadius: 8, fontSize: 13, color: '#6b7280', marginBottom: 24, border: '1px solid #e5e7eb' }}>
            Your account is currently pending administrator verification. Please contact the administrator after approval to access the Professor Dashboard.
          </div>
          <button id="go-to-signin-btn" className="auth-submit" onClick={() => onNavigate('login')}>
            Return to Sign in
          </button>
        </div>
      </div>
    )
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
          {role === 'professor' && (
            <label>
              Verified RGMCET Faculty Member
              <select
                id="select-faculty-member"
                value={selectedProfId}
                onChange={(e) => handleSelectFaculty(e.target.value)}
                style={{ width: '100%', padding: '10px 12px', borderRadius: 8, border: '1px solid #ddd', fontSize: 13, marginTop: 4, background: '#fcfdfa' }}
              >
                <option value="">-- Select from Official RGMCET Faculty Portal --</option>
                {facultyList.map((f) => (
                  <option key={f.professor_id} value={f.professor_id}>
                    {f.name} ({f.designation}) {f.official_email ? `— ${f.official_email}` : ''}
                  </option>
                ))}
              </select>
            </label>
          )}

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
            {role === 'professor' ? 'Official RGMCET Email' : 'Email address'}
            <input
              id="register-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder={role === 'professor' ? 'faculty@rgmcet.edu.in' : 'you@example.com'}
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
          <span>
            {role === 'professor'
              ? 'Professor registrations link to official RGMCET records and require Admin approval'
              : 'Students can register with their email to request appointments'}
          </span>
        </div>
      </div>
    </div>
  )
}
