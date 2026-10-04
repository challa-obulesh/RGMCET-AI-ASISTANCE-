import { useEffect, useState } from 'react'
import { CalendarClock, Check, Clock3, RefreshCw, X, CalendarDays } from 'lucide-react'
import { api } from '../services/api.js'
import { useAuth } from '../contexts/AuthContext.jsx'

function formatDate(value) {
  return new Date(`${value}T12:00:00`).toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' })
}

function StatusPill({ status }) {
  const cls = { APPROVED: 'approved', REJECTED: 'rejected', CANCELLED: 'cancelled' }[status] || ''
  return <span className={`status-pill ${cls}`}>{status.replaceAll('_', ' ')}</span>
}

function AppointmentCard({ item, onCancel, onDecide, isBusy, showActions }) {
  const canCancel = ['PENDING_APPROVAL', 'APPROVED'].includes(item.status)
  return (
    <article className={`appointment-row ${isBusy ? 'row-busy' : ''}`}>
      <div className="appointment-date">
        <strong>{formatDate(item.date)}</strong>
        <span>{item.start_time}–{item.end_time}</span>
      </div>
      <div className="appointment-person">
        <strong>{item.professor_name || item.student_name}</strong>
        <span title={item.reason}>{item.reason?.slice(0, 60)}{item.reason?.length > 60 ? '…' : ''}</span>
      </div>
      <StatusPill status={item.status} />
      {item.calendar_event_id && (
        <span className="calendar-sync-status" title="Synced to Google Calendar">
          <CalendarDays size={14} style={{ marginRight: '4px', verticalAlign: 'middle', color: '#4CAF50' }} />
          <small style={{ color: '#4CAF50' }}>Synced</small>
        </span>
      )}
      <div className="row-actions">
        {showActions && item.status === 'PENDING_APPROVAL' && (
          <>
            <button id={`approve-${item.appointment_id}`} className="approve-button" onClick={() => onDecide(item.appointment_id, 'approve')} aria-label="Approve appointment" title="Approve">
              <Check size={16} />
            </button>
            <button id={`reject-${item.appointment_id}`} className="reject-button" onClick={() => onDecide(item.appointment_id, 'reject')} aria-label="Reject appointment" title="Reject">
              <X size={16} />
            </button>
          </>
        )}
        {!showActions && canCancel && onCancel && (
          <button id={`cancel-${item.appointment_id}`} className="reject-button" onClick={() => onCancel(item.appointment_id)} aria-label="Cancel appointment" title="Cancel">
            <X size={16} />
          </button>
        )}
      </div>
    </article>
  )
}

export default function StudentDashboard() {
  const { user } = useAuth()
  const [appointments, setAppointments] = useState([])
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState('')
  const [loading, setLoading] = useState(true)

  async function load() {
    setLoading(true)
    try {
      const data = await api.myAppointments()
      setAppointments(data)
      setError('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function cancel(id) {
    setBusyId(id)
    try { await api.decideAppointment(id, 'cancel'); await load() }
    catch (err) { setError(err.message) }
    finally { setBusyId('') }
  }

  const pending = appointments.filter((a) => a.status === 'PENDING_APPROVAL')
  const approved = appointments.filter((a) => a.status === 'APPROVED')
  const past = appointments.filter((a) => ['REJECTED', 'CANCELLED'].includes(a.status))

  return (
    <section className="page-content dashboard-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">STUDENT PORTAL</p>
          <h1>My Dashboard</h1>
          <p>Welcome back, <strong>{user?.name || 'Student'}</strong>. Here are your appointment requests.</p>
        </div>
        <button className="icon-button" onClick={load} aria-label="Refresh" title="Refresh">
          <RefreshCw size={16} />
        </button>
      </div>

      {/* Stats row */}
      <div className="dash-stats">
        <div className="stat-card">
          <span className="stat-number">{appointments.length}</span>
          <span className="stat-label">Total</span>
        </div>
        <div className="stat-card stat-pending">
          <span className="stat-number">{pending.length}</span>
          <span className="stat-label">Pending</span>
        </div>
        <div className="stat-card stat-approved">
          <span className="stat-number">{approved.length}</span>
          <span className="stat-label">Approved</span>
        </div>
      </div>

      {error && <p className="form-error">{error}</p>}

      {loading ? (
        <div className="loading-state"><RefreshCw size={16} /><span>Loading appointments…</span></div>
      ) : appointments.length === 0 ? (
        <div className="empty-state dashboard-empty">
          <CalendarClock size={32} />
          <div>
            <p><strong>No appointments yet</strong></p>
            <p>Go to the Chat to request a meeting with a professor.</p>
          </div>
        </div>
      ) : (
        <>
          {pending.length > 0 && (
            <section className="appointment-section">
              <div className="section-title">
                <Clock3 size={18} />
                <h2>Pending approval</h2>
                <span>{pending.length}</span>
              </div>
              <div className="appointment-list">
                {pending.map((item) => (
                  <AppointmentCard key={item.appointment_id} item={item} onCancel={cancel} isBusy={busyId === item.appointment_id} showActions={false} />
                ))}
              </div>
            </section>
          )}
          {approved.length > 0 && (
            <section className="appointment-section">
              <div className="section-title">
                <Check size={18} />
                <h2>Approved</h2>
                <span>{approved.length}</span>
              </div>
              <div className="appointment-list">
                {approved.map((item) => (
                  <AppointmentCard key={item.appointment_id} item={item} onCancel={cancel} isBusy={busyId === item.appointment_id} showActions={false} />
                ))}
              </div>
            </section>
          )}
          {past.length > 0 && (
            <section className="appointment-section">
              <div className="section-title">
                <CalendarClock size={18} />
                <h2>Past / Closed</h2>
                <span>{past.length}</span>
              </div>
              <div className="appointment-list">
                {past.map((item) => (
                  <AppointmentCard key={item.appointment_id} item={item} isBusy={busyId === item.appointment_id} showActions={false} />
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </section>
  )
}
