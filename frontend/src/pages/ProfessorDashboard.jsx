import { useEffect, useState } from 'react'
import { CalendarCheck, Check, Clock3, GraduationCap, RefreshCw, X } from 'lucide-react'
import { api } from '../services/api.js'
import { useAuth } from '../contexts/AuthContext.jsx'

function formatDate(value) {
  return new Date(`${value}T12:00:00`).toLocaleDateString(undefined, { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' })
}

function StatusPill({ status }) {
  const cls = { APPROVED: 'approved', REJECTED: 'rejected', CANCELLED: 'cancelled' }[status] || ''
  return <span className={`status-pill ${cls}`}>{status.replaceAll('_', ' ')}</span>
}

function PendingCard({ item, onDecide, isBusy }) {
  return (
    <article className={`dash-request-card ${isBusy ? 'row-busy' : ''}`} id={`request-${item.appointment_id}`}>
      <div className="request-student">
        <div className="request-avatar"><GraduationCap size={18} /></div>
        <div>
          <strong className="request-name">{item.student_name || 'Student'}</strong>
          <span className="request-id">{item.student_id}</span>
        </div>
      </div>
      <div className="request-details">
        <div className="request-when">
          <strong>{formatDate(item.date)}</strong>
          <span>{item.start_time} – {item.end_time}</span>
        </div>
        <p className="request-reason">{item.reason}</p>
      </div>
      <div className="request-actions">
        <button
          id={`approve-btn-${item.appointment_id}`}
          className="primary-action approve-action"
          onClick={() => onDecide(item.appointment_id, 'approve')}
          disabled={isBusy}
          aria-label={`Approve appointment from ${item.student_name}`}
        >
          <Check size={16} /> Approve
        </button>
        <button
          id={`reject-btn-${item.appointment_id}`}
          className="outline-action reject-action"
          onClick={() => onDecide(item.appointment_id, 'reject')}
          disabled={isBusy}
          aria-label={`Reject appointment from ${item.student_name}`}
        >
          <X size={16} /> Reject
        </button>
      </div>
    </article>
  )
}

export default function ProfessorDashboard() {
  const { user } = useAuth()
  const [pending, setPending] = useState([])
  const [upcoming, setUpcoming] = useState([])
  const [history, setHistory] = useState([])
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState('')
  const [loading, setLoading] = useState(true)

  async function load() {
    setLoading(true)
    try {
      const all = await api.professorAppointments()
      setPending(all.filter((a) => a.status === 'PENDING_APPROVAL'))
      setUpcoming(all.filter((a) => a.status === 'APPROVED'))
      setHistory(all.filter((a) => ['REJECTED', 'CANCELLED'].includes(a.status)))
      setError('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function decide(id, action) {
    setBusyId(id)
    try { await api.decideAppointment(id, action); await load() }
    catch (err) { setError(err.message) }
    finally { setBusyId('') }
  }

  const total = pending.length + upcoming.length + history.length

  return (
    <section className="page-content dashboard-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">PROFESSOR PORTAL</p>
          <h1>Professor Dashboard</h1>
          <p>Welcome, <strong>{user?.name || 'Professor'}</strong>. Manage your student appointment requests below.</p>
        </div>
        <button className="icon-button" onClick={load} aria-label="Refresh dashboard" title="Refresh">
          <RefreshCw size={16} />
        </button>
      </div>

      {/* Stats row */}
      <div className="dash-stats">
        <div className="stat-card">
          <span className="stat-number">{total}</span>
          <span className="stat-label">Total requests</span>
        </div>
        <div className="stat-card stat-pending">
          <span className="stat-number">{pending.length}</span>
          <span className="stat-label">Pending review</span>
        </div>
        <div className="stat-card stat-approved">
          <span className="stat-number">{upcoming.length}</span>
          <span className="stat-label">Approved</span>
        </div>
      </div>

      {error && <p className="form-error">{error}</p>}

      {loading ? (
        <div className="loading-state"><RefreshCw size={16} /><span>Loading requests…</span></div>
      ) : (
        <>
          {/* Pending requests */}
          <section className="appointment-section">
            <div className="section-title">
              <Clock3 size={18} />
              <h2>Pending requests</h2>
              <span>{pending.length}</span>
            </div>
            {pending.length === 0 ? (
              <div className="quiet-empty"><Check size={18} /><span>No pending requests. You're all caught up!</span></div>
            ) : (
              <div className="request-cards">
                {pending.map((item) => (
                  <PendingCard
                    key={item.appointment_id}
                    item={item}
                    onDecide={decide}
                    isBusy={busyId === item.appointment_id}
                  />
                ))}
              </div>
            )}
          </section>

          {/* Upcoming approved */}
          <section className="appointment-section">
            <div className="section-title">
              <CalendarCheck size={18} />
              <h2>Upcoming appointments</h2>
              <span>{upcoming.length}</span>
            </div>
            {upcoming.length === 0 ? (
              <div className="quiet-empty"><Clock3 size={18} /><span>No upcoming appointments.</span></div>
            ) : (
              <div className="appointment-list">
                {upcoming.map((item) => (
                  <article className="appointment-row" key={item.appointment_id}>
                    <div className="appointment-date">
                      <strong>{formatDate(item.date)}</strong>
                      <span>{item.start_time}–{item.end_time}</span>
                    </div>
                    <div className="appointment-person">
                      <strong>{item.student_name || 'Student'}</strong>
                      <span title={item.reason}>{item.reason?.slice(0, 60)}{item.reason?.length > 60 ? '…' : ''}</span>
                    </div>
                    <span className="status-pill approved">APPROVED</span>
                    <div className="row-actions" />
                  </article>
                ))}
              </div>
            )}
          </section>

          {/* History */}
          {history.length > 0 && (
            <section className="appointment-section">
              <div className="section-title">
                <CalendarCheck size={18} />
                <h2>Closed</h2>
                <span>{history.length}</span>
              </div>
              <div className="appointment-list">
                {history.map((item) => (
                  <article className="appointment-row" key={item.appointment_id}>
                    <div className="appointment-date">
                      <strong>{formatDate(item.date)}</strong>
                      <span>{item.start_time}–{item.end_time}</span>
                    </div>
                    <div className="appointment-person">
                      <strong>{item.student_name || 'Student'}</strong>
                      <span title={item.reason}>{item.reason?.slice(0, 60)}</span>
                    </div>
                    <StatusPill status={item.status} />
                    <div className="row-actions" />
                  </article>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </section>
  )
}
