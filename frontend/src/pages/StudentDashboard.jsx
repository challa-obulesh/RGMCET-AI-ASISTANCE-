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

function AppointmentCard({ item, onCancel, isBusy }) {
  const canCancel = ['PENDING_APPROVAL', 'APPROVED'].includes(item.status)
  return (
    <article className={`appointment-row ${isBusy ? 'row-busy' : ''}`} style={{ display: 'block', padding: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '8px' }}>
        <div className="appointment-date">
          <strong>{formatDate(item.date)}</strong>
          <span>{item.start_time}–{item.end_time}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <StatusPill status={item.status} />
          {item.calendar_event_id && (
            <span className="calendar-sync-status" title="Synced to Google Calendar">
              <CalendarDays size={14} style={{ marginRight: '4px', verticalAlign: 'middle', color: '#4CAF50' }} />
              <small style={{ color: '#4CAF50' }}>Synced</small>
            </span>
          )}
          {canCancel && onCancel && (
            <button id={`cancel-${item.appointment_id}`} className="reject-button" onClick={() => onCancel(item.appointment_id)} aria-label="Cancel appointment" title="Cancel">
              <X size={16} />
            </button>
          )}
        </div>
      </div>

      <div style={{ marginTop: '10px', fontSize: '0.9rem' }}>
        <div><strong>Professor:</strong> {item.professor_name || 'Assigned Faculty'} {item.department ? `(${item.department})` : ''}</div>
        <div style={{ marginTop: '4px', color: '#4b5563' }}><strong>Purpose:</strong> {item.reason}</div>
      </div>

      <div style={{ marginTop: '10px', padding: '8px 12px', borderRadius: '6px', fontSize: '0.85rem', background: '#f8fafc', borderLeft: '3px solid #cbd5e1' }}>
        {item.status === 'PENDING_APPROVAL' && (
          <span style={{ color: '#b45309' }}>
            ⏳ <strong>PENDING PROFESSOR APPROVAL:</strong> Waiting for {item.professor_name || 'the professor'} to review your request.
          </span>
        )}
        {item.status === 'APPROVED' && (
          <span style={{ color: '#15803d' }}>
            ✓ <strong>Your appointment with {item.professor_name || 'the professor'} has been approved.</strong> Please be available at the scheduled time.
          </span>
        )}
        {item.status === 'REJECTED' && (
          <span style={{ color: '#b91c1c' }}>
            ✕ <strong>Request Rejected.</strong> {item.rejection_reason ? `Reason: ${item.rejection_reason}` : 'No reason provided.'}
          </span>
        )}
        {item.status === 'RESCHEDULED' && (
          <span style={{ color: '#0369a1' }}>
            🔄 <strong>Professor requested a new appointment time.</strong> Updated slot: {item.date} at {item.start_time}–{item.end_time}.
          </span>
        )}
        {item.status === 'CANCELLED' && (
          <span style={{ color: '#64748b' }}>
            ⊘ Appointment has been cancelled.
          </span>
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
