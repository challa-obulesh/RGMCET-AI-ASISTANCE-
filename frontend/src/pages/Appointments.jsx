import { useEffect, useState } from 'react'
import { CalendarClock, Check, Clock3, X } from 'lucide-react'
import { api } from '../services/api.js'
import { useAuth } from '../contexts/AuthContext.jsx'

function formatDate(value) {
  return new Date(`${value}T12:00:00`).toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' })
}

function AppointmentRow({ item, actions, onDecision, onCancel }) {
  const canCancel = ['PENDING_APPROVAL', 'APPROVED'].includes(item.status)
  return (
    <article className="appointment-row">
      <div className="appointment-date">
        <strong>{formatDate(item.date)}</strong>
        <span>{item.start_time}–{item.end_time}</span>
      </div>
      <div className="appointment-person">
        <strong>{item.professor_name}</strong>
        <span>{item.student_name || 'Student'} · {item.reason}</span>
      </div>
      <span className={`status-pill ${item.status === 'APPROVED' ? 'approved' : item.status === 'REJECTED' ? 'rejected' : item.status === 'CANCELLED' ? 'cancelled' : ''}`}>
        {item.status.replaceAll('_', ' ')}
      </span>
      {(actions || (canCancel && onCancel)) && (
        <div className="row-actions">
          {actions && (
            <>
              <button className="approve-button" onClick={() => onDecision(item.appointment_id, 'approve')} aria-label="Approve appointment"><Check size={16} /></button>
              <button className="reject-button" onClick={() => onDecision(item.appointment_id, 'reject')} aria-label="Reject appointment"><X size={16} /></button>
            </>
          )}
          {canCancel && onCancel && (
            <button className="reject-button" onClick={() => onCancel(item.appointment_id)} aria-label="Cancel appointment" title="Cancel appointment"><X size={16} /></button>
          )}
        </div>
      )}
    </article>
  )
}

export default function Appointments() {
  const { user } = useAuth()
  const [mine, setMine] = useState([])
  const [pending, setPending] = useState([])
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState('')

  async function load() {
    try {
      if (user && user.role === 'student') {
        // Authenticated student — GET /api/appointments uses JWT to filter by student
        const [own, queue] = await Promise.all([api.myAppointments(), api.pendingAppointments()])
        setMine(own)
        setPending(queue)
      } else if (user && user.role === 'professor') {
        // Professor view — show all pending for them to review
        const queue = await api.pendingAppointments()
        setMine([])
        setPending(queue)
      } else {
        // Demo / unauthenticated — fall back to all appointments list
        const [own, queue] = await Promise.all([api.myAppointments(), api.pendingAppointments()])
        setMine(own)
        setPending(queue)
      }
      setError('')
    } catch (exception) {
      setError(exception.message)
    }
  }

  useEffect(() => { load() }, [user])

  async function decide(id, action) {
    setBusyId(id)
    try { await api.decideAppointment(id, action); await load() } catch (exception) { setError(exception.message) } finally { setBusyId('') }
  }

  async function cancel(id) {
    setBusyId(id)
    try { await api.decideAppointment(id, 'cancel'); await load() } catch (exception) { setError(exception.message) } finally { setBusyId('') }
  }

  return (
    <section className="page-content appointments-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">MEETINGS & REQUESTS</p>
          <h1>Appointments</h1>
          <p>Requests stay pending until a professor reviews them.</p>
        </div>
      </div>
      {error && <p className="form-error">{error}</p>}
      <section className="appointment-section">
        <div className="section-title">
          <CalendarClock size={18} />
          <h2>My appointments</h2>
          <span>{mine.length}</span>
        </div>
        {mine.length
          ? <div className="appointment-list">
              {mine.map((item) => (
                <div className={busyId === item.appointment_id ? 'row-busy' : ''} key={item.appointment_id}>
                  <AppointmentRow item={item} onCancel={cancel} />
                </div>
              ))}
            </div>
          : <div className="quiet-empty"><Clock3 size={18} /><span>No appointments to show yet.</span></div>
        }
      </section>
      <section className="appointment-section">
        <div className="section-title">
          <Clock3 size={18} />
          <h2>Pending requests</h2>
          <span>{pending.length}</span>
        </div>
        {pending.length
          ? <div className="appointment-list">
              {pending.map((item) => (
                <div className={busyId === item.appointment_id ? 'row-busy' : ''} key={item.appointment_id}>
                  <AppointmentRow item={item} actions onDecision={decide} />
                </div>
              ))}
            </div>
          : <div className="quiet-empty"><Check size={18} /><span>No pending requests.</span></div>
        }
      </section>
    </section>
  )
}